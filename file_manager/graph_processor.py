"""
Graph processor: merges file-manager extraction results into the single Brain knowledge graph (KG).

All users' entries (files, equations, objects, methods) are added to one shared KG instance.
Uses Brain schema (BrainNodeType, BrainEdgeRel) for consistency with Brain class.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import networkx as nx

logger = logging.getLogger(__name__)

# Use Brain schema so the same G is consumed by Brain
try:
    from qbrain.graph.brn.brain_schema import BrainEdgeRel, BrainNodeType
except Exception:
    class BrainEdgeRel:
        REFERENCES_TABLE_ROW = "references_table_row"
        DERIVED_FROM = "derived_from"
        PARENT_OF = "parent_of"

    class BrainNodeType:
        USER = "USER"
        LONG_TERM_STORAGE = "LONG_TERM_STORAGE"
        CONTENT = "CONTENT"
        FILE = "FILE"
        EQUATION = "EQUATION"
        OBJECT = "OBJECT"
        METHOD = "METHOD"


def _ensure_clean_attrs(attrs: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values and stringify for networkx/storage."""
    return {k: (v if v is not None else "") for k, v in attrs.items()}


class GraphProcessor:
    """
    Merges file-manager outputs into a single Brain knowledge graph.
    Call merge() after process_and_upload_file_config to add FILE, EQUATION, OBJECT, METHOD nodes.
    """

    def __init__(self, G: Optional[nx.MultiGraph] = None):
        self.G = G

    def set_graph(self, G: nx.MultiGraph) -> None:
        self.G = G

    def _add_node(self, nid: str, attrs: Dict[str, Any]) -> None:
        if not self.G:
            return
        clean = _ensure_clean_attrs({**attrs, "id": nid})
        if self.G.has_node(nid):
            self.G.nodes[nid].update(clean)
        else:
            self.G.add_node(nid, **{k: v for k, v in clean.items() if k != "id"})

    def _add_edge(self, src: str, trt: str, rel: str, src_layer: str, trgt_layer: str) -> None:
        if not self.G:
            return
        self.G.add_edge(
            src, trt,
            rel=rel,
            src_layer=src_layer,
            trgt_layer=trgt_layer,
        )

    def merge(
        self,
        user_id: str,
        module_id: str,
        file_result: Dict[str, Any],
        created_components: Optional[Dict[str, Any]] = None,
        classification: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        Merge file-manager result into the KG. All users' entries go into the same G.

        file_result: type=CONTENT_EXTRACTED, data={param, field, method}, created_components.
        created_components: optional override {param: [], field: [], method: []}.
        classification: optional map item_id -> "object" | "equation" (infer equation from behaviour vs handwritten).

        Returns number of nodes added/updated.
        """
        if not self.G:
            logger.warning("[GraphProcessor] no graph set, skip merge")
            return 0

        created = created_components or file_result.get("created_components") or {}
        data = file_result.get("data") or {}
        param_ids = list(dict.fromkeys(data.get("param") or []))
        field_ids = list(dict.fromkeys(data.get("field") or []))
        method_ids = list(dict.fromkeys(data.get("method") or []))

        user_node_id = f"USER::{user_id}"
        if not self.G.has_node(user_node_id):
            self._add_node(user_node_id, {"type": BrainNodeType.USER, "user_id": user_id})

        count = 0

        # FILE node (one per module_id for this upload)
        file_node_id = f"LTS::files::{module_id}"
        self._add_node(file_node_id, {
            "type": BrainNodeType.FILE,
            "user_id": user_id,
            "module_id": module_id,
            "table_name": "files",
            "row_id": module_id,
        })
        self._add_edge(
            user_node_id, file_node_id,
            rel=BrainEdgeRel.REFERENCES_TABLE_ROW,
            src_layer=BrainNodeType.USER,
            trgt_layer=BrainNodeType.LONG_TERM_STORAGE,
        )
        count += 1

        # PARAM nodes (long-term storage refs)
        for pid in param_ids:
            nid = f"LTS::params::{pid}"
            self._add_node(nid, {
                "type": BrainNodeType.LONG_TERM_STORAGE,
                "user_id": user_id,
                "table_name": "params",
                "row_id": str(pid),
            })
            self._add_edge(
                user_node_id, nid,
                rel=BrainEdgeRel.REFERENCES_TABLE_ROW,
                src_layer=BrainNodeType.USER,
                trgt_layer=BrainNodeType.LONG_TERM_STORAGE,
            )
            self._add_edge(file_node_id, nid, rel=BrainEdgeRel.DERIVED_FROM, src_layer=BrainNodeType.FILE, trgt_layer=BrainNodeType.LONG_TERM_STORAGE)
            count += 1

        # FIELD nodes
        for fid in field_ids:
            nid = f"LTS::fields::{fid}"
            self._add_node(nid, {
                "type": BrainNodeType.LONG_TERM_STORAGE,
                "user_id": user_id,
                "table_name": "fields",
                "row_id": str(fid),
            })
            self._add_edge(
                user_node_id, nid,
                rel=BrainEdgeRel.REFERENCES_TABLE_ROW,
                src_layer=BrainNodeType.USER,
                trgt_layer=BrainNodeType.LONG_TERM_STORAGE,
            )
            self._add_edge(file_node_id, nid, rel=BrainEdgeRel.DERIVED_FROM, src_layer=BrainNodeType.FILE, trgt_layer=BrainNodeType.LONG_TERM_STORAGE)
            count += 1

        # METHOD / EQUATION nodes (equations → method manager conversion already done in file_lib)
        for mid in method_ids:
            nid = f"LTS::methods::{mid}"
            kind = (classification or {}).get(mid, "equation")
            self._add_node(nid, {
                "type": BrainNodeType.METHOD if kind == "equation" else BrainNodeType.OBJECT,
                "user_id": user_id,
                "table_name": "methods",
                "row_id": str(mid),
                "content_type": kind,  # "equation" | "object" (infer equation from behaviour)
            })
            self._add_edge(
                user_node_id, nid,
                rel=BrainEdgeRel.REFERENCES_TABLE_ROW,
                src_layer=BrainNodeType.USER,
                trgt_layer=BrainNodeType.LONG_TERM_STORAGE,
            )
            self._add_edge(file_node_id, nid, rel=BrainEdgeRel.DERIVED_FROM, src_layer=BrainNodeType.FILE, trgt_layer=BrainNodeType.METHOD)
            count += 1

        logger.info("[GraphProcessor] merge: user_id=%s module_id=%s nodes_added=%s", user_id, module_id, count)
        return count


def get_graph_processor(G: Optional[nx.MultiGraph] = None) -> GraphProcessor:
    """Return a GraphProcessor bound to the given G (or shared KG)."""
    return GraphProcessor(G=G)
