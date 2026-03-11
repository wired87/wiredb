import json
import networkx as nx
from google.cloud import storage
from tqdm import tqdm

from qbrain.utils.file import CHUNK_SIZE, BUCKET_NAME, OUTPUT_FOLDER


def load_graph_from_json(json_path):
    """Loads a networkx graph from a JSON file."""
    with open(json_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)
    return nx.node_link_graph(graph_data)  # Converts JSON to a NetworkX graph


def graph_to_json(graph, metadata):
    """Converts a NetworkX graph to a JSON structure with custom metadata."""
    graph_json = {
        "nodes": [],
        "EDGES": []
    }

    # Convert nodes (preserving structure)
    for node, data in graph.nodes(data=True):
        data["id"] = node  # Ensure node ID is included
        data["metadata"] = metadata  # Attach metadata
        graph_json["nodes"].append(data)

    # Convert edges (preserving structure)
    for source, target, data in graph.edges(data=True):
        data["source"] = source
        data["target"] = target
        data["metadata"] = metadata  # Attach metadata
        graph_json["EDGES"].append(data)

    return graph_json


def chunk_data(graph_json):
    """Splits JSON admin_data into 9MB chunks while keeping valid JSON structure."""
    json_str = json.dumps(graph_json)  # Convert entire graph to string
    json_bytes = json_str.encode("utf-8")

    chunks = []
    current_size = 0
    current_chunk = {"nodes": [], "EDGES": []}

    for node in graph_json["nodes"]:
        node_size = len(json.dumps(node).encode("utf-8"))
        if current_size + node_size > CHUNK_SIZE:
            chunks.append(current_chunk)
            current_chunk = {"nodes": [], "EDGES": []}
            current_size = 0
        current_chunk["nodes"].append(node)
        current_size += node_size

    for edge in graph_json["EDGES"]:
        edge_size = len(json.dumps(edge).encode("utf-8"))
        if current_size + edge_size > CHUNK_SIZE:
            chunks.append(current_chunk)
            current_chunk = {"nodes": [], "EDGES": []}
            current_size = 0
        current_chunk["EDGES"].append(edge)
        current_size += edge_size

    if current_chunk["nodes"] or current_chunk["EDGES"]:
        chunks.append(current_chunk)

    return chunks


def upload_to_gcs(chunks, bucket_name, folder):
    """Uploads each JSON chunk to Google Cloud Storage as a JSON file."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    for i, chunk in tqdm(enumerate(chunks), total=len(chunks), desc="Uploading to GCS"):
        chunk_filename = f"{folder}graph_chunk_{i}.json"
        blob = bucket.blob(chunk_filename)
        blob.upload_from_string(json.dumps(chunk, indent=4), content_type="application/json")
        print(f"Uploaded: {chunk_filename}")


def main(json_graph_path, metadata):
    """Processes a NetworkX graph and uploads it to Google Cloud Storage as JSON chunks."""
    graph = load_graph_from_json(json_graph_path)
    graph_json = graph_to_json(graph, metadata)
    chunks = chunk_data(graph_json)
    upload_to_gcs(chunks, BUCKET_NAME, OUTPUT_FOLDER)


if __name__ == "__main__":
    graph_path = r"/main_ckpt/sne/go_term.json"  # Path to your input graph JSON file
    custom_metadata = {"type": "Gene Ontology Entry", "timestamp": "2025-02-13"}  # Example metadata
    main(graph_path, custom_metadata)
