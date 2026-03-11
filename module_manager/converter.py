import json
import os
from typing import Dict, Any

from qbrain.a_b_c.gemw.chat_main import Chat
from fb_core.real_time_database import FBRTDBMgr

# Importiere hier die Prompts als Konstanten
from qbrain.core.module_manager.utils.prompts import *

class Converter:
    """
    Converter class to:
    - fetch module files (firebase / local)
    - extract physics info via AI prompts
    - generate runnable JAX code classes
    - save all extracted info locally
    """

    def __init__(self, testing_mode: bool = False, save_dir: str = "arsenal"):
        self.chat = Chat()
        self.fb = FBRTDBMgr() if 'FBRTDBMgr' in globals() else None
        self.testing_mode = testing_mode
        self.save_dir = save_dir
        self.arsenal: Dict[str, Any] = {}  # dict[equation_name, callable]
        self.world_cfg: dict = {}

        os.makedirs(save_dir, exist_ok=True)


    # ------------------- Query Helpers -------------------
    def query_agent(self, prompt: str, file_content: str) -> str:
        """
        Run the local Chat agent on a prompt + file content
        """
        try:
            response = self.chat.ask(
                user_prompt=prompt,
                file_list=[file_content]
            )
            return response
        except Exception as e:
            print(f"Error querying agent: {e}")
            return ""

    # ------------------- Extraction Methods -------------------
    def extract_equations(self, file_content: str) -> str:
        """
        Extract equations and convert them to optimized JAX Python class
        Save final code to self.save_dir
        """
        code = self.query_agent(EQUATION_PROMPT, file_content)
        if code and "class " in code:
            # write to file
            file_name = os.path.join(self.save_dir, "equations.py")
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(code)
            print(f"Equations code written to {file_name}")
        return code

    def extract_parameters(self, file_content: str) -> Dict[str, str]:
        """
        Extract all parameters as dict[name, type]
        """
        response = self.query_agent(PARAMETER_PROMPT, file_content)
        try:
            params = json.loads(response)
            if isinstance(params, dict):
                return params
        except Exception:
            pass
        return {}

    def extract_center_field(self, file_content: str, allowed_fields: list[str]) -> str:
        """
        Extract main field, compare to allowed_fields
        """
        # pass the allowed_fields as context to prompt
        prompt = f"{CENTER_FIELD_PROMPT}\nallowed_fields={allowed_fields}"
        response = self.query_agent(prompt, file_content)
        return response.strip() if response else ""

    def extract_graph_links(self, file_content: str) -> list[str]:
        """
        Extract all interacting fields
        """
        response = self.query_agent(GRAPH_LINK_PROMPT, file_content)
        try:
            links = json.loads(response).get("graph_links", [])
            if isinstance(links, list):
                return links
        except Exception:
            pass
        return []

    # ------------------- Full Processing -------------------
    def process_file(self, file_content: str, allowed_fields: list[str] = []) -> Dict[str, Any]:
        """
        Run all extractions on a single file content
        """
        extracted = {}
        extracted['equations_code'] = self.extract_equations(file_content)
        extracted['parameters'] = self.extract_parameters(file_content)
        extracted['center_field'] = self.extract_center_field(file_content, allowed_fields)
        extracted['graph_links'] = self.extract_graph_links(file_content)
        return extracted



    # ------------------- Check Equation Master -------------------
    def check_eq_master(self, eq_content: str) -> str:
        """
        Return eq content and append a TODO comment
        """
        return f"{eq_content}\n\n# TODO: verify correctness and numerical stability for production use."
