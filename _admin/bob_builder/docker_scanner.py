"""
Scan project root for directories that contain a Dockerfile and collect them for building.
"""
from pathlib import Path


def get_project_root() -> Path:
    """Project root: bob_builder lives under _admin/bob_builder."""
    bob_builder_dir = Path(__file__).resolve().parent
    return bob_builder_dir.parent.parent


# Directories to skip when scanning for Dockerfiles (internal/tooling, not deployable apps)
_DOCKERFILE_SCAN_SKIP_PARTS = frozenset({"_admin", ".git", "node_modules", "__pycache__"})


def find_dockerfile_dirs(project_root: Path | None = None) -> list[tuple[Path, str]]:
    """
    Scan all direct and nested directories under project_root for a file named 'Dockerfile'.
    Returns a list of (directory_path, image_name) where image_name is derived from the dir name.

    Only considers directories that contain a file named exactly 'Dockerfile' (case-sensitive).
    Skips paths under _admin, .git, node_modules, __pycache__ so only app/component images are built.
    """
    root = project_root or get_project_root()
    try:
        root = Path(root).resolve()
    except Exception:
        root = Path(root)
    if not root.is_dir():
        return []

    results: list[tuple[Path, str]] = []

    for path in root.rglob("Dockerfile"):
        if not path.is_file():
            continue
        dir_path = path.parent
        if _DOCKERFILE_SCAN_SKIP_PARTS.intersection(dir_path.parts):
            continue
        image_name = _dir_to_image_name(dir_path, root)
        results.append((dir_path, image_name))

    results.sort(key=lambda x: str(x[0]))
    return results


def _dir_to_image_name(dir_path: Path, project_root: Path) -> str:
    """Convert directory path to a valid Docker image name (lowercase, alphanumeric + underscore)."""
    name = dir_path.name
    if dir_path == project_root:
        # Root Dockerfile: use project root folder name
        name = project_root.name
    elif dir_path.name == "core" and dir_path.parent.name == "qbrain":
        # Avoid ambiguous "core" project/image name in user-visible lists
        name = "qbrain-core"
    normalized = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
    normalized = normalized.lower().strip("._-") or "image"
    return normalized
