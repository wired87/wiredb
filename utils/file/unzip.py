import zipfile
import os

def unzip_file(zip_filepath, extract_to_dir):
    """Checks if a file is a zip file and unzips it.

    Args:
        zip_filepath: Path to the zip file.
        extract_to_dir: Directory to extract the contents to.

    Returns:
        True if the file was a zip file and successfully unzipped, False otherwise.
        Also returns an error message as a second value if something went wrong.
    """
    try:
        if not zipfile.is_zipfile(zip_filepath):
            return False, "Not a zip file"

        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            try:
                zip_ref.extractall(extract_to_dir)
                return True, ""  # Success!
            except Exception as e:
                return False, f"Extraction error: {e}"

    except FileNotFoundError:
        return False, "File not found."
    except zipfile.BadZipFile:
        return False, "Corrupted zip file"
    except Exception as e:  # Catch other potential exceptions
        return False, f"An unexpected error occurred: {e}"



def process_archive(filepath, extract_to_dir):
    """Processes a file, attempting to unzip or handle other archive types.

    Args:
        filepath: Path to the file.
        extract_to_dir: Directory to extract contents to (if applicable).

    Returns:
       True, "" on success, False, "error message" on failure.
    """

    filename, ext = os.path.splitext(filepath)  # Split filename and extension

    try:
        if ext.lower() == ".zip" or ext.lower() == ".zipx":
            return unzip_file(filepath, extract_to_dir)  # Handles .zip and .zipx
        elif ext.lower() == ".gz" or ext.lower() == ".tgz":
            return extract_gzip(filepath, extract_to_dir) # Handles .gz and .tgz
        elif ext.lower() == ".bz2" or ext.lower() == ".tbz":
            return extract_bzip2(filepath, extract_to_dir)  # Handles .bz2 and .tbz
        elif ext.lower() == ".xz":
            return extract_xz(filepath, extract_to_dir)  # Handles .xz
        elif ext.lower() == ".7z":
            return extract_7z(filepath, extract_to_dir) # Handles .7z
        elif ext.lower() == ".tar":
            return extract_tar(filepath, extract_to_dir) #Handles .tar (no decompression)
        elif ext.lower() == ".rar":
            return extract_rar(filepath, extract_to_dir) # Handles .rar
        elif ext.lower() == ".cbr" or ext.lower() == ".cbz":
            return unzip_file(filepath, extract_to_dir) # treats like a zip
        elif ext.lower() == ".jar" or ext.lower() == ".war" or ext.lower() == ".ear":
            return unzip_file(filepath, extract_to_dir) # treats like a zip
        # Add more elif conditions for other extensions as needed
        else:
            return False, "Unsupported archive type"

    except Exception as e:
        return False, f"A general error occurred: {e}"


def unzip_file(zip_filepath, extract_to_dir):
    # (Implementation from previous response)
    try:
        if not zipfile.is_zipfile(zip_filepath):
            return False, "Not a zip file"

        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            try:
                zip_ref.extractall(extract_to_dir)
                return True, ""  # Success!
            except Exception as e:
                return False, f"Extraction error: {e}"

    except FileNotFoundError:
        return False, "File not found."
    except zipfile.BadZipFile:
        return False, "Corrupted zip file"
    except Exception as e:  # Catch other potential exceptions
        return False, f"An unexpected error occurred: {e}"

# Placeholder functions (you'll need to implement these based on the libraries you use)
def extract_gzip(filepath, extract_to_dir):
    try:
        import gzip
        with gzip.open(filepath, 'rb') as f_in, open(os.path.join(extract_to_dir, os.path.splitext(os.path.basename(filepath))[0]), 'wb') as f_out: #Extracts to filename without extension
            f_out.writelines(f_in)
        return True, ""
    except Exception as e:
        return False, f"Gzip extraction error: {e}"

def extract_bzip2(filepath, extract_to_dir):
    try:
        import bz2
        with bz2.open(filepath, 'rb') as f_in, open(os.path.join(extract_to_dir, os.path.splitext(os.path.basename(filepath))[0]), 'wb') as f_out: #Extracts to filename without extension
            f_out.writelines(f_in)
        return True, ""
    except Exception as e:
        return False, f"Bzip2 extraction error: {e}"

def extract_xz(filepath, extract_to_dir):
    try:
        import lzma #Python 3.3+
        with lzma.open(filepath, 'rb') as f_in, open(os.path.join(extract_to_dir, os.path.splitext(os.path.basename(filepath))[0]), 'wb') as f_out: #Extracts to filename without extension
            f_out.writelines(f_in)
        return True, ""
    except Exception as e:
        return False, f"XZ extraction error: {e}"

def extract_7z(filepath, extract_to_dir):
    try:
        import py7zr #Install with: pip install py7zr
        with py7zr.SevenZipFile(filepath, mode='r') as z:
            z.extractall(path=extract_to_dir)
        return True, ""
    except Exception as e:
        return False, f"7z extraction error: {e}"

def extract_tar(filepath, extract_to_dir):
    try:
        import tarfile
        with tarfile.open(filepath, 'r') as tar:
            tar.extractall(path=extract_to_dir)
        return True, ""
    except Exception as e:
        return False, f"Tar extraction error: {e}"

def extract_rar(filepath, extract_to_dir):
    try:
        import patool #Install with: pip install patool
        import shutil
        patool.extract_archive(filepath, outdir=extract_to_dir)
        return True, ""
    except Exception as e:
        return False, f"RAR extraction error: {e}"



