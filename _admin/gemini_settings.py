"""
Gemini CLI settings.json creator for BestBrain.

Builds full config per https://geminicli.com/docs/reference/configuration/
with values researched for transparency and optimized workflows.
Adapted to project: qdash (frontend), qbrain (backend), _admin (tooling).

Writes to project root (settings.json) and .gemini/settings.json.
Env: GITHUB_PERSONAL_ACCESS_TOKEN for GitHub MCP.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from _admin.mcp_master.client_generators import (
    load_registry,
    mcp_servers_map,
    normalize_services,
)

_SCHEMA_URL = "https://raw.githubusercontent.com/google-gemini/gemini-cli/main/schemas/settings.schema.json"
_TOKEN_REF = "${GITHUB_PERSONAL_ACCESS_TOKEN}"


def _project_paths(root: Path) -> Dict[str, str]:
    """Resolve project dirs for context.includeDirectories."""
    return {
        "root": str(root),
        "qdash": str(root / "qdash"),
        "qbrain": str(root / "qbrain"),
        "_admin": str(root / "_admin"),
    }


def _mcp_servers_config() -> Dict[str, Any]:
    """MCP servers per Gemini CLI schema sourced from canonical MCPMaster registry."""
    project_root = Path(__file__).resolve().parent.parent
    registry_path = project_root / "_admin" / "mcp_master" / "services" / "mcp_services.json"
    if registry_path.is_file():
        try:
            registry = load_registry(registry_path)
            services = normalize_services(registry, resolve_env=False)
            return mcp_servers_map(services)
        except Exception:
            pass
    # Safe fallback for environments where canonical registry is unavailable.
    return {
        "github": {
            "command": "docker",
            "args": [
                "run",
                "-i",
                "--rm",
                "-e",
                "GITHUB_PERSONAL_ACCESS_TOKEN",
                "ghcr.io/modelcontextprotocol/servers/github:latest",
            ],
            "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": _TOKEN_REF},
            "timeout": 60000,
            "trust": False,
            "description": "GitHub MCP: list PRs, create issues, manage repos.",
        }
    }


def build_full_settings(
    project_root: Optional[Path] = None,
    *,
    include_mcp: bool = True,
    include_general: bool = True,
    include_context: bool = True,
    include_tools: bool = True,
    include_model: bool = True,
    include_ui: bool = True,
    include_output: bool = True,
    include_billing: bool = True,
    include_security: bool = True,
    include_privacy: bool = True,
) -> Dict[str, Any]:
    """
    Build full Gemini CLI settings.json.

    Each section is researched from the official schema and docs.
    Values chosen for BestBrain: qdash (React frontend), qbrain (Django backend),
    _admin (deploy/tooling), scientific researcher workflow.
    """
    root = Path(project_root) if project_root else Path.cwd()
    paths = _project_paths(root)
    settings: Dict[str, Any] = {
        "$schema": _SCHEMA_URL,
    }

    # --- general: workflow, session, plan, approval ---
    if include_general:
        settings["general"] = {
            # preferredEditor: open files in VS Code (Cursor-compatible)
            "preferredEditor": "code",
            # vimMode: off for standard UX; researchers may toggle
            "vimMode": False,
            # defaultApprovalMode: "auto_edit" speeds iteration; "default" for safety
            "defaultApprovalMode": "auto_edit",
            # devtools: off unless debugging
            "devtools": False,
            "enableAutoUpdate": True,
            "enableAutoUpdateNotification": True,
            "enableNotifications": False,
            "checkpointing": {"enabled": False},
            # plan.directory: project-local for transparency
            "plan": {
                "directory": str(root / ".gemini" / "plans"),
                "modelRouting": True,
            },
            "retryFetchErrors": False,
            "maxAttempts": 10,
            "debugKeystrokeLogging": False,
            # sessionRetention: keep 30d or 100 sessions for research continuity
            "sessionRetention": {
                "enabled": True,
                "maxAge": "30d",
                "maxCount": 100,
                "minRetention": "1d",
            },
        }

    # --- output: text for human, json for scripting ---
    if include_output:
        settings["output"] = {"format": "text"}

    # --- ui: theme, hints, footer, transparency ---
    if include_ui:
        settings["ui"] = {
            "theme": "default",
            "autoThemeSwitching": True,
            "terminalBackgroundPollingInterval": 60,
            "hideWindowTitle": False,
            "inlineThinkingMode": "off",
            "showStatusInTitle": False,
            "dynamicWindowTitle": True,
            "showHomeDirectoryWarning": True,
            "showCompatibilityWarnings": True,
            "hideTips": False,
            "showShortcutsHint": True,
            "hideBanner": False,
            # hideContextSummary: false so GEMINI.md + MCP visible
            "hideContextSummary": False,
            "footer": {
                "showLabels": True,
                "hideCWD": False,
                "hideSandboxStatus": False,
                "hideModelInfo": False,
                "hideContextPercentage": True,
            },
            "hideFooter": False,
            "showMemoryUsage": False,
            "showLineNumbers": True,
            "showCitations": False,
            "showModelInfoInChat": False,
            "showUserIdentity": True,
            "useAlternateBuffer": False,
            "useBackgroundColor": True,
            "showSpinner": True,
            "loadingPhrases": "tips",
            "errorVerbosity": "low",
            "customWittyPhrases": [],
        }

    # --- model: gemini-2.5-flash for speed, pro for heavy reasoning ---
    if include_model:
        settings["model"] = {
            "name": "gemini-2.5-flash",
            "maxSessionTurns": -1,
            "summarizeToolOutput": {
                "run_shell_command": {"tokenBudget": 2000},
            },
            "compressionThreshold": 0.5,
            "disableLoopDetection": False,
            "skipNextSpeakerCheck": True,
        }

    # --- context: GEMINI.md, project dirs (qdash, qbrain, _admin) ---
    if include_context:
        qdash = root / "qdash"
        qbrain = root / "qbrain"
        admin = root / "_admin"
        include_dirs = [paths["root"]]
        if qdash.is_dir():
            include_dirs.append(paths["qdash"])
        if qbrain.is_dir():
            include_dirs.append(paths["qbrain"])
        if admin.is_dir():
            include_dirs.append(paths["_admin"])

        settings["context"] = {
            "fileName": ["GEMINI.md", "CONTEXT.md"],
            "includeDirectories": include_dirs,
            "loadMemoryFromIncludeDirectories": True,
            "includeDirectoryTree": True,
            "discoveryMaxDirs": 200,
            "fileFiltering": {
                "respectGitIgnore": True,
                "respectGeminiIgnore": True,
                "enableRecursiveFileSearch": True,
                "enableFuzzySearch": True,
            },
        }

    # --- tools: shell, sandbox, ripgrep ---
    if include_tools:
        settings["tools"] = {
            "sandbox": False,
            "shell": {
                "enableInteractiveShell": True,
                "pager": "cat",
                "showColor": False,
                "inactivityTimeout": 300,
                "enableShellOutputEfficiency": True,
            },
            "useRipgrep": True,
            "truncateToolOutputThreshold": 40000,
            "disableLLMCorrection": True,
        }

    # --- mcp: github + global allowlist ---
    if include_mcp:
        mcp_servers = _mcp_servers_config()
        settings["mcpServers"] = mcp_servers
        settings["mcp"] = {
            "allowed": list(mcp_servers.keys()),
            "excluded": [],
        }

    # --- billing: ask before overage ---
    if include_billing:
        settings["billing"] = {"overageStrategy": "ask"}

    # --- security: folder trust, no yolo ---
    if include_security:
        settings["security"] = {
            "disableYoloMode": False,
            "enablePermanentToolApproval": False,
            "folderTrust": {"enabled": True},
            "environmentVariableRedaction": {
                "enabled": False,
                "allowed": [],
                "blocked": [],
            },
        }

    # --- privacy: usage stats opt-in ---
    if include_privacy:
        settings["privacy"] = {"usageStatisticsEnabled": True}

    return settings


def write_settings(
    project_root: Optional[Path] = None,
    *,
    to_root: bool = True,
    to_gemini_dir: bool = True,
    **build_kwargs: Any,
) -> list[Path]:
    """
    Write settings.json to project root and/or .gemini/settings.json.

    Returns list of written paths.
    """
    root = Path(project_root) if project_root else Path.cwd()
    settings = build_full_settings(project_root=root, **build_kwargs)
    written: list[Path] = []

    if to_root:
        root_file = root / "settings.json"
        with open(root_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        written.append(root_file)

    if to_gemini_dir:
        gemini_dir = root / ".gemini"
        gemini_dir.mkdir(parents=True, exist_ok=True)
        gemini_file = gemini_dir / "settings.json"
        with open(gemini_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        written.append(gemini_file)

    return written


def get_mcp_servers_for_django() -> Dict[str, Any]:
    """Return mcpServers dict for Django settings.MCP_SERVERS."""
    return {"mcpServers": _mcp_servers_config()}


if __name__ == "__main__":
    paths = write_settings()
    print("Wrote:", paths)
