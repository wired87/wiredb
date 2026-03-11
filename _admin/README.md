# _admin

Admin CLI for BestBrain: discover projects, classify by type, and **start backends and React web frontends** from inferred project dirs with `--local` (React Native is skipped).

## Virtual environment

This project has its **own venv** at `_admin/.venv` (one venv per Python project). Create and use it from **project root**:

```bash
python -m venv _admin/.venv
# Windows:
_admin\.venv\Scripts\activate
# Linux/macOS:
# source _admin/.venv/bin/activate
pip install -r r.txt
```

Run the admin CLI from **project root** so `qbrain` and `_admin` are on the path:

```bash
python -m _admin.main [options]
```

See **docs/VENV_SETUP.md** for the full one-venv-per-project layout (root, _admin, jax_test).

## Entrypoint

```bash
python -m _admin.main [options]
```

## Run locally (no Docker)

Run discovered apps natively by inferring start commands from project structure.

| Option | Description |
|--------|-------------|
| `--run-local` | Run all runnable projects (or the one given by `--run-local-project`). No build/deploy. |
| `--run-local-project PATH` | Run only this project (path relative to repo root, e.g. `qdash`, `jax_test`). |
| `--run-local-port PORT_OR_MAP` | Port or mapping, e.g. `8000` or `backend_drf:8000,frontend:3000`. Defaults: backend 8000, frontend 3000. |
| `--run-local-scan-only` | Print discovered projects with inferred type, command, and cwd; no execution. |

### Inferred commands and run context

| Project path | Type | Has Dockerfile | Inferred local run |
|--------------|------|----------------|--------------------|
| (root) | monolith | Yes | `python startup.py --backend-only` (cwd=root) |
| qbrain | backend_drf | Yes | Root cwd: `python -m daphne ... qbrain.bm.asgi:application` (or root `startup.py --backend-only`) |
| qdash | frontend_react | Yes | cwd=qdash: `npm run start` |
| jax_test | backend_py | Yes | cwd=jax_test: `python test_gnn_run.py` (from Dockerfile CMD) |
| qbrain/core | backend_* | Yes | **Skipped**: VM bootstrap (`startup.sh`), not a standalone app; use root backend. |

- **Root vs qbrain**: Only one Django process is started when both root and qbrain are discovered (root with `startup.py` takes precedence; qbrain is skipped to avoid duplicate backend).
- **Dockerfile CMD/ENTRYPOINT** is parsed and used as a fallback for backend_py (e.g. jax_test).
- Backend ports are assigned in order (8000, 8001, …); frontend ports (3000, 3001, …). Set `PORT` in the environment for frontends (e.g. Create React App respects it).

## Start backends and web frontends (`--local`)

With `--local` (or `--run-local`), the CLI starts backend applications (DRF, FastAPI, pure Python) and React web frontends from inferred project dirs. React Native projects are not started.

| Option | Description |
|--------|-------------|
| `--local` | Start backends and React web frontends from inferred dirs; skip React Native. |
| `--run-local` | Alias for `--local`. |
| `--run-local-project PATH` | Start only this project (e.g. `qdash`, `jax_test`). |
| `--run-local-port PORT_OR_MAP` | Port or mapping (defaults: backend 8000, frontend 3000). |
| `--run-local-testing` | Like `--local` but skip pure-Python backends and set TESTING=1. |
| `--scan-only` | Print discovered and classified project dirs; exit. |
| `--run-local-scan-only` | Print inferred type, start command, and cwd per project; no execution. |

Discovery uses `_admin.project_discovery` and `_admin.bob_builder.docker_scanner`; classification uses `_admin.project_classifier` (backend_drf, backend_fastapi, backend_py, frontend_react, mobile_react_native).

## Record qdash demo (MP4 + HTML for OpenAI app creator)

Start qdash, drive the UI (press buttons), capture HTML at each step, and save a video to project root. The **local path** to the demo MP4 and HTML dir is written to `app_handler/openai_asdk/demo_paths.json` so the OpenAI app creator / submission workflow can use it (e.g. demo video for App Store submission).

| Option | Description |
|--------|-------------|
| `--record-qdash-demo` | Start `cd qdash && npm start`, test app (click buttons), capture HTML and record video; save MP4 (or WebM) in project root; write paths to `openai_asdk/demo_paths.json`. |
| `--qdash-demo-out PATH` | Output path for demo video (default: `project_root/qdash_demo.mp4`). |

**Requires:** `pip install playwright` and `playwright install chromium`. If ffmpeg is installed, output is MP4; otherwise WebM.

**Usage:**

```bash
python -m _admin.main --record-qdash-demo
python -m _admin.main --record-qdash-demo --qdash-demo-out ./my_demo.mp4
```

**Local path for OpenAI app creator:** After a successful run, `app_handler/openai_asdk/config.py` exposes `get_demo_paths()` and `get_demo_video_path()`; the workflow prints them in STEP 6b. Use the returned paths when submitting the app (e.g. attach demo video or reference HTML captures).
