"""
Classify project paths as backend (DRF / FastAPI / pure Python), frontend (React), or mobile (React Native).
Used by Admin to choose build strategy per path.
"""
from pathlib import Path
import json

# Project type constants
BACKEND_DRF = "backend_drf"           # Django / Django REST Framework
BACKEND_FASTAPI = "backend_fastapi"   # FastAPI
BACKEND_PY = "backend_py"             # Pure Python app (no framework)
FRONTEND_REACT = "frontend_react"     # React (CRA, Vite, etc.)
MOBILE_REACT_NATIVE = "mobile_react_native"
UNKNOWN = "unknown"

PROJECT_TYPES = (BACKEND_DRF, BACKEND_FASTAPI, BACKEND_PY, FRONTEND_REACT, MOBILE_REACT_NATIVE, UNKNOWN)


def classify(path: Path, project_root: Path | None = None) -> str:
    """
    Classify a directory path as one of backend_drf, backend_fastapi, backend_py,
    frontend_react, mobile_react_native, or unknown.
    """
    if not path.is_dir():
        return UNKNOWN
    path = path.resolve()
    proj_root = Path(project_root).resolve() if project_root else None

    # --- Repo root monolith: qbrain/bm/settings.py (no manage.py at root) ---
    if proj_root is not None and path == proj_root:
        if (path / "qbrain" / "bm" / "settings.py").exists():
            return BACKEND_DRF

    # --- Frontend / Mobile: package.json ---
    pkg = path / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            deps_lower = {k.lower(): str(v).lower() for k, v in deps.items()}
            if "react-native" in deps_lower or any("react-native" in k for k in deps_lower):
                return MOBILE_REACT_NATIVE
            if "react" in deps_lower or any("react" in k for k in deps_lower):
                return FRONTEND_REACT
        except Exception:
            pass
        return FRONTEND_REACT  # package.json with no react -> still treat as possible frontend

    # --- Backend: Python markers ---
    manage_py = path / "manage.py"
    if manage_py.exists():
        # Likely Django; confirm with settings or asgi
        if (path / "settings.py").exists() or (path / "asgi.py").exists() or (path / "wsgi.py").exists():
            return BACKEND_DRF
        for sub in ("bm", "config", "core"):
            if (path / sub / "settings.py").exists():
                return BACKEND_DRF
        # Monolith: project root with manage.py and qbrain/bm (e.g. BestBrain root)
        if proj_root is not None and path == proj_root and (path / "qbrain" / "bm" / "settings.py").exists():
            return BACKEND_DRF
        return BACKEND_DRF

    # Subdirs that commonly contain Django app (e.g. qbrain/bm)
    for sub in ["bm", "config", "core"]:
        settings_candidate = path / sub / "settings.py"
        if settings_candidate.exists():
            try:
                t = settings_candidate.read_text(encoding="utf-8", errors="ignore")
                if "INSTALLED_APPS" in t or "django" in t.lower():
                    return BACKEND_DRF
            except Exception:
                pass

    # FastAPI: main.py with FastAPI() or requirements with fastapi
    req_txt = path / "requirements.txt"
    req_content = ""
    if req_txt.exists():
        req_content = req_txt.read_text(encoding="utf-8", errors="ignore").lower()
    if "fastapi" in req_content:
        return BACKEND_FASTAPI

    pyproject = path / "pyproject.toml"
    if pyproject.exists():
        try:
            t = pyproject.read_text(encoding="utf-8", errors="ignore").lower()
            if "fastapi" in t:
                return BACKEND_FASTAPI
        except Exception:
            pass

    for main_candidate in ["main.py", "app.py"]:
        main_p = path / main_candidate
        if main_p.exists():
            try:
                t = main_p.read_text(encoding="utf-8", errors="ignore")
                if "FastAPI(" in t or "from fastapi import" in t:
                    return BACKEND_FASTAPI
            except Exception:
                pass

    # Pure Python: requirements.txt or pyproject.toml, no Django/FastAPI
    if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
        return BACKEND_PY

    return UNKNOWN


def classify_with_docker(path: Path, project_root: Path | None = None) -> tuple[str, bool]:
    """
    Return (project_type, has_dockerfile).
    """
    kind = classify(path, project_root)
    has_docker = (path / "Dockerfile").exists()
    return kind, has_docker
