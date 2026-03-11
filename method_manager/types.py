"""
Type definitions for MethodManager handler methods.
Captures req_struct and out_struct data types for each relay case.
"""
from typing import TypedDict, List, Dict, Any, Optional


# =============================================================================
# DATATYPES - Exact data structures used by handler methods (nested list[dict])
# =============================================================================

class MethodItemData(TypedDict, total=False):
    """Exact type for method passed to MethodManager.set_method()."""
    id: str
    equation: str
    params: List[str]  # List of param names/IDs
    origins: List[Any]  # List of origin strings (e.g. "self")
    description: str
    code: str
    jax_code: str


class ReqDataSetMethod(TypedDict):
    """req_struct.data for SET_METHOD. Handler passes data to set_method()."""
    id: str
    equation: str
    params: List[str]
    origins: List[Any]
    description: str
    code: str
    jax_code: str


# --- Auth types ---
class AuthUserId(TypedDict):
    user_id: str


class AuthUserMethodSessionId(TypedDict):
    user_id: str
    method_id: str
    session_id: str


class AuthUserMethodId(TypedDict):
    user_id: str
    method_id: str


class AuthUserOriginalId(TypedDict):
    user_id: str
    original_id: Optional[str]


class AuthMethodId(TypedDict):
    method_id: str


# --- Request payload data types ---
class ReqSetMethodData(TypedDict):
    id: str
    equation: str
    params: List[Any]
    origins: List[Any]
    description: str
    code: str
    jax_code: str


class ReqListUsersMethods(TypedDict):
    auth: AuthUserId


class ReqGetSessionsMethods(TypedDict):
    auth: Dict[str, str]  # user_id, session_id


class ReqLinkSessionMethod(TypedDict):
    auth: AuthUserMethodSessionId


class ReqRmLinkSessionMethod(TypedDict):
    auth: AuthUserMethodSessionId


class ReqDelMethod(TypedDict):
    auth: AuthUserMethodId


class ReqSetMethod(TypedDict):
    data: ReqSetMethodData
    auth: AuthUserOriginalId


class ReqGetMethod(TypedDict):
    auth: AuthMethodId


# --- Response data types ---
class OutListUsersMethods(TypedDict):
    type: str  # "LIST_USERS_METHODS"
    data: Dict[str, List[Dict[str, Any]]]  # {"methods": [...]}


class OutGetSessionsMethods(TypedDict):
    type: str  # "GET_SESSIONS_METHODS"
    data: Dict[str, List[Dict[str, Any]]]  # {"methods": [...]}


class OutGetMethod(TypedDict):
    type: str  # "GET_METHOD"
    data: Dict[str, Any]


# --- Relay case struct type ---
class RelayCaseStruct(TypedDict, total=False):
    case: str
    desc: str
    func: Any
    func_name: Optional[str]
    req_struct: Dict[str, Any]
    out_struct: Dict[str, Any]
