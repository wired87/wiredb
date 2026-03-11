"""
OperatorHandler: Parses a code string (e.g. lambda_H*psi), splits by param/operator,
creates OPERATOR and PARAM nodes and links them recursively (p -> o -> p).
"""
import re
from typing import List

import ast
import networkx as nx
import numpy as np

from qbrain.graph.local_graph_utils import GUtils
from qbrain.utils.math.operators import OPS

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




class EqExtractor(ast.NodeVisitor):
    """
    Parse equation strings attached to METHOD nodes and, optionally, project them
    as operator chains into a graph (p -> OPERATOR -> p -> ...).

    Usage patterns:
      - Single equation parsing (legacy):
            extractor = EqExtractor()
            extractor.visit(ast.parse(code, mode="eval"))
            batches = extractor.batches

      - Graph-wide extraction (new):
            extractor = EqExtractor(g=brain)  # brain is a GUtils instance
            extractor.main()  # walks METHOD nodes, builds p->op->p chains
    """

    def __init__(self, g=None):
        # g is expected to be a GUtils-like object (e.g. Brain) with .G, .add_node, .add_edge
        self.g = g
        self.batches = []
        self.temp_count = 0

    def _get_target(self):
        target = f"temp_{self.temp_count}"
        self.temp_count += 1
        return target

    def visit_Call(self, node):
        # 1. Funktionsname extrahieren
        if isinstance(node.func, ast.Attribute):
            # Fall: psi.conj() -> op: 'conj', left: psi
            func_name = node.func.attr
            left_val = self.visit(node.func.value)
        elif isinstance(node.func, ast.Name):
            # Fall: jnp.dot(a, b) -> op: 'dot'
            func_name = node.func.id
            left_val = None
        else:
            func_name = "unknown_func"
            left_val = None

        args = [self.visit(arg) for arg in node.args]
        target = self._get_target()

        # Wenn es ein Methodenaufruf wie .conj() war, ist left_val gesetzt
        actual_left = left_val if left_val is not None else (args[0] if args else None)
        actual_right = args[1] if left_val is None and len(args) > 1 else (args[0] if left_val and args else None)

        self.batches.append({
            "left": actual_left,
            "op": func_name,
            "right": actual_right,
            "res": target,
            "all_args": args
        })
        return target

    def visit_Attribute(self, node):
        # Behandelt .T (Transponieren)
        value = self.visit(node.value)
        target = self._get_target()

        self.batches.append({
            "left": value,
            "op": node.attr,  # z.B. "T"
            "right": None,
            "res": target
        })
        return target

    def visit_Subscript(self, node):
        # Behandelt gamma[0]
        value = self.visit(node.value)
        # In Python 3.9+ ist node.slice direkt ein Constant oder Name
        index = self.visit(node.slice) if hasattr(node, 'slice') else "unknown_idx"

        target = self._get_target()
        self.batches.append({
            "left": value,
            "op": "get_item",
            "right": index,
            "res": target
        })
        return target

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_sym = self._get_op_sym(node.op)
        target = self._get_target()
        self.batches.append({"left": left, "op": op_sym, "right": right, "res": target})
        return target

    def _get_op_sym(self, op):
        mapping = {
            ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
            ast.Div: "/", ast.MatMult: "@",
            ast.Pow: "**", ast.BitXor: "**"
        }
        return mapping.get(type(op), "unknown")

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            target = self._get_target()
            self.batches.append({"left": operand, "op": "neg", "right": None, "res": target})
            return target

    def visit_Name(self, node):
        return node.id

    def visit_Constant(self, node):
        return node.value

    # ------------------------------------------------------------------
    # Graph projection helpers
    # ------------------------------------------------------------------
    def _ensure_param_node(self, method_id, name):
        """
        Ensure a PARAM node exists for the given method-local symbol name.
        Nodes are scoped by method so temporary symbols do not collide.
        """
        if self.g is None or getattr(self.g, "G", None) is None:
            return None
        nid = f"EQ_PARAM::{method_id}::{name}"
        if not self.g.G.has_node(nid):
            self.g.add_node(
                {
                    "id": nid,
                    "type": "PARAM",
                    "name": str(name),
                    "method_id": method_id,
                }
            )
        # Link param node to parent METHOD node for navigation and grouping.
        try:
            self.g.add_edge(
                src=method_id,
                trt=nid,
                attrs={
                    "rel": "has_eq_param",
                    "src_layer": "METHOD",
                    "trgt_layer": "PARAM",
                },
            )
        except Exception as e:
            print(f"[EqExtractor] _ensure_param_node: edge creation failed for {method_id}->{nid}: {e}")
        return nid

    def _ensure_op_node(self, method_id, idx, op_name):
        """
        Ensure an OPERATOR node exists for a specific batch index of a method.
        """
        if self.g is None or getattr(self.g, "G", None) is None:
            return None
        nid = f"EQ_OP::{method_id}::{idx}"
        if not self.g.G.has_node(nid):
            self.g.add_node(
                {
                    "id": nid,
                    "type": "OPERATOR",
                    "op": str(op_name),
                    "method_id": method_id,
                    "op_index": idx,
                }
            )
        # Link operator node to parent METHOD node for navigation and grouping.
        try:
            self.g.add_edge(
                src=method_id,
                trt=nid,
                attrs={
                    "rel": "has_eq_op",
                    "src_layer": "METHOD",
                    "trgt_layer": "OPERATOR",
                },
            )
        except Exception as e:
            print(f"[EqExtractor] _ensure_op_node: edge creation failed for {method_id}->{nid}: {e}")
        return nid

    def main(self):
        """
        Loop over METHOD nodes in self.g, parse their 'equation' strings and
        create chains within the graph of the form:

            PARAM -> OPERATOR -> PARAM -> OPERATOR -> PARAM -> ...

        For each parsed batch we:
          - create/update PARAM nodes for left/right/res symbols (scoped per method)
          - create/update an OPERATOR node for the batch
          - add edges:
                left_param  --eq_input--> OPERATOR
                right_param --eq_input--> OPERATOR (if present)
                OPERATOR    --eq_output-> result_param
        """
        if self.g is None or getattr(self.g, "G", None) is None:
            print("[EqExtractor] main: no graph attached, aborting")
            return

        import ast as _ast  # local alias to avoid confusion with module import

        for nid, attrs in self.g.G.nodes(data=True):
            ntype = str(attrs.get("type") or "").upper()
            if ntype != "METHOD":
                continue

            equation = attrs.get("equation")
            if not isinstance(equation, str) or not equation.strip():
                continue

            # Reset batches for this method
            self.batches = []
            self.temp_count = 0

            try:
                code = equation.replace("^", "**")
                self.visit(_ast.parse(code, mode="eval"))
            except Exception as e:
                print(f"[EqExtractor] main: skip method {nid} due to parse error: {e}")
                continue

            for idx, b in enumerate(self.batches):
                op_name = b.get("op")
                if not op_name:
                    continue

                op_nid = self._ensure_op_node(nid, idx, op_name)
                if op_nid is None:
                    continue

                # Inputs: left and right (if present)
                for side in ("left", "right"):
                    val = b.get(side)
                    if val is None:
                        continue
                    p_nid = self._ensure_param_node(nid, val)
                    if p_nid is None:
                        continue
                    self.g.add_edge(
                        src=p_nid,
                        trt=op_nid,
                        attrs={
                            "rel": "eq_input",
                            "src_layer": "PARAM",
                            "trgt_layer": "OPERATOR",
                        },
                    )

                # Output: result symbol of this batch
                res_val = b.get("res")
                if res_val is not None:
                    res_nid = self._ensure_param_node(nid, res_val)
                    if res_nid is not None:
                        self.g.add_edge(
                            src=op_nid,
                            trt=res_nid,
                            attrs={
                                "rel": "eq_output",
                                "src_layer": "OPERATOR",
                                "trgt_layer": "PARAM",
                            },
                        )



