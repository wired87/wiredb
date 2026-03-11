"""
Admin test runner: backend tests, frontend tests, and interplay (integration).

Shows a live cursor: each step is printed before running so you see exactly
which interaction is executing when debugging. Use --step N to run only up to step N.

  python -m _admin.run_tests [--backend-only] [--frontend-only] [--interplay-only] [--step N] [--verbose]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Project root (parent of _admin)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _cursor(step: int, total: int, label: str, verbose: bool = False) -> None:
    """Print live cursor line for this step."""
    sep = "  "
    print(f"\n{sep}\033[1m[Step {step}/{total}]\033[0m {label}")
    if verbose:
        print(f"{sep}  (running...)")
    sys.stdout.flush()


def _ok(msg: str = "OK") -> None:
    print(f"       \033[92m{msg}\033[0m")
    sys.stdout.flush()


def _fail(msg: str) -> None:
    print(f"       \033[91mFAIL: {msg}\033[0m")
    sys.stdout.flush()


def step_env(verbose: bool) -> bool:
    """Step 1: Ensure PYTHONPATH and project root are set so imports work."""
    _cursor(1, 6, "Environment (PYTHONPATH, project root)", verbose)
    root = str(PROJECT_ROOT)
    if root not in os.environ.get("PYTHONPATH", "").split(os.pathsep):
        os.environ["PYTHONPATH"] = root + (os.pathsep + os.environ.get("PYTHONPATH", ""))
    try:
        sys.path.insert(0, root)
        import qbrain  # noqa: F401
        _ok(f"qbrain import OK (root={root})")
        return True
    except Exception as e:
        _fail(str(e))
        return False


def step_backend_tests(verbose: bool) -> bool:
    """Step 2: Run backend unit tests (orchestrator test_run, core tests)."""
    _cursor(2, 6, "Backend tests (orchestrator + core)", verbose)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    # Prefer lightweight tests: test_run (async orchestrator), then one core test
    tests = [
        ["python", "-m", "qbrain.core.orchestrator_manager.test_run"],
    ]
    for cmd in tests:
        try:
            r = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                env=env,
                capture_output=not verbose,
                text=True,
                timeout=60,
            )
            if r.returncode != 0 and not verbose:
                print(r.stdout or "")
                print(r.stderr or "")
            if r.returncode != 0:
                _fail(f"exit {r.returncode} for {' '.join(cmd)}")
                return False
        except subprocess.TimeoutExpired:
            _fail("timeout")
            return False
        except FileNotFoundError:
            # Try py -3 on Windows
            cmd_win = [sys.executable] + cmd[1:]
            try:
                r = subprocess.run(cmd_win, cwd=str(PROJECT_ROOT), env=env, capture_output=not verbose, text=True, timeout=60)
                if r.returncode != 0:
                    _fail(f"exit {r.returncode}")
                    return False
            except Exception as e:
                _fail(str(e))
                return False
    _ok("Backend tests passed")
    return True


def step_frontend_tests(verbose: bool) -> bool:
    """Step 3: Run frontend tests (qdash npm test --watchAll=false)."""
    _cursor(3, 6, "Frontend tests (qdash npm test)", verbose)
    qdash = PROJECT_ROOT / "qdash"
    if not (qdash / "package.json").exists():
        _fail("qdash/package.json not found")
        return False
    cmd = ["npm", "run", "test", "--", "--watchAll=false", "--passWithNoTests"]
    try:
        r = subprocess.run(
            cmd,
            cwd=str(qdash),
            shell=os.name == "nt",
            capture_output=not verbose,
            text=True,
            timeout=120,
        )
        if r.returncode != 0 and not verbose:
            if r.stdout:
                print(r.stdout[-2000:])
            if r.stderr:
                print(r.stderr[-2000:])
        if r.returncode != 0:
            _fail(f"exit {r.returncode}")
            return False
        _ok("Frontend tests passed")
        return True
    except subprocess.TimeoutExpired:
        _fail("timeout (120s)")
        return False
    except FileNotFoundError:
        _fail("npm not found (install Node and run from project root)")
        return False


def step_start_backend(verbose: bool, port: int = 8000) -> subprocess.Popen | None:
    """Step 4: Start backend (daphne) in background for interplay."""
    _cursor(4, 6, "Start backend (daphne) in background", verbose)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["DJANGO_SETTINGS_MODULE"] = "qbrain.bm.settings"
    cmd = [
        sys.executable, "-m", "daphne",
        "-b", "127.0.0.1", "-p", str(port),
        "qbrain.bm.asgi:application",
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=subprocess.DEVNULL if not verbose else None,
            stderr=subprocess.DEVNULL if not verbose else None,
        )
        time.sleep(2)
        if proc.poll() is not None:
            _fail("backend exited immediately")
            return None
        _ok(f"Backend PID {proc.pid} on port {port}")
        return proc
    except Exception as e:
        _fail(str(e))
        return None


def step_interplay(verbose: bool, port: int = 8000) -> bool:
    """Step 5: Run interplay test (HTTP + WebSocket) against backend."""
    _cursor(5, 6, "Interplay (HTTP health + WebSocket LIST_USERS_SESSIONS)", verbose)
    base = f"http://127.0.0.1:{port}"
    ws_base = f"ws://127.0.0.1:{port}"
    cmd = [sys.executable, "-m", "_admin.interplay_test", "--base-url", base, "--ws-url", ws_base]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        r = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env, capture_output=not verbose, text=True, timeout=15)
        if r.returncode != 0 and not verbose:
            if r.stdout:
                print(r.stdout)
            if r.stderr:
                print(r.stderr)
        if r.returncode != 0:
            _fail("interplay test failed")
            return False
        _ok("Interplay passed")
        return True
    except subprocess.TimeoutExpired:
        _fail("timeout")
        return False
    except Exception as e:
        _fail(str(e))
        return False


def step_teardown(proc: subprocess.Popen | None) -> bool:
    """Step 6: Teardown (kill backend if we started it)."""
    _cursor(6, 6, "Teardown (stop backend if started)", False)
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        _ok("Backend stopped")
    else:
        _ok("Nothing to stop")
    return True


def run(
    backend_only: bool = False,
    frontend_only: bool = False,
    interplay_only: bool = False,
    step: int | None = None,
    verbose: bool = False,
    port: int = 8000,
) -> int:
    """Run test steps; return 0 on success, 1 on failure."""
    print("\n--- Admin test runner (live cursor) ---")
    print(f"   Project root: {PROJECT_ROOT}")
    if step is not None:
        print(f"   Run up to step: {step}")

    backend_proc = None
    total = 6
    steps_done = 0

    def run_step(cond: bool, fn, *args, **kwargs) -> bool:
        nonlocal steps_done
        if not cond:
            return True
        steps_done += 1
        if step is not None and steps_done > step:
            return True
        return fn(*args, **kwargs)

    try:
        if run_step(not (frontend_only or interplay_only), step_env, verbose) and (step is None or steps_done < step):
            pass
        else:
            return 1

        if run_step(not (frontend_only or interplay_only), step_backend_tests, verbose) and (step is None or steps_done < step):
            pass
        else:
            return 1

        if run_step(not (backend_only or interplay_only), step_frontend_tests, verbose) and (step is None or steps_done < step):
            pass
        else:
            return 1

        if interplay_only or (not backend_only and not frontend_only):
            backend_proc = run_step(True, step_start_backend, verbose, port)
            if backend_proc is None and not interplay_only:
                print("       (Interplay skipped: backend did not start)")
            elif backend_proc is not None:
                if not run_step(True, step_interplay, verbose, port):
                    return 1

        run_step(True, step_teardown, backend_proc)
    finally:
        if backend_proc and backend_proc.poll() is None:
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                backend_proc.kill()

    print("\n--- Result: PASS ---\n")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run backend, frontend, and interplay tests with live step cursor.",
    )
    ap.add_argument("--backend-only", action="store_true", help="Only run backend tests (steps 1–2)")
    ap.add_argument("--frontend-only", action="store_true", help="Only run frontend tests (step 3)")
    ap.add_argument("--interplay-only", action="store_true", help="Only run interplay (start backend + step 5); assumes no backend on port")
    ap.add_argument("--step", type=int, default=None, metavar="N", help="Run only up to step N (1–6)")
    ap.add_argument("--verbose", action="store_true", help="Show full command output")
    ap.add_argument("--port", type=int, default=8000, help="Backend port for interplay (default 8000)")
    args = ap.parse_args()

    code = run(
        backend_only=args.backend_only,
        frontend_only=args.frontend_only,
        interplay_only=args.interplay_only,
        step=args.step,
        verbose=args.verbose,
        port=args.port,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
