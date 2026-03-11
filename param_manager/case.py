from .params_lib import (
    handle_get_users_params, handle_set_param, handle_del_param,
    handle_link_field_param, handle_rm_link_field_param, handle_get_fields_params
)
from .types import (
    ParamItemData, LinkFieldParamItem,
    ReqListUsersParams, ReqSetParam, ReqDelParam,
    ReqLinkFieldParam, ReqRmLinkFieldParam, ReqGetFieldsParams,
    OutListUsersParams, OutGetFieldsParams,
    RelayCaseStruct,
)

# Case structs - req_struct.data uses exact datatypes (ParamItemData, ReqDataSetParam)
LIST_USERS_PARAMS_CASE: RelayCaseStruct = {
    "case": "LIST_USERS_PARAMS", "desc": "Get Users Params", "func": handle_get_users_params,
    "req_struct": {"auth": {"user_id": str}},
    "req_schema": ReqListUsersParams.model_json_schema(),
    "out_struct": {"type": "LIST_USERS_PARAMS", "data": {"params": list}},
}
SET_PARAM_CASE: RelayCaseStruct = {
    "case": "SET_PARAM", "desc": "Set Param", "func": handle_set_param,
    "req_struct": {
        "auth": {"user_id": str, "original_id": str},
        "data": {"param": dict},
    },
    "req_schema": ReqSetParam.model_json_schema(),
    "out_struct": {"type": "LIST_USERS_PARAMS", "data": {"params": list}},
}
DEL_PARAM_CASE: RelayCaseStruct = {
    "case": "DEL_PARAM", "desc": "Delete Param", "func": handle_del_param,
    "req_struct": {"auth": {"user_id": str, "param_id": str}},
    "req_schema": ReqDelParam.model_json_schema(),
    "out_struct": {"type": "LIST_USERS_PARAMS", "data": {"params": list}},
}

LINK_FIELD_PARAM_CASE: RelayCaseStruct = {
    "case": "LINK_FIELD_PARAM", "desc": "Link Field Param", "func": handle_link_field_param,
    "req_struct": {"auth": {"user_id": str}, "data": {"links": list}},
    "req_schema": ReqLinkFieldParam.model_json_schema(),
    "out_struct": {"type": "GET_FIELDS_PARAMS", "data": {"params": list}},
}
RM_LINK_FIELD_PARAM_CASE: RelayCaseStruct = {
    "case": "RM_LINK_FIELD_PARAM", "desc": "Rm Link Field Param", "func": handle_rm_link_field_param,
    "req_struct": {"auth": {"user_id": str, "field_id": str, "param_id": str}},
    "req_schema": ReqRmLinkFieldParam.model_json_schema(),
    "out_struct": {"type": "GET_FIELDS_PARAMS", "data": {"params": list}},
}
GET_FIELDS_PARAMS_CASE: RelayCaseStruct = {
    "case": "GET_FIELDS_PARAMS", "desc": "Get Fields Params", "func": handle_get_fields_params,
    "req_struct": {"auth": {"user_id": str, "field_id": str}},
    "req_schema": ReqGetFieldsParams.model_json_schema(),
    "out_struct": {"type": "GET_FIELDS_PARAMS", "data": {"params": list}},
}

RELAY_PARAM = [
    LIST_USERS_PARAMS_CASE, SET_PARAM_CASE, DEL_PARAM_CASE,
    LINK_FIELD_PARAM_CASE, RM_LINK_FIELD_PARAM_CASE, GET_FIELDS_PARAMS_CASE,
]
