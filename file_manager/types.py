"""
Type definitions for FileManager handler methods.
Captures req_struct and out_struct data types for each relay case.
"""
from typing import TypedDict, List, Dict, Any, Optional, Union


# =============================================================================
# DATATYPES - Exact data structures used by handler methods (nested list[dict])
# =============================================================================

# files can be List[bytes] or List[file-like] - converted to bytes in handler
class SetFileItemData(TypedDict, total=False):
    """Exact type for data passed to FileManager.process_and_upload_file_config()."""
    id: str
    files: List[Union[bytes, Any]]  # List of file bytes or file-like objects
    name: Optional[str]
    description: Optional[str]
    prompt: Optional[str]
    msg: Optional[str]


class ReqDataSetFile(TypedDict):
    """req_struct.data for SET_FILE."""
    id: str
    files: List[Any]
    name: str
    description: str
    prompt: str
    msg: str


# --- Auth types ---
class AuthUserOriginalId(TypedDict):
    user_id: str
    original_id: Optional[str]


# --- Request payload data types ---
class ReqSetFileData(TypedDict):
    id: str
    files: List[Any]
    name: str
    description: str
    prompt: str
    msg: str


class ReqSetFile(TypedDict):
    data: ReqSetFileData
    auth: AuthUserOriginalId


# --- Response data types ---
class OutSetFile(TypedDict):
    type: str  # "LIST_USERS_MODULES"
    data: Dict[str, List[Dict[str, Any]]]  # {"modules": [...]}


# --- Relay case struct type ---
class RelayCaseStruct(TypedDict, total=False):
    case: str
    desc: str
    func: Any
    func_name: Optional[str]
    req_struct: Dict[str, Any]
    out_struct: Dict[str, Any]
