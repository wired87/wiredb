import json
import os

import boto3


def convert_json_to_jsonl(json_file_path, jsonl_file_path):
    def write_file(data):
        stuff_to_loop = []
        if isinstance(data, list):
            stuff_to_loop = data
        else:
            for key, value in data.items():
                stuff_to_loop.append({key: value})
        return stuff_to_loop
    try:
        # Load the JSON admin_data
        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)

        # Open the JSONL file for writing
        with open(jsonl_file_path, 'w') as jsonl_file:
            # If the JSON is a list, write each item as a line
            if isinstance(data, list):
                for item in write_file(data):
                    jsonl_file.write(json.dumps(item) + '\n')
            else:
                raise ValueError("Input JSON file must contain a list of objects.")

        print(f"Successfully converted {json_file_path} to {jsonl_file_path}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if os.name == 'nt':
        in_dir = r"C:\Users\wired\OneDrive\Desktop\Projects\aws_to_bucket\extract_data\data\filtered_data\final"
        out_dir = r"C:\Users\wired\OneDrive\Desktop\Projects\aws_to_bucket\extract_data\data\filtered_data\delimited"
        for item in os.listdir(in_dir):
            print(item)
            out_file = rf"{out_dir}\{item}l"
            in_file = rf"{in_dir}\{item}"
            if not os.path.exists(out_file) and os.path.exists(in_file):
                convert_json_to_jsonl(in_file, out_file)
    else:
        in_dir = ""
        print("AWS instance recognized...")
        in_file_name = "uniprotkb_9606.json"
        in_file = rf"/home/ec2-user/work/{in_file_name}"
        out_file = f"{in_file}l"
        convert_json_to_jsonl(in_file, out_file)
        # Load environment variables from the .env file
        ACCESS_ID = "fun"
        SECRET_KEY = "fun"
        REGION = "eu-central-1"
        BUCKET = "genexfabric"

        # Access environment variables
        aws_access_key_id = ACCESS_ID
        aws_secret_access_key = SECRET_KEY
        region_name = REGION
        bucket_name = BUCKET
        s3 = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )
        s3.upload_file(
            Filename=f"{in_file_name}l",  # Local file name
            Bucket=bucket_name,  # S3 bucket name
            Key=f"{bucket_name}/{in_file_name}l",  # S3 key (path in the bucket)
        )