if __name__ == "__main__":
    # Test-Gleichungen
    test_codes = [
        "a + jnp.dot(b, c)",  # Einfaches P-O-P
        "-a * b.conj().T",  # Negativer Parameter
        "(a + b) * (c - d)",  # Klammern und mehrere Batches
        "-x * (y + 5) / z^2"  # Komplexer Ausdruck (Hinweis: Python nutzt ** für Potenz)
    ]

    # Da Python's AST standardmäßig ** für Potenzen nutzt,
    # ersetzen wir ^ durch ** für den Parser.
    print(f"{'GLEICHUNG':<25} | {'BATCH-SCHRITTE (P-O-P)'}")
    print("-" * 80)

    for code in test_codes:
        print(f"{code:<25} | ", end="")
        try:
            # Wir bereiten den String kurz vor (Python-konforme Operatoren)
            clean_code = code.replace("^", "**")

            # Extraktion starten
            extractor = EqExtractor()
            extractor.visit(ast.parse(clean_code, mode='eval'))

            if not extractor.batches:
                print("Keine Operationen gefunden.")
                continue

            # Formatierte Ausgabe der Batches
            steps = []
            for b in extractor.batches:
                right_val = b['right'] if b['right'] is not None else ""
                steps.append(f"[{b['left']} {b['op']} {right_val} -> {b['res']}]")
            print("STEPS")
            print("  ".join(steps))
        except SyntaxError:
            print(f"Syntax Fehler in der Gleichung!")
        except Exception as e:
            print(f"Fehler: {e}")


