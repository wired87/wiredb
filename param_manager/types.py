"""
Type definitions for ParamManager handler methods.
Pydantic BaseModel classes capture exact request structure for each handler,
including all nested keys in list[dict]. Enables ML models to programmatically
recognize structure, collect data, and invoke runnables.
"""
from typing import List, Dict, Any, Optional, Union, TypedDict

from pydantic import BaseModel, Field


class RelayCaseStruct(TypedDict, total=False):
    """Relay case struct for RELAY_PARAM list."""
    case: str
    desc: str
    func: Any
    func_name: Optional[str]
    req_struct: Dict[str, Any]
    req_schema: Dict[str, Any]  # Full JSON schema from BaseModel for ML
    out_struct: Dict[str, Any]


# =============================================================================
# NESTED DATA ITEMS - Full structure for list[dict] elements
# =============================================================================

class ParamItemData(BaseModel):
    """
    Single param item for SET_PARAM. All keys used by ParamsManager.set_param().
    ML model must collect: id/name, type, value, const/is_constant, etc.
    """
    id: Optional[str] = Field(None, description="Unique param ID. Auto-generated if absent.")
    name: Optional[str] = Field(None, description="Display name. Falls back to id if absent.")
    type: Optional[str] = Field(None, description="Param type: STRING, FLOAT64, BOOL, etc.")
    description: Optional[str] = Field(None, description="Human-readable description.")
    value: Optional[Any] = Field(None, description="Param value. JSON-serialized when stored.")
    const: Optional[bool] = Field(None, description="Whether param is constant (axis_def=0).")
    is_constant: Optional[bool] = Field(None, description="Alias for const.")
    axis_def: Optional[Any] = Field(None, description="Axis definition for JAX. Derived from const if absent.")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for the param.")


class LinkFieldParamItem(BaseModel):
    """
    Single link for LINK_FIELD_PARAM. Each item in data.links.
    Handler also accepts flat auth.field_id, auth.param_id, data.param_value.
    """
    field_id: str = Field(..., description="ID of the field to link.")
    param_id: str = Field(..., description="ID of the param to link.")
    param_value: Optional[Any] = Field(None, description="Value for this field-param link. Stored as string.")
    id: Optional[str] = Field(None, description="Link ID. Auto-generated if absent.")


# =============================================================================
# AUTH BLOCKS - Reusable auth structures
# =============================================================================

class AuthUserId(BaseModel):
    """Auth for handlers requiring only user_id."""
    user_id: str = Field(..., description="Owner user ID.")


class AuthUserOriginalId(BaseModel):
    """Auth for SET_PARAM when replacing existing param."""
    user_id: str = Field(..., description="Owner user ID.")
    original_id: Optional[str] = Field(None, description="ID of param to replace. If set, deletes old first.")


class AuthUserParamId(BaseModel):
    """Auth for DEL_PARAM."""
    user_id: str = Field(..., description="Owner user ID.")
    param_id: str = Field(..., description="ID of param to delete.")


class AuthUserIdFieldId(BaseModel):
    """Auth for GET_FIELDS_PARAMS (user_id, field_id only)."""
    user_id: str = Field(..., description="Owner user ID.")
    field_id: str = Field(..., description="Field ID.")


class AuthFieldParamId(BaseModel):
    """Auth for RM_LINK_FIELD_PARAM (user_id, field_id, param_id)."""
    user_id: str = Field(..., description="Owner user ID.")
    field_id: str = Field(..., description="Field ID.")
    param_id: str = Field(..., description="Param ID to unlink.")


# =============================================================================
# REQUEST PAYLOADS - Full structure per handler
# =============================================================================

class ReqListUsersParams(BaseModel):
    """Payload for LIST_USERS_PARAMS / handle_get_users_params."""
    auth: AuthUserId = Field(..., description="Auth with user_id.")


class ReqSetParamData(BaseModel):
    """data block for SET_PARAM."""
    param: Union[ParamItemData, List[ParamItemData]] = Field(
        ...,
        description="Single param dict or list of param dicts. Each item: id, name, type, value, const, etc."
    )


class ReqSetParam(BaseModel):
    """Payload for SET_PARAM / handle_set_param."""
    auth: AuthUserOriginalId = Field(..., description="Auth with user_id, optional original_id.")
    data: ReqSetParamData = Field(..., description="Data with param(s).")


class ReqDelParam(BaseModel):
    """Payload for DEL_PARAM / handle_del_param."""
    auth: AuthUserParamId = Field(..., description="Auth with user_id, param_id.")


