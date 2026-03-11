"""
Record qdash demo: start qdash (cd qdash && npm start), test the app by pressing
buttons, capture HTML at each step, and save a video (MP4) to project root.

Used for OpenAI app creator process: the resulting MP4 path and HTML captures
are written to a local config so the Apps SDK workflow can reference them
(e.g. demo video for submission).

Requires: pip install playwright && playwright install chromium

Usage:
  python -m _admin.main --record-qdash-demo
  python -m _admin.main --record-qdash-demo --qdash-demo-out ./my_demo.mp4
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Project root (parent of _admin)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
QDASH_DIR = PROJECT_ROOT / "qdash"
DEFAULT_DEMO_MP4 = PROJECT_ROOT / "qdash_demo.mp4"
DEFAULT_HTML_DIR = PROJECT_ROOT / "qdash_demo_html"
FRONTEND_URL = "http://localhost:3000"
STARTUP_TIMEOUT = 120  # seconds to wait for npm start
RECORD_TIMEOUT_MS = 90_000  # max recording duration


def _wait_for_url(url: str, timeout: float = 60) -> bool:
    """Poll url until 200 or timeout."""
    try:
        import urllib.request
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    if r.status == 200:
                        return True
            except OSError:
                pass
            time.sleep(1)
    except Exception:
        pass
    return False


def _start_qdash() -> subprocess.Popen | None:
    """Start qdash (cd qdash && npm run start). Returns Popen or None."""
    if not QDASH_DIR.is_dir():
        print(f"[record-qdash-demo] qdash dir not found: {QDASH_DIR}")
        return None
    use_shell = os.name == "nt"
    cmd = "npm run start" if use_shell else ["npm", "run", "start"]
    print(f"[record-qdash-demo] Starting qdash in {QDASH_DIR} ...")
    try:
        p = subprocess.Popen(
            cmd,
            cwd=str(QDASH_DIR),
            shell=use_shell,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "BROWSER": "none"},  # prevent CRA opening browser
        )
        return p
    except Exception as e:
        print(f"[record-qdash-demo] Failed to start qdash: {e}")
        return None


def _run_recorder(
    out_mp4: Path,
    html_dir: Path,
    duration_sec: int = 45,
) -> bool:
    """Use Playwright to open qdash, click buttons, capture HTML, record video. Returns True on success."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[record-qdash-demo] Playwright not installed. Run: pip install playwright && playwright install chromium")
        return False

    html_dir.mkdir(parents=True, exist_ok=True)
    video_dir = out_mp4.parent / "_demo_video_tmp"
    video_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()
        try:
            page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=15000)
        except Exception as e:
            print(f"[record-qdash-demo] Navigate failed: {e}")
            context.close()
            browser.close()
            return False

        step = 0
        # Preferred workflow order: click these first (by text or aria-label) for a smooth demo
        WORKFLOW_ORDER = [
            "Initialize",
            "Environment configuration",
            "Create session",
            "Link",
            "Add",
            "Enable Standard Model",
            "worldConfig",
            "Close",
        ]

        def try_click_by_text_or_aria(labels: list) -> int:
            nonlocal step
            clicked = 0
            for label in labels:
                try:
                    loc = page.locator(f"button:has-text('{label}'), [role='button']:has-text('{label}'), [aria-label='{label}']")
                    if loc.count() >= 1:
                        el = loc.first
                        if el.is_visible():
                            step += 1
                            (html_dir / f"step_{step:02d}_before.html").write_text(page.content(), encoding="utf-8")
                            el.click(timeout=2000)
                            time.sleep(0.8)
                            step += 1
                            (html_dir / f"step_{step:02d}_after.html").write_text(page.content(), encoding="utf-8")
                            clicked += 1
                except Exception:
                    pass
            return clicked

        workflow_clicks = try_click_by_text_or_aria(WORKFLOW_ORDER)
        # Fallback: click remaining buttons in DOM order
        clicked = workflow_clicks
        try:
            buttons = page.query_selector_all("button, [role='button']")
            for i, btn in enumerate(buttons[:15]):  # cap at 15 clicks total
                try:
                    if not btn.is_visible():
                        continue
                    # Capture HTML before click
                    step += 1
                    snapshot = page.content()
                    (html_dir / f"step_{step:02d}_before.html").write_text(snapshot, encoding="utf-8")
                    btn.click(timeout=2000)
                    time.sleep(0.8)
                    step += 1
                    (html_dir / f"step_{step:02d}_after.html").write_text(page.content(), encoding="utf-8")
                    clicked += 1
                except Exception:
                    continue
                if clicked >= 10:
                    break  # total clicks cap (workflow + fallback)
        except Exception as e:
            print(f"[record-qdash-demo] Click loop: {e}")

        time.sleep(1)
        # Final HTML snapshot
        (html_dir / "final.html").write_text(page.content(), encoding="utf-8")

        context.close()
        browser.close()

    # Playwright saves video to context dir; move to final path
    actual_video_path: Path | None = None
    try:
        video_files = list(video_dir.glob("*.webm"))
        if video_files:
            p = video_files[0]
            # Convert webm -> mp4 if ffmpeg available; else save as webm
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(p), "-c", "copy", str(out_mp4)],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                actual_video_path = out_mp4
                print(f"[record-qdash-demo] Saved MP4: {out_mp4}")
            except (FileNotFoundError, subprocess.CalledProcessError):
                webm_path = out_mp4.with_suffix(".webm")
                webm_path.write_bytes(p.read_bytes())
                actual_video_path = webm_path
                print(f"[record-qdash-demo] Saved as WebM (install ffmpeg for MP4): {webm_path}")
        else:
            print("[record-qdash-demo] No video file produced")
    finally:
        for f in video_dir.glob("*"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            video_dir.rmdir()
        except Exception:
            pass

    if actual_video_path:
        write_demo_paths_config(actual_video_path, out_mp4, html_dir)
    return True


def write_demo_paths_config(actual_video_path: Path, out_mp4: Path, html_dir: Path) -> None:
    """Write local paths to OpenAI app creator config (for submission workflow)."""
    config_dir = PROJECT_ROOT / "_admin" / "app_handler" / "openai_asdk"
    config_file = config_dir / "demo_paths.json"
    try:
        import json
        data = {
            "demo_video_path": str(actual_video_path.resolve()),
            "demo_html_dir": str(html_dir.resolve()),
            "demo_video_webm": str(actual_video_path.resolve()) if actual_video_path.suffix == ".webm" else (str(out_mp4.with_suffix(".webm").resolve()) if out_mp4.with_suffix(".webm").exists() else None),
        }
        config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[record-qdash-demo] Wrote local paths to {config_file}")
    except Exception as e:
        print(f"[record-qdash-demo] Could not write config: {e}")


def run_record_qdash_demo(
    out_mp4: Path | None = None,
    html_dir: Path | None = None,
    duration_sec: int = 45,
) -> bool:
    """
    Start qdash, record session (press buttons, capture HTML), save MP4 to project root.
    Writes demo paths to app_handler/openai_asdk/demo_paths.json for OpenAI app creator.
    """
    out_mp4 = out_mp4 or DEFAULT_DEMO_MP4
    html_dir = html_dir or DEFAULT_HTML_DIR

    proc = _start_qdash()
    if not proc:
        return False

    try:
        if not _wait_for_url(FRONTEND_URL, timeout=STARTUP_TIMEOUT):
            print(f"[record-qdash-demo] qdash did not become ready at {FRONTEND_URL}")
            return False
        print("[record-qdash-demo] qdash ready; starting recorder ...")
        ok = _run_recorder(out_mp4, html_dir, duration_sec=duration_sec)
        return ok
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[record-qdash-demo] qdash process stopped.")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Record qdash demo (start app, press buttons, save MP4 + HTML)")
    ap.add_argument("--out", type=Path, default=None, help=f"Output MP4 path (default: {DEFAULT_DEMO_MP4})")
    ap.add_argument("--html-dir", type=Path, default=None, help=f"HTML snapshots dir (default: {DEFAULT_HTML_DIR})")
    ap.add_argument("--duration", type=int, default=45, help="Max record duration in seconds")
    args = ap.parse_args()
    success = run_record_qdash_demo(out_mp4=args.out, html_dir=args.html_dir, duration_sec=args.duration)
    sys.exit(0 if success else 1)
