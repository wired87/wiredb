import os

from extract_data.functions.read_json_content import read_json_content


def check_ds_exists(path):
    print("Check for existing admin_data...")
    if os.path.exists(path):
        content = read_json_content(path=path)
        print("Content exists, extract...")
        return content