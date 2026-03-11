import time
import json
from typing import Any, List, Dict

from qbrain.math.operator_handler import EqExtractor
from qbrain.core.module_manager.module_loader import ModuleLoader
from qbrain.qf_utils.field_utils import FieldUtils


class Modulator(
    ModuleLoader,
    EqExtractor,
):
    def __init__(
            self,
            G,
            mid: str,
            qfu,
    ):
        from qbrain.graph.local_graph_utils import GUtils
        self.id = mid
        self.g = GUtils(G=G)
        self.qfu = qfu
        self.fu = FieldUtils()
        
        # Initialize StructInspector manually as ModuleLoader init is skipped
        self.current_class = None
        
        #StateHandler.__init__(self)
        EqExtractor.__init__(self, self.g)


    def register_modules_G(self, modules: List[Dict]):
        """
        Registers modules and their parameters into the local graph (self.g).
        """
        print(f"Registering {len(modules)} modules to G")
        try:
            for module in modules:
                module_id = module.get("id")
                if not module_id:
                    print(f"Skipping module without id: {module}")
                    continue

                # 1. Add Module Node
                # Ensure nid and type are set for GUtils.add_node
                module_attrs = module.copy()
                module_attrs["id"] = module_id
                module_attrs["type"] = "MODULE"
                
                self.g.add_node(attrs=module_attrs)

                # 2. Process Params
                params_raw = module.get("params")
                params = {}
                if params_raw:
                    if isinstance(params_raw, str):
                        try:
                            params = json.loads(params_raw)
                        except Exception as e:
                            print(f"Error parsing params for module {module_id}: {e}")
                            params = {}
                    elif isinstance(params_raw, dict):
                        params = params_raw
                
                # 3. Create Param Nodes and Links
                for param_id, data_type in params.items():
                    # Add Param Node
                    param_attrs = {
                        "id": param_id,
                        "type": "PARAM",
                        "data_type": data_type
                    }
                    self.g.add_node(attrs=param_attrs)
                    
                    # Link Module -> Param
                    edge_attrs = {
                        "rel": "uses_param",
                        "src_layer": "MODULE",
                        "trgt_layer": "PARAM"
                    }
                    self.g.add_edge(
                        src=module_id,
                        trt=param_id,
                        attrs=edge_attrs
                    )

        except Exception as e:
            print(f"Error in register_modules_G: {e}")


    def set_constants(self):
        print("set_constants...")
        env_keys = list(self.qfu.create_env().keys())
        for k,v in self.g.G.nodes(data=True):
            if v["type"] == "PARAM":
                if k in env_keys:
                    v["const"] = True
                else:
                    v["const"] = False
        print("set_constants... done")



    def module_conversion_process(self):
        try:
            if not self.g.G.has_node(self.id):
                self.g.add_node(
                    attrs=dict(
                        id=self.id,
                        type="MODULE",
                    )
                )

            # init here because  if isdir fields, params mus be def
            ModuleLoader.__init__(
                self,
                G=self.g.G,
                id=self.id,
                #fields=self.fields,
            )

            self.load_local_module_codebase(code_base=self.g.G.nodes[self.id].get("code"))

            # code -> G
            self.create_code_G(mid=self.id)

            # G -> sorted runnables -> add inde to node
            self.set_constants()

            #self.set_axis_method_params()
            print("module_conversion_process... done")
            #print("self.arsenal_struct", self.arsenal_struct)
        except Exception as e:
            print("MODULE CONVERSION FAILED:", e)



    def set_field_data(self, field, dim=3):
        """
        Set example field data
        """
        print("set_field_data for ", field)
        try:

            data: dict = self.qfu.batch_field_single(
                ntype=field,
                dim=dim,
            )

            # set params for module
            keys = list(data.keys())
            values = list(data.values())

            axis_def = self.set_axis(values)
            print(f"update field node {field}")
            self.g.update_node(
                dict(
                    id=field,
                    keys=keys,
                    values=values,
                    axis_def=axis_def,
                )
            )
        except Exception as e:
            print("Err set_field_data:", e)
        print("create_modules finished")


    def set_pattern(self):
        STRUCT_SCHEMA = []

        for f in self.fields:
            node = self.g.G.nodes[f]
            keys = node["keys"]

            # loop single eqs
            for struct in self.arsenal_struct:
                for p in struct["params"]:
                    struct_item = []
                    # param lccal?
                    if p in keys:
                        struct_item = [
                            self.module_index,
                             node["field_index"],
                            keys.index(p)
                        ]

                    elif p in self.fu.env:
                        struct_item = [
                            self.module_index,
                            [0], # first and single field
                            self.fu.env.index(p),
                        ]

                    else:
                        # param from neighbor field ->
                        # get all NEIGHBOR FIELDS
                        nfs = self.g.get_neighbor_list(
                            node=f["id"],
                            target_type="FIELD",
                        )

                    STRUCT_SCHEMA[
                        node["field_index"]
                    ] = struct_item







    def set_return_des(self):
        # param: default v
        field_param_map: dict[str, Any] = self.g.G.nodes[self.id]["field_param_map"].keys()

        # create PATTERN
        k = list(field_param_map.keys())
        return_param_pattern = [
            None
            for _ in range(len(k))
        ]

        # LINKFIELD PARAM -> RETURN KEY
        for i, item in enumerate(self.arsenal_struct):
            return_key = item["return_key"]
            return_param_pattern[i]: int = field_param_map.index(return_key)
        print(f"{self.id} runnable creared")



    def create_field_workers(
            self,
            fields:list[str]
    ):
        # todo may add module based axis def
        start = time.perf_counter_ns()
        try:
            for i, fid in enumerate(fields):
                self.set_field_data(
                    field=fid,
                )
        except Exception as e:
            print("Err create_field_workers", e)
        end = time.perf_counter_ns()
        print("Field Workers created successfully after s:", end - start)

    def set_axis(self, data:list) -> tuple:
        """
        Determines the vmap axis for each parameter in the admin_data bundle.
        - Use axis 0 for array-like admin_data (map over it).
        - Use None for scalar admin_data (broadcast it).
        """
        return tuple(
            0
            if not isinstance(
                param, (int, float)
            )
            else None
            for param in data
        )

