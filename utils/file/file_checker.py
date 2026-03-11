import io
import json
import chardet
import gzip
import tarfile
import zipfile
import pandas as pd
from PIL import Image


def dynamic_file_to_csv(file_type, ds_content, key=None):
    """
    Dynamically converts various dataset formats (JSON, CSV, Excel, Text, TSV, Parquet, TIF, BAM, GZ, ZIP) into CSV format.

    Args:
        file_type (str): The type of the input file (e.g., "json", "csv", "excel", "text", "tsv", "parquet", "tif", "bam", "gz").
        ds_content (bytes | str): The dataset content as bytes or a string.
        key (str, optional): Key for JSON normalization.

    Returns:
        str: CSV admin_data as a string, or None if an error occurs.
    """
    try:
        file_type = file_type.lower()  # Normalize file type

        # Convert JSON to CSV (text-based processing)
        if file_type == "json":
            try:
                if isinstance(ds_content, bytes):
                    encoding = chardet.detect(ds_content)['encoding']
                    ds_content = ds_content.decode(encoding or 'utf-8', errors='replace')

                data = json.loads(ds_content)
                if isinstance(data, dict):  # Convert single object to a list
                    data = [data]
                df = pd.json_normalize(data, sep="_")
            except json.JSONDecodeError:
                return None, "Invalid JSON format"

        # Convert CSV
        elif file_type == "csv":
            try:
                if isinstance(ds_content, bytes):
                    ds_content = ds_content.decode('utf-8', errors='replace')

                df = pd.read_csv(io.StringIO(ds_content))
            except pd.errors.ParserError:
                return None, "Invalid CSV format"

        # Convert Excel (XLSX)
        elif file_type in ["excel", "xlsx", "xls"]:
            try:
                df = pd.read_excel(io.BytesIO(ds_content), engine='openpyxl')
            except Exception as e:
                return None, f"Error reading Excel file: {e}"

        # Convert TSV
        elif file_type == "tsv":
            try:
                if isinstance(ds_content, bytes):
                    ds_content = ds_content.decode('utf-8', errors='replace')

                df = pd.read_csv(io.StringIO(ds_content), sep='\t')
            except pd.errors.ParserError:
                return None, "Invalid TSV format"

        # Convert Text (auto-detect separator)
        elif file_type == "text":
            try:
                if isinstance(ds_content, bytes):
                    ds_content = ds_content.decode('utf-8', errors='replace')

                df = pd.read_csv(io.StringIO(ds_content), sep=None, engine='python')
            except pd.errors.ParserError:
                return None, "Invalid text format"

        # Convert Parquet
        elif file_type == "parquet":
            try:
                df = pd.read_parquet(io.BytesIO(ds_content))
            except Exception as e:
                return None, f"Error reading Parquet file: {e}"

        # Convert TIF (extract metadata)
        elif file_type in ["tif", "tiff"]:
            try:
                with Image.open(io.BytesIO(ds_content)) as img:
                    metadata = img.info
                df = pd.DataFrame([metadata])
            except Exception as e:
                return None, f"Error reading TIF file: {e}"

            """# Convert BAM (extract read statistics)
            elif file_type == "bam":
                try:
                    bamfile = htseq.BAM_Reader(io.BytesIO(ds_content))
                    records = []
                    for read in bamfile:
                        records.append({
                            "QNAME": read.read.name,
                            "FLAG": read.flag,
                            "RNAME": read.iv.chrom if read.iv is not None else None,
                            "POS": read.iv.start if read.iv is not None else None,
                            "MAPQ": read.aQual,  # Analogous to `mapping_quality`
                            "CIGAR": read.cigar if read.cigar is not None else None
                        })
                    df = pd.DataFrame(records)
                    return df, None
                except Exception as e:
                    return None, f"Error processing BAM file: {e}"""

        # Handle compressed files (GZ, TAR, ZIP) - Keep binary mode
        elif file_type in ["gz", "tar.gz", "tar", "zip"]:
            extracted_data = []

            if file_type == "gz":
                try:
                    with gzip.open(io.BytesIO(ds_content), "rb") as f:
                        extracted_content = f.read()
                    extracted_data.append(dynamic_file_to_csv("txt", extracted_content, key))
                except Exception as e:
                    return None, f"Error extracting GZ file: {e}"

            elif file_type in ["tar.gz", "tar"]:
                try:
                    with tarfile.open(fileobj=io.BytesIO(ds_content), mode="r:gz") as tar:
                        for member in tar.getmembers():
                            if member.isfile():
                                extracted_file = tar.extractfile(member).read()
                                file_ext = member.name.split('.')[-1]
                                csv_data = dynamic_file_to_csv(file_ext, extracted_file, key)
                                if csv_data:
                                    extracted_data.append(csv_data)
                except Exception as e:
                    return None, f"Error extracting TAR file: {e}"

            elif file_type == "zip":
                try:
                    with zipfile.ZipFile(io.BytesIO(ds_content), "r") as zip_ref:
                        for file_name in zip_ref.namelist():
                            with zip_ref.open(file_name) as f:
                                extracted_file = f.read()
                                file_ext = file_name.split('.')[-1]
                                csv_data = dynamic_file_to_csv(file_ext, extracted_file, key)
                                if csv_data:
                                    extracted_data.append(csv_data)
                except Exception as e:
                    return None, f"Error extracting ZIP file: {e}"

            return "\n".join(extracted_data) if extracted_data else None

        # Unsupported file type
        else:
            return None, f"Unsupported file type: {file_type}"

        if df.empty:
            return None, "Converted DataFrame is empty!"

        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        cols = df.columns
        print("Cols set:", list(cols))
        return csv_buffer.getvalue()

    except Exception as e:
        print(f"Error in dynamic_file_to_csv: {e}")
        return None
