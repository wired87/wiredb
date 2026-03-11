from qbrain.core.env_manager.env_lib import handle_link_env_module, handle_rm_link_env_module
from .modules_lib import (
    handle_del_module, handle_link_session_module, handle_rm_link_session_module,
    handle_set_module, handle_get_module, handle_get_sessions_modules,
    handle_list_users_modules
)
from .types import (
    ModuleItemData, ReqDataSetModule, ReqDataConvertModule,
    OutListUsersModules, OutGetSessionsModules, OutLinkEnvModule,
    OutGetModule, OutConvertModule, RelayCaseStruct,
)

# Case structs - req_struct.data uses exact datatypes (ModuleItemData, ReqDataSetModule)
DEL_MODULE_CASE: RelayCaseStruct = {
    "case": "DEL_MODULE", "desc": "Delete Module", "func": handle_del_module,
    "req_struct": {"auth": {"module_id": str, "user_id": str}},
    "out_struct": {"type": "LIST_USERS_MODULES", "data": {"modules": list}},  # OutListUsersModules
}
LINK_SESSION_MODULE_CASE: RelayCaseStruct = {
    "case": "LINK_SESSION_MODULE", "desc": "Link Session Module", "func": handle_link_session_module,
    "req_struct": {"auth": {"user_id": str, "session_id": str, "module_id": str}},
    "out_struct": {"type": "GET_SESSIONS_MODULES", "data": {"modules": list}},  # OutGetSessionsModules
}
RM_LINK_SESSION_MODULE_CASE: RelayCaseStruct = {
    "case": "RM_LINK_SESSION_MODULE", "desc": "Remove Link Session Module", "func": handle_rm_link_session_module,
    "req_struct": {"auth": {"user_id": str, "session_id": str, "module_id": str}},
    "out_struct": {"type": "GET_SESSIONS_MODULES", "data": {"modules": list}},  # OutGetSessionsModules
}
LINK_ENV_MODULE_CASE: RelayCaseStruct = {
    "case": "LINK_ENV_MODULE", "desc": "Link Env Module", "func": handle_link_env_module,
    "req_struct": {"auth": {"user_id": str, "session_id": str, "env_id": str, "module_id": str}},
    "out_struct": {"type": "LINK_ENV_MODULE", "data": {"sessions": dict}},  # OutLinkEnvModule
}
RM_LINK_ENV_MODULE_CASE: RelayCaseStruct = {
    "case": "RM_LINK_ENV_MODULE", "desc": "Remove Link Env Module", "func": handle_rm_link_env_module,
    "req_struct": {"auth": {"user_id": str, "session_id": str, "env_id": str, "module_id": str}},
    "out_struct": {"type": "RM_LINK_ENV_MODULE", "auth": {"session_id": str, "env_id": str, "module_id": str}, "data": dict},  # Aligned with frontend
}
SET_MODULE_CASE: RelayCaseStruct = {
    "case": "SET_MODULE", "desc": "Set Module", "func": handle_set_module,
    "req_struct": {
        "data": {"id": str, "fields": list, "methods": list, "description": str},  # ReqDataSetModule
        "auth": {"user_id": str, "original_id": str}
    },
    "out_struct": {"type": "LIST_USERS_MODULES", "data": {"modules": list}},  # OutListUsersModules
}
GET_MODULE_CASE: RelayCaseStruct = {
    "case": "GET_MODULE", "desc": "Get Module", "func": handle_get_module,
    "req_struct": {"auth": {"module_id": str}},
    "out_struct": {"type": "GET_MODULE", "data": dict},  # OutGetModule
}
GET_SESSIONS_MODULES_CASE: RelayCaseStruct = {
    "case": "GET_SESSIONS_MODULES", "desc": "Get Session Modules", "func": handle_get_sessions_modules,
    "req_struct": {"auth": {"user_id": str, "session_id": str}},
    "out_struct": {"type": "GET_SESSIONS_MODULES", "data": {"modules": list}, "auth": {"session_id": str}},  # OutGetSessionsModules
}
LIST_USERS_MODULES_CASE: RelayCaseStruct = {
    "case": "LIST_USERS_MODULES", "desc": "List User Modules", "func": handle_list_users_modules,
    "req_struct": {"auth": {"user_id": str}},
    "out_struct": {"type": "LIST_USERS_MODULES", "data": {"modules": list}},  # OutListUsersModules
}
CONVERT_MODULE_CASE: RelayCaseStruct = {
    "case": "CONVERT_MODULE", "desc": "Convert Module", "func": None, "func_name": "_handle_convert_module",
    "req_struct": {"auth": {"module_id": str}, "data": {"files": dict}},  # ReqDataConvertModule
    "out_struct": {"type": "CONVERT_MODULE", "data": dict},  # OutConvertModule
}

RELAY_MODULE = [
    DEL_MODULE_CASE, LINK_SESSION_MODULE_CASE, RM_LINK_SESSION_MODULE_CASE,
    LINK_ENV_MODULE_CASE, RM_LINK_ENV_MODULE_CASE, SET_MODULE_CASE, GET_MODULE_CASE,
    GET_SESSIONS_MODULES_CASE, LIST_USERS_MODULES_CASE, CONVERT_MODULE_CASE,
]
