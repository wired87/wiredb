import base64
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

from google.cloud import bigquery


from qbrain.core.file_manager import RawModuleExtractor
from qbrain.core.qbrain_manager import get_qbrain_table_manager
from qbrain.core.handler_utils import require_param, require_param_truthy, get_val

_MODULE_DEBUG = "[ModuleWsManager]"

# Define Schemas
MODULE_SCHEMA = [
    bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("file_type", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("binary_data", "BYTES", mode="NULLABLE"),
    bigquery.SchemaField("code", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("params", "STRING", mode="NULLABLE"),
]

SESSIONS_MODULES_SCHEMA = [
    bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("session_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("module_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
]

MODULES_METHODS_SCHEMA = [
    bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("module_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("method_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
]

def generate_numeric_id() -> str:
    """Generate a random numeric ID."""
    return str(random.randint(1000000000, 9999999999))

class ModuleWsManager:
    DATASET_ID = "QBRAIN"
    MODULES_TABLE = "modules"
    SESSIONS_MODULES_TABLE = "sessions_to_modules"
    MODULES_METHODS_TABLE = "modules_to_methods"

    def __init__(self, qb):
        self.qb = qb
        self.table_ref = f"{self.MODULES_TABLE}"
        self.session_link_ref = f"{self.SESSIONS_MODULES_TABLE}"
        self.module_creator = RawModuleExtractor()

    def _ensure_module_table(self):
        schema = {f.name: f.field_type for f in MODULE_SCHEMA}
        self.qb.get_table_schema(table_id=self.MODULES_TABLE, schema=schema, create_if_not_exists=True)

    def _ensure_sessions_modules_table(self):
        schema = {f.name: f.field_type for f in SESSIONS_MODULES_SCHEMA}
        self.qb.get_table_schema(table_id=self.SESSIONS_MODULES_TABLE, schema=schema, create_if_not_exists=True)

    def _ensure_modules_methods_table(self):
        schema = {f.name: f.field_type for f in MODULES_METHODS_SCHEMA}
        self.qb.get_table_schema(table_id=self.MODULES_METHODS_TABLE, schema=schema, create_if_not_exists=True)

    def set_module(self, rows, user_id: str):
        if isinstance(rows, dict):
            rows = [rows]

        now = datetime.now()
        for row in rows:
            row["user_id"] = user_id

            row["created_at"] = now
            row["updated_at"] = now

            if row.get("parent"):
                row.pop("parent")

            if row.get("module_index"):
                row.pop("module_index")

        print("set module rows", len(rows), rows)
        self.qb.set_item(self.MODULES_TABLE, rows)

    def link_session_module(self, session_id: str, module_id: str, user_id: str):
        """Link a module to a session."""
        row_id = generate_numeric_id()
        row = {
            "id": row_id,
            "session_id": session_id,
            "module_id": module_id,
            "user_id": user_id,
        }
        self.qb.set_item(self.SESSIONS_MODULES_TABLE, row) #, keys={"id": row["id"]}

    def link_module_methods(self, module_id: str, method_ids: List[str], user_id: str):
        """Link methods to a module."""
        # First, soft delete existing links for this module to avoid duplicates/stale links
        query = f"UPDATE {self.qb._table_ref(self.MODULES_METHODS_TABLE)} SET status = 'deleted' WHERE module_id = @module_id AND user_id = @user_id"
        self.qb.db.execute(query, params={"module_id": module_id, "user_id": user_id})

        # Upsert new links
        rows = []
        for mid in method_ids:
            row_id = generate_numeric_id()
            rows.append({
                "id": row_id,
                "module_id": module_id,
                "method_id": mid,
                "user_id": user_id,
                "status": "active"
            })
        
        if rows:
            self.qb.set_item(self.MODULES_METHODS_TABLE, rows)

    def delete_module(self, module_id: str, user_id: str):
        """Delete module and its links."""
        # Delete from modules (Soft Delete)
        self.qb.del_entry(
            id=module_id,
            table=self.MODULES_TABLE,
            user_id=user_id
        )

        # Delete from sessions_to_modules (Soft Delete)
        query2 = f"UPDATE {self.qb._table_ref(self.SESSIONS_MODULES_TABLE)} SET status = 'deleted' WHERE module_id = @module_id AND user_id = @user_id"
        self.qb.db.execute(query2, params={"module_id": module_id, "user_id": user_id})

        query3 = f"UPDATE {self.qb._table_ref(self.MODULES_METHODS_TABLE)} SET status = 'deleted' WHERE module_id = @module_id AND user_id = @user_id"
        self.qb.db.execute(query3, params={"module_id": module_id, "user_id": user_id})


    def rm_link_session_module(self, session_id: str, module_id: str, user_id: str):
        """Remove link session module (soft delete)."""
        self.qb.rm_link_session_link(
            session_id=session_id,
            id=module_id,
            user_id=user_id,
            session_link_table=self.session_link_ref,
            session_to_link_name_id="module_id"
        )


    def update_module_params(self, module_id: str, user_id: str, params: Dict[str, Any] = None):
        """
        Update params field of a module.
        """
        if params is None:
            params = {}

        self.qb.set_item(
            self.MODULES_TABLE, 
            {"params": params}, 
            keys={"id": module_id, "user_id": user_id}
        )

    def retrieve_user_modules(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve all modules for a user."""
        try:
            print(f"{_MODULE_DEBUG} retrieve_user_modules: user_id={user_id}")
            result = self.qb.get_users_entries(
                user_id=user_id,
                table=self.table_ref
            )
            modules = []
            for row in result:
                row_dict = dict(row)
                if row_dict.get("binary_data", None):
                    row_dict["binary_data"] = base64.b64encode(
                        row_dict["binary_data"]).decode("utf-8")
                modules.append(row_dict)
            print(f"{_MODULE_DEBUG} retrieve_user_modules: got {len(modules)} module(s)")
            return modules
        except Exception as e:
            print(f"{_MODULE_DEBUG} retrieve_user_modules: error: {e}")
            import traceback
            traceback.print_exc()
            return []



    def retrieve_session_modules(self, session_id: str, user_id: str, select: str = "m.*") -> List[Dict[str, Any]]:
        """Retrieve modules for a session."""
        # get sessions_to_modules rows -> get module rows
        links = self.qb.list_session_entries(
            user_id=user_id,
            session_id=session_id,
            table=self.session_link_ref,
            select="module_id"
        )
        
        module_ids = [row['module_id'] for row in links]
        
        # Now get the modules
        # Reuse get_module_by_id logic or call row_from_id directly
        # get_module_by_id returns {"modules": [...]}, we want just the list here or consistent return
        
        result = self.qb.row_from_id(
            id=module_ids,
            select="*",
            table=self.table_ref
        )

        modules = []
        for row in result:
            row_dict = dict(row)
            # Process binary data if needed?
            # "return: data={modules:list[modules-table rows]}"
            # We usually shouldn't send bytes directly in JSON.
            # I will encode binary_data to base64 string if present
            if row_dict.get("binary_data"):
                row_dict["binary_data"] = base64.b64encode(row_dict["binary_data"]).decode('utf-8')
            modules.append(row_dict)
        return modules

    def get_module_by_id(
            self, module_id: str or list, select: str = "*") -> Optional[Dict[str, Any]]:
        """Get a single module by ID."""
        if isinstance(module_id, str):
            module_id = [module_id]

        rows = self.qb.row_from_id(
            id=module_id,
            select=select,
            table=self.MODULES_TABLE
        )
        return {"modules": rows}


    def get_modules_fields(self, user_id: str, session_id: str, select: str = "f.*") -> Dict[str, Any]:
        """
        Get fields associated with modules in a session.
        """
        from qbrain.core.managers_context import get_field_manager
        fm = get_field_manager()
        field_ids = fm.retrieve_session_fields(session_id, user_id)

        if not field_ids:
            return {"fields": []}

        response = fm.get_fields_by_id(field_ids, select="*")
        return response


# Default instance for standalone use (no orchestrator context)

_default_module_manager = ModuleWsManager(get_qbrain_table_manager(None))
module_manager = _default_module_manager  # backward compat

# -- RELAY HANDLERS --

def handle_list_users_modules(data=None, auth=None):
    """Retrieve all modules owned by a user. Required: user_id (auth or data)."""
    from qbrain.core.managers_context import get_module_manager
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    if err := require_param(user_id, "user_id"):
        return err
    return {"type": "LIST_USERS_MODULES", "data": {"modules": get_module_manager().retrieve_user_modules(user_id)}}


def handle_send_sessions_modules(data=None, auth=None):
    """Retrieve all modules linked to a session. Required: user_id, session_id (auth or data)."""
    from qbrain.core.managers_context import get_module_manager
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    session_id = get_val(data, auth, "session_id")
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param(session_id, "session_id"):
        return err
    return {"type": "GET_SESSIONS_MODULES", "data": {"modules": get_module_manager().retrieve_session_modules(session_id, user_id)}}


def handle_get_sessions_modules(data=None, auth=None):
    """Alias for handle_send_sessions_modules."""
    return handle_send_sessions_modules(data=data, auth=auth)


def handle_link_session_module(data=None, auth=None):
    """Link a module to a session. Required: user_id, module_id, session_id (auth or data)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    module_id = get_val(data, auth, "module_id")
    session_id = get_val(data, auth, "session_id")
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param(module_id, "module_id"):
        return err
    if err := require_param(session_id, "session_id"):
        return err
    from qbrain.core.managers_context import get_module_manager
    get_module_manager().link_session_module(session_id, module_id, user_id)
    return handle_send_sessions_modules(data={"session_id": session_id}, auth={"user_id": user_id})


def handle_rm_link_session_module(data=None, auth=None):
    """Remove the link between a session and a module. Required: user_id, session_id, module_id (auth or data)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    session_id = get_val(data, auth, "session_id")
    module_id = get_val(data, auth, "module_id")
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param(session_id, "session_id"):
        return err
    if err := require_param(module_id, "module_id"):
        return err
    from qbrain.core.managers_context import get_module_manager
    get_module_manager().rm_link_session_module(session_id, module_id, user_id)
    return handle_send_sessions_modules(data={"session_id": session_id}, auth={"user_id": user_id})


def handle_del_module(data=None, auth=None):
    """Delete a module by ID. Required: user_id, module_id (auth or data)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    module_id = get_val(data, auth, "module_id")
    if err := require_param(user_id, "user_id"):
        return err
    if err := require_param(module_id, "module_id"):
        return err
    from qbrain.core.managers_context import get_module_manager
    get_module_manager().delete_module(module_id, user_id)
    return handle_list_users_modules(data={}, auth={"user_id": user_id})


def handle_set_module(data=None, auth=None):
    """Create or update a module. Required: user_id (auth). Optional: id, fields, methods, description (data), original_id (auth)."""
    data, auth = data or {}, auth or {}
    user_id = get_val(data, auth, "user_id")
    original_id = get_val(data, auth, "original_id")
    d = data if isinstance(data, dict) else {}
    fields = d.get("fields", [])
    methods = d.get("methods", [])
    description = d.get("description", "")
    module_id = d.get("id")
    if err := require_param(user_id, "user_id"):
        return err
    from qbrain.core.managers_context import get_module_manager
    mm = get_module_manager()
    row = dict(id=module_id, user_id=user_id, fields=fields, methods=methods, description=description, status="active")
    if original_id:
        mm.delete_module(original_id, user_id)
    mm.set_module(row, user_id)
    return handle_list_users_modules(data={}, auth={"user_id": user_id})


def handle_get_module(data=None, auth=None):
    """Retrieve a single module by ID. Required: module_id (auth or data)."""
    from qbrain.core.managers_context import get_module_manager
    data, auth = data or {}, auth or {}
    module_id = get_val(data, auth, "module_id")
    if err := require_param(module_id, "module_id"):
        return err
    row = get_module_manager().get_module_by_id(module_id)
    if not row:
        return {"error": "Module not found"}
    return {"type": "GET_MODULE", "data": row}


