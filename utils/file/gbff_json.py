"""
GBFF (GenBank Flat File)
are hierarchical and contain detailed annotations about sequences, organized in a block-based format.
This structure is completely different from the tabular format of GFF/GTF.
"""
import json
from Bio import SeqIO

target=r"C:\Users\wired\OneDrive\Desktop\Projects\aws_to_bucket\extract_data\data\filtered_data\ncbi\ALLgrch38\gbff.json"
input=r"C:\Users\wired\OneDrive\Desktop\Projects\aws_to_bucket\extract_data\data\raw\ncbi\GRCh38(hs)\GCF_000001405.40\genomic.gbff"


def gbff_to_json(gbff_file_path=input, json_file_path=target):
    """
    Converts a GBFF file to JSON format and saves it locally.

    Parameters:
        gbff_file_path (str): Path to the input .gbff file.
        json_file_path (str): Path to save the output .json file.

    Returns:
        None
    """

    try:
        records = []
        with open(gbff_file_path, "r") as gbff_file:
            for record in SeqIO.parse(gbff_file, "genbank"):
                records.append(record.annotations)  # Add the full annotations dictionary

        with open(json_file_path, "w") as json_file:
            json.dump(records, json_file, indent=4)

        print(f"Converted GBFF admin_data saved to {json_file_path}")

    except Exception as e:
        print(f"Error while converting GBFF to JSON: {e}")


if __name__ == "__main__":
    gbff_to_json()
