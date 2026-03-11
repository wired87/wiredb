import base64
import json
import os
import sys
import pprint
from pathlib import Path
from qbrain.core.file_manager.file_lib import file_manager

# Windows console: avoid UnicodeEncodeError for emoji/special chars
def _safe_print(s):
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("utf-8", errors="replace").decode("ascii", errors="replace"))

def test_file_manager_pipeline():
    _safe_print("Testing File Manager Pipeline...")
    
    repo_root = Path(__file__).resolve().parents[4]
    file_path = repo_root / "test_paper.pdf"
    if file_path.exists():
        with open(file_path, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode("utf-8")
        _safe_print(f"Using PDF: {file_path}")
    else:
        # Fallback: sample text for extraction (no PDF)
        sample = b"Sample equations: E=mc^2, dx/dt = v, F = ma. Params: mass m, velocity v."
        encoded_string = base64.b64encode(sample).decode("utf-8")
        _safe_print(f"File not found: {file_path} - using sample text fallback")

    files = [encoded_string]
    data = {
        "id": "test_module_id_123",
        "name": "Test Module from PDF",
        "description": "Something physical.",
        "files": files
    }
    user_id = "test_user"
    mock = "--mock" in sys.argv or "-m" in sys.argv
    if mock:
        _safe_print("(Using mock extraction - no Gemini API calls)")

    try:
        result = file_manager.process_and_upload_file_config(
            user_id=user_id,
            data=data,
            testing=True,
            mock_extraction=mock,
        )
        _safe_print("\n\n--- Test Results ---")
        pprint.pprint({k: v for k, v in result.items() if k != "created_components"})
        
        # Print all created components in exact handler input format
        # (same format relay_station dispatches to handle_set_param/field/method)
        cc = result.get("created_components", {})
        _safe_print("\n\n--- Created Components (exact handler input format) ---")
        handler_map = {
            "param": "handle_set_param  (params_lib)  expects: {auth:{user_id}, data:{param:...}}",
            "field": "handle_set_field  (fields_lib)  expects: {auth:{user_id}, data:{field:...}}",
            "method": "handle_set_method (method_lib)  expects: {auth:{user_id}, data:{equation,params,...}}",
        }
        for content_type in ("param", "field", "method"):
            items = cc.get(content_type, [])
            if not items:
                continue
            _safe_print(f"\n>>> {handler_map[content_type]}")
            _safe_print(f"    ({len(items)} payload(s)):")
            for i, payload in enumerate(items):
                try:
                    out = json.dumps(payload, default=str, indent=2, ensure_ascii=False)
                except (TypeError, ValueError):
                    out = repr(payload)
                _safe_print(f"  [{i+1}] {out}")
    except Exception as e:
        _safe_print(f"\n\n--- Error ---\n{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Usage: python -m core.file_manager.test_pipeline [--mock|-m]
    # --mock: use mock extraction (no Gemini API), fast run to verify created_components format
    test_file_manager_pipeline()
