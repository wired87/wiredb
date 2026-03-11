import os
from urllib.parse import urlparse


def get_filename_without_extension(url):
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)  # Extract filename with extension
    name_without_ext = os.path.splitext(filename)[0]  # Remove extension
    return name_without_ext