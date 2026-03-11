"""
Centralized SQL query builders for QBrainTableManager.

- DuckDB queries live here (returned as SQL + params).
- BigQuery query templates live on BQGroundZero; this module exposes thin wrappers
  to keep legacy call sites stable.

All queries use parameter placeholders for safety.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple


def _flatten_ids(ids: List[Any]) -> List[str]:
    """
    Normalize ids for IN clause: expand JSON strings, flatten nested lists,
    filter None/null, deduplicate. Ensures each id gets its own ? placeholder.
    """
    out: List[str] = []
    seen: set = set()
    for x in ids:
        if x is None:
            continue
        if isinstance(x, str):
            s = x.strip()
            if not s or s.lower() == "null":
                continue
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        for p in _flatten_ids(parsed):
                            if p not in seen:
                                seen.add(p)
                                out.append(p)
                        continue
                except json.JSONDecodeError:
                    pass
            if s not in seen:
                seen.add(s)
                out.append(s)
        elif isinstance(x, (list, tuple)):
            for p in _flatten_ids(list(x)):
                if p not in seen:
                    seen.add(p)
                    out.append(p)
        else:
            s = str(x).strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
    return out


# --------------------------------------------------------------------------------------
# DuckDB query builders
# --------------------------------------------------------------------------------------

# DuckDB queries return (sql, params) where params is either:
# - dict for @param placeholders (DBManager converts @x -> ?), or
# - list for positional ? placeholders (used for IN lists / dynamic arity).


def duck_get_users_entries(table: str, user_id: str, select: str = "*") -> Tuple[str, Dict[str, Any]]:
    query = f"""
        SELECT {select}
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY created_at DESC) AS row_num
            FROM {table}
            WHERE (user_id = @user_id OR user_id = 'public') AND (status != 'deleted' OR status IS NULL)
        )
        WHERE row_num = 1
    """
    return query, {"user_id": user_id}


def duck_get_envs_by_user_goal(
    table: str,
    user_id: str,
    goal_id: Optional[str] = None,
    select: str = "*",
) -> Tuple[str, Dict[str, Any]]:
    """Query envs by user_id and optionally goal_id. Returns latest rows per env."""
    goal_filter = " AND goal_id = @goal_id" if goal_id else ""
    params: Dict[str, Any] = {"user_id": user_id}
    if goal_id:
        params["goal_id"] = goal_id
    query = f"""
        SELECT {select}
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY created_at DESC) AS row_num
            FROM {table}
            WHERE user_id = @user_id AND (status != 'deleted' OR status IS NULL){goal_filter}
        )
        WHERE row_num = 1
    """
    return query, params


def duck_list_session_entries(
    table: str,
    user_id: str,
    session_id: str,
    select: str = "*",
    partition_key: str = "id",
) -> Tuple[str, Dict[str, Any]]:
    query = f"""
        SELECT {select}, status
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY {partition_key} ORDER BY created_at DESC) AS row_num
            FROM {table}
            WHERE user_id = @user_id AND session_id = @session_id
        )
        WHERE row_num = 1
    """
    return query, {"user_id": user_id, "session_id": str(session_id)}


def duck_get_envs_linked_rows(
    table: str,
    env_id: str,
    linked_row_id: str,
    linked_row_id_name: str,
    user_id: str,
    select: str = "*",
) -> Tuple[str, Dict[str, Any]]:
    query = f"""
        SELECT {select}
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY created_at DESC) AS row_num
            FROM {table}
            WHERE env_id = @env_id AND {linked_row_id_name} = @{linked_row_id_name}
              AND user_id = @user_id AND (status != 'deleted' OR status IS NULL)
        )
        WHERE row_num = 1
    """
    return query, {"env_id": env_id, linked_row_id_name: linked_row_id, "user_id": user_id}


def duck_get_modules_linked_rows(
    table: str,
    module_id: str,
    linked_row_id: str,
    linked_row_id_name: str,
    user_id: str,
    select: str = "*",
) -> Tuple[str, Dict[str, Any]]:
    query = f"""
        SELECT {select}
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY created_at DESC) AS row_num
            FROM {table}
            WHERE module_id = @module_id AND {linked_row_id_name} = @{linked_row_id_name}
              AND user_id = @user_id AND (status != 'deleted' OR status IS NULL)
        )
        WHERE row_num = 1
    """
    return query, {"module_id": module_id, linked_row_id_name: linked_row_id, "user_id": user_id}


def duck_row_from_id(
    table: str,
    ids: List[str],
    select: str = "*",
    user_id: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    flat_ids = _flatten_ids(ids)
    if not flat_ids:
        raise ValueError("ids must not be empty (after flattening)")
    id_placeholders = ", ".join(["?"] * len(flat_ids))
    user_filter = " AND user_id = ?" if user_id else ""
    params: List[Any] = list(flat_ids)
    if user_id:
        params.append(user_id)
    query = f"""
    FROM {table}
    WHERE id IN ({id_placeholders})
    AND (status != 'deleted' OR status IS NULL){user_filter}
    ORDER BY created_at DESC
    LIMIT 1;
    """
    return query, params


def duck_upsert_copy_select(table: str, keys: Dict[str, Any]) -> Tuple[str, List[Any]]:
    where_clause = " AND ".join([f"{k} = ?" for k in keys.keys()])
    query = f"SELECT * FROM {table} WHERE {where_clause} ORDER BY created_at DESC LIMIT 1"
    return query, list(keys.values())


def duck_get_user(uid: str) -> Tuple[str, Dict[str, Any]]:
    query = """
        SELECT *
        FROM users
        WHERE id = @uid AND (status != 'deleted' OR status IS NULL)
        LIMIT 1
    """
    return query, {"uid": uid}


def duck_ensure_user_exists(uid: str) -> Tuple[str, Dict[str, Any]]:
    query = """
        SELECT id
        FROM users
        WHERE id = @uid AND (status != 'deleted' OR status IS NULL)
        LIMIT 1
    """
    return query, {"uid": uid}


def duck_get_payment_record(uid: str) -> Tuple[str, Dict[str, Any]]:
    query = """
        SELECT *
        FROM payment
        WHERE uid = @uid AND (status != 'deleted' OR status IS NULL)
        ORDER BY created_at DESC
        LIMIT 1
    """
    return query, {"uid": uid}


def duck_ensure_payment_exists(uid: str) -> Tuple[str, Dict[str, Any]]:
    query = """
        SELECT id
        FROM payment
        WHERE uid = @uid AND (status != 'deleted' OR status IS NULL)
        LIMIT 1
    """
    return query, {"uid": uid}


def duck_get_standard_stack(user_id: str) -> Tuple[str, Dict[str, Any]]:
    query = """
        SELECT *
        FROM users
        WHERE id = @user_id AND (status != 'deleted' OR status IS NULL)
        LIMIT 1
    """
    return query, {"user_id": user_id}


# --------------------------------------------------------------------------------------
# BigQuery wrappers (templates live on BQGroundZero)
# --------------------------------------------------------------------------------------


def _bq():
    from qbrain._bigquery_toolbox.bq_handler import BQGroundZero  # noqa: WPS433

    return BQGroundZero


def bq_get_users_entries(ds_ref: str, table: str, user_id: str, select: str = "*"):
    return _bq().q_get_users_entries(ds_ref=ds_ref, table=table, user_id=user_id, select=select)


def bq_list_session_entries(
    ds_ref: str,
    table: str,
    user_id: str,
    session_id: str,
    select: str = "*",
    partition_key: str = "id",
):
    return _bq().q_list_session_entries(
        ds_ref=ds_ref,
        table=table,
        user_id=user_id,
        session_id=session_id,
        select=select,
        partition_key=partition_key,
    )


def bq_get_envs_linked_rows(
    ds_ref: str,
    table_name: str,
    env_id: str,
    linked_row_id: str,
    linked_row_id_name: str,
    user_id: str,
    select: str = "*",
):
    return _bq().q_get_envs_linked_rows(
        ds_ref=ds_ref,
        table_name=table_name,
        env_id=env_id,
        linked_row_id=linked_row_id,
        linked_row_id_name=linked_row_id_name,
        user_id=user_id,
        select=select,
    )


def bq_get_modules_linked_rows(
    ds_ref: str,
    table_name: str,
    module_id: str,
    linked_row_id: str,
    linked_row_id_name: str,
    user_id: str,
    select: str = "*",
):
    return _bq().q_get_modules_linked_rows(
        ds_ref=ds_ref,
        table_name=table_name,
        module_id=module_id,
        linked_row_id=linked_row_id,
        linked_row_id_name=linked_row_id_name,
        user_id=user_id,
        select=select,
    )


def bq_row_from_id(ds_ref: str, table: str, ids: List[str], select: str = "*", user_id: Optional[str] = None):
    return _bq().q_row_from_id(ds_ref=ds_ref, table=table, ids=ids, select=select, user_id=user_id)


def bq_upsert_copy_select(table_ref: str, keys: Dict[str, Any]):
    return _bq().q_upsert_copy_select(table_ref=table_ref, keys=keys)


def bq_get_user(pid: str, dataset_id: str, uid: str):
    return _bq().q_get_user(pid=pid, dataset_id=dataset_id, uid=uid)


def bq_get_payment_record(pid: str, dataset_id: str, uid: str):
    return _bq().q_get_payment_record(pid=pid, dataset_id=dataset_id, uid=uid)


def bq_get_standard_stack(pid: str, dataset_id: str, user_id: str):
    return _bq().q_get_standard_stack(pid=pid, dataset_id=dataset_id, user_id=user_id)


def bq_ensure_user_exists(pid: str, dataset_id: str, uid: str):
    return _bq().q_ensure_user_exists(pid=pid, dataset_id=dataset_id, uid=uid)


def bq_ensure_payment_exists(pid: str, dataset_id: str, uid: str):
    return _bq().q_ensure_payment_exists(pid=pid, dataset_id=dataset_id, uid=uid)

