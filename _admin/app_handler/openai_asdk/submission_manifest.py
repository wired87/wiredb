"""
Build the OpenAI App Store submission manifest with all required data.

Used when submitting at https://platform.openai.com/apps-manage.
Writes app_submission_manifest.json with every field needed for the form.
Ref: https://developers.openai.com/apps-sdk/deploy/submission
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

# Default metadata; override via build_submission_manifest(metadata=...)
DEFAULT_METADATA = {
    "name": "BestBrain",
    "subtitle": "Physics simulation and scientific computing for lattice field theory",
    "version": "0.1.0",
    "description": "Physics simulation and scientific computing environment for lattice field theory, fermions, and gauge fields. Run and manage simulations, list saved environments, and create new physics simulations with configurable modules.",
    "privacy_policy_url": "https://bestbrain.tech/privacy",
    "terms_of_service_url": "https://bestbrain.tech/terms",
    "support_contact": "support@bestbrain.tech",
    "company_url": "https://bestbrain.tech",
    "logo_url": "https://bestbrain.tech/logo.png",
    "category": "Developer tools",
}

# MCP connector: user must deploy and paste HTTPS URL
MCP_INSTRUCTIONS = (
    "Deploy the MCP server to a publicly accessible HTTPS URL (e.g. Cloud Run, Fly.io, or use ngrok for testing). "
    "Then in the submission form, set Connector URL to: https://<your-domain>/mcp"
)

# CSP: required for submission; list domains the app fetches from
CSP_CONNECT_DOMAINS = ["https://api.openai.com", "https://bestbrain.tech"]
CSP_RESOURCE_DOMAINS = ["https://bestbrain.tech"]
CSP_FRAME_DOMAINS: List[str] = []


def get_tools_from_workflow() -> List[Dict[str, Any]]:
    """Import TOOLS from workflow so manifest stays in sync."""
    from _admin.app_handler.openai_asdk.workflow import TOOLS
    return list(TOOLS)


def get_golden_prompts_from_workflow() -> Dict[str, List[str]]:
    from _admin.app_handler.openai_asdk.workflow import GOLDEN_PROMPTS
    return dict(GOLDEN_PROMPTS)


def get_test_cases_for_form() -> List[Dict[str, str]]:
    """Test prompts and expected responses for the submission form."""
    return [
        {
            "prompt": "List my simulations",
            "expected_response_summary": "App calls list_simulations and returns a list of saved simulations (or empty list with count 0). No side effects.",
        },
        {
            "prompt": "Show me my saved simulations",
            "expected_response_summary": "Same as above; list_simulations returns simulations without modifying anything.",
        },
        {
            "prompt": "Create a new simulation with env_id demo_env and modules FERMION",
            "expected_response_summary": "App calls create_simulation with env_id and modules; returns confirmation of created simulation.",
        },
        {
            "prompt": "What's the weather today?",
            "expected_response_summary": "App should NOT be triggered (negative test); ChatGPT answers without using BestBrain.",
        },
    ]


def get_demo_paths() -> Dict[str, str]:
    try:
        from _admin.app_handler.openai_asdk.config import get_demo_paths as _get
        return _get()
    except Exception:
        return {}


def build_submission_manifest(
    metadata: Dict[str, Any] | None = None,
    tools: List[Dict[str, Any]] | None = None,
    out_path: Path | None = None,
) -> Dict[str, Any]:
    """
    Build the full submission manifest and optionally write to JSON.

    Returns a dict with every field required for the OpenAI App Store submission form.
    """
    meta = {**DEFAULT_METADATA, **(metadata or {})}
    tools = tools if tools is not None else get_tools_from_workflow()
    golden = get_golden_prompts_from_workflow()
    test_cases = get_test_cases_for_form()
    demo = get_demo_paths()

    manifest = {
        "submission_url": "https://platform.openai.com/apps-manage",
        "app_name": meta["name"],
        "subtitle": meta.get("subtitle", ""),
        "version": meta.get("version", "0.1.0"),
        "description": meta["description"],
        "privacy_policy_url": meta["privacy_policy_url"],
        "terms_of_service_url": meta.get("terms_of_service_url", ""),
        "support_contact": meta["support_contact"],
        "company_url": meta.get("company_url", ""),
        "logo_url": meta["logo_url"],
        "category": meta.get("category", "Developer tools"),
        "mcp_connector_instructions": MCP_INSTRUCTIONS,
        "mcp_path": "/mcp",
        "content_security_policy": {
            "connectDomains": CSP_CONNECT_DOMAINS,
            "resourceDomains": CSP_RESOURCE_DOMAINS,
            "frameDomains": CSP_FRAME_DOMAINS,
        },
        "tools": tools,
        "tool_count": len(tools),
        "golden_prompts": golden,
        "test_prompts_and_responses": test_cases,
        "localization": {
            "default_locale": "en",
            "locales_supported": ["en"],
        },
        "demo_video_path": demo.get("demo_video_path", ""),
        "demo_html_dir": demo.get("demo_html_dir", ""),
        "screenshots_note": "Upload screenshots of the app in use (required dimensions per dashboard).",
        "checklist_before_submit": [
            "Organization verification completed (Dashboard → Settings → General).",
            "Owner role in organization.",
            "MCP server deployed at public HTTPS URL (e.g. https://your-app.run.app/mcp).",
            "CSP defined; no localhost in production.",
            "Demo account (no MFA) if app requires auth.",
        ],
    }

    if out_path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    return manifest
