from langchain_community.chat_models import ChatOpenAI

from ggoogle.storage.storage import GBucket


class ChatGPTGraphExtractor:
    def __init__(self, api_key, model="gpt-4-turbo", local_path="graph.gml"):
        """
        Initializes the ChatGPT-based Graph Extractor.
        :param api_key: OpenAI API key.
        :param model: ChatGPT model name (default: GPT-4 Turbo).
        :param local_path: Path to save the extracted graph.
        """
        self.api_key = api_key
        self.model = model
        self.local_path = local_path
        self.graph = nx.Graph()

    async def process_data(self, data):
        """
        Entry point to process dataset, extract schema, and construct graph.
        :param data: The input dataset (JSON, CSV, or parsed dictionary).
        """
        schema = await self.extract_schema(data)
        nodes, edges = await self.extract_nodes_and_edges(data, schema)
        self.build_graph(nodes, edges)
        await self.save_graph()

    async def extract_schema(self, data):
        """
        Uses ChatGPT API with function calling to extract a graph schema.
        """
        sample_data = json.dumps(data[:5] if isinstance(data, list) else [data], indent=2)

        prompt = f"""
        You are an expert in structured admin_data extraction. Analyze the provided dataset sample and **identify a structured schema** for nodes and edges.

        ### Expected JSON Output:
        {{
            "nodes": [
                {{"id": "<unique_node_identifier>", "attributes": ["<list_of_additional_fields>"]}}
            ],
            "EDGES": [
                {{"src": "<source_node_id>", "tgt": "<target_node_id>", "rel": "<relationship_type>"}}
            ]
        }}

        ### Important Instructions:
        - **Nodes**: Extract **unique identifiers** from each entity.
        - **Edges**: Extract relationships **explicitly**.
          - Use `is_a` for **hierarchical** relationships.
          - Use `disjoint_from` for **exclusion** relationships.
          - Use `synonym` for **alias** relationships.
        - **Output must always be a valid JSON object** (do not return "unknown").
        - **Do NOT include markdown formatting (` ```json ... ``` `) in the output**.

        ### Dataset Sample:
        {sample_data}

        **Return ONLY valid JSON output, no explanations.**
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            functions=[
                {
                    "name": "extract_graph_schema",
                    "description": "Extracts nodes and edges schema from sample admin_data.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "nodes": {
                                "type": "array",
                                "description": "List of identified node fields.",
                                "items": {"type": "string"}
                            },
                            "EDGES": {
                                "type": "array",
                                "description": "List of detected relationships between nodes.",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "src": {"type": "string", "description": "Source node field."},
                                        "tgt": {"type": "string", "description": "Target node field."},
                                        "rel": {"type": "string", "description": "Relationship type."}
                                    },
                                    "required": ["src", "tgt", "rel"]
                                }
                            }
                        },
                        "required": ["nodes", "EDGES"]
                    }
                }
            ],
            function_call="auto",
        )

        schema_text = response
        schema = schema_text
        print("✅ Extracted Schema:", schema)
        return schema

    async def extract_nodes_and_edges(self, data, schema):
        """
        Extracts nodes and edges from admin_data using the identified schema.
        """
        nodes, edges = set(), set()

        for entry in data:
            node_id = entry.get("id")
            if node_id:
                attributes = {k: v for k, v in entry.items() if k != "id"}
                nodes.add((node_id, attributes))

            for edge_schema in schema.get("EDGES", []):
                src, tgt, rel = edge_schema.get("src"), edge_schema.get("tgt"), edge_schema.get("rel")
                if src and tgt:
                    edges.add((entry.get(src), entry.get(tgt), {"relationship": rel}))

        return nodes, edges

    def build_graph(self, nodes, edges):
        """
        Constructs a NetworkX graph from extracted nodes and edges.
        """
        self.graph.add_nodes_from(nodes)
        self.graph.add_edges_from(edges)

    async def save_graph(self):
        """
        Saves the constructed graph.
        """
        nx.write_gml(self.graph, self.local_path)
        print(f"✅ Graph saved to {self.local_path}")


# --- INTEGRATION WITH DynamicGraphExtractor ---
import os

import json
import aiohttp
import asyncio
import pandas as pd
import networkx as nx
from pathlib import Path
from typing import Union

from qbrain.utils.file.flatten_dict import flatten_attributes
from openai import OpenAI


class GraphBuilder:
    def __init__(self, info, model="gpt-4-turbo"):
        """
        Initializes the GraphBuilder with an AI-powered model for intelligent edge inference.

        :param model: Local or cloud-based LLM instance for schema recognition.
        :param local_path: Path to save the generated graph.
        """
        self.model = model if model else ChatOpenAI(model="gpt-4")  # LLM for edge detection
        self.graph = nx.Graph()
        self.local_path = info["local"]
        self.bucket_path = info["bucket"]
        self.bucket =GBucket("bestbrain")
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model= model

    async def process(self, json_path: str):
        """
        Main function to load, parse, and build a graph from a JSON file.

        :param json_path: Path to JSON file.
        """
        data = await self.load_json_dynamically(json_path)
        nodes, edges = await self.extract_nodes_edges(data)
        self.build_graph(nodes, edges)
        self.save_graph()

    async def load_json_dynamically(self, path: str) -> list:
        """
        Efficiently loads JSON by identifying the primary admin_data list dynamically.

        :param path: JSON file path.
        :return: Extracted admin_data list.
        """
        with open(path, "r", encoding="utf-8") as file:
            sample_data = file.read(2048)  # Read the first 2048 bytes
            json_content = json.loads(sample_data)

            # Find the primary list in JSON
            if isinstance(json_content, dict):
                for key, value in json_content.items():
                    if isinstance(value, list) and len(value) > 0:
                        return value  # Assume first detected list is the main admin_data
            elif isinstance(json_content, list):
                return json_content

        raise ValueError("No valid admin_data list found in JSON file.")



    async def load_data(self, source: str) -> Union[dict, list, pd.DataFrame]:
        """
        Loads admin_data dynamically from various sources, including files and URLs.
        Supports CSV, JSON, FASTA, HDF5, and more.

        :param source: File path or URL.
        :return: Loaded admin_data in a structured format.
        """
        if source.startswith("http"):
            return await self.fetch_from_url(source)

        ext = Path(source).suffix.lower()

        if ext in [".json", ".jsonl"]:
            return self.load_json(source)
        elif ext in [".csv", ".tsv"]:
            return pd.read_csv(source)
        elif ext in [".fna", ".fasta"]:
            return self.load_fasta(source)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    async def fetch_from_url(self, url: str):
        """
        Asynchronously fetches JSON or text admin_data from a URL.

        :param url: Web URL.
        :return: Parsed JSON or text admin_data.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if "json" in resp.headers.get("Content-Type", ""):
                    return await resp.json()
                return await resp.text()




    async def extract_nodes_edges(self, data: list):
        """
        Extracts nodes and edges dynamically using an LLM.

        :param data: List of JSON objects.
        :return: Tuple (nodes, edges)
        """
        if not data:
            return [], []

        # Identify potential edge fields via LLM
        sample_item = json.dumps(data[0])
        llm_prompt = f"""
        Given the following JSON object, identify fields that could be used as edges in a graph.
        Example JSON: {sample_item}
        Output a list of key names that likely reference relationships between entities.
        """

        accession_prompt = f"""
        Recognize the main identifier of the provided object. return nothing but its key (without value)

        """
        edge_fields = await self.llm_call(llm_prompt)
        dataset_id = await self.llm_call(accession_prompt)
        # Process Nodes & Edges
        nodes = []
        edges = []
        for item in data:
            node_id = item.get(dataset_id, str(hash(json.dumps(item))))  # Unique node ID
            nodes.append((node_id, flatten_attributes(item)))  # Store as (ID, attributes)

            # Extract edges
            for field in edge_fields:
                if field in item:
                    target_nodes = item[field]
                    if isinstance(target_nodes, list):  # Multi-edge field
                        for target in target_nodes:
                            edges.append((node_id, str(target)))
                    else:
                        edges.append((node_id, str(target_nodes)))

        return nodes, edges

    async def llm_call(self, prompt: str, json_mode: bool = False):
        """
        Calls an LLM to extract suitable edge fields.

        :param prompt: Text prompt for the LLM.
        :param json_mode: If True, forces the model to return JSON.
        :return: List of field names or structured JSON.
        """
        messages = [{"role": "user", "content": prompt}]

        # Force structured JSON mode if enabled
        if json_mode:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format="json"
            )
        else:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )

        # Validate and parse JSON response
        try:
            content = response.choices[0].message.content
            return json.loads(content) if json_mode else content
        except json.JSONDecodeError:
            print("❌ Error: Invalid JSON response from LLM")
            return []



    def build_graph(self, nodes, edges):
        """
        Constructs the graph with identified nodes and edges.

        :param nodes: List of (node_id, attributes).
        :param edges: List of (node_id, target_node_id).
        """
        for node_id, attributes in nodes:
            self.graph.add_node(node_id, **attributes)

        self.graph.add_edges_from(edges)

    def save_graph(self):
        """Saves the graph in GML format."""
        os.makedirs(self.local_path, exist_ok=True)
        nx.write_gml(self.graph, self.local_path)
        file_name = "_".join() + ".gml"

        asyncio.run(self.bucket.upload_bucket(
            dest_path=os.path.join(self.bucket_path, file_name),
            src_path=os.path.join(self.local_path, file_name),
        ))
        print(f"✅ Graph saved at {self.local_path}")

    async def main(self, paths):
        tasks = [self.process(path) for path in paths]
        await asyncio.gather(*tasks)
# ✅ Running the script
if __name__ == "__main__":
    json_file_path = []

    graph_builder = GraphBuilder()
    asyncio.run(graph_builder.main())


"""

convert json
read json sample
identify edges & id
loop whole json content
extract everything in networkx.graph format


"""