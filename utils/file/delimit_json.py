import json

def delimit_json(input_file, output_file):
    """
    Delimits JSON for BigQuery compatibility:
    - Ensures objects are properly flattened and arrays are preserved.
    - Saves the delimited JSON to the output file.

    Args:
        input_file (str): Path to the input JSON file.
        output_file (str): Path to the output JSON file.
    """
    def flatten_dict(d, parent_key='', sep='__'):
        """Flatten nested dictionaries, maintaining arrays as-is."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def process_json(obj):
        """Process each JSON object (dictionary or list)."""
        if isinstance(obj, dict):
            return flatten_dict(obj)
        elif isinstance(obj, list):
            return [process_json(item) if isinstance(item, dict) else item for item in obj]
        return obj  # For other types, return as-is.

    with open(input_file, 'r') as infile:
        data = json.load(infile)

    if isinstance(data, list):
        # Process each object in the array
        delimited_data = [process_json(item) for item in data]
    else:
        # Process single JSON object
        delimited_data = [process_json(data)]

    with open(output_file, 'w') as outfile:
        json.dump(delimited_data, outfile, indent=2)
        print(f"Delimited JSON saved to {output_file}")
