import json
import re
import aiofiles


async def transform_db_xref(db_xref_str):
    """
    Transforms a db_xref string into an object with dynamic keys.

    Args:
        db_xref_str (str): A string containing database references, e.g.,
                           "CCDS:CCDS72675.1,Ensembl:ENSP00000409316.1,GeneID:729759".

    Returns:
        dict: An object where each database reference becomes a key-value pair.
    """
    if not db_xref_str:
        return {}

    db_xref_object = {}

    # Split the string by commas and process each key-value pair
    for ref in db_xref_str.split(','):
        if ':' in ref:  # Ensure the format is valid
            key, value = ref.split(':', 1)  # Split on the first colon
            db_xref_object[key] = value

    return db_xref_object


async def fna_to_json(fna_file_path, output_json_path):
    """
    Transforms an .fna file with multiple entries into JSON format.

    Args:
        fna_file_path (str): Path to the input .fna file.
        output_json_path (str): Path to save the JSON output.
    """
    entries = []

    # Regex to match the header details
    details_regex = re.compile(r"\[([a-zA-Z_]+)=([^\]]+)\]")

    try:
        # Read the input file asynchronously
        async with aiofiles.open(fna_file_path, mode='r') as file:
            content = await file.read()
            print("Content extracted...")
            records = content.strip().split('>')[1:]  # Split by '>' to isolate entries
            print("Records extracted...")

            for index, record in enumerate(records):
                print(f"Working on item {index}...")
                lines = record.strip().split('\n')
                header = lines[0]  # First line is the header
                sequence = "".join(lines[1:])  # Remaining lines are the sequence
                print(f"Header: {header}")
                print(f"Sequence extracted: {sequence[:30]}...")  # Display first 30 chars for brevity

                # Extract fields from the header using regex
                fields = {
                    key: value
                    for key, value in details_regex.findall(header)
                }
                print(f"Extracted fields: {fields}")

                # Construct the entry
                entry = {
                    "gene": fields.get("gene"),
                    "db_xrefs": await transform_db_xref(fields.get("db_xref")),
                    "protein": fields.get("protein"),
                    "protein_id": fields.get("protein_id"),
                    "location": fields.get("location"),
                    "gbkey": fields.get("gbkey"),
                    "sequence": sequence
                }
                entries.append(entry)

        # Write entries to JSON asynchronously
        async with aiofiles.open(output_json_path, mode='w') as json_file:
            await json_file.write(json.dumps(entries, indent=2))

        print(f"Transformation complete! JSON saved at {output_json_path}")
        return entries
    except Exception as e:
        print(f"Error occurred: {e}")
