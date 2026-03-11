"""
"Write a highly efficient Python script to convert React code (in .tsx format) into a networkx.Graph admin_data structure. The script should:

Take a list of project paths (nested folder structures containing React components, fnuctions,  and pages).
Define Unique component- and page names as components  as nodes from .tsx files, correctly identifying React components, pages, imports, and their relationships.
Classify each node based on at least 5 key attributes:
Type (layer(e.g. components or page), component placement/position (where its placed inside a "page"-type node),, etc.),
the whole component code,
 Complexity (Number of lines of code or dependencies)
f& Dependencies (Which components a file depends on)
Export Type (Default export, named exports, etc.)
Define edges for all meaningful relationships, such as:
Component usage (imports → links to the files they are used in).
Parent-child relationships (nesting of components).
Prop drilling or context sharing.
API calls or admin_data dependencies.
Ensure accurate parsing, handling syntax differences, and deeply nested imports.
Keep the script concise and well-commented for maintainability and efficiency."
"""

################################################

import re

from pathlib import Path

from qbrain.graph.utils import Utils

# Entry paths to scan project_paths = [
project_paths = [
    r"C:\\Users\\wired\\Desktop\\demo_raw_c2\\src\\app\\(site)",
    r"C:\\Users\\wired\\Desktop\\demo_raw_c2\\src\\components",
]


def extract_imports(file_path):
    """Extracts imported components/pages from a .tsx file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    imports = re.findall(r"import\s+\{?(\w+)\}?.*?from\s+['\"](.+?)['\"]", content)
    return {imp[0]: imp[1] for imp in imports}  # {Component: Path}


def extract_components(file_path):
    """Extracts component names from a .tsx file by looking for function/class declarations."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    matches = re.findall(r"export\s+(?:default\s+)?function\s+(\w+)|export\s+const\s+(\w+)", content)
    components = [m[0] or m[1] for m in matches if any(m)]
    return components, content


def classify_node(file_path, component_name, content):
    """Classifies a component/page with attributes."""
    lines_of_code = len(content.split("\n"))
    dependencies = extract_imports(file_path)
    export_type = "default" if "export default" in content else "named"
    node_type = "page" if "pages" in str(file_path) else "component"

    return {
        "type": node_type,
        "location": str(file_path),
        "code": content,
        "complexity": lines_of_code,
        "dependencies": list(dependencies.keys()),
        "export_type": export_type
    }


def build_graph(project_paths):
    """Builds a NetworkX graph from a React project's structure."""
    G = nx.Graph()

    for root_path in project_paths:
        for root, _, files in os.walk(root_path):
            for file in files:
                if file.endswith(".tsx"):
                    file_path = Path(root) / file
                    components, content = extract_components(file_path)
                    for component in components:
                        node_attrs = classify_node(file_path, component, content)
                        G.add_node(component, **node_attrs)

                        # Add edges for imports
                        imports = extract_imports(file_path)
                        for imp, imp_path in imports.items():
                            G.add_edge(imp, component, relationship="imported_by")
                            G.nodes[imp]["type"] = "external"  # Mark external components
    return G


import os
import torch
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv
from torch_geometric.data import Data
from sklearn.preprocessing import LabelEncoder


class GraphSAGE(torch.nn.Module):
    """
    Simple GraphSAGE-based Graph Neural Network
    """
    def __init__(self, in_channels, hidden_channels, out_channels):
        super(GraphSAGE, self).__init__()
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        return x