class AuthLinkFieldParam(BaseModel):
    """Auth for LINK_FIELD_PARAM. Flat mode: field_id, param_id here; data.param_value for value."""
    user_id: str = Field(..., description="Owner user ID.")
    field_id: Optional[str] = Field(None, description="For flat mode: single field to link.")
    param_id: Optional[str] = Field(None, description="For flat mode: single param to link.")


class ReqLinkFieldParamData(BaseModel):
    """data block for LINK_FIELD_PARAM. links is list of LinkFieldParamItem. Flat mode: param_value only."""
    links: Optional[List[LinkFieldParamItem]] = Field(
        None,
        description="List of {field_id, param_id, param_value}. Omit if using flat auth.field_id, auth.param_id."
    )
    param_value: Optional[Any] = Field(None, description="For flat mode: value for the single link.")


class ReqLinkFieldParam(BaseModel):
    """Payload for LINK_FIELD_PARAM / handle_link_field_param."""
    auth: AuthLinkFieldParam = Field(..., description="Auth. Flat mode: auth.field_id, auth.param_id + data.param_value.")
    data: ReqLinkFieldParamData = Field(..., description="Data. Either links list or param_value for flat mode.")


class ReqRmLinkFieldParam(BaseModel):
    """Payload for RM_LINK_FIELD_PARAM / handle_rm_link_field_param."""
    auth: AuthFieldParamId = Field(..., description="Auth with user_id, field_id, param_id.")


class ReqGetFieldsParams(BaseModel):
    """Payload for GET_FIELDS_PARAMS / handle_get_fields_params."""
    auth: AuthUserIdFieldId = Field(..., description="Auth with user_id, field_id.")


# =============================================================================
# RESPONSE TYPES
# =============================================================================

class OutParamRow(BaseModel):
    """Single param row in response. Keys from BQ params table + link_value, link_id when from get_fields_params."""
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    value: Optional[Any] = None
    const: Optional[bool] = None
    user_id: Optional[str] = None
    link_value: Optional[str] = Field(None, description="Value from fields_to_params link.")
    link_id: Optional[str] = Field(None, description="Link row ID.")


class OutListUsersParams(BaseModel):
    """Response for LIST_USERS_PARAMS, SET_PARAM, DEL_PARAM."""
    type: str = Field("LIST_USERS_PARAMS", description="Response type.")
    data: Dict[str, List[Dict[str, Any]]] = Field(..., description='{"params": [...]}')


class OutGetFieldsParams(BaseModel):
    """Response for LINK_FIELD_PARAM, RM_LINK_FIELD_PARAM, GET_FIELDS_PARAMS."""
    type: str = Field("GET_FIELDS_PARAMS", description="Response type.")
    data: Dict[str, List[Dict[str, Any]]] = Field(..., description='{"params": [...]}')
    auth: Optional[Dict[str, str]] = Field(None, description="Echo of field_id when relevant.")


# =============================================================================
# HANDLER SCHEMA REGISTRY - For ML model programmatic use
# =============================================================================

HANDLER_REQUEST_SCHEMAS = {
    "LIST_USERS_PARAMS": ReqListUsersParams.model_json_schema(),
    "handle_get_users_params": ReqListUsersParams.model_json_schema(),
    "handle_list_users_params": ReqListUsersParams.model_json_schema(),
    "SET_PARAM": ReqSetParam.model_json_schema(),
    "handle_set_param": ReqSetParam.model_json_schema(),
    "DEL_PARAM": ReqDelParam.model_json_schema(),
    "handle_del_param": ReqDelParam.model_json_schema(),
    "LINK_FIELD_PARAM": ReqLinkFieldParam.model_json_schema(),
    "handle_link_field_param": ReqLinkFieldParam.model_json_schema(),
    "RM_LINK_FIELD_PARAM": ReqRmLinkFieldParam.model_json_schema(),
    "handle_rm_link_field_param": ReqRmLinkFieldParam.model_json_schema(),
    "GET_FIELDS_PARAMS": ReqGetFieldsParams.model_json_schema(),
    "handle_get_fields_params": ReqGetFieldsParams.model_json_schema(),
}


def get_handler_schema(case_or_func: str) -> Optional[Dict[str, Any]]:
    """Return JSON schema for a handler. Use case name (e.g. SET_PARAM) or func name (e.g. handle_set_param)."""
    return HANDLER_REQUEST_SCHEMAS.get(case_or_func)


def get_all_schemas() -> Dict[str, Dict[str, Any]]:
    """Return all handler schemas. ML model can iterate to recognize structure and collect data."""
    return HANDLER_REQUEST_SCHEMAS.copy()
