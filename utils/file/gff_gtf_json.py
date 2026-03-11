"""
General feature Format to Json

describe the features of biological sequences, such as genes, exons, and regulatory elements.
It provides a standardized way to annotate sequences and is widely used for genomic admin_data.
"""
import json
from pathlib import Path

target = r"C:\Users\wired\OneDrive\Desktop\Projects\aws_to_bucket\extract_data\data\filtered_data\ncbi\ALLgrch38\gtf.json"
src=r"C:\Users\wired\OneDrive\Desktop\Projects\aws_to_bucket\extract_data\data\raw\ncbi\GRCh38(hs)\GCF_000001405.40\genomic.gtf"


def gff_gtf_to_json(file_path=src, json_file_path=target):

    try:
        gff_data = []

        with open(file_path, 'r') as file:
            file_type = Path(file_path).suffix.lower()
            print(f"Recognized {file_type}")
            for line in file:
                # Skip comments and empty lines
                if line.startswith("#") or not line.strip():
                    continue

                # Split the line into columns
                columns = line.strip().split('\t')

                if len(columns) < 9:
                    continue  # Skip malformed lines

                # Parse the GFF fields into a dictionary
                entry = {
                    "seqid": columns[0],
                    "source": columns[1],
                    "type": columns[2],
                    "start": int(columns[3]),
                    "end": int(columns[4]),
                    "score": columns[5] if columns[5] != '.' else None,
                    "strand": columns[6],
                    "phase": columns[7] if columns[7] != '.' else None,
                    "attributes": parse_attributes(columns[8], file_type)
                }

                gff_data.append(entry)

        # Save the parsed admin_data as a JSON file
        with open(json_file_path, 'w') as json_file:
            json.dump(gff_data, json_file, indent=4)

        print(f"Converted {file_type} admin_data saved to {json_file_path}")

    except Exception as e:
        print(f"Error while converting GFF to JSON: {e}")

def parse_attributes(attribute_string, file_type):
    """
    Parses the attributes field of a GFF entry into a dictionary.

    Parameters:
        attribute_string (str): The attributes string from the GFF file.

    Returns:
        dict: Parsed attributes as key-value pairs.
    """
    if file_type == ".gff":
        attributes = {}
        for attribute in attribute_string.split(';'):
            if "=" in attribute:
                key, value = attribute.split('=', 1)
                attributes[key.strip()] = value.strip()
        return attributes
    elif file_type == ".gtf":

        attributes = {}
        for attribute in attribute_string.split(';'):
            if attribute.strip():
                key, value = attribute.strip().split(' ', 1)
                attributes[key.strip()] = value.strip().strip('"')
        return attributes

if __name__ == "__main__":
    gff_gtf_to_json()
