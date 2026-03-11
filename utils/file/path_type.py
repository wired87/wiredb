import os


def check_path_type(path):
    if os.path.isdir(path):
        return "Directory"
    elif os.path.isfile(path):
        return "File"
    else:
        return "Path does not exist"