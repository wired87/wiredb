"""
Gemini config wrapper that delegates generation to MCPMaster's canonical pipeline.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

from _admin.mcp_master.mcp_master import MCPMaster


def _basedir() -> Path:
    return Path(__file__).resolve().parent.parent.parent


class GeminiCfgCreator:
    """Backward-compatible API around centralized MCPMaster generation."""

    def __init__(self, basedir_path: Optional[Path] = None):
        self.basedir = Path(basedir_path) if basedir_path else _basedir()
        self.mcpmaster = self.basedir / "_admin" / "mcp_master" / "clients" / "gemini"

    def gem_cli_cfg_creator(self, use_gem: bool = True, out_dir: Optional[Path] = None) -> Path:
        return gem_cli_cfg_creator(
            basedir_path=self.basedir,
            use_gem=use_gem,
            out_dir=out_dir or self.mcpmaster,
        )


def gem_cli_cfg_creator(
    basedir_path: Optional[Path] = None,
    use_gem: bool = True,
    out_dir: Optional[Path] = None,
) -> Path:
    """
    Generate gemini-extension.json + GEMINI.md from MCPMaster canonical service registry.
    """
    _ = use_gem  # Kept for API compatibility; generation now uses canonical templates.
    master = MCPMaster()
    master.generate_multi_client_configs(resolve_env=False)

    source_dir = master.clients_dir / "gemini"
    source_cfg = source_dir / "gemini-extension.json"
    source_md = source_dir / "GEMINI.md"
    source_settings = source_dir / "settings.json"
    if not source_cfg.exists():
        raise FileNotFoundError(f"Expected generated config missing: {source_cfg}")

    out_path = Path(out_dir) if out_dir else source_dir
    out_path.mkdir(parents=True, exist_ok=True)

    target_cfg = out_path / "gemini-extension.json"
    target_md = out_path / "GEMINI.md"
    target_settings = out_path / "settings.json"
    if source_cfg.resolve() != target_cfg.resolve():
        shutil.copy2(source_cfg, target_cfg)
    if source_md.exists():
        if source_md.resolve() != target_md.resolve():
            shutil.copy2(source_md, target_md)
    if source_settings.exists():
        if source_settings.resolve() != target_settings.resolve():
            shutil.copy2(source_settings, target_settings)

    # Keep old root-level files in sync for compatibility with existing workflows.
    legacy_root = master.base_dir
    legacy_cfg = legacy_root / "gemini-extension.json"
    legacy_md = legacy_root / "GEMINI.md"
    legacy_cfg.write_text(target_cfg.read_text(encoding="utf-8"), encoding="utf-8")
    if target_md.exists():
        legacy_md.write_text(target_md.read_text(encoding="utf-8"), encoding="utf-8")

    return target_cfg


if __name__ == "__main__":
    out = gem_cli_cfg_creator()
    print(f"Created: {out}")
