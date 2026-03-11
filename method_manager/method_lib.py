import json
import logging
import random
from typing import Dict, Any, List, Optional, Callable

import numpy as np

from qbrain.core.method_manager.gen_type import generate_methods_out_schema
from qbrain.core.method_manager.xtrct_prompt import xtrct_method_prompt
from qbrain.core.module_manager.create_runnable import create_runnable
from qbrain.core.param_manager.params_lib import ParamsManager
from qbrain.core.qbrain_manager import get_qbrain_table_manager, QBrainTableManager
from qbrain.core.handler_utils import require_param, require_param_truthy, get_val
from qbrain.graph import GUtils
from qbrain.qf_utils.qf_utils import QFUtils

def generate_numeric_id() -> str:
    """Generate a random numeric ID."""
    return str(random.randint(1000000000, 9999999999))

class MethodManager:
    DATASET_ID = "QBRAIN"
    METHODS_TABLE = "methods"
    SESSIONS_METHODS_TABLE = "sessions_to_methods"

    def __init__(self, qb:QBrainTableManager, params_manager):
        self.qb = qb
        self.params_manager=params_manager
        self.pid = qb.pid
        self.table_ref = f"{self.METHODS_TABLE}"
        self.session_link_ref = f"{self.SESSIONS_METHODS_TABLE}"
        self.qfu = QFUtils()
        self._extract_prompt = None  # built lazily to avoid circular import with case


    def execute_method_testwise(self, methods: list[dict], user_id, g):
        print("[START] execute_method_testwise")
        try:
            return_key_ids = self._collect_return_keys(methods)
            return_key_param_entries = self._load_return_param_entries(return_key_ids)
            param_entries = self._load_user_params(user_id)

            self._merge_graph_param_entries(g, return_key_ids, return_key_param_entries)
            self._merge_graph_param_entries_into_user_params(g, param_entries)

            print("Entries fetched:")
            print("return_key_ids",return_key_ids)
            print("return_key_param_entries",return_key_param_entries)
            print("param_entries",param_entries)

            adapted_return_params = self._process_methods(
                methods,
                param_entries,
                return_key_param_entries,
                user_id,
            )
            self._persist_params(adapted_return_params, user_id)
        except Exception as e:
            print("[ERROR] execute_method_testwise", e)
        print("[DONE] execute_method_testwise")

    def _collect_return_keys(self, methods):
        print("[START] _collect_return_keys")
        try:
            ids = [m["return_key"] for m in methods]
            print("return_key_ids:", ids)
            return ids
        except Exception as e:
            print("[ERROR] _collect_return_keys", e)
            return []
        finally:
            print("[DONE] _collect_return_keys")

    def _load_return_param_entries(self, return_key_ids):
        print("[START] _load_return_param_entries")
        try:
            entries = self.qb.row_from_id(return_key_ids, table="params")
            if entries:
                entries = {p["id"]: p for p in entries}
            else:
                entries = {}
            return entries
        except Exception as e:
            print("[ERROR] _load_return_param_entries", e)
            return {}
        finally:
            print("[DONE] _load_return_param_entries")

    def _load_user_params(self, user_id):
        print("[START] _load_user_params")
        try:
            entries = self.qb.get_users_entries(user_id, table="params")
            if entries:
                entries = {p["id"]: p for p in entries}
            else:
                entries = {}
            return entries
        except Exception as e:
            print("[ERROR] _load_user_params", e)
            return {}
        finally:
            print("[DONE] _load_user_params")

    def _merge_graph_param_entries(self, g, return_key_ids, return_key_param_entries):
        print("[START] _merge_graph_param_entries")
        try:
            for k in return_key_ids:
                node_data = {}
                if g.G.has_node(k):
                    node_data = g.G.nodes[k]

                if k in return_key_param_entries:
                    return_key_param_entries[k].update(node_data)
                else:
                    return_key_param_entries[k] = node_data
        except Exception as e:
            print("[ERROR] _merge_graph_param_entries", e)
        finally:
            print("[DONE] _merge_graph_param_entries")

    def _merge_graph_param_entries_into_user_params(self, g, param_entries):
        """Merge PARAM nodes from graph into param_entries so method execution has all params (fixes mismatch vs param_rows from SM workflow)."""
        try:
            for nid, attrs in g.G.nodes(data=True):
                if attrs.get("type") == "PARAM":
                    param_data = {
                        "id": nid,
                        "param_type": attrs.get("param_type"),
                        "description": attrs.get("description", ""),
                        "const": attrs.get("const"),
                        "axis_def": attrs.get("axis_def"),
                        "value": attrs.get("value"),
                        "shape": attrs.get("shape"),
                    }
                    if nid in param_entries:
                        param_entries[nid].update(param_data)
                    else:
                        param_entries[nid] = param_data
        except Exception as e:
            print("[ERROR] _merge_graph_param_entries_into_user_params", e)

    def _process_methods(self, methods, param_entries, return_key_param_entries, user_id):
        print("[START] _process_methods")
        adapted_return_params = []

        try:
            for method in methods:
                payload = self._execute_single_method(
                    method,
                    param_entries,
                    return_key_param_entries,
                )

                if payload:
                    adapted_return_params.append(payload)

        except Exception as e:
            print("[ERROR] _process_methods", e)

        print("[DONE] _process_methods")
        return adapted_return_params

    def _execute_single_method(self, method, param_entries, return_key_param_entries):
        print("[START] _execute_single_method")

        try:
            params = method.get("params")
            code = method.get("code")
            return_key = method.get("return_key")
            _def_id = method["id"]

            print("CALC METHOD TESTWISE WITH:")
            print("code:", code)
            print("return_key:", return_key)
            #print("params:", params)

            param_entry = return_key_param_entries.get(return_key)
            param_shape = None

            if param_entry:
                param_shape = param_entry.get("shape")

            if param_shape:
                print("shape already known:", param_shape)
                return None

            val_params = self._build_placeholder_params(params, param_entries)
            runnable: Callable = create_runnable(code)
            result = runnable(*val_params)

            if result is None:
                print("no result returned")
                return None

            result_shape = np.array(result).shape

            if param_entry:
                payload = param_entry
            else:
                payload = dict(
                    id=return_key,
                    param_type=str(type(result)),
                    axis_def=0,
                    description=f"return key of {_def_id}",
                )

            payload["shape"] = result_shape
            return payload

        except Exception as e:
            print("[ERROR] _execute_single_method", e)
            return None
        finally:
            print("[DONE] _execute_single_method")

    def _build_placeholder_params(self, params, param_entries):
        print("[START] _build_placeholder_params")
        val_params = []
        # inbalance between params and methods params -> create param entries from -> maybe user_id wrong?
        try:
            for p_key in params:
                p_shape = param_entries[p_key]["shape"]
                param_type = param_entries[p_key]["param_type"]
                param_value = param_entries[p_key]["value"]

                resolved = self.adapt_to_n_dims(
                    p_key=p_key,
                    param_type=param_type,
                    flat_value=param_value,
                    shape=p_shape,
                )

                is_array = resolved and isinstance(resolved, (list, tuple)) and len(resolved)

                if is_array:
                    arr_shape = np.array(resolved).shape
                    # Replace dim 1 with 2 for matmul compatibility: (1,) @ (2,2) fails
                    arr_shape = tuple(2 if d == 1 else d for d in arr_shape)
                    val_params.append(np.ones(arr_shape, dtype=np.complex64))
                else:
                    # Use (2,2) so matmul/@ works; (1,1) can mismatch when other param has dim 2
                    val_params.append(np.ones((2, 2), dtype=np.complex64))

            print("val_params built:", val_params)
            return val_params

        except Exception as e:
            print("[ERROR] _build_placeholder_params", e)
            return []
        finally:
            print("[DONE] _build_placeholder_params")

    def _persist_params(self, adapted_return_params, user_id):
        print("[START] _persist_params")

        try:
            if adapted_return_params:
                self.params_manager.set_param(
                    param_data=adapted_return_params,
                    user_id=user_id,
                )
        except Exception as e:
            print("[ERROR] _persist_params", e)
        finally:
            print("[DONE] _persist_params")








    def extract_prompt(
        self,
        params: List[Dict[str, Any]],
        fallback_params: List[Dict[str, Any]],
        instructions: str,
    ) -> str:
        """Static prompt for extraction. Used by intelligent_extraction as manager_prompt_ext."""
        return xtrct_method_prompt(
            params=params,
            fallback_params=fallback_params,
            instructions=instructions,
        )

    def intelligent_processor(
        self,
        raw_payload: Dict[str, Any] | List[Dict[str, Any]],
        user_id: str,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Process raw extraction payload into normalized method dicts for set_item.
        Infers params (required args) from method definition; fallback from methods.params.
        Returns list ready for set_method.
        """
        items = []
        if isinstance(raw_payload, list):
            items = [m for m in raw_payload if isinstance(m, dict)]
        elif isinstance(raw_payload, dict):
            for key in ("methods", "items"):
                val = raw_payload.get(key)
                if isinstance(val, list):
                    items = [m for m in val if isinstance(m, dict)]
                    break
                elif isinstance(val, dict):
                    items = [val]
                    break

        result = []
        for m in items:
            mid = m.get("id") or generate_numeric_id()
            m["id"] = mid
            m["user_id"] = user_id
            if "equation" in m and "code" not in m:
                m["code"] = m.get("equation", "")
            if "params" in m and not isinstance(m["params"], list):
                if isinstance(m["params"], str):
                    try:
                        m["params"] = json.loads(m["params"]) if m["params"] else []
                    except json.JSONDecodeError:
                        m["params"] = [m["params"]] if m["params"] else []
                elif m["params"] is None:
                    m["params"] = []
            if "params" not in m:
                m["params"] = []
            result.append(m)
        return result

    def extract_from_file_bytes(
            self,
            content: bytes or str,
            params,
            fallback_params,
            instructions,

    ) -> Optional[Dict[str, Any]]:
        """
        Extract manager-specific method/equation content from file bytes using the static prompt.
        Uses Gem LLM with req_struct/out_struct from SET_METHOD case.
        """
        try:
            from qbrain.gem_core.gem import Gem
            gem = Gem()

            prompt = xtrct_method_prompt(
                params,
                fallback_params,
                instructions,
            )

            try:
                content = f"{prompt}\n\n--- FILE CONTENT ---\n{content}"
                response = gem.ask(
                    content,
                    config=generate_methods_out_schema
                )
                text = (response or "").strip().replace("```json", "").replace("```", "").strip()
                parsed = json.loads(text)
                if "methods" in parsed:
                    return {
                        "methods": parsed["methods"] if isinstance(parsed["methods"], list) else [parsed["methods"]]}
                if "id" in parsed or "equation" in parsed:
                    return {"methods": parsed}

                print("extracted mehods:", parsed)
                return {"methods": parsed}
            except Exception as e:
                print("Err method amanger extract_from_file_bytes", e)
        except Exception as e:
            logging.error(f"MethodManager extract_from_file_bytes error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def set_method(self, rows: List[Dict] or Dict, user_id: str, g:GUtils=None):
        if isinstance(rows, dict):
            rows = [rows]
        print("set method rows", len(rows))
        self.qb.set_item(self.METHODS_TABLE, rows)

    def link_session_method(self, session_id: str, method_id: str, user_id: str):
        """Link a method to a session."""
        row_id = generate_numeric_id()
        row = {
            "id": row_id,
            "session_id": session_id,
            "method_id": method_id,
            "user_id": user_id,
            "status": "active"
        }
        self.qb.set_item(self.SESSIONS_METHODS_TABLE, row)

    def delete_method(self, method_id: str, user_id: str):
        """Delete method and its links."""
        # Delete from methods (Soft Delete)
        self.qb.del_entry(
            id=method_id,
            table=self.METHODS_TABLE,
            user_id=user_id
        )

        # Delete from sessions_to_methods (Soft Delete)
        query2 = f"UPDATE {self.qb._table_ref(self.SESSIONS_METHODS_TABLE)} SET status = 'deleted' WHERE method_id = @method_id AND user_id = @user_id"
        self.qb.db.execute(query2, params={"method_id": method_id, "user_id": user_id})

    def rm_link_session_method(self, session_id: str, method_id: str, user_id: str):
        """Remove link session method (soft delete)."""
        self.qb.rm_link_session_link(
            session_id=session_id,
            id=method_id,
            user_id=user_id,
            session_link_table=self.session_link_ref,
            session_to_link_name_id="method_id"
        )

    def update_method_params(self, method_id: str, user_id: str, params: Dict[str, Any] = None):
        """
        Update params field of a method.
        """
        if params is None:
            params = {}

        self.qb.set_item(
            self.METHODS_TABLE, 
            {"params": params}
        )

    def retrieve_user_methods(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve all methods for a user."""
        result = self.qb.get_users_entries(
            user_id=user_id,
            table=self.table_ref
        )
        return [dict(row) for row in result]

    def retrieve_session_methods(self, session_id: str, user_id: str, select: str = "*") -> List[Dict[str, Any]]:
        """Retrieve methods for a session."""
        # get sessions_to_methods rows -> get method rows
        links = self.qb.list_session_entries(
            user_id=user_id,
            session_id=session_id,
            table=self.session_link_ref,
            select="method_id"
        )
        
        method_ids = [row['method_id'] for row in links]
        
        result = self.qb.row_from_id(
            nid=method_ids,
            select="*",
            table=self.table_ref
        )

        return [dict(row) for row in result]

    def get_method_by_id(
            self, method_id: str or list, select: str = "*") -> Optional[Dict[str, Any]]:
        """Get a single method by ID."""
        if isinstance(method_id, str):
            method_id = [method_id]

        rows = self.qb.row_from_id(
            nid=method_id,
            select=select,
            table=self.METHODS_TABLE
        )
        return {"methods": rows}








# Instantiate

_qb:QBrainTableManager = get_qbrain_table_manager(None)
params_manager = ParamsManager(_qb)

_default_method_manager = MethodManager(_qb, params_manager)
method_manager = _default_method_manager  # backward compat

# -- RELAY HANDLERS --

def handle_list_users_methods(data=None, auth=None):
    """Retrieve all methods owned by a user. Required: user_id (auth or data)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    if err := require_param(user_id, "user_id"):
        return err
    from qbrain.core.managers_context import get_method_manager
    return {"type": "LIST_USERS_METHODS", "data": {"methods": get_method_manager().retrieve_user_methods(user_id)}}


def handle_send_sessions_methods(data=None, auth=None):
    """Retrieve all methods linked to a session. Required: user_id, session_id (auth or data)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    session_id = get_val(data, auth, "session_id")
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param(session_id, "session_id"):
        return err
    from qbrain.core.managers_context import get_method_manager
    return {"type": "GET_SESSIONS_METHODS", "data": {"methods": get_method_manager().retrieve_session_methods(session_id, user_id)}}


def handle_get_sessions_methods(data=None, auth=None):
    """Alias for handle_send_sessions_methods."""
    return handle_send_sessions_methods(data=data, auth=auth)


def handle_link_session_method(data=None, auth=None):
    """Link a method to a session. Required: user_id, method_id, session_id (auth or data)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    method_id = get_val(data, auth, "method_id")
    session_id = get_val(data, auth, "session_id")
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param(method_id, "method_id"):
        return err
    if err := require_param(session_id, "session_id"):
        return err
    from qbrain.core.managers_context import get_method_manager
    get_method_manager().link_session_method(session_id, method_id, user_id)
    return handle_send_sessions_methods(data={"session_id": session_id}, auth={"user_id": user_id})


def handle_rm_link_session_method(data=None, auth=None):
    """Remove the link between a session and a method. Required: user_id, session_id, method_id (auth or data)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    session_id = get_val(data, auth, "session_id")
    method_id = get_val(data, auth, "method_id")
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param(session_id, "session_id"):
        return err
    if err := require_param(method_id, "method_id"):
        return err
    from qbrain.core.managers_context import get_method_manager
    get_method_manager().rm_link_session_method(session_id, method_id, user_id)
    return handle_send_sessions_methods(data={"session_id": session_id}, auth={"user_id": user_id})


def handle_del_method(data=None, auth=None):
    """Delete a method by ID. Required: user_id, method_id (auth or data)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    method_id = get_val(data, auth, "method_id")
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param(method_id, "method_id"):
        return err
    from qbrain.core.managers_context import get_method_manager
    get_method_manager().delete_method(method_id, user_id)
    return handle_list_users_methods(data={}, auth={"user_id": user_id})


def handle_set_method(data=None, auth=None):
    """Create or update a method. Required: user_id (auth), data (method dict with equation, description, id, params). Optional: original_id (auth)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    original_id = get_val(data, auth, "original_id")
    method_data = data if isinstance(data, dict) else None
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param_truthy(method_data, "data"):
        return err

    equation = method_data.get("equation")
    params = method_data.get("params")

    method_data["code"] = equation
    if "jax_code" not in method_data:
        from qbrain.core.managers_context import get_file_manager
        method_data["jax_code"] = get_file_manager().jax_predator(method_data["code"])

    # Ensure ID
    if "id" not in method_data or not method_data["id"]:
        method_data["id"] = generate_numeric_id()
        
    # Process Params if list
    if isinstance(params, list):
         origins = method_data.get("origins")
         if isinstance(origins, list):
             key_counts = {}
             for i, key in enumerate(params):
                 if i < len(origins):
                     origin = origins[i]
                     if key in key_counts:
                         if origin != "self":
                             params[i] = "_" * key_counts[key] + key
                     key_counts[key] = key_counts.get(key, 0) + 1
         method_data["params"] = json.dumps(params)
         
    # Generate JAX Code
    if equation:
        print(f"Generating JAX code for equation: {equation}")
        try:
            from qbrain.core.managers_context import get_file_manager
            jax_code = get_file_manager().jax_predator(equation)
            #method_data["jax_code"] = jax_code
            print("JAX Code generated:", jax_code)
        except Exception as e:
            print(f"Failed to generate JAX code: {e}")

    # handle set method
    from qbrain.core.managers_context import get_method_manager
    mm = get_method_manager()
    # test_exec_method



    # set
    mm.set_method(method_data, user_id)
    return handle_list_users_methods(data={}, auth={"user_id": user_id})


def handle_get_method(data=None, auth=None):
    """Retrieve a single method by ID. Required: method_id (auth or data)."""
    data, auth = data or {}, auth or {}
    method_id = get_val(data, auth, "method_id")
    if err := require_param(method_id, "method_id"):
        return err
    from qbrain.core.managers_context import get_method_manager
    row = get_method_manager().get_method_by_id(method_id)
    if not row:
        return {"error": "Method not found"}
    return {"type": "GET_METHOD", "data": row}


"""

    def adapt_to_n_dims(self, p_key, param_type: type, flat_value: list, shape: Tuple[int, ...]) -> Union[List, Tuple]:
        try:
            # Normalize shape: may come as scalar, None, tuple, or JSON string
            if isinstance(shape, str):
                try:
                    s = json.loads(shape)
                    shape = tuple(s) if isinstance(s, (list, tuple)) else (s,) if s is not None else ()
                except Exception:
                    shape = ()
            elif shape is None:
                shape = ()
            elif not isinstance(shape, (list, tuple)):
                shape = (shape,) if shape else ()

            # Parse flat_value if JSON string
            if isinstance(flat_value, str):
                try:
                    flat_value = json.loads(flat_value)
                except Exception:
                    pass

            if not shape:
                print("no shape for", p_key, param_type, flat_value, shape)
                if flat_value is None:
                    return None
                if isinstance(flat_value, (list, tuple)):
                    return flat_value[0] if flat_value else None
                return flat_value  # scalar (int, float, etc.)

            # flat_value must be iterable for reshaping
            if not isinstance(flat_value, (list, tuple)):
                return flat_value

            # Container type for nesting: only list/tuple are valid
            container = list if param_type not in (list, tuple) else param_type

            # Calculate how many elements belong in each sub-slice of the current dimension
            stride = 1
            for dim in shape[1:]:
                stride *= dim

            nested = []
            for i in range(0, len(flat_value), stride):
                chunk = flat_value[i: i + stride]

                if len(shape) > 1:
                    nested.append(self.adapt_to_n_dims(p_key, param_type, chunk, shape[1:]))
                else:
                    nested.extend(chunk)
                    break

            ptype = container(nested)
            print("param_shape", ptype)
            return ptype
        except Exception as e:
            print(f"Err method manager adapt_to_n_dims", e)
        return None

"""