class GNNTrainer:
    """
    Trains a GraphSAGE model on the React component graph.
    """

    def __init__(self, graph, model_path="main_ckpt/gnn_model.pth"):
        self.graph = graph
        self.model_path = model_path
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.data = self._prepare_graph_data()

    def predict_best_components_for_page(self, page_name, num_components=5):
        """
        Predicts the best component combination for a given page (layer node type)
        by finding the most similar components using the trained GNN embeddings.
        """

        if self.model is None:
            self.load_model()

        self.model.eval()
        with torch.no_grad():
            node_list = list(self.graph.nodes())
            set_nodes = set(n["type"] for n in node_list)
            print(f"{[sn for sn in set_nodes]}")
            if page_name not in node_list:
                print(f"❌ Page '{page_name}' not found in the graph.")
                return None

            # Get page embedding
            index = node_list.index(page_name)
            page_embedding = self.model(self.data.x, self.data.edge_index)[index].cpu().numpy().reshape(1, -1)

            # Get all component embeddings
            all_embeddings = self.model(self.data.x, self.data.edge_index).cpu().numpy()
            all_names = np.array(node_list)

            # Compute similarity scores
            similarities = cosine_similarity(page_embedding, all_embeddings)[0]

            # Sort by similarity (descending)
            sorted_indices = np.argsort(similarities)[::-1]

            # Select top components (ignoring the page itself)
            best_components = []
            for i in sorted_indices:
                if all_names[i] != page_name:  # Exclude itself
                    best_components.append((all_names[i], similarities[i]))

                if len(best_components) >= num_components:
                    break

            print(f"🔮 Predicted best components for '{page_name}':")
            for comp, score in best_components:
                print(f" - {comp} (Similarity: {score:.4f})")

            return best_components


    def _prepare_graph_data(self):
        """
        Convert NetworkX graph to PyTorch Geometric Data.
        """
        node_list = list(self.graph.nodes())
        encoder = LabelEncoder()
        node_ids = encoder.fit_transform(node_list)

        # Create node features (dummy features for now)
        num_nodes = len(node_list)
        x = torch.rand((num_nodes, 16))  # 16 feature dimensions (can be improved)

        # Create edge index
        edge_list = [(node_list.index(u), node_list.index(v)) for u, v in self.graph.edges()]
        edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()

        return Data(x=x, edge_index=edge_index).to(self.device)

    def train_gnn(self, epochs=100, lr=0.01):
        """
        Train the GraphSAGE model on the graph.
        """
        model = GraphSAGE(in_channels=16, hidden_channels=32, out_channels=16).to(self.device)
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        loss_fn = torch.nn.MSELoss()

        print("🚀 Training GNN...")
        for epoch in range(epochs):
            model.train()
            optimizer.zero_grad()
            out = model(self.data.x, self.data.edge_index)
            loss = loss_fn(out, self.data.x)  # Self-supervised (dummy target)
            loss.backward()
            optimizer.step()

            if epoch % 10 == 0:
                print(f"Epoch {epoch}/{epochs} - Loss: {loss.item():.4f}")

        print("✅ Training complete!")
        self.model = model

        # Save model
        self.save_model()

    def save_model(self):
        """
        Save the trained GNN model locally.
        """
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        torch.save(self.model.state_dict(), self.model_path)
        print(f"✅ Model saved at {self.model_path}")

    def load_model(self):
        """
        Load a pre-trained model if it exists.
        """
        if os.path.exists(self.model_path):
            self.model = GraphSAGE(in_channels=16, hidden_channels=32, out_channels=16).to(self.device)
            self.model.load_state_dict(torch.load(self.model_path))
            print(f"✅ Loaded pre-trained model from {self.model_path}")
        else:
            print("❌ No pre-trained model found. Train the model first.")

    def predict_component(self, component_name):
        """
        Get the predicted embedding of a React component.
        """
        if self.model is None:
            self.load_model()

        self.model.eval()
        with torch.no_grad():
            node_list = list(self.graph.nodes())
            if component_name in node_list:
                index = node_list.index(component_name)
                embedding = self.model(self.data.x, self.data.edge_index)[index].cpu().numpy()
                print(f"🔮 Predicted embedding for {component_name}: {embedding}")
                return embedding
            else:
                print(f"❌ Component '{component_name}' not found.")
                return None


import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.metrics.pairwise import cosine_similarity


