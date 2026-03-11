"""
Collect all project files and dirs (except README, _admin, miracleai, jax_test,
qdash, LICENSE, and general project files) into a single qbrain package.
"""
from pathlib import Path
import shutil

# Project root = parent of _admin (bob_builder lives under _admin/bob_builder)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Names to exclude from collection (top-level dirs and files only)
QBRAIN_EXCLUDE = frozenset({
    # Explicit exclusions
    "README.md",
    "LICENSE",
    "_admin",  # bob_builder, _ray_core live here
    "bob_builder",
    "MiracleAI",
    "miracleai",
    "jax_test",
    "qdash",
    "qbrain",  # avoid collecting into self
    # General project / tooling
    ".git",
    ".gitignore",
    ".env",
    ".env.example",
    ".dockerignore",
    ".cursor",
    ".idea",
    ".venv",
    ".agent",
    "__pycache__",
    "r.txt",
    "manage.py",
    "Dockerfile",
    "startup.sh",
    "startup.py",
    "node_modules",
    "static_root",
    "media",
    "outputs",
})


def get_collectible_items(root: Path | None = None) -> tuple[list[Path], list[Path]]:
    """Return (dirs, files) under root that should be collected into qbrain."""
    root = root or PROJECT_ROOT
    dirs: list[Path] = []
    files: list[Path] = []
    for p in root.iterdir():
        name = p.name
        if name in QBRAIN_EXCLUDE:
            continue
        if p.is_dir():
            dirs.append(p)
        else:
            files.append(p)
    return (sorted(dirs), sorted(files))


def collect_into_qbrain(root: Path | None = None, copy: bool = True) -> Path:
    """
    Create qbrain/ and copy (or move) all collectible dirs and files into it.
    Returns the path to the qbrain package directory.
    """
    root = root or PROJECT_ROOT
    qbrain_dir = root / "qbrain"
    qbrain_dir.mkdir(exist_ok=True)

    dirs, files = get_collectible_items(root)
    op = shutil.copytree if copy else shutil.move
    op_file = shutil.copy2 if copy else shutil.move

    for d in dirs:
        dest = qbrain_dir / d.name
        if dest.exists():
            shutil.rmtree(dest)
        if copy:
            shutil.copytree(d, dest, ignore=shutil.ignore_patterns("__pycache__", ".git", ".pyc"))
        else:
            shutil.move(str(d), str(dest))

    for f in files:
        dest = qbrain_dir / f.name
        if dest.exists():
            dest.unlink()
        op_file(str(f), str(dest))

    # Write __init__.py and manifest
    _write_qbrain_init(qbrain_dir, dirs, files)
    _write_manifest(qbrain_dir, dirs, files)
    return qbrain_dir


def _write_manifest(qbrain_dir: Path, dirs: list[Path], files: list[Path]) -> None:
    """Write qbrain/PACKAGE_CONTENTS.md listing collected dirs and files."""
    content = [
        "# qbrain package contents",
        "",
        "Collected from project root (excluding README.md, _admin, MiracleAI, jax_test, qdash, LICENSE, and general project files).",
        "",
        "## Directories",
        "",
    ]
    for d in dirs:
        content.append(f"- `{d.name}/`")
    content.extend(["", "## Top-level files", ""])
    for f in files:
        content.append(f"- `{f.name}`")
    (qbrain_dir / "PACKAGE_CONTENTS.md").write_text("\n".join(content), encoding="utf-8")


def _write_qbrain_init(qbrain_dir: Path, dirs: list[Path], files: list[Path]) -> None:
    """Write qbrain/__init__.py listing collected subpackages and modules."""
    subpackages = [d.name for d in dirs]
    modules = [f.stem for f in files if f.suffix == ".py" and f.name != "__init__.py"]
    lines = [
        '"""',
        "qbrain package: collected application code (core, bm, auth, graph, etc.).",
        "Excludes: README.md, _admin, MiracleAI, jax_test, qdash, LICENSE, general project files.",
        '"""',
        "",
        "__all__ = [",
    ]
    for n in sorted(subpackages) + sorted(modules):
        lines.append(f'    {n!a},')
    lines.append("]")
    (qbrain_dir / "__init__.py").write_text("\n".join(lines), encoding="utf-8")


def list_collectible(root: Path | None = None) -> dict[str, list[str]]:
    """Return dict of 'dirs' and 'files' names that would be collected (for manifest/docs)."""
    root = root or PROJECT_ROOT
    dirs, files = get_collectible_items(root)
    return {
        "dirs": [p.name for p in dirs],
        "files": [p.name for p in files],
    }
