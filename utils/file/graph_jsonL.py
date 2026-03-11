import json
import networkx as nx
from google.cloud import storage
from tqdm import tqdm

# Constants
CHUNK_SIZE = 9 * 1024 * 1024  # 9MB
BUCKET_NAME = "bestbrain"  # Change to your GCS bucket name
OUTPUT_FOLDER = "model_graph/train_data/jsonl/go_term/"  # Folder in GCS


def load_graph_from_json(json_path):
    """Loads a networkx graph from a JSON file."""
    with open(json_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)
    return nx.node_link_graph(graph_data)  # Converts JSON to a NetworkX graph


def graph_to_jsonl(graph, metadata):
    """Converts a NetworkX graph to JSONL format with custom metadata."""
    jsonl_data = []

    # Convert nodes
    for node, data in graph.nodes(data=True):
        node_entry = {"type": "node", "id": node, "attributes": data, "metadata": metadata}
        jsonl_data.append(json.dumps(node_entry))

    # Convert edges
    for source, target, data in graph.edges(data=True):
        edge_entry = {"type": "edge", "source": source, "target": target, "attributes": data, "metadata": metadata}
        jsonl_data.append(json.dumps(edge_entry))

    return jsonl_data


def chunk_data(jsonl_data):
    """Splits JSONL admin_data into 9MB chunks."""
    chunks = []
    current_chunk = []
    current_size = 0

    for line in jsonl_data:
        line_size = len(line.encode("utf-8"))
        if current_size + line_size > CHUNK_SIZE:
            chunks.append(current_chunk)
            current_chunk = []
            current_size = 0
        current_chunk.append(line)
        current_size += line_size

    if current_chunk:
        chunks.append(current_chunk)  # Add remaining chunk

    return chunks


def upload_to_gcs(chunks, bucket_name, folder):
    """Uploads each chunk to Google Cloud Storage."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    for i, chunk in tqdm(enumerate(chunks), total=len(chunks), desc="Uploading to GCS"):
        chunk_filename = f"{folder}graph_chunk_{i}.jsonl"
        blob = bucket.blob(chunk_filename)
        blob.upload_from_string("\n".join(chunk), content_type="application/jsonl")
        print(f"Uploaded: {chunk_filename}")


def main(json_graph_path, metadata):
    """Processes a NetworkX graph and uploads it to Google Cloud Storage."""
    graph = load_graph_from_json(json_graph_path)
    jsonl_data = graph_to_jsonl(graph, metadata)
    chunks = chunk_data(jsonl_data)
    upload_to_gcs(chunks, BUCKET_NAME, OUTPUT_FOLDER)


if __name__ == "__main__":
    graph_path = r"/main_ckpt/sne/go_term.json"  # Path to your input graph JSON file
    custom_metadata = {"type": "Gene Ontology Entry", "timestamp": "2025-02-13"}  # Example metadata
    main(graph_path, custom_metadata)
