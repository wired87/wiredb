import os


def get_unique_filename(path):
    """
    Generate a unique file path by appending an incrementing number
    if the file already exists.
    """
    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(path):
        path = f"{base}_{counter}{ext}"
        counter += 1
    return path