class GNNTester:
    """
    Loads and tests the trained GNN model using embeddings from the React component graph.
    """

    def __init__(self, graph_file, embedding_file="react_embeddings.npy"):
        self.graph = None
        self.embeddings = None
        self.node_names = None
        self.load_graph(graph_file)
        self.load_embeddings(embedding_file)



    def load_embeddings(self, embedding_file):
        """Loads the trained embeddings from a NumPy file."""
        print(f"📂 Loading embeddings from {embedding_file}...")
        self.embeddings = np.load(embedding_file, allow_pickle=True).item()
        self.node_names = list(self.embeddings.keys())  # List of component names
        print(f"✅ Embeddings loaded for {len(self.embeddings)} components!")

    def find_similar_components(self, component_name, top_n=5):
        """Finds the most similar components using cosine similarity."""
        if component_name not in self.embeddings:
            print(f"❌ Error: Component {component_name} not found in embeddings!")
            return []

        print(f"🔍 Finding components similar to {component_name}...")

        # Compute cosine similarity between components
        component_vector = np.array(self.embeddings[component_name]).reshape(1, -1)
        all_vectors = np.array(list(self.embeddings.values()))
        similarities = cosine_similarity(component_vector, all_vectors)[0]

        # Sort by similarity (excluding itself)
        sorted_indices = np.argsort(similarities)[::-1]
        similar_components = [(self.node_names[i], similarities[i]) for i in sorted_indices if
                              self.node_names[i] != component_name][:top_n]

        print(f"✅ Most similar components to '{component_name}':")
        for comp, score in similar_components:
            print(f" - {comp} (Similarity: {score:.4f})")

        return similar_components

    def visualize_embeddings(self):
        """Visualizes the component embeddings using t-SNE for dimensionality reduction."""
        print("📊 Visualizing component embeddings...")
        vectors = np.array(list(self.embeddings.values()))
        labels = np.array(self.node_names)

        # Reduce dimensionality
        tsne = TSNE(n_components=2, perplexity=10, random_state=42)
        reduced_vectors = tsne.fit_transform(vectors)

        # Plot
        plt.figure(figsize=(12, 8))
        plt.scatter(reduced_vectors[:, 0], reduced_vectors[:, 1], alpha=0.7)
        for i, label in enumerate(labels):
            plt.annotate(label, (reduced_vectors[i, 0], reduced_vectors[i, 1]), fontsize=8, alpha=0.7)

        plt.title("React Component Embeddings (t-SNE)")
        plt.xlabel("Dimension 1")
        plt.ylabel("Dimension 2")
        plt.show()
        print("✅ Visualization complete!")

    def predict_component_structure(self, new_component_name="HelloBotWorld"):
        """
        Predicts the structure of a new component based on similar components in the trained graph.
        """
        similar_components = self.find_similar_components(new_component_name, top_n=3)

        if not similar_components:
            print(f"❌ No similar components found for {new_component_name}.")
            return None

        print(f"🔮 Predicted Structure for '{new_component_name}':\n")
        for comp, similarity in similar_components:
            component_attrs = self.graph.nodes.get(comp, {})
            print(f"🟢 Similar to: {comp} (Similarity: {similarity:.4f})")
            print(f"📂 Type: {component_attrs.get('type', 'Unknown')}")
            print(f"📏 Complexity (Lines of Code): {component_attrs.get('complexity', 'Unknown')}")
            print(f"🔗 Dependencies: {component_attrs.get('dependencies', [])}")
            print(f"🔄 Export Type: {component_attrs.get('export_type', 'Unknown')}\n")

        return similar_components







if __name__ == "__main__":
    project_paths = [
        r"C:\\Users\\wired\\Desktop\\demo_raw_c2\\src\\app\\(site)",
        r"C:\\Users\\wired\\Desktop\\demo_raw_c2\\src\\components",
    ]

    graph = build_graph(project_paths)
    ut = Utils()

    print("✅ Graph saved successfully.")

    # Example Usage
    gnn_trainer = GNNTrainer(graph)
    embeddings = gnn_trainer.train_node_embeddings()
    gnn_trainer.save_embeddings(embeddings)

    tester = GNNTester(
        graph_file="/main_ckpt/nx/frontend/frontend_11.json",
        embedding_file=r"/main_ckpt/nx/frontend/frontend.npy"
    )

    # Test similarity search
    similar_components = tester.find_similar_components("Navbar", top_n=5)

    # Visualize embeddings
    tester.visualize_embeddings()
    tester.predict_component_structure()
    # Print summary
    print(f"✅ Graph built with {len(graph.nodes())} nodes and {len(graph.edges())} edges.")


if __name__ == "__main__":
    project_paths = [
        "dir/to/react/comps"
        "dir/to/react/pages"
    ]

    # Build the graph from React project
    graph = build_graph(project_paths)

    # Train and save the GNN
    gnn_trainer = GNNTrainer(graph)
    gnn_trainer.train_gnn()

    # Predict a component's structure
    gnn_trainer.predict_component("Navbar")
    gnn_trainer.predict_best_components_for_page("HomePage", num_components=5)
