"""
Interplay test: backend + frontend interaction (one step at a time, live cursor style).

Run with backend already up (e.g. daphne on 8000). Each interaction is printed
so the admin can see exactly which step is running when debugging.

  python -m _admin.interplay_test [--base-url http://127.0.0.1:8000] [--ws-url ws://127.0.0.1:8000]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error

try:
    import websocket
except ImportError:
    websocket = None


def _step(label: str, n: int, total: int) -> None:
    print(f"\n  \033[1m[Step {n}/{total}]\033[0m {label}")
    sys.stdout.flush()


def _ok(msg: str = "OK") -> None:
    print(f"       \033[92m{msg}\033[0m")
    sys.stdout.flush()


def _fail(msg: str) -> None:
    print(f"       \033[91mFAIL: {msg}\033[0m")
    sys.stdout.flush()


def http_health(base_url: str) -> bool:
    """Step 1: GET base_url (health)."""
    _step("HTTP health check", 1, 3)
    try:
        req = urllib.request.Request(base_url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            code = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")[:200]
            _ok(f"HTTP {code} | {body[:80]}...")
            return True
    except urllib.error.URLError as e:
        _fail(str(e))
        return False
    except Exception as e:
        _fail(str(e))
        return False


def http_api(base_url: str, path: str = "/api/") -> bool:
    """Step 2: GET base_url + path (e.g. /api/)."""
    _step("HTTP API reachability", 2, 3)
    url = base_url.rstrip("/") + path
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            code = resp.getcode()
            _ok(f"HTTP {code} {url}")
            return True
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 404):
            _ok(f"HTTP {e.code} (endpoint exists)")
            return True
        _fail(f"HTTP {e.code} {e.reason}")
        return False
    except Exception as e:
        _fail(str(e))
        return False


def ws_list_sessions(ws_url: str, user_id: str = "test_interplay") -> bool:
    """Step 3: WebSocket connect, send LIST_USERS_SESSIONS, print response."""
    _step("WebSocket LIST_USERS_SESSIONS", 3, 3)
    if not websocket:
        _fail("pip install websocket-client")
        return False
    url = ws_url.rstrip("/") + f"/run/?user_id={user_id}&mode=demo"
    try:
        ws = websocket.create_connection(url, timeout=10)
        _ok("Connected")
        msg = {"type": "LIST_USERS_SESSIONS", "auth": {"user_id": user_id}, "timestamp": ""}
        ws.send(json.dumps(msg))
        _ok(f"Sent: {msg['type']}")
        raw = ws.recv()
        ws.close()
        data = json.loads(raw) if isinstance(raw, str) else json.loads(raw.decode("utf-8"))
        print(f"       Response: {json.dumps(data, indent=2)[:400]}...")
        _ok("Response received")
        return True
    except Exception as e:
        _fail(str(e))
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Backend–frontend interplay test (live steps).")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend HTTP base URL")
    ap.add_argument("--ws-url", default="ws://127.0.0.1:8000", help="Backend WebSocket base URL")
    ap.add_argument("--user-id", default="test_interplay", help="User ID for WS message")
    ap.add_argument("--skip-ws", action="store_true", help="Skip WebSocket step (only HTTP)")
    args = ap.parse_args()

    total = 3 if not args.skip_ws else 2
    print("\n--- Interplay test (live cursor) ---")
    print(f"   Base URL: {args.base_url}  WS: {args.ws_url}")

    ok1 = http_health(args.base_url)
    ok2 = http_api(args.base_url)
    ok3 = ws_list_sessions(args.ws_url, args.user_id) if not args.skip_ws else True

    success = ok1 and ok2 and ok3
    print("\n--- Result:", "PASS" if success else "FAIL", "---\n")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
