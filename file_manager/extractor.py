import json
import base64
import logging
import pprint
import networkx as nx
import vertexai
from vertexai.generative_models import GenerativeModel, Part
import dotenv
import filetype

from qbrain.core.module_manager.mcreator import ModuleCreator
from qbrain.core.file_manager.extraction_prompts import EXTRACT_EQUATIONS_PROMPT, CONV_EQ_CODE_TO_JAX_PROMPT
from qbrain.core.file_manager.google_lens_equations import detect_equations_from_image_url
from qbrain.qf_utils.qf_utils import QFUtils

dotenv.load_dotenv()

from qbrain.core.app_utils import GCP_ID
from qbrain.auth.load_sa_creds import load_service_account_credentials

class RawModuleExtractor:

    def __init__(self):
        try:
            vertexai.init(
                project=GCP_ID, 
                location="us-central1", 
                credentials=load_service_account_credentials()
            ) 
            self.model = GenerativeModel("gemini-2.5-pro")
        except Exception as e:
            logging.error(f"Failed to init Vertex AI: {e}")
            self.model = None

    def _prepare_content_parts(self, files: list[str]):
        """
        Processes a list of stringified byte strings, detects their type,
        and returns a list of Vertex AI Part objects.
        """
        print("_prepare_content_parts...")

        classified_files = self._classify_files(files)
        print("classified_files", classified_files)

        parts = []

        for ftype, file_list in classified_files.items():
            print(f"ftype, file_list", ftype, file_list)

            mime_type = self._get_mime_type(ftype)

            for f_bytes in file_list:
                try:
                    parts.append(
                        Part.from_data(f_bytes, mime_type=mime_type)
                    )
                except Exception as e:
                    logging.error(f"Error creating Part for {ftype}: {e}")
        print(f"Content parts prepared. Classified types: {list(classified_files.keys())}")
        return parts, classified_files


    def _classify_files(self, files: list[str]) -> dict:
        """
        Classifies files based on their content (bytes).
        Input: List of stringified byte strings (or base64 strings).
        Output: Dictionary { 'pdf': [bytes, ...], 'image': [bytes, ...] }
        """
        classified = {}
        for f_str in files:
            try:
                # Handle base64 prefix if present
                if isinstance(f_str, str):
                    if "base64," in f_str:
                         f_str = f_str.split("base64,")[1]
                    f_bytes = base64.b64decode(f_str)
                else:
                    f_bytes = f_str

                # Detect type
                kind = filetype.guess(f_bytes)
                if kind:
                    ftype = kind.extension
                else:
                    # Fallback or default
                    ftype = "unknown"
                
                if ftype not in classified:
                    classified[ftype] = []
                classified[ftype].append(f_bytes)
                
            except Exception as e:
                 logging.error(f"Error classifying file: {e}")
        
        return classified

    def _get_mime_type(self, extension: str) -> str:
        """Maps extensions to MIME types."""
        mimes = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",

            "jpeg": "image/jpeg",
            "txt": "text/plain",
            "csv": "text/csv"
        }
        return mimes.get(extension, "application/octet-stream")

    def extract_equation_content_from_pdf(self, pdf_bytes: bytes) -> dict:
        """
        Preprocessing: extract math/LaTeX from PDF using local pdfminer + regex.
        Returns equation_content struct: {latex: [...], math_elements: [...], equations: [...]}
        """
        import re
        from io import BytesIO
        print("[Extractor] extract_equation_content_from_pdf: starting")
        if not pdf_bytes:
            print("[Extractor] extract_equation_content_from_pdf: empty bytes, returning empty")
            return {"latex": [], "math_elements": [], "equations": []}
        try:
            from pdfminer.high_level import extract_text
            text = extract_text(BytesIO(pdf_bytes))
            latex, equations = [], []
            # LaTeX blocks: \[...\], \(...\), $...$
            for m in re.finditer(r'\\\[(.*?)\\\]|\\\((.*?)\\\)|\$([^$]+)\$', text, re.DOTALL):
                s = (m.group(1) or m.group(2) or m.group(3) or "").strip()
                if s:
                    latex.append(s)
            # Lines with = or \ (likely math)
            for line in text.splitlines():
                line = line.strip()
                if line and ("=" in line or "\\" in line) and len(line) > 2:
                    equations.append(line)
            result = {"latex": list(dict.fromkeys(latex)), "math_elements": equations[:100], "equations": equations[:50]}
            print(f"[Extractor] extract_equation_content_from_pdf: done -> latex={len(result['latex'])}, equations={len(result['equations'])}")
            return result
        except Exception as e:
            logging.error(f"extract_equation_content_from_pdf error: {e}")
            return {"latex": [], "math_elements": [], "equations": []}

    def get_equation_content_from_image_url(self, image_url: str) -> dict:
        """
        Use Google Lens (gs-ai API) to detect equations from an image URL.
        Returns same shape as extract_equation_content_from_pdf: {latex, math_elements, equations}.
        Requires GS_AI_API_KEY (and optional GS_AI_BASE_URL) in environment.
        """
        return detect_equations_from_image_url(image_url)

    def extract_params_and_data_types(self, parts):
        if not self.model or not parts:
            return {}
            
        # Add prompt to parts
        prompt = "Extract all parameters used in equations from the following documents. Return a dictionary mapping parameter names to BigQuery data types (e.g. FLOAT64, STRING). Output valid JSON only."
        request_parts = parts + [prompt]
        try:
            response = self.model.generate_content(request_parts)
            text = response.text
            text = text.replace("```json", "").replace("```", "").strip()
            params = json.loads(text)
            print(f"Extracted params: {params}")
            return params
        except Exception as e:
            logging.error(f"Gemini extract params error: {e}")
            return {}

    def extract_equations(self, parts):
        print("_extract_equations...")
        request_parts = parts +[EXTRACT_EQUATIONS_PROMPT]
        try:
            print("_extract_equations... request_parts")
            response = self.model.generate_content(request_parts)
            print("_extract_equations... response", response)
            text = response.text.strip()
            text = text.replace("```python", "").replace("```", "").strip()
            print(f"Extracted equations code length: {len(text)}:", text)
            return text
        except Exception as e:
             logging.error(f"Gemini extract equations error: {e}")
             return ""

    def jax_predator(self, code):
        prompt = CONV_EQ_CODE_TO_JAX_PROMPT
        prompt += f"""\n\nPYTHON CODE: {code}"""

        try:
             response = self.model.generate_content(prompt)
             text = response.text.strip()
             text = text.replace("```python", "").replace("```", "").strip()
             print(f"Generated JAX code length: {len(text)}:", text)
             return text
        except Exception as e:
             logging.error(f"Gemini jax predator error: {e}")
             return code 

    def process(self, mid:str, files: list[str]):
        """
        Main workflow: process files -> extract params -> extract equations -> optimize.
        Returns extracted data structure.
        """
        G = nx.Graph()
        self.mcreator = ModuleCreator(
            G=G,
            qfu=QFUtils(G=G),
        )

        # 1. Prepare parts once
        parts, classified_files = self._prepare_content_parts(files)
        print("1. Files prepared.")

        # 3. Extract Equations
        print("2. Extracting equations...")
        code = self.extract_equations(parts)
        
        # MODULE STUFF
        print("3. Processing module graph...")
        self.mcreator.create_modulator(
            mid, code
        )

        params_edges = self.mcreator.qfu.g.get_neighbor_list(
            node=mid,
            target_type="PARAM",
        )

        params = {
            p["trgt"]: p["attrs"].get("type", "Any")
            for p in params_edges.values()
        }
        
        # EXTRACT METHODS
        method_edges = self.mcreator.qfu.g.get_neighbor_list(
            node=mid,
            target_type="METHOD",
        )
        methods = [m["attrs"] for m in method_edges.values()]

        # EXTRACT FIELDS (CLASS_VAR)
        field_edges = self.mcreator.qfu.g.get_neighbor_list(
            node=mid,
            target_type="CLASS_VAR",
        )
        fields = [f["attrs"] for f in field_edges.values()]

        print(f"Module params identified: {params}")
        print(f"Module methods identified: {len(methods)}")
        print(f"Module fields identified: {len(fields)}")

        # 4. Optimize
        print("4. Optimizing with JAX...")
        jax_code = self.jax_predator(code)
        
        # 5. Return Data
        data= {
            "params": params,
            "methods": methods,
            "fields": fields,
            "code": code,
            "jax_code": jax_code,
        }
        print("data extracted:")
        pprint.pp(data)
        return data

    def process_bytes(self, mid: str, file_contents: list[bytes]):
        """
        Main workflow for raw bytes: process files -> extract params -> extract equations -> optimize.
        Returns extracted data structure.
        """
        G = nx.Graph()
        self.mcreator = ModuleCreator(
            G=G,
            qfu=QFUtils(G=G),
        )

        # 1. Prepare parts directly from bytes
        # Assuming all are PDFs or text for now, or use classification logic if needed.
        # Reusing _classify_files logic but adapting for direct bytes input if needed,
        # or just wrapping them directly if we trust the source.
        # Let's reuse _prepare_content_parts but pass the bytes directly as if they were strings
        # (since _classify_files handles bytes too).
        
        # However, _classify_files expects a list of strings/bytes.
        parts, classified_files = self._prepare_content_parts(file_contents)
        print("1. Files prepared from bytes.")

        # 3. Extract Equations
        print("2. Extracting equations...")
        code = self.extract_equations(parts)
        
        # MODULE STUFF
        print("3. Processing module graph...")
        self.mcreator.create_modulator(
            mid, code
        )

        params_edges = self.mcreator.qfu.g.get_neighbor_list(
            node=mid,
            target_type="PARAM",
        )

        params = {
            p["trgt"]: p["attrs"].get("type", "Any")
            for p in params_edges.values()
        }
        
        # EXTRACT METHODS
        method_edges = self.mcreator.qfu.g.get_neighbor_list(
            node=mid,
            target_type="METHOD",
        )
        methods = [m["attrs"] for m in method_edges.values()]

        # EXTRACT FIELDS (CLASS_VAR)
        field_edges = self.mcreator.qfu.g.get_neighbor_list(
            node=mid,
            target_type="CLASS_VAR",
        )
        fields = [f["attrs"] for f in field_edges.values()]

        print(f"Module params identified: {params}")
        print(f"Module methods identified: {len(methods)}")
        print(f"Module fields identified: {len(fields)}")

        # 4. Optimize
        print("4. Optimizing with JAX...")
        jax_code = self.jax_predator(code)
        
        # 5. Return Data
        data= {
            "params": params,
            "methods": methods,
            "fields": fields,
            "code": code,
            "jax_code": jax_code,
        }
        print("data extracted:")
        pprint.pp(data)
        return data
