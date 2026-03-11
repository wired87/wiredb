import asyncio
import json

import httpx
from tqdm import tqdm



def extract_tree(d, indent=0):
    """Recursively extracts and prints the tree of a nested dictionary."""
    if isinstance(d, dict):
        for key, value in d.items():
            print("  " * indent + str(key))  # Print the key with indentation
            extract_tree(value, indent + 1)  # Recur for nested structures
    elif isinstance(d, list):
        print("  " * indent + "[0]")  # Always annotate the first entry only
        extract_tree(d[0], indent + 1)
    else:
        print("  " * indent + str(d))

async def download_json_content(url, j=True, save=False):
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url) as response:
            # Check if the response is successful
            if response.status_code != 200:
                print(f"Failed to download JSON: {response.status_code}")
                return None
            total_size = int(response.headers.get("content-length", 0))
            print(f"File size: {total_size}")
            progress = tqdm(total=total_size, unit="B", unit_scale=True, desc="Downloading JSON")
            print("Downloading JSON", progress)
            # Gather content
            content = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=1024):
                content.extend(chunk)
                progress.update(len(chunk))

            progress.close()

            # Decode JSON content
            try:
                if j:
                    content = json.loads(content.decode('utf-8'))  # Parse JSON
                    #print("JSON content", json_content)
                    if save:
                        file_path = url.split("/")[-1]
                        r"""      await asave_data_checkpoint(
                            rf"C:\Users\wired\OneDrive\Desktop\Projects\pythonProject\data\{file_path}",
                            content)"""
                else:
                    content = content.decode('utf-8')
                return content
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {e}")
                return None

if __name__ == "__main__":
    url="https://www.encodeproject.org/report/?type=Experiment&status=released&control_type%21=%2A&replicates.library.biosample.donor.organism.scientific_name=Homo+sapiens&biosample_ontology.organ_slims=brain&limit=all"
    data = asyncio.run(download_json_content(url))
    print(extract_tree(data))