"""
Type definitions for ModuleManager (ws_modules_manager) handler methods.
Captures req_struct and out_struct data types for each relay case.
"""
from typing import TypedDict, List, Dict, Any, Optional


# =============================================================================
# DATATYPES - Exact data structures used by handler methods (nested list[dict])
# =============================================================================

class ModuleItemData(TypedDict, total=False):
    """Exact type for module row passed to ModuleManager.set_module()."""
    id: str
    fields: List[Dict[str, Any]]  # List of field IDs or field dicts
    methods: List[Dict[str, Any]]  # List of method IDs or method dicts
    description: Optional[str]


class ReqDataSetModule(TypedDict):
    """req_struct.data for SET_MODULE. Handler builds row from data."""
    id: str
    fields: List[Any]
    methods: List[Any]
    description: Optional[str]


class ReqDataConvertModule(TypedDict):
    """req_struct.data for CONVERT_MODULE."""
    files: Dict[str, Any]


# --- Auth types ---
class AuthModuleUserId(TypedDict):
    module_id: str
    user_id: str


class AuthUserSessionModuleId(TypedDict):
    user_id: str
    session_id: str
    module_id: str


class AuthUserSessionEnvModuleId(TypedDict):
    user_id: str
    session_id: str
    env_id: str
    module_id: str


class AuthUserId(TypedDict):
    user_id: str


class AuthUserOriginalId(TypedDict):
    user_id: str
    original_id: Optional[str]


class AuthModuleId(TypedDict):
    module_id: str


class AuthUserSessionId(TypedDict):
    user_id: str
    session_id: str


# --- Request payload data types ---
class ReqSetModuleData(TypedDict):
    id: str
    fields: List[Any]
    methods: List[Any]
    description: Optional[str]


class ReqDelModule(TypedDict):
    auth: AuthModuleUserId


class ReqLinkSessionModule(TypedDict):
    auth: AuthUserSessionModuleId


class ReqRmLinkSessionModule(TypedDict):
    auth: AuthUserSessionModuleId


class ReqLinkEnvModule(TypedDict):
    auth: AuthUserSessionEnvModuleId


class ReqRmLinkEnvModule(TypedDict):
    auth: AuthUserSessionEnvModuleId


class ReqSetModule(TypedDict):
    data: ReqSetModuleData
    auth: AuthUserOriginalId


class ReqGetModule(TypedDict):
    auth: AuthModuleId


class ReqGetSessionsModules(TypedDict):
    auth: AuthUserSessionId


class ReqListUsersModules(TypedDict):
    auth: AuthUserId


class ReqConvertModule(TypedDict):
    auth: AuthModuleId
    data: Dict[str, Any]  # {"files": dict}


# --- Response data types ---
class OutListUsersModules(TypedDict):
    type: str  # "LIST_USERS_MODULES"
    data: Dict[str, List[Dict[str, Any]]]  # {"modules": [...]}


class OutGetSessionsModules(TypedDict):
    type: str  # "GET_SESSIONS_MODULES"
    data: Dict[str, List[Dict[str, Any]]]  # {"modules": [...]}
    auth: Optional[Dict[str, str]]  # {"session_id": str}


class OutLinkEnvModule(TypedDict):
    type: str  # "LINK_ENV_MODULE"
    data: Dict[str, Any]  # {"sessions": {...}}


class OutGetModule(TypedDict):
    type: str  # "GET_MODULE"
    data: Dict[str, Any]


class OutConvertModule(TypedDict):
    type: str  # "CONVERT_MODULE"
    data: Dict[str, Any]


# --- Relay case struct type ---
class RelayCaseStruct(TypedDict, total=False):
    case: str
    desc: str
    func: Any
    func_name: Optional[str]
    req_struct: Dict[str, Any]
    out_struct: Dict[str, Any]
