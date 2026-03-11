import json

def fasta_to_json(fasta_file, output_json_file):
    """
    Converts the contents of a FASTA file (like .fna) to a JSON file.

    Parameters:
        fasta_file (str): Path to the input FASTA file.
        output_json_file (str): Path to save the output JSON file.
    """
    try:
        fasta_dict = {}
        current_sequence_id = None
        current_sequence = []
        current_metadata = ""

        # Read the FASTA file line by line
        with open(fasta_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith(">"):  # Sequence ID line
                    # Save the previous sequence, if exists
                    if current_sequence_id:
                        fasta_dict[current_sequence_id] = {
                            'sequence': ''.join(current_sequence).replace('N', 'unknown'),
                            'metadata': current_metadata
                        }

                    # Start a new sequence
                    parts = line[1:].split(" ", 1)  # Split at first space: sequence ID and description
                    current_sequence_id = parts[0]  # The sequence ID is before the first space
                    current_metadata = parts[1] if len(parts) > 1 else ""  # The description comes after
                    current_sequence = []  # Reset sequence for the new entry
                else:
                    # Append the sequence admin_data (nucleotide sequence)
                    current_sequence.append(line)

            # Save the last sequence after exiting the loop
            if current_sequence_id:
                fasta_dict[current_sequence_id] = {
                    'sequence': ''.join(current_sequence).replace('N', 'unknown'),
                    'metadata': current_metadata
                }

        # Write the dictionary to a JSON file with nested structure
        with open(output_json_file, 'w') as json_file:
            json.dump(fasta_dict, json_file, indent=4)

        print(f"FASTA content has been successfully converted to JSON and saved to {output_json_file}")

    except Exception as e:
        print(f"An error occurred: {e}")


fasta_file = r"C:\Users\wired\OneDrive\Desktop\Projects\aws_to_bucket\extract_data\data\raw\ncbi\GRCh38(hs)\GCF_000001405.40\rna.fna"
output_json_file = r"C:\Users\wired\OneDrive\Desktop\Projects\aws_to_bucket\extract_data\data\filtered_data\ncbi\ALLgrch38\rna.json"  # Path to save the JSON output

if __name__ == "__main__":
    fasta_to_json(fasta_file, output_json_file)
