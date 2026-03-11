from google.cloud import storage
from torch_geometric.nn import Node2Vec

from qbrain.utils.embedder import get_embedder
from qbrain.utils.file import BUCKET_NAME, OUTPUT_FOLDER
import networkx as nx
import numpy as np
import json



class GraphEmbeddingConverter:
    def __init__(self, embedding_dim=768, key_properties=None, model_name="all-MiniLM-L6-v2"):
        """
        Simple Graph Embedding Constructor
        :param embedding_dim: Number of embedding dimensions (1-768)
        :param key_properties: List of up to 2 key properties for A/B testing
        :param model_name: Pretrained model for text embeddings
        """
        assert 1 <= embedding_dim <= 768, "Embedding dimension must be between 1 and 768."

        self.embedding_dim = embedding_dim
        self.key_properties = key_properties if key_properties else []
        self.text_model = get_embedder()

    def generate_graph_embeddings(self, G):
        """
        Generates graph embeddings using Node2Vec from KarateClub.
        :param G: NetworkX graph
        :return: Dictionary mapping nodes to graph embeddings
        """
        model = Node2Vec(dimensions=self.embedding_dim)
        model.fit(G)
        embeddings = model.get_embedding()

        return {node: embeddings[i] for i, node in enumerate(G.nodes())}

    def graph_to_embeddings(self, G, metadata_fields=None):
        """
        Converts a NetworkX graph into embeddings.
        :param G: NetworkX graph
        :param metadata_fields: List of node attributes to include in embeddings
        :return: Dictionary of node embeddings and metadata
        """
        graph_embeddings = self.generate_graph_embeddings(G)

        embeddings_dict = {}
        for node in G.nodes():
            metadata = G.nodes[node] if metadata_fields else {}

            # Text-based embeddings (if text exists in metadata)
            text_embedding = np.zeros(self.embedding_dim)
            if "text" in metadata:
                text_embedding = self.text_model.encode(metadata["text"])
                text_embedding = text_embedding[:self.embedding_dim]  # Ensure correct size

            # Merge graph and text embeddings
            final_embedding = np.concatenate([graph_embeddings[node], text_embedding[:len(graph_embeddings[node])]])
            final_embedding = final_embedding[:self.embedding_dim]  # Ensure within limit

            # Store results
            embeddings_dict[node] = {
                "embedding": final_embedding.tolist(),
                "metadata": {field: metadata.get(field, None) for field in metadata_fields} if metadata_fields else {},
                "key_properties": {field: metadata.get(field, None) for field in self.key_properties}
            }

        return embeddings_dict

    def save_embeddings(self, embeddings, filename="graph_embeddings.json"):
        """
        Saves embeddings to a JSON file.
        """
        with open(filename, "w") as f:
            json.dump(embeddings, f, indent=2)

        upload_to_gcs(filename, BUCKET_NAME, OUTPUT_FOLDER)


def upload_to_gcs(filename, bucket_name, folder):
    """Uploads the JSON file to Google Cloud Storage."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    chunk_filename = f"{folder}/graph_embed.json"
    blob = bucket.blob(chunk_filename)
    blob.upload_from_filename(filename)
    print(f"Uploaded: {chunk_filename}")


# Example Usage
if __name__ == "__main__":
    graph_path = r"/main_ckpt/sne/go_term.json"  # Path to input graph JSON file

    def load_graph_from_json(json_path):
        """Loads a networkx graph from a JSON file."""
        with open(json_path, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
        return nx.node_link_graph(graph_data)  # Converts JSON to a NetworkX graph

    G = load_graph_from_json(graph_path)

    # Convert graph to embeddings
    converter = GraphEmbeddingConverter(embedding_dim=128, key_properties=["category"])
    embeddings = converter.graph_to_embeddings(G, metadata_fields=["text", "category"])

    # Save embeddings
    converter.save_embeddings(embeddings)

    # Print sample output
    print(json.dumps(embeddings, indent=4))

