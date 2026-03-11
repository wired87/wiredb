"""
OperatorHandler: Parses equation/code strings into operator chains and projects
scientific equation structures into a multigraph.
"""
from __future__ import annotations

import ast
import hashlib
import re
from typing import Any, Dict, List, Optional, Set

import networkx as nx
import numpy as np

from graph.local_graph_utils import GUtils
from math.operators import OPS

try:
    import sympy as sp
except Exception:
    sp = None

try:
    from sympy.parsing.latex import parse_latex as sympy_parse_latex
except Exception:
    sympy_parse_latex = None

# Operators to split on (order matters for regex)
_OPS = r"([+\-*/])"


def split_eq(code: str) -> List[str]:
    """Split code into [param, op, param, op, ...]. Params are identifiers."""
    tokens = re.split(_OPS, code)
    return [t.strip() for t in tokens if t.strip()]


class OperatorHandler:
    """
    Receives GUtils, processes a code string, creates equation map (p -> o -> p).
    Set pathway -> for each eq
    Sepparate in Dublets first param represents the starting point for
    the equation pathway.
    a -> * -> b -> * -> c -> ...
    """
    
    def __init__(self, g=None):
        self.g = g or GUtils(G=nx.MultiDiGraph())
        self._op_counter = 0

        len_ops = len(list(OPS.keys()))

        self.ops_ctlr = np.arange(len_ops).tolist()

        self.ops_struct = [
            []
            for _ in range(len_ops)
        ]

        self.method_schema = None

        self.grid_ctlr = []
        self.op_ctlr = []


    def add_ops(self):
        print("add op nodes...")
        for i, (k, v) in enumerate(OPS.items()):
            self.g.add_node({
                "id": k,
                "type": "OPERATOR",
                "operator_idx": i,
            })
        print("add op nodes... done")


    def set_start_coords(self, midx, param_db_coords):
        for item in param_db_coords:
            self.start_point_ctlr[midx].append(item)
        return



def eq_extractor_main(equation, eq_store_item):
    """
    First indice in each item points to dest struct
    """
    print("eq_extractor_main...")
    eq_idx_map = []

    if equation is None or (isinstance(equation, str) and not equation.strip()):
        print("eq_extractor_main... done (empty equation, skipping)")
        return eq_idx_map

    eq_extractor = EqExtractor()

    eq_extractor.visit(
        ast.parse(equation, mode='eval')
    )

    for b in eq_extractor.batches:
        right_val = b['right']

        # add calculator function indices to method
        if right_val is None:
            # -
            left_val = b['left']
            fun_idx = list(OPS.keys()).index("neg")
            param_val = eq_store_item.index(left_val)

            # neg fun idx
            eq_idx_map.append([0, fun_idx])

            # param idx
            eq_idx_map.append([1, param_val])
        else:
            # +
            left_val = b['left']
            left_val_idx = eq_store_item.index(left_val)

            right_val = b['right']
            right_val_idx = eq_store_item.index(right_val)

            _operator = b['op']
            fun_idx = list(OPS.keys()).index(_operator)

            # left
            eq_idx_map.append([1, left_val_idx])

            # op fun idx
            eq_idx_map.append([0, fun_idx])

            # right
            eq_idx_map.append([1, right_val_idx])
    print("eq_extractor_main... done")
    return eq_idx_map



