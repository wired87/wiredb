"""
MCP Master: scans relay cases, exposes HTTP routes, and generates multi-client MCP config files.
"""
import ast
import importlib
import importlib.util
import json
import os
import pprint
from pathlib import Path
from typing import Any, Dict

from _admin.mcp_master.client_generators import (
    load_registry,
    normalize_services,
    render_claude_desktop_config,
    render_cursor_mcp_json,
    render_gemini_extension,
    render_gemini_markdown,
    render_gemini_settings,
    render_openai_connector_manifest,
)


def _resolve_qbrain_root() -> str:
    """Resolve qbrain package root (parent of bm)."""
    this = Path(__file__).resolve()
    project_root = this.parent.parent.parent
    qbrain = project_root / "qbrain"
    return str(qbrain) if qbrain.is_dir() else str(project_root)


class MCPMaster:
    def __init__(self):
        self.rbp = None
        self.relay_cfg: Dict[str, Any] = {}

        self.project_root = Path(__file__).resolve().parents[2]
        self.base_dir = self.project_root / "_admin" / "mcp_master"
        self.services_dir = self.base_dir / "services"
        self.clients_dir = self.base_dir / "clients"
        self.registry_path = self.services_dir / "mcp_services.json"
        self.registry: Dict[str, Any] = {}
        self.normalized_services: list[Dict[str, Any]] = []

        self.server_struct_out = str(self.base_dir / "mcp_server")

    def main(self) -> None:
        print("MCP conversion...")
        gen = self.generate_multi_client_configs()
        print("multi-client generation:", gen)
        self.relay_cfg = self.scan_cases_and_update_relay()
        self.expose_api()
        print("MCP conversion... done")

    def _default_registry(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "description": "Canonical MCP service registry for multi-client config generation.",
            "services": [
                {
                    "id": "eq-storage",
                    "description": "Primary eq_storage MCP server (streamable HTTP).",
                    "transport": "command",
                    "command": "py",
                    "args": ["-m", "_admin.mcp_master.mcp_server"],
                    "cwd": "${PROJECT_ROOT}",
                    "env": {
                        "MCP_HOST": "${MCP_HOST}",
                        "MCP_PORT": "${MCP_PORT}",
                        "MCP_PATH": "${MCP_PATH}",
                    },
                    "meta": {"timeout": 60000, "trust": False},
                },
                {
                    "id": "github",
                    "description": "Official GitHub MCP server via Docker image.",
                    "transport": "command",
                    "command": "docker",
                    "args": [
                        "run",
                        "-i",
                        "--rm",
                        "-e",
                        "GITHUB_PERSONAL_ACCESS_TOKEN",
                        "ghcr.io/modelcontextprotocol/servers/github:latest",
                    ],
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}",
                    },
                    "meta": {"timeout": 60000, "trust": False},
                },
            ],
            "openai": {
                "connector_name": "eq-storage",
                "connector_description": "MCP connector for eq_storage graph and equation tooling.",
                "public_endpoint_env": "OPENAI_MCP_ENDPOINT",
            },
        }

    def ensure_registry_exists(self) -> Path:
        self.services_dir.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(self._default_registry(), f, indent=2, ensure_ascii=False)
        return self.registry_path

    def load_registry(self) -> Dict[str, Any]:
        self.ensure_registry_exists()
        self.registry = load_registry(self.registry_path)
        return self.registry

    def build_normalized_services(self, *, resolve_env: bool = False) -> list[Dict[str, Any]]:
        if not self.registry:
            self.load_registry()
        self.normalized_services = normalize_services(self.registry, resolve_env=resolve_env)
        return self.normalized_services

    def _extract_cases(self) -> list[Dict[str, Any]]:
        cases: list[Dict[str, Any]] = []
        try:
            from qbrain.predefined_case import RELAY_CASES_CONFIG  # type: ignore

            if isinstance(RELAY_CASES_CONFIG, list):
                for item in RELAY_CASES_CONFIG:
                    if isinstance(item, dict):
                        cases.append(item)
        except Exception:
            pass

        if not cases and isinstance(self.relay_cfg, dict):
            for key, value in self.relay_cfg.items():
                if isinstance(value, dict):
                    cases.append(
                        {
                            "case": value.get("case", key),
                            "desc": value.get("desc", ""),
                            "req_struct": value.get("req_struct", {}),
                        }
                    )
        return cases

    def _write_if_changed(self, path: Path, content: str) -> bool:
        path.parent.mkdir(parents=True, exist_ok=True)
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old == content:
            return False
        path.write_text(content, encoding="utf-8")
        return True

    def _write_json_if_changed(self, path: Path, payload: Dict[str, Any]) -> bool:
        return self._write_if_changed(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    def generate_multi_client_configs(self, *, resolve_env: bool = False) -> Dict[str, Any]:
        self.load_registry()
        services = self.build_normalized_services(resolve_env=resolve_env)
        cases = self._extract_cases()

        outputs = {
            "cursor": self.clients_dir / "cursor" / "mcp.json",
            "gemini_extension": self.clients_dir / "gemini" / "gemini-extension.json",
            "gemini_md": self.clients_dir / "gemini" / "GEMINI.md",
            "gemini_settings": self.clients_dir / "gemini" / "settings.json",
            "claude": self.clients_dir / "claude" / "claude_desktop_config.json",
            "openai_connector": self.clients_dir / "openai" / "openai_connector_manifest.json",
            "openai_submission": self.clients_dir / "openai" / "app_submission_manifest.json",
        }

        changed = {
            "cursor": self._write_json_if_changed(outputs["cursor"], render_cursor_mcp_json(services)),
            "gemini_extension": self._write_json_if_changed(outputs["gemini_extension"], render_gemini_extension(services)),
            "gemini_md": self._write_if_changed(outputs["gemini_md"], render_gemini_markdown(cases)),
            "gemini_settings": self._write_json_if_changed(outputs["gemini_settings"], render_gemini_settings(services)),
            "claude": self._write_json_if_changed(outputs["claude"], render_claude_desktop_config(services)),
            "openai_connector": self._write_json_if_changed(
                outputs["openai_connector"],
                render_openai_connector_manifest(self.registry),
            ),
            "openai_submission": False,
        }

        try:
            from _admin.app_handler.openai_asdk.submission_manifest import build_submission_manifest

            payload = build_submission_manifest()
            changed["openai_submission"] = self._write_json_if_changed(outputs["openai_submission"], payload)
        except Exception:
            changed["openai_submission"] = False

        return {
            "outputs": {k: str(v) for k, v in outputs.items()},
            "changed": changed,
            "service_count": len(services),
            "case_count": len(cases),
        }

    def validate_generated_configs(self) -> Dict[str, Any]:
        required_files = [
            self.clients_dir / "cursor" / "mcp.json",
            self.clients_dir / "gemini" / "gemini-extension.json",
            self.clients_dir / "gemini" / "settings.json",
            self.clients_dir / "claude" / "claude_desktop_config.json",
            self.clients_dir / "openai" / "openai_connector_manifest.json",
        ]
        missing = [str(p) for p in required_files if not p.exists()]
        json_errors = []
        for p in required_files:
            if not p.exists():
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception as e:
                json_errors.append({"path": str(p), "error": str(e)})

        return {
            "ok": not missing and not json_errors,
            "missing": missing,
            "json_errors": json_errors,
        }

    def set_route_blueprint(self):
        from rest_framework.views import APIView
        from requests import Response

        class RouteBlueprint(APIView):
            """POST mcp/{sub_route}/{case} — invoke relay case handler."""

            def post(self, request, *args, **kwargs):
                try:
                    response = self.case_struct["func"](*request.data)
                    return Response(response)
                except Exception as e:
                    return Response({"error": str(e)})

        return RouteBlueprint

    def expose_api(self) -> None:
        from django.conf import settings
        from django.urls import path

        print("expose_api...")
        server_struct = []

        urls = importlib.import_module(settings.ROOT_URLCONF)
        route_view = self.set_route_blueprint()

        for sub_route, items in self.relay_cfg.items():
            for item in items:
                route = f"mcp/{sub_route}/{item['case']}"
                urls.urlpatterns.append(path(route, route_view.as_view(case_struct=item)))
                server_struct.append(
                    {
                        "endpoint": route,
                        "req_struct": item["req_struct"],
                        "description": item["desc"],
                    }
                )
        print("expose_api... done")

    def scan_cases_and_update_relay(self, root_dir: str | None = None) -> Dict[str, Any]:
        if root_dir is None:
            root_dir = _resolve_qbrain_root()

        root_dir = os.path.normpath(root_dir)
        result: Dict[str, Any] = {
            "scanned": 0,
            "relay_cases_found": 0,
            "imported": 0,
            "errors": [],
        }
        relay_cfg: Dict[str, Any] = {}
        skip_dirs = {"__pycache__", ".git", "venv", ".venv", "node_modules"}

        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]

            for name in filenames:
                if name != "case.py":
                    continue
                filepath = os.path.join(dirpath, name)
                result["scanned"] += 1

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        code = f.read()
                except Exception as e:
                    result["errors"].append({"path": filepath, "error": str(e)})
                    continue

                try:
                    tree = ast.parse(code)
                except Exception as e:
                    result["errors"].append({"path": filepath, "error": f"AST parse error: {e}"})
                    continue

                relay_vars = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and "RELAY" in target.id:
                                relay_vars.append(target.id)

                if not relay_vars:
                    continue

                result["relay_cases_found"] += len(relay_vars)

                try:
                    spec = importlib.util.spec_from_file_location("relay_case_module", filepath)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                except Exception as e:
                    result["errors"].append({"path": filepath, "error": f"Import error: {e}"})
                    continue

                for var in relay_vars:
                    try:
                        value = getattr(module, var)
                        relay_cfg[var] = value
                        result["imported"] += 1
                    except Exception as e:
                        result["errors"].append(
                            {"path": filepath, "error": f"Variable load error {var}: {e}"}
                        )

        print("case structs found")
        pprint.pp(result)
        return relay_cfg
