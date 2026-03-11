"""
Type definitions for UserManager handler methods.
Captures req_struct and out_struct data types for each relay case.
"""
from typing import TypedDict, Dict, Any, Optional


# --- Relay case struct type (no handlers in RELAY_CASES_CONFIG currently) ---
class RelayCaseStruct(TypedDict, total=False):
    case: str
    desc: str
    func: Any
    func_name: Optional[str]
    req_struct: Dict[str, Any]
    out_struct: Dict[str, Any]
