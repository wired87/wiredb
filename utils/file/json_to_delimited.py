import json


def convert_json_to_ndjson(input_file, output_file):
    """
    Converts a standard JSON file (array of objects) into newline-delimited JSON (NDJSON).

    Args:
        input_file (str): Path to the input JSON file.
        output_file (str): Path to save the output NDJSON file.

    Returns:
        None
    """
    try:
        # Read the JSON array from the input file
        with open(input_file, "r", encoding="utf-8") as infile:
            data = json.load(infile)

        # Ensure the input is a list of objects
        if not isinstance(data, list):
            raise ValueError("Input JSON must be an array of objects.")

        # Write each object as a new line in the NDJSON file
        with open(output_file, "w", encoding="utf-8") as outfile:
            for record in data:
                json.dump(record, outfile)  # Serialize JSON object
                outfile.write("\n")  # Add a newline after each object

        print(f"Successfully converted JSON to NDJSON: {output_file}")

    except Exception as e:
        print(f"Error processing file: {e}")


if __name__ == "__main__":
    convert_json_to_ndjson(
        input_file=r"C:\Users\wired\OneDrive\Desktop\Projects\aws_to_bucket\extract_data\data\filtered_data\checkpoints\eco.json",
        output_file=r"C:\Users\wired\OneDrive\Desktop\Projects\aws_to_bucket\extract_data\data\filtered_data\checkpoints\delimited\eco.json"
    )