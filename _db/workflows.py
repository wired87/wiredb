from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List, Optional

import duckdb
from duckdb import DuckDBPyConnection

try:
    from _duckdb import DuckDBPyConnection as ddb_res
except ImportError:
    ddb_res = DuckDBPyConnection  # type: ignore

try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None  # type: ignore

from qbrain._db.config import duck_db_path
from qbrain._db.log_facade import db_log

# ---------- CORE ----------


def db_connect() -> DuckDBPyConnection:
    path = duck_db_path()
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    try:
        con = duckdb.connect(path)
        db_log("info", "[duck] connect: ok", path=path)
        return con
    except Exception as e:
        msg = str(e).lower()
        if "being used by another process" in msg or "file is already open" in msg:
            # Try read_only so we see data from the main file (CLI check, etc.)
            try:
                con = duckdb.connect(path, read_only=True)
                db_log("warn", f"DuckDB file locked: {path}. Opened read_only.")
                return con
            except Exception:
                pass
            # Fallback: per-process file (writes go here; reads from main won't see them)
            alt = str(Path(path).with_name(f"{Path(path).stem}.{os.getpid()}{Path(path).suffix}"))
            alt_dir = os.path.dirname(alt)
            if alt_dir and not os.path.exists(alt_dir):
                os.makedirs(alt_dir)
            db_log("warn", f"DuckDB file locked: {path}. Falling back to {alt}")
            return duckdb.connect(alt)
        raise


def db_close(con: DuckDBPyConnection) -> None:
    con.close()
    db_log("info", "[duck] close: ok")


def duck_insert(con:DuckDBPyConnection, table_name: str, rows: list[dict], upsert=False):
    try:
        if not rows:
            return True

        # collect all columns
        cols = []
        for row in rows:
            for k in row.keys():
                if k not in cols:
                    cols.append(k)

        cols_sql = ", ".join(cols)
        placeholders = ", ".join(["?"] * len(cols))

        values = []
        for row in rows:
            values.append([row.get(c) for c in cols])

        con.executemany(
            f"INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders})",
            values
        )
        db_log("info", f"[duck] insert: ok {table_name} {len(values)} rows")
        return True
    except Exception as e:
        db_log("error", f"[duck] insert: err {table_name}", error=str(e))
        return False

# ---------- MODULE-LEVEL FUNCTIONS (con passed explicitly) ----------

def db_exec(con: DuckDBPyConnection, sql: str, params: Optional[List[Any]] = None):
    r: ddb_res = con.execute(sql, params) if params is not None else con.execute(sql)
    db_log("info", "[duck] exec: ok")
    return r


def db_query(con: DuckDBPyConnection, sql: str, params: Optional[List[Any]] = None):
    rows = con.execute(sql, params).fetchall() if params is not None else con.execute(sql).fetchall()
    db_log("info", f"[duck] query: ok {len(rows)} rows")
    return rows


def db_query_df(con: DuckDBPyConnection, sql: str):
    if pd is None:
        raise ImportError("pandas is required for db_query_df(). Install pandas to use this helper.")
    df = con.execute(sql).df()
    db_log("info", f"[duck] query_df: ok {len(df)} rows")
    return df


# ---------- TABLE MANAGEMENT ----------

def db_create_table(con: DuckDBPyConnection, table_name: str, schema_sql: str) -> None:
    try:
        con.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({schema_sql})")
        db_log("info", f"[duck] create_table: ok {table_name}")
    except Exception as e:
        db_log("error", f"[duck] create_table: err {table_name}", error=str(e))


def db_drop_table(con: DuckDBPyConnection, table_name: str) -> None:
    con.execute(f"DROP TABLE IF EXISTS {table_name}")
    db_log("info", f"[duck] drop_table: ok {table_name}")


# ---------- INSERT / UPDATE / DELETE ----------

def db_insert(con: DuckDBPyConnection, table: str, columns: List[str], values: List[Any]) -> None:
    placeholders = ",".join(["?"] * len(values))
    cols = ",".join(columns)
    con.execute(
        f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
        values
    )
    db_log("info", f"[duck] db_insert: ok {table} 1 row")


def db_update(con: DuckDBPyConnection, table: str, set_clause: str, where_clause: str) -> None:
    con.execute(f"UPDATE {table} SET {set_clause} WHERE {where_clause}")
    db_log("info", f"[duck] update: ok {table}")


def db_delete(con: DuckDBPyConnection, table: str, where_clause: str) -> None:
    con.execute(f"DELETE FROM {table} WHERE {where_clause}")
    db_log("info", f"[duck] delete: ok {table}")


# ---------- DATAFRAME SUPPORT ----------

def db_register_df(con: DuckDBPyConnection, df: pd.DataFrame, view_name: str) -> None:
    if pd is None:
        raise ImportError("pandas is required for db_register_df(). Install pandas to use this helper.")
    con.register(view_name, df)


def db_insert_df(con: DuckDBPyConnection, table_name: str, df: pd.DataFrame) -> None:
    if pd is None:
        raise ImportError("pandas is required for db_insert_df(). Install pandas to use this helper.")
    con.register("tmp_df", df)
    con.execute(f"INSERT INTO {table_name} SELECT * FROM tmp_df")
    db_log("info", f"[duck] insert_df: ok {table_name} {len(df)} rows")


# ---------- FILE IMPORT ----------

def db_read_csv(con: DuckDBPyConnection, path: str, table_name: str) -> None:
    con.execute(
        f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto('{path}')"
    )
    db_log("info", f"[duck] read_csv: ok {table_name}")


def db_read_parquet(con: DuckDBPyConnection, path: str, table_name: str) -> None:
    con.execute(
        f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_parquet('{path}')"
    )
    db_log("info", f"[duck] read_parquet: ok {table_name}")


# ---------- FILE EXPORT ----------

def db_export_csv(con: DuckDBPyConnection, table_name: str, path: str) -> None:
    con.execute(
        f"COPY {table_name} TO '{path}' (HEADER, DELIMITER ',')"
    )
    db_log("info", f"[duck] export_csv: ok {table_name} -> {path}")


def db_export_parquet(con: DuckDBPyConnection, table_name: str, path: str) -> None:
    con.execute(
        f"COPY {table_name} TO '{path}' (FORMAT PARQUET)"
    )
    db_log("info", f"[duck] export_parquet: ok {table_name} -> {path}")


# ---------- STATUS / CHECK ----------


def db_check(con: DuckDBPyConnection) -> bool:
    """Quick health check: connection alive and DB reachable."""
    try:
        con.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False


def db_status(con: DuckDBPyConnection) -> dict:
    """Return DB status: path, tables, connection_alive."""
    from qbrain._db.config import duck_db_path

    tables = []
    try:
        rows = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name"
        ).fetchall()
        tables = [r[0] for r in rows]
    except Exception:
        pass

    return {
        "path": duck_db_path(),
        "tables": tables,
        "connection_alive": db_check(con),
    }