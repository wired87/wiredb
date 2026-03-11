from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

# Ensure project root imports resolve when running this file directly.
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from _db.manager import DBManager

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover - optional runtime dependency
    pd = None  # type: ignore


class _MiniFrame:
    """
    Very small DataFrame-like fallback for CSV export when pandas is unavailable.
    """

    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self.rows = rows

    def __len__(self) -> int:
        return len(self.rows)

    def to_csv(self, path: Path, index: bool = False) -> None:  # noqa: ARG002 - keep pandas-like API
        fieldnames: List[str] = []
        for row in self.rows:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.rows:
                writer.writerow(row)


class VisualizeGraph:
    """
    Build and export a user/public graph view from DB rows and edge rows.
    """

    ITEM_TABLES = ("methods", "params", "operators")

    def __init__(self, db: Optional[DBManager] = None, project_root: Optional[Path] = None) -> None:
        print("[VisualizeGraph.__init__] START")
        self.db = db or DBManager()
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None
        print(f"[VisualizeGraph.__init__] project_root={self.project_root}")
        print("[VisualizeGraph.__init__] END")

    def _table_exists(self, table_name: str) -> bool:
        print(f"[VisualizeGraph._table_exists] START table={table_name}")
        rows = self.db.run_query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main' AND table_name = ?",
            params=[table_name],
        )
        exists = len(rows) > 0
        print(f"[VisualizeGraph._table_exists] END exists={exists}")
        return exists

    def _table_schema(self, table_name: str) -> Dict[str, str]:
        print(f"[VisualizeGraph._table_schema] START table={table_name}")
        schema = self.db.get_table_schema(table_name)
        print(f"[VisualizeGraph._table_schema] END columns={list(schema.keys())}")
        return schema

    @staticmethod
    def _safe_json_loads(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        text = value.strip()
        if not text:
            return value
        try:
            return json.loads(text)
        except Exception:
            return value

    @staticmethod
    def _normalize_node_row(row: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        # Keep all table attributes but enforce id and table marker.
        rid = str(row.get("id") or "")
        normalized = {
            "id": rid,
            "_table": table_name,
            **row,
        }
        return normalized

    @staticmethod
    def _normalize_edge_row(row: Dict[str, Any], table_name: str, src_col: str, trgt_col: str) -> Dict[str, Any]:
        return {
            "id": row.get("attrs").get("id"),
            **row
        }

    def fetch_items(self, user_id: str) -> List[Dict[str, Any]]:
        print("[VisualizeGraph.fetch_items] START")
        print(f"[VisualizeGraph.fetch_items] LOGIC_GATE user_id={user_id}")
        all_rows: List[Dict[str, Any]] = []
        for table_name in self.ITEM_TABLES:
            if not self._table_exists(table_name):
                print(f"[VisualizeGraph.fetch_items] LOGIC_GATE skip missing table={table_name}")
                continue

            schema = self._table_schema(table_name)
            where_parts: List[str] = []
            params: List[Any] = []

            if "user_id" in schema:
                where_parts.append("user_id = ?")
                params.append(user_id)
                where_parts.append("user_id = ?")
                params.append("public")
            if "is_public" in schema:
                where_parts.append("is_public = TRUE")

            sql = f"SELECT * FROM {table_name}"
            if where_parts:
                sql += " WHERE " + " OR ".join(where_parts)

            rows = self.db.run_query(sql, params=params if params else None, conv_to_dict=True)
            print(f"[VisualizeGraph.fetch_items] fetched table={table_name} count={len(rows)}")
            for row in rows:
                normalized = self._normalize_node_row(row, table_name)
                if normalized.get("id"):
                    all_rows.append(normalized)
        print(f"[VisualizeGraph.fetch_items] END total_items={len(all_rows)}")
        return all_rows


    def _discover_edge_tables(self) -> List[Tuple[str, str, str]]:
        print("[VisualizeGraph._discover_edge_tables] START")
        rows = self.db.run_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='main'
            ORDER BY table_name
            """,
            conv_to_dict=True,
        )
        out: List[Tuple[str, str, str]] = []
        for row in rows:
            table_name = str(row.get("table_name"))
            schema = self._table_schema(table_name)
            cols = set(schema.keys())
            if {"src", "trgt"}.issubset(cols):
                out.append((table_name, "src", "trgt"))
            elif {"source", "target"}.issubset(cols):
                out.append((table_name, "source", "target"))
        print(f"[VisualizeGraph._discover_edge_tables] END edge_tables={out}")
        return out

    def fetch_edges_for_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        print("[VisualizeGraph.fetch_edges_for_items] START")
        item_ids = [str(x["id"]) for x in items if x.get("id")]
        print(f"[VisualizeGraph.fetch_edges_for_items] LOGIC_GATE item_count={len(item_ids)}")
        if not item_ids:
            print("[VisualizeGraph.fetch_edges_for_items] END no item ids")
            return []

        out: List[Dict[str, Any]] = []

        for table_name, src_col, trgt_col in self._discover_edge_tables():
            placeholders = ",".join(["?"] * len(item_ids))
            sql = (
                f"SELECT * FROM {table_name} "
                f"WHERE {src_col} IN ({placeholders}) OR {trgt_col} IN ({placeholders})"
            )
            params = item_ids + item_ids
            rows = self.db.run_query(sql, params=params, conv_to_dict=True)
            print(f"[VisualizeGraph.fetch_edges_for_items] fetched table={table_name} count={len(rows)}")
            for row in rows:
                normalized = self._normalize_edge_row(row, table_name, src_col, trgt_col)
                out.append(normalized)
        print(f"[VisualizeGraph.fetch_edges_for_items] END total_edges={len(out)}")
        return out

    def build_multigraph(self, items: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> nx.MultiGraph:
        print("[VisualizeGraph.build_multigraph] START")
        G = nx.MultiGraph()
        for row in items:
            nid = str(row.get("id") or "")
            if not nid:
                continue
            attrs = {k: v for k, v in row.items() if k != "id"}
            G.add_node(nid, **attrs)

        for edge in edges:
            src = edge.get("src")
            trgt = edge.get("trgt")
            if not src or not trgt:
                continue
            attrs = {k: v for k, v in edge.items() if k not in {"src", "trgt"}}
            G.add_edge(str(src), str(trgt), **attrs)
        print(f"[VisualizeGraph.build_multigraph] END nodes={G.number_of_nodes()} edges={G.number_of_edges()}")
        return G

    def get_status_G(self, G: nx.MultiGraph, get_frame: bool = False):
        print("[VisualizeGraph.get_status_G] START")
        type_counts: Dict[str, int] = {}
        for _, attrs in G.nodes(data=True):
            ntype = str(attrs.get("type") or attrs.get("_table") or "UNKNOWN")
            type_counts[ntype] = type_counts.get(ntype, 0) + 1

        status = {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "node_type_counts": type_counts,
            "is_multigraph": isinstance(G, nx.MultiGraph),
        }
        print(f"[VisualizeGraph.get_status_G] LOGIC_GATE get_frame={get_frame}")
        if get_frame:
            if pd is None:
                frame = _MiniFrame([status])
                print("[VisualizeGraph.get_status_G] END returning mini metadata frame")
                return frame
            frame = pd.DataFrame([status])  # type: ignore[attr-defined]
            print("[VisualizeGraph.get_status_G] END returning metadata frame")
            return frame
        print("[VisualizeGraph.get_status_G] END returning dict")
        return status

    def _resolve_output_dir(self, user_id: str, test: bool) -> Path:
        print("[VisualizeGraph._resolve_output_dir] START")
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        if test:
            out_dir = self.project_root / "output" / f"graph_export_{user_id}_{ts}"
            out_dir.mkdir(parents=True, exist_ok=True)
            print(f"[VisualizeGraph._resolve_output_dir] END test=True dir={out_dir}")
            return out_dir

        self._temp_dir = tempfile.TemporaryDirectory(prefix="eq_graph_export_")
        out_dir = Path(self._temp_dir.name)
        print(f"[VisualizeGraph._resolve_output_dir] END test=False temp_dir={out_dir}")
        return out_dir

    def _export_pyvis_html(self, G: nx.MultiGraph, html_path: Path) -> Optional[str]:
        print("[VisualizeGraph._export_pyvis_html] START")
        try:
            from pyvis.network import Network
        except Exception as exc:
            print(f"[VisualizeGraph._export_pyvis_html] LOGIC_GATE pyvis unavailable: {exc}")
            return None

        net = Network(
            notebook=False,
            cdn_resources="in_line",
            height="900px",
            width="100%",
            bgcolor="#111111",
            font_color="white",
        )
        net.toggle_physics(True)
        net.barnes_hut()

        vis_G = nx.Graph()
        for nid, attrs in G.nodes(data=True):
            vis_G.add_node(
                nid,
                label=str(nid),
                title=json.dumps({k: str(v) for k, v in attrs.items()}, indent=2),
                type=attrs.get("type") or attrs.get("_table"),
            )
        for src, trgt, attrs in G.edges(data=True):
            vis_G.add_edge(src, trgt, title=str(attrs.get("rel") or attrs.get("id") or "edge"))

        net.from_nx(vis_G)
        html_path.write_text(net.generate_html(), encoding="utf-8")
        print(f"[VisualizeGraph._export_pyvis_html] END html={html_path}")
        return str(html_path)

    def _export_json(self, G: nx.MultiGraph, json_path: Path) -> Path:
        print("[VisualizeGraph._export_json] START")
        data = nx.node_link_data(G, edges="edges")
        json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        print(f"[VisualizeGraph._export_json] END json={json_path}")
        return json_path

    def _build_rows_edges_frame(self, items: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        print("[VisualizeGraph._build_rows_edges_frame] START")
        rows: List[Dict[str, Any]] = []
        for item in items:
            rows.append({"kind": "node", **item})
        for edge in edges:
            rows.append({"kind": "edge", **edge})

        if pd is None:
            frame = _MiniFrame(rows)
            print(f"[VisualizeGraph._build_rows_edges_frame] END mini-frame rows={len(frame)}")
            return frame
        frame = pd.DataFrame(rows)  # type: ignore[attr-defined]
        print(f"[VisualizeGraph._build_rows_edges_frame] END rows={len(frame)}")
        return frame

    def _zip_dir(self, dir_path: Path) -> Path:
        print("[VisualizeGraph._zip_dir] START")
        zip_base = str(dir_path)
        zip_file = Path(shutil.make_archive(zip_base, "zip", root_dir=str(dir_path)))
        print(f"[VisualizeGraph._zip_dir] END zip={zip_file}")
        return zip_file

    def run(self, user_id: str, test: bool = False) -> Dict[str, Any]:
        print("[VisualizeGraph.run] START")
        print(f"[VisualizeGraph.run] LOGIC_GATE user_id={user_id} test={test}")
        if not user_id:
            raise ValueError("user_id is required")

        items = self.fetch_items(user_id=user_id)
        edges = self.fetch_edges_for_items(items=items)
        G = self.build_multigraph(items=items, edges=edges)

        output_dir = self._resolve_output_dir(user_id=user_id, test=test)
        graph_json_path = self._export_json(G, output_dir / f"graph_{user_id}.json")
        html_path = self._export_pyvis_html(G, output_dir / f"graph_{user_id}.html")

        rows_edges_frame = self._build_rows_edges_frame(items=items, edges=edges)
        rows_edges_csv_path: Optional[Path] = None
        if rows_edges_frame is not None and hasattr(rows_edges_frame, "to_csv"):
            rows_edges_csv_path = output_dir / f"graph_rows_edges_{user_id}.csv"
            rows_edges_frame.to_csv(rows_edges_csv_path, index=False)
            print(f"[VisualizeGraph.run] rows_edges_csv={rows_edges_csv_path}")

        metadata_frame = self.get_status_G(G, get_frame=True)
        metadata_csv_path: Optional[Path] = None
        if hasattr(metadata_frame, "to_csv"):
            metadata_csv_path = output_dir / f"graph_metadata_{user_id}.csv"
            metadata_frame.to_csv(metadata_csv_path, index=False)
            print(f"[VisualizeGraph.run] metadata_csv={metadata_csv_path}")

        zip_path: Optional[Path] = None
        if not test:
            zip_path = self._zip_dir(output_dir)

        result = {
            "status": "ok",
            "user_id": user_id,
            "nodes": [{"id": str(nid), "attrs": attrs} for nid, attrs in G.nodes(data=True)],
            "edges": [
                {"source": str(src), "target": str(trgt), "attrs": attrs}
                for src, trgt, attrs in G.edges(data=True)
            ],
            "stats": self.get_status_G(G, get_frame=False),
            "artifacts": {
                "output_dir": str(output_dir),
                "graph_json": str(graph_json_path),
                "graph_html": html_path,
                "rows_edges_csv": str(rows_edges_csv_path) if rows_edges_csv_path else None,
                "metadata_csv": str(metadata_csv_path) if metadata_csv_path else None,
                "zip_path": str(zip_path) if zip_path else None,
            },
        }
        print("[VisualizeGraph.run] END")
        return result

    def run_hardcoded_demo(self, test: bool = True) -> Dict[str, Any]:
        """
        Test view with hardcoded nx.Graph to demonstrate full workflow.
        """
        print("[VisualizeGraph.run_hardcoded_demo] START")
        demo_items = [
            {"id": "method::f", "type": "METHOD", "label": "f = m * a", "user_id": "demo"},
            {"id": "param::m", "type": "PARAM", "label": "m", "user_id": "demo"},
            {"id": "param::a", "type": "PARAM", "label": "a", "user_id": "demo"},
            {"id": "param::f", "type": "PARAM", "label": "f", "user_id": "demo"},
        ]
        demo_edges = [
            {"id": "method::f__param::m", "src": "method::f", "trgt": "param::m", "rel": "uses_param"},
            {"id": "method::f__param::a", "src": "method::f", "trgt": "param::a", "rel": "uses_param"},
            {"id": "method::f__param::f", "src": "method::f", "trgt": "param::f", "rel": "returns_param"},
        ]
        G = self.build_multigraph(items=demo_items, edges=demo_edges)
        output_dir = self._resolve_output_dir(user_id="hardcoded_demo", test=test)
        self._export_json(G, output_dir / "graph_hardcoded_demo.json")
        self._export_pyvis_html(G, output_dir / "graph_hardcoded_demo.html")
        frame = self._build_rows_edges_frame(demo_items, demo_edges)
        if frame is not None and hasattr(frame, "to_csv"):
            frame.to_csv(output_dir / "graph_rows_edges_hardcoded_demo.csv", index=False)
        metadata = self.get_status_G(G, get_frame=True)
        if hasattr(metadata, "to_csv"):
            metadata.to_csv(output_dir / "graph_metadata_hardcoded_demo.csv", index=False)
        print("[VisualizeGraph.run_hardcoded_demo] END")
        return {"status": "ok", "output_dir": str(output_dir)}


def _main() -> None:
    parser = argparse.ArgumentParser(description="VisualizeGraph test runner")
    parser.add_argument("--user-id", default="walkthrough_user")
    args = parser.parse_args()

    viz = VisualizeGraph()
    print("[__main__] Running DB-backed workflow with test=True")
    result = viz.run(user_id=args.user_id, test=True)
    print(json.dumps(result.get("artifacts", {}), indent=2))

    print("[__main__] Running hardcoded graph demo workflow")
    demo_result = viz.run_hardcoded_demo(test=True)
    print(json.dumps(demo_result, indent=2))


if __name__ == "__main__":
    # Runnable command:
    # .\.venv\Scripts\python.exe graph\qa\visual_g.py --user-id walkthrough_user
    _main()
