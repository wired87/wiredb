from ftplib import FTP, error_perm
from google.cloud import storage
import io


def check_ftp_connection(ftp_url):
    """
    Checks if the FTP server is reachable.

    Parameters:
        ftp_url (str): FTP site URL.

    Returns:
        bool: True if the connection is successful, False otherwise.
    """
    try:
        ftp = FTP(ftp_url, timeout=10)
        ftp.login()  # Anonymous login
        ftp.quit()
        print(f"✅ Successfully connected to FTP: {ftp_url}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to FTP: {ftp_url}\nError: {e}")
        return False


def check_gcs_connection(bucket_name):
    """
    Checks if the Google Cloud Storage bucket is reachable.

    Parameters:
        bucket_name (str): GCS bucket name.

    Returns:
        bool: True if the bucket is accessible, False otherwise.
    """
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        if bucket.exists():
            print(f"✅ Successfully connected to GCS bucket: {bucket_name}")
            return True
        else:
            print(f"❌ GCS bucket does not exist: {bucket_name}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to GCS bucket: {bucket_name}\nError: {e}")
        return False


def list_ftp_files(ftp, directory):
    """
    Recursively lists all files in an FTP directory, including nested directories.

    Parameters:
        ftp (FTP): Active FTP connection.
        directory (str): Directory path to traverse.

    Returns:
        List of file paths.
    """
    files = []
    try:
        ftp.cwd(directory)
        items = ftp.nlst()

        for item in items:
            full_path = f"{directory}/{item}"
            try:
                ftp.cwd(full_path)  # If successful, it's a directory
                files.extend(list_ftp_files(ftp, full_path))  # Recurse
                ftp.cwd("..")  # Go back up
            except error_perm:
                # If it fails, it's a file
                files.append(full_path)

        return files
    except Exception as e:
        print(f"❌ Error listing files in {directory}: {e}")
        return []


def upload_file_to_gcs(ftp, file_path, bucket):
    """
    Fetches a file from FTP and uploads it directly to Google Cloud Storage.

    Parameters:
        ftp (FTP): Active FTP connection.
        file_path (str): Full path of the file in FTP.
        bucket (google.cloud.storage.Bucket): GCS bucket object.
    """
    try:
        file_stream = io.BytesIO()
        ftp.retrbinary(f"RETR {file_path}", file_stream.write)
        file_stream.seek(0)  # Reset pointer

        # Define blob path inside the bucket
        blob = bucket.blob(file_path.lstrip('/'))  # Remove leading '/'
        blob.upload_from_file(file_stream, content_type="application/octet-stream")

        print(f"✅ Uploaded: {file_path} to GCS bucket {bucket.name}")
    except Exception as e:
        print(f"❌ Failed to upload {file_path} to GCS: {e}")


def ftp_to_gcs(ftp_url, ftp_directory, gcs_bucket_name):
    """
    Traverses all files in an FTP directory (including nested folders) and uploads them to Google Cloud Storage.

    Parameters:
        ftp_url (str): FTP site URL.
        ftp_directory (str): Directory path on the FTP server.
        gcs_bucket_name (str): Name of the GCS bucket.
    """
    # **Status Check: FTP and GCS**
    if not check_ftp_connection(ftp_url) or not check_gcs_connection(gcs_bucket_name):
        print("❌ Aborting: Connection issues detected.")
        return

    try:
        # Connect to FTP
        ftp = FTP(ftp_url, timeout=10)
        ftp.login()

        # Initialize GCS client
        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)

        # Fetch all files recursively
        print(f"📂 Scanning FTP directory: {ftp_directory}")
        all_files = list_ftp_files(ftp, ftp_directory)

        if not all_files:
            print("⚠️ No files found for upload.")
            return

        print(f"📦 Found {len(all_files)} files to upload. Starting upload process...")

        # Upload each file
        for idx, file in enumerate(all_files, start=1):
            print(f"🚀 Uploading {idx}/{len(all_files)}: {file}")
            upload_file_to_gcs(ftp, file, bucket)

        # Close FTP connection
        ftp.quit()
        print("🎉 All files uploaded successfully to GCS!")

    except Exception as e:
        print(f"❌ Error during FTP to GCS transfer: {e}")


if __name__ == "__main__":
    # Usage Example
    ftp_to_gcs('ftp.ncbi.nlm.nih.gov', '/dbgap/studies/', 'bestbrain')
