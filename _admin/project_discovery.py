"""
Discover all project paths under project root (Dockerfile dirs + package.json / manage.py / etc.),
then classify each. Used by Admin to build by type.
"""
from pathlib import Path

from _admin.bob_builder.docker_scanner import (
    find_dockerfile_dirs,
    get_project_root,
)
from _admin.project_classifier import (
    classify_with_docker,
    BACKEND_DRF,
    BACKEND_FASTAPI,
    BACKEND_PY,
    FRONTEND_REACT,
    MOBILE_REACT_NATIVE,
    UNKNOWN,
)


def _dir_to_image_name(dir_path: Path, project_root: Path) -> str:
    """Same logic as docker_scanner: valid Docker image name from dir name."""
    name = dir_path.name
    if dir_path == project_root:
        name = project_root.name
    elif dir_path.name == "core" and dir_path.parent.name == "qbrain":
        # Avoid ambiguous "core" project/image name in user-visible lists
        name = "qbrain-core"
    normalized = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
    return normalized.lower().strip("._-") or "image"


def discover_projects(
    project_root: Path | None = None,
    max_depth: int = 2,
) -> list[tuple[Path, str, str, bool]]:
    """
    Discover all project paths under project root, classify each.
    Returns list of (path, image_name, project_type, has_dockerfile).

    - Paths with a Dockerfile are always included (from find_dockerfile_dirs).
    - Additional paths: direct children of root (depth 1) that have package.json,
      manage.py, requirements.txt, or pyproject.toml; and at depth 2 we only add
      dirs that have a Dockerfile (already covered).
    """
    root = (project_root or get_project_root())
    try:
        root = root.resolve()
    except Exception:
        pass
    if not root.is_dir():
        return []

    # 1) All dirs that have a Dockerfile (existing behavior)
    dockerfile_pairs = find_dockerfile_dirs(root)
    by_path = {str(p): (p, name) for p, name in dockerfile_pairs}

    # Top-level dirs to never treat as projects (tooling / meta)
    _skip_top_dirs = frozenset({"_admin", ".git", "node_modules", "docs"})

    # 2) Top-level dirs that look like projects (no Dockerfile yet)
    for child in root.iterdir():
        if not child.is_dir() or child.name in _skip_top_dirs:
            continue
        key = str(child)
        if key in by_path:
            continue
        if (child / "package.json").exists() or (child / "manage.py").exists():
            by_path[key] = (child, _dir_to_image_name(child, root))
        elif (child / "requirements.txt").exists() or (child / "pyproject.toml").exists():
            by_path[key] = (child, _dir_to_image_name(child, root))

    # 3) Classify each
    result = []
    for path, image_name in sorted(by_path.values(), key=lambda x: str(x[0])):
        project_type, has_docker = classify_with_docker(path, root)
        result.append((path, image_name, project_type, has_docker))

    return result
