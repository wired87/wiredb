import os
import json
import h5py
import numpy as np
from google.cloud import storage
import scipy.sparse

class H5ToJsonConverter:
    def __init__(self, h5_file, bucket_name="bestbrain"):
        self.h5_file = h5_file
        self.bucket_name = bucket_name
        self.storage_client = storage.Client()

    def _convert_h5_to_dict(self, h5_obj):
        """
        Converts an HDF5 file/group/dataset to a JSON-compatible Python dictionary.
        Handles large datasets, byte strings, and sparse matrices.
        """
        result = {}

        def visit(name, obj):
            if isinstance(obj, h5py.Dataset):  # If it's a dataset
                try:
                    # Handle small datasets fully, large datasets partially
                    if obj.size < 1000000:  # Limit full extraction for large datasets
                        data = obj[()]
                    else:
                        data = obj[:100]  # Extract only first 100 values

                    # Handle byte strings
                    if isinstance(data, np.ndarray) and data.dtype.kind in {'S', 'O'}:
                        result[name] = [item.decode('utf-8') if isinstance(item, bytes) else item for item in data.tolist()]
                    elif isinstance(data, bytes):
                        result[name] = data.decode('utf-8')
                    else:
                        result[name] = data.tolist()

                except MemoryError:
                    result[name] = f"[Large Dataset: {obj.shape}]"
                except Exception as e:
                    result[name] = f"[Error reading dataset: {e}]"

            elif isinstance(obj, h5py.Group):  # If it's a group (folder)
                result[name] = {}

        h5_obj.visititems(visit)

        # Handle AnnData sparse matrices (if in h5ad format)
        if "X" in h5_obj.keys():
            try:
                sparse_data = h5_obj["X"]
                if isinstance(sparse_data, h5py.Dataset):
                    sparse_data = sparse_data[()]
                    if scipy.sparse.issparse(sparse_data):  # Convert sparse matrix to dense
                        result["X"] = sparse_data.toarray().tolist()
                    else:
                        result["X"] = sparse_data.tolist()
            except Exception as e:
                result["X"] = f"[Error processing sparse matrix: {e}]"

        return result

    def convert(self, output_json_file):
        """Converts an HDF5 file to JSON and uploads it to GCS."""
        with h5py.File(self.h5_file, 'r') as f:
            data_dict = self._convert_h5_to_dict(f)

        # Write JSON with UTF-8 encoding and ensure all admin_data is serializable
        with open(output_json_file, 'w', encoding="utf-8") as json_file:
            json.dump(data_dict, json_file, ensure_ascii=False, indent=2)

        print(f"✅ JSON file saved: {output_json_file}")
        self.upload_to_gcs(output_json_file)

    def upload_to_gcs(self, source_file_name):
        """Uploads a file to Google Cloud Storage."""
        bucket = self.storage_client.bucket(self.bucket_name)
        blob = bucket.blob(os.path.basename(source_file_name))
        blob.upload_from_filename(source_file_name)
        print(f"✅ Uploaded {source_file_name} to gs://{self.bucket_name}/{os.path.basename(source_file_name)}")

def download_from_gcs(bucket_name, source_blob_name, destination_file_name):
    """Efficiently downloads a file from Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
    print(f"✅ Downloaded gs://{bucket_name}/{source_blob_name} to {destination_file_name}")

# Example Usage
if __name__ == "__main__":
    file_name = "non_neuronal_brain.h5ad"

    converter = H5ToJsonConverter(r"C:\Users\wired\Downloads\train_data_cell_non_neuronal_cells.h5ad", "bestbrain")
    json_output_file = rf"C:\Users\wired\OneDrive\Desktop\Projects\bm\data\files\{file_name.replace('.h5ad', '.json')}"

    converter.convert(json_output_file)
