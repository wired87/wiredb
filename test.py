from __future__ import annotations

import asyncio
import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import duckdb
from _db.config import duck_db_path

class MCPWalkthroughTester:
    def __init__(
        self,
        *,
        server: Optional[Any] = None,
        user_id: str = "walkthrough_user",
        module_id: str = "walkthrough_module",
    ) -> None:
        if server is None:
            from mcp_server.app import app as default_app

            server = default_app
        self.server = server
        self.user_id = user_id
        self.module_id = module_id
        self.cleanup_enabled = os.getenv("TEST_CLEANUP", "0") == "1"
        self.root = Path(__file__).resolve().parent
        self.artifacts = self.root / "tmp_test_artifacts"
        self.sample_pdf = self.artifacts / "exp.pdf"
        self.tool_names: set[str] = set()
        self.tool_input_schemas: Dict[str, Dict[str, Any]] = {}

    def _tool_name(self, preferred: str, fallback: str) -> str:
        if preferred in self.tool_names:
            return preferred
        if fallback in self.tool_names:
            return fallback
        raise RuntimeError(f"Missing tool names: neither '{preferred}' nor '{fallback}' is registered")

    def _tool_args(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        schema = self.tool_input_schemas.get(tool_name) or {}
        props = schema.get("properties") if isinstance(schema, dict) else None
        if isinstance(props, dict) and "request" in props:
            return {"request": payload}
        return payload

    @staticmethod
    def expect_ok(step: str, payload: Dict[str, Any]) -> None:
        status = str(payload.get("status") or "")
        if status != "ok":
            raise RuntimeError(f"{step} failed: expected status=ok, got {status}, payload={payload}")

    @staticmethod
    def print_step(title: str, payload: Dict[str, Any]) -> None:
        print("\n" + "=" * 88)
        print(title)
        print("-" * 88)
        print(json.dumps(payload, indent=2, default=str))

    @staticmethod
    def normalize_tool_result(result: Any) -> Dict[str, Any]:
        if result is None:
            return {"status": "ok", "_raw": None}

        if isinstance(result, dict):
            return result

        if isinstance(result, list):
            if not result:
                return {"status": "ok", "_raw": []}
            return {"status": "ok", "_raw": result}

        # FastMCP can return (content_blocks, structured_result_meta).
        if isinstance(result, tuple) and len(result) == 2:
            maybe_meta = result[1]
            if isinstance(maybe_meta, dict):
                if "status" in maybe_meta:
                    return maybe_meta
                structured = maybe_meta.get("result")
                if isinstance(structured, dict):
                    return structured

        raise RuntimeError(f"Unsupported tool result shape: {type(result)} -> {result}")

    @staticmethod
    def load_table_snapshot(con: duckdb.DuckDBPyConnection, table: str) -> Dict[str, Any]:
        try:
            cur = con.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            return {
                "count": len(rows),
                "rows": [dict(zip(cols, row)) for row in rows],
            }
        except Exception as exc:
            return {"count": 0, "rows": [], "error": str(exc)}

    def print_db_snapshot(self, title: str) -> None:
        db_path = Path(duck_db_path())
        if not db_path.exists():
            self.print_step(
                title,
                {
                    "db_path": str(db_path),
                    "note": "Skipping DB snapshot because configured DB file does not exist yet.",
                },
            )
            return
        try:
            con = duckdb.connect(str(db_path), read_only=True)
        except Exception as exc:
            self.print_step(
                title,
                {
                    "db_path": str(db_path),
                    "warning": "Skipping DB snapshot (database is locked or unavailable).",
                    "error": str(exc),
                },
            )
            return
        try:
            snapshot = {
                "db_path": str(db_path),
                "methods": self.load_table_snapshot(con, "methods"),
                "params": self.load_table_snapshot(con, "params"),
                "operators": self.load_table_snapshot(con, "operators"),
                "files": self.load_table_snapshot(con, "files"),
            }
        finally:
            con.close()
        self.print_step(title, snapshot)

    async def run(self) -> None:
        self.artifacts.mkdir(exist_ok=True)
        pdf_bytes = self.sample_pdf.read_bytes()
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

        print("\nMCP terminal walkthrough")
        print(f"Sample PDF: {self.sample_pdf}")
        print(f"PDF size bytes: {len(pdf_bytes)}")
        self.print_db_snapshot("0) DB snapshot BEFORE run")

        # 1) MCP list tools
        tools = await self.server.list_tools()
        tool_names = [t.name for t in tools]
        self.tool_names = set(tool_names)
        self.tool_input_schemas = {
            t.name: dict(getattr(t, "inputSchema", {}) or {})
            for t in tools
            if getattr(t, "name", None)
        }
        self.print_step("1) list_tools", {"count": len(tools), "tool_names": tool_names})
        required_tools = {"upsert", "get_entry", "get_graph", "delete_entries"}
        missing_tools = sorted(required_tools - set(tool_names))
        if missing_tools:
            raise RuntimeError(f"MCP tool list missing required tools: {missing_tools}")

        # 2) MCP upsert
        upsert_args = {
            "user_id": self.user_id,
            "module_id": self.module_id,
            "data": {"files": [pdf_b64], "equation": "f = m * a"},
        }
        upsert_json = self.normalize_tool_result(
            await self.server.call_tool("upsert", self._tool_args("upsert", upsert_args))
        )
        self.expect_ok("upsert", upsert_json)
        self.print_step("2) call_tool(upsert)", {"arguments": upsert_args, "json": upsert_json})

        # 3) MCP graph
        graph_tool = self._tool_name("get_graph", "graph_get")
        graph_json = self.normalize_tool_result(
            await self.server.call_tool(
                graph_tool,
                self._tool_args(graph_tool, {"user_id": self.user_id, "test": False}),
            )
        )
        self.expect_ok(graph_tool, graph_json)
        self.print_step(f"3) call_tool({graph_tool})", {"json": graph_json})

        # 4) MCP entry_get on first method node (if present)
        first_method_id = None
        for node in graph_json.get("nodes") or []:
            attrs = node.get("attrs") or {}
            if attrs.get("type") == "METHOD":
                first_method_id = node.get("id")
                break

        if first_method_id:
            entry_tool = self._tool_name("get_entry", "entry_get")
            entry_json = self.normalize_tool_result(
                await self.server.call_tool(
                    entry_tool,
                    self._tool_args(entry_tool, {"entry_id": first_method_id, "table": "methods", "user_id": self.user_id}),
                )
            )
            if entry_json.get("status") not in {"ok", "not_found"}:
                raise RuntimeError(f"{entry_tool} returned unexpected payload: {entry_json}")
            self.print_step(f"4) call_tool({entry_tool})", {"entry_id": first_method_id, "json": entry_json})
        else:
            self.print_step("4) call_tool(get_entry)", {"skipped": "No METHOD node found in graph response"})

        if self.cleanup_enabled:
            delete_tool = self._tool_name("delete_entries", "entries_delete")
            # 5) Delete one (if present)
            if first_method_id:
                delete_one_json = self.normalize_tool_result(
                    await self.server.call_tool(
                        delete_tool,
                        self._tool_args(
                            delete_tool,
                            {"user_id": self.user_id, "table": "methods", "entry_id": first_method_id},
                        ),
                    )
                )
                self.expect_ok(f"{delete_tool}(single)", delete_one_json)
                self.print_step(f"5) call_tool({delete_tool} single)", {"json": delete_one_json})
            else:
                self.print_step(f"5) call_tool({delete_tool} single)", {"skipped": "No method id available"})

            # 6) Delete all (idempotent cleanup)
            delete_all_json = self.normalize_tool_result(
                await self.server.call_tool(
                    delete_tool,
                    self._tool_args(delete_tool, {"user_id": self.user_id, "table": "methods"}),
                )
            )
            self.expect_ok(f"{delete_tool}(all)", delete_all_json)
            self.print_step(f"6) call_tool({delete_tool} all)", {"json": delete_all_json})
            self.print_db_snapshot("7) DB snapshot AFTER walkthrough (cleanup enabled)")
        else:
            self.print_step(
                "5) Cleanup skipped",
                {
                    "cleanup_enabled": self.cleanup_enabled,
                    "note": "Set TEST_CLEANUP=1 to run delete steps and leave DB empty.",
                },
            )
            self.print_db_snapshot("6) DB snapshot AFTER walkthrough (data persisted)")

        print("\nWalkthrough completed successfully.\n")


async def main() -> None:
    await MCPWalkthroughTester().run()


if __name__ == "__main__":
    asyncio.run(main())
