"""
Google Lens–based equation detection using a gs-ai–compatible API.

Uses a Google Lens API (e.g. SearchAPI, SerpAPI, or gs-ai) to analyze an image URL
and extract equation-like text from visual search / related content results.

Environment:
- GS_AI_API_KEY: API key for the provider (required).
- GS_AI_BASE_URL: Optional. Defaults to SearchAPI Google Lens endpoint.
  SerpAPI: https://serpapi.com/search
  SearchAPI: https://www.searchapi.io/api/v1/search
"""

import os
import re
import logging
from typing import Dict, List, Any

import requests

# Default: SearchAPI Google Lens–compatible endpoint
DEFAULT_BASE_URL = "https://www.searchapi.io/api/v1/search"


def _equation_like(text: str) -> bool:
    """Heuristic: string looks like a math equation (contains = or LaTeX/math symbols)."""
    if not text or len(text) < 2:
        return False
    s = text.strip()
    if "=" in s:
        return True
    if re.search(r"\\[a-zA-Z]+|\\frac|\\sum|\\int|\\sqrt|\^|[\d]\s*[+\-*/]\s*[\d]", s):
        return True
    return False


def _extract_equation_candidates(data: Dict[str, Any]) -> List[str]:
    """Collect equation-like strings from Google Lens API response."""
    candidates: List[str] = []
    seen = set()

    def add(s: str) -> None:
        s = s.strip()
        if s and s not in seen and _equation_like(s):
            seen.add(s)
            candidates.append(s)

    # visual_matches titles sometimes contain equations or formula names
    for item in data.get("visual_matches") or []:
        title = item.get("title") or item.get("link") or ""
        if title:
            add(title)
    # related_content / related_searches
    for item in data.get("related_content") or data.get("related_searches") or []:
        q = item.get("query") or item.get("title") or ""
        if q:
            add(q)
    # about_this_image text if present (OCR-style)
    about = data.get("about_this_image") or {}
    if isinstance(about, dict):
        for v in about.values():
            if isinstance(v, str):
                for line in v.splitlines():
                    add(line)
            elif isinstance(v, list):
                for x in v:
                    if isinstance(x, str):
                        add(x)
    elif isinstance(about, str):
        for line in about.splitlines():
            add(line)
    # Optional: search_metadata or inline text
    for key in ("inline_answers", "knowledge_graph"):
        block = data.get(key)
        if isinstance(block, list):
            for b in block:
                if isinstance(b, dict) and "snippet" in b:
                    add(b["snippet"])
                elif isinstance(b, str):
                    add(b)
        elif isinstance(block, dict) and "description" in block:
            add(block["description"])

    return candidates


def detect_equations_from_image_url(
    image_url: str,
    api_key: str | None = None,
    base_url: str | None = None,
    search_type: str = "all",
    timeout: int = 30,
) -> Dict[str, List[str]]:
    """
    Call Google Lens–compatible API (gs-ai / SearchAPI / SerpAPI) and parse equation-like content.

    Args:
        image_url: Public URL of the image to analyze (required; APIs typically do not accept raw bytes).
        api_key: Override for GS_AI_API_KEY.
        base_url: Override for API base (e.g. SerpAPI: https://serpapi.com/search).
        search_type: Lens search type: "all", "about_this_image", "visual_matches", "products", "exact_matches".
        timeout: Request timeout in seconds.

    Returns:
        Dict with keys: "latex", "math_elements", "equations" (each a list of strings).
        Same shape as RawModuleExtractor.extract_equation_content_from_pdf for downstream compatibility.
    """
    key = api_key or os.environ.get("GS_AI_API_KEY", "").strip()
    if not key:
        logging.warning("[GoogleLens] GS_AI_API_KEY not set; skipping equation detection.")
        return {"latex": [], "math_elements": [], "equations": []}

    base = (base_url or os.environ.get("GS_AI_BASE_URL", "")).strip() or DEFAULT_BASE_URL
    base = base.rstrip("/")

    # SearchAPI uses engine=google_lens + search_type; SerpAPI uses engine=google_lens + type
    params: Dict[str, Any] = {
        "engine": "google_lens",
        "url": image_url,
        "api_key": key,
    }
    if search_type and search_type != "all":
        if "serpapi" in base.lower():
            params["type"] = search_type
        else:
            params["search_type"] = search_type

    try:
        resp = requests.get(base, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logging.error(f"[GoogleLens] API request failed: {e}")
        return {"latex": [], "math_elements": [], "equations": []}
    except ValueError as e:
        logging.error(f"[GoogleLens] Invalid JSON: {e}")
        return {"latex": [], "math_elements": [], "equations": []}

    candidates = _extract_equation_candidates(data)
    # Split into latex vs plain equations by simple heuristic
    latex: List[str] = []
    equations: List[str] = []
    for c in candidates:
        if "\\" in c or re.search(r"\\[a-zA-Z]", c):
            latex.append(c)
        else:
            equations.append(c)
    math_elements = list(dict.fromkeys(latex + equations))

    return {
        "latex": latex[:50],
        "math_elements": math_elements[:100],
        "equations": equations[:50],
    }
