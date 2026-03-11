import random
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

import numpy as np
from google.cloud import bigquery

from qbrain.core.param_manager.extraction_prompt import xtract_params_prompt

from qbrain.core.qbrain_manager import get_qbrain_table_manager
from qbrain.core.handler_utils import require_param, require_param_truthy, get_val
from qbrain.gem_core.gem import Gem
from qbrain.qf_utils.all_subs import FERMIONS, G_FIELDS, H
from qbrain.qf_utils.qf_utils import QFUtils

_PARAMS_DEBUG = "[ParamsManager]"


def generate_numeric_id() -> str:
    """Generate a random numeric ID."""
    return str(random.randint(1000000000, 9999999999))

class ParamsManager:
    DATASET_ID = "QBRAIN"
    PARAMS_TABLE = "params"
    FIELDS_TO_PARAMS_TABLE = "fields_to_params"

    def __init__(self, qb):
        self.qb = qb
        self.pid = qb.pid
        self.table = f"{self.PARAMS_TABLE}"
        self._extract_prompt = None  # built lazily to avoid circular import with case

    def get_axis(self, params:dict):
        # get axis for pasm from BQ
        return [self.get_axis_param(p["const"]) for p in params]

    def get_axis_param(self, const:bool):
        return None if const is True else 1

    def _get_extract_prompt(self, instructions, content, users_params) -> str:
        """Build prompt lazily to avoid circular import with case."""
        if self._extract_prompt is None:
            from qbrain.core.param_manager import case as param_case
            set_case = next((c for c in param_case.RELAY_PARAM if c.get("case") == "SET_PARAM"), None)
            req_struct = set_case.get("req_struct", {}) if set_case else {}
            self._extract_prompt = xtract_params_prompt(
                req_struct,
                instructions,
                content,
                users_params,
            )

        return self._extract_prompt

    def extract_prompt(self, instructions: str, content: str, users_params: List[Dict[str, Any]]) -> str:
        """Static prompt for extraction. Used by intelligent_extraction as manager_prompt_ext."""
        from qbrain.core.param_manager import case as param_case
        set_case = next((c for c in param_case.RELAY_PARAM if c.get("case") == "SET_PARAM"), None)
        req_struct = set_case.get("req_struct", {}) if set_case else {}
        return xtract_params_prompt(req_struct, instructions, content, users_params)

    def get_schema_for_extraction(self, param_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Return key:type struct for intelligent_extraction.
        Uses param row if param_id given; else req_struct from SET_PARAM.
        """
        if param_id:
            rows = self.qb.row_from_id([param_id], "params")
            if rows:
                row = rows[0]
                for field in ("shape", "axis_def"):
                    val = row.get(field)
                    if isinstance(val, str):
                        try:
                            struct = json.loads(val)
                            if isinstance(struct, dict):
                                return struct
                        except json.JSONDecodeError:
                            pass
                    elif isinstance(val, dict):
                        return val

        from qbrain.core.param_manager import case as param_case
        set_case = next((c for c in param_case.RELAY_PARAM if c.get("case") == "SET_PARAM"), None)
        req_struct = set_case.get("req_struct", {}) if set_case else {}
        data_struct = req_struct.get("data", req_struct) or {}
        param_def = data_struct.get("param", data_struct) if isinstance(data_struct, dict) else data_struct
        if isinstance(param_def, dict) and param_def and not isinstance(param_def.get("type"), type):
            return param_def
        return {
            "id": "string",
            "name": "string",
            "type": "string",
            "description": "string",
            "value": "any",
            "const": "bool",
            "axis_def": "any",
        }

    def intelligent_processor(
        self,
        raw_payload: Dict[str, Any] | List[Dict[str, Any]],
        user_id: str,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Process raw extraction payload into normalized param dicts for set_item.
        Sets params from fields keys, params section. Returns list ready for set_param.
        """
        items = []
        if isinstance(raw_payload, list):
            items = [p for p in raw_payload if isinstance(p, dict)]
        elif isinstance(raw_payload, dict):
            for key in ("param", "params", "items"):
                val = raw_payload.get(key)
                if isinstance(val, list):
                    items = [p for p in val if isinstance(p, dict)]
                    break
                elif isinstance(val, dict):
                    items = [val]
                    break

        result = []
        for p in items:
            pid = p.get("id") or p.get("name") or generate_numeric_id()
            p["id"] = pid
            p["name"] = p.get("name") or p.get("id")
            p["user_id"] = user_id
            if "value" in p and p["value"] is not None:
                if isinstance(p["value"], (np.ndarray,)):
                    p["value"] = json.dumps(p["value"].tolist())
                else:
                    p["value"] = json.dumps(p["value"], default=str)
            if ("axis_def" not in p or p.get("axis_def") is None) and "const" in p:
                p["axis_def"] = 0
            if "type" in p and "param_type" not in p:
                p["param_type"] = p["type"]
            result.append(p)
        return result



    def load_g(self, user_id, ):
        pass



    def param_cfg(self):
        """
        Configuration for Gem structured response.
        Keep it simple to avoid typing issues from invalid generics.
        """
        return {
            "response_mime_type": "application/json",
        }

    def extract_from_file_bytes(self, content: bytes or str, instructions, users_params) -> Optional[Dict[str, Any]]:
        """
        Extract manager-specific param content from file bytes using the static prompt.
        Uses Gem LLM with req_struct/out_struct from SET_PARAM case.
        """
        print("param manager, extract_from_file_bytes...")
        try:
            prompt = self._get_extract_prompt(
                instructions,
                content,
                users_params,
            )
            gem = Gem()

            parsed = gem.ask(
                content=prompt,
                config=self.param_cfg()
            )
            print("parsed params:", parsed)
            return {"param": parsed}
        except Exception as e:
            print(f"{_PARAMS_DEBUG} extract_from_file_bytes error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_users_params(self, user_id: str, select: str = "*") -> List[Dict[str, Any]]:
        print("get_users_params", user_id)
        result = self.qb.get_users_entries(
            user_id=user_id,
            table=self.table,
            select=select
        )
        return [dict(row) for row in result]

    def set_param(
            self,
            param_data: Dict[str, Any] or List[dict],
            user_id: str,
    ):
        """
        Upsert parameters.
        Schema: id, name, type, user_id, description, embedding (ARRAY<FLOAT64>), status, created_at, updated_at
        """
        try:
            print(f"{_PARAMS_DEBUG} set_param: user_id={user_id}, count={1 if not isinstance(param_data, list) else len(param_data)}")
            if not isinstance(param_data, list):
                param_data = [param_data]

            prev_params = []

            for p in param_data:
                # Normalize id/name from extraction (LLM may return only "name")
                p["id"] = p.get("id") or p.get("name") or generate_numeric_id()
                p["name"] = p.get("name") or p.get("id")
                p["user_id"] = user_id
                if "value" in p:
                    if isinstance(p["value"], (np.ndarray, )):
                        p["value"] = json.dumps(p["value"].tolist())
                    else:
                        p["value"] = json.dumps(p["value"], default=str)

                # Only derive axis_def when we actually have a const flag
                if ("axis_def" not in p or p.get("axis_def") is None) and "const" in p:
                    p["axis_def"] = 0 # todo , self.get_axis_param(p["is_constant"])

                if "embedding" in p and p["embedding"]:
                    if isinstance(p["embedding"], str):
                        try:
                            p["embedding"] = json.loads(p["embedding"])
                        except Exception:
                            pass

                prev_param = p.copy()
                prev_param["id"] = f"prev_{p['id']}"
                prev_param["description"] = "Prev variation to trac emergence over time. The val field is empty and taks the prev val of its parent at each iteration"
                prev_param["value"] = None
                prev_params.append(prev_param)

            self.qb.set_item(
                self.PARAMS_TABLE,
                param_data,
            )

            print(f"{_PARAMS_DEBUG} set_param: done")
        except Exception as e:
            print(f"{_PARAMS_DEBUG} set_param: error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def delete_param(self, param_id: str, user_id: str):
        try:
            print(f"{_PARAMS_DEBUG} delete_param: param_id={param_id}, user_id={user_id}")
            self.qb.del_entry(
                id=param_id,
                table=self.table,
                user_id=user_id
            )
            print(f"{_PARAMS_DEBUG} delete_param: done")
        except Exception as e:
            print(f"{_PARAMS_DEBUG} delete_param: error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def link_field_param(self, data: List[Dict[str, Any]] or Dict[str, Any], user_id: str):
        """
        Link field to param.
        Schema: id, field_id, param_id, param_value (STRING), user_id, status, ...
        """
        if isinstance(data, dict):
            data = [data]

        now = datetime.now()
        
        for item in data:
            row = {
                "id": item.get("id", generate_numeric_id()),
                "field_id": item["field_id"],
                "param_id": item["param_id"],
                "param_value": str(item.get("param_value", "")), # Store value as string
                "user_id": user_id,
                "status": "active",
                "created_at": now,
                "updated_at": now
            }
            self.qb.set_item(self.FIELDS_TO_PARAMS_TABLE, row, keys={"id": row["id"]})

    def rm_link_field_param(self, field_id: str, param_id: str, user_id: str):
        """
        Remove link between field and param.
        Using upsert_copy with custom matching since we might want to target specfic link?
        But table has 'id'. If we don't have link ID, we match by field_id + param_id.
        Schema of fields_to_params has 'id'.
        
        If we want to delete by field_id + param_id:
        """
        
        # We need a custom query or strict logic. QBrainTableManager.rm_module_link uses upsert_copy with keys.
        # Let's use similar logic. 
        # But we have two keys: field_id AND param_id.
        
        keys = {
            "field_id": field_id,
            "param_id": param_id,
            "user_id": user_id
        }
        updates = {"status": "deleted"}
        self.qb.set_item(self.FIELDS_TO_PARAMS_TABLE, updates, keys=keys)

    def get_fields_params(self, field_id: str, user_id: str) -> List[Dict[str, Any]]:
        """
        Get info about params linked to a field.
        We probably want the param details AND the value from the link table.
        """
        
        # 1. Get links
        query = f"""
            SELECT * FROM `{self.pid}.{self.DATASET_ID}.{self.FIELDS_TO_PARAMS_TABLE}`
            WHERE field_id = @field_id AND user_id = @user_id AND (status != 'deleted' OR status IS NULL)
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("field_id", "STRING", field_id),
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
            ]
        )
        links = self.qb.db.run_query(query, conv_to_dict=True, job_config=job_config)
        
        if not links:
            return []

        # 2. Get param details
        param_ids = [l["param_id"] for l in links]
        # De-duplicate IDs
        param_ids = list(set(param_ids))
        
        params_details = self.qb.row_from_id(
            id=param_ids,
            table=self.PARAMS_TABLE,
            select="*"
        )
        
        # 3. Merge details
        # We want to return a list of params, perhaps with 'value' attached?
        # Or return links + expanded param info?
        
        params_map = {p["id"]: p for p in params_details}
        
        result = []
        for l in links:
            pid = l["param_id"]
            if pid in params_map:
                p_info = params_map[pid].copy()
                # Attach value from link
                p_info["link_value"] = l.get("param_value")
                p_info["link_id"] = l.get("id")
                result.append(p_info)
                
        return result


    def upload_sm_params(self, user_id: str):
        print(f"Uploading SM params for user {user_id}")
        qfu = QFUtils()
        collected_params = {}

        all_fields = FERMIONS + G_FIELDS + H

        for field in all_fields:
            try:
                # batch_field_single returns a dict of attributes (params)
                params = qfu.batch_field_single(field, dim=3)
                
                if isinstance(params, dict):
                    for k, v in params.items():
                        # Determine BQ type
                        bq_type = "STRING"
                        if isinstance(v, (int, float)):
                            bq_type = "FLOAT64"
                        elif isinstance(v, bool):
                            bq_type = "BOOL"
                            
                        if k not in collected_params:
                            collected_params[k] = bq_type
            except Exception as e:
                print(f"Error extracting params for {field}: {e}")

        # Batch upsert
        batch_data = []
        for p_name, p_type in collected_params.items():
            batch_data.append({
                "id": p_name, # Use name as ID for standard params
                "name": p_name,
                "param_type": p_type,
                "description": f"Standard Model Parameter: {p_name}"
            })

        if batch_data:
            self.set_param(batch_data, user_id)
            print(f"Uploaded {len(batch_data)} SM params")


_default_param_manager = ParamsManager(get_qbrain_table_manager(None))
params_manager = _default_param_manager  # backward compat

def handle_get_users_params(data=None, auth=None):
    """Retrieve all params owned by a user. Required: user_id (auth or data)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    if err := require_param(user_id, "user_id"):
        return err
    from qbrain.core.managers_context import get_param_manager
    params = get_param_manager().get_users_params(user_id)
    return {"type": "LIST_USERS_PARAMS", "data": {"params": params}}


def handle_list_users_params(data=None, auth=None):
    """Alias for handle_get_users_params."""
    return handle_get_users_params(data=data, auth=auth)


def handle_set_param(data=None, auth=None):
    """Create or update a param. Required: user_id (auth), param (data). Optional: original_id (auth)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    param_data = data.get("param") if isinstance(data, dict) else None
    original_id = get_val(data, auth, "original_id")
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param_truthy(param_data, "param"):
        return err
    from qbrain.core.managers_context import get_param_manager
    pm = get_param_manager()
    if original_id:
        pm.delete_param(original_id, user_id)
    pm.set_param(param_data, user_id)
    return handle_get_users_params(data={}, auth={"user_id": user_id})


def handle_del_param(data=None, auth=None):
    """Delete a param by ID. Required: user_id, param_id (auth or data)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    param_id = get_val(data, auth, "param_id")
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param(param_id, "param_id"):
        return err
    from qbrain.core.managers_context import get_param_manager
    get_param_manager().delete_param(param_id, user_id)
    return handle_get_users_params(data={}, auth={"user_id": user_id})


def handle_link_field_param(data=None, auth=None):
    """Link a param to a field. Required: user_id (auth). Required: links (data) or field_id+param_id (auth/data)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    links = data.get("links") if isinstance(data, dict) else None
    if not links:
        fid = get_val(data, auth, "field_id")
        pid = get_val(data, auth, "param_id")
        pv = get_val(data, auth, "param_value")
        if fid and pid:
            links = [{"field_id": fid, "param_id": pid, "param_value": pv}]
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param_truthy(links, "links"):
        return err
    from qbrain.core.managers_context import get_param_manager
    pm = get_param_manager()
    pm.link_field_param(links, user_id)
    target_field_id = links[0]["field_id"]
    return {
        "type": "GET_FIELDS_PARAMS",
        "data": {"params": pm.get_fields_params(target_field_id, user_id)},
        "auth": {"field_id": target_field_id}
    }


def handle_rm_link_field_param(data=None, auth=None):
    """Remove the link between a field and a param. Required: user_id, field_id, param_id (auth or data)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    field_id = get_val(data, auth, "field_id")
    param_id = get_val(data, auth, "param_id")
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param(field_id, "field_id"):
        return err
    if err := require_param(param_id, "param_id"):
        return err
    from qbrain.core.managers_context import get_param_manager
    get_param_manager().rm_link_field_param(field_id, param_id, user_id)
    return {
        "type": "GET_FIELDS_PARAMS",
        "data": {"params": params_manager.get_fields_params(field_id, user_id)},
        "auth": {"field_id": field_id}
    }


def handle_get_fields_params(data=None, auth=None):
    """Retrieve all params linked to a field. Required: user_id, field_id (auth or data)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    field_id = get_val(data, auth, "field_id")
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param(field_id, "field_id"):
        return err
    from qbrain.core.managers_context import get_param_manager
    params = get_param_manager().get_fields_params(field_id, user_id)
    return {"type": "GET_FIELDS_PARAMS", "data": {"params": params}, "auth": {"field_id": field_id}}
