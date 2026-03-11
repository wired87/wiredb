from typing import List, Dict

class MethodDataProcessor:
    def __init__(self, g_utils):
        """
        Initialize MethodDataProcessor with a GUtils instance.
        """
        self.g = g_utils
        self.arsenal_struct: List[Dict] = []

    def process_module_methods(self, module_id: str) -> List[Dict]:
        """
        Main entry point to process methods for a module:
        1. Gather methods and params from qbrain.graph.
        2. Sort execution order.
        3. Update method nodes with execution index.
        4. Update module node with arsenal struct and params.
        """
        return self.set_arsenal_struct(module_id)

    def set_arsenal_struct(self, module_id: str) -> List[Dict]:
        """
        Gather parent MODULE (e.g. fermion)
        -> get child methods
        -> sort from
        """
        print("set_arsenal_struct")
        try:
            # get all methods for the desired task
            print("start retrieve_arsenal_struct")
            arsenal_struct: List[Dict] = []
            modules_params = set()
            methods: Dict[str, Dict] = self.g.get_neighbor_list(
                node=module_id,
                target_type="METHOD",
            )

            print(f"defs found {module_id}:", methods.keys())

            if methods:
                for i, (mid, attrs) in enumerate(methods.items()):
                    if "__init__" in mid or "main" in mid or mid.split(".")[-1].startswith("_"):
                        continue

                    params = self.g.get_neighbor_list_rel(
                        node=mid,
                        trgt_rel="requires_param",
                        as_dict=True,
                    )

                    print("params set")
                    pkeys = list(params.keys())
                    for key in pkeys:
                        modules_params.add(key)

                    attrs["params"] = pkeys
                    arsenal_struct.append(attrs)

            # sort
            self.arsenal_struct = self.get_execution_order(
                method_definitions=arsenal_struct
            )

            self.set_method_exec_index()
            self.update_module_node(module_id, list(modules_params))
            print("set_arsenal_struct... done")
            return self.arsenal_struct
            
        except Exception as e:
            print(f"Error RELAY.retrieve_arsenal_struct: {e}")
            import traceback
            traceback.print_exc()
            return []


    def update_module_node(self, module_id: str, modules_params):
        try:
            self.g.update_node(
                dict(
                    id=module_id,
                    arsenal_struct=self.arsenal_struct,
                    params=modules_params,
                ),
            )
            # pprint.pp(self.arsenal_struct)
            print("update_module_node... done")
        except Exception as e:
            print(f"Error MLOADER.update_module_node: {e}")
            return []

    def set_method_exec_index(self):
        # add method index to node to ensure persistency in equaton handling
        try:
            print("set_method_exec_index...")
            for i, item in enumerate(self.arsenal_struct):
                self.g.update_node(
                    dict(
                        **{k:v for k,v in item.items() if k not in ["type"]},
                        type="METHOD",
                    )
                )
            print("set_method_exec_index... done")
        except Exception as e:
            print(f"Error MLOADER.update_method_exec_index: {e}")


    def get_execution_order(
            self,
            method_definitions: List[Dict]
    ) -> List[Dict]:
        """
        Determines the correct execution order of methods based on admin_data dependencies.

        Args:
            method_definitions: List of dictionaries, each describing a method:
            {'method_name': str, 'return_key': str, 'parameters': List[str]}

        Returns:
            List[str]: The method names in the required dependency order.
        """

        # Identify all keys that are returned/produced by *any* method in the list.
        internal_returns = {m['return_key'] for m in method_definitions if m.get('return_key')}

        scheduled_order = []
        # Tracks keys that have been produced by methods already scheduled.
        produced_keys = set()

        # Use a mutable copy of the input list for processing.
        remaining_methods = method_definitions

        # Loop until all methods are scheduled or a dependency cycle is found.
        while remaining_methods:
            ready_to_run = []

            # 1. Identify all methods ready in this iteration
            for method in remaining_methods:
                required_params = set(method.get('params', []))

                # Dependencies are the internal keys required by the method.
                # External initial inputs (like 'mass', 'vev') are ignored here,
                # as they are assumed to be always available from the start.
                internal_dependencies = required_params.intersection(internal_returns)

                # Check if all required internal dependencies are met by the produced keys.
                if internal_dependencies.issubset(produced_keys):
                    ready_to_run.append(method)

            # Break if no method can run (indicates a cycle or incomplete definition)
            if not ready_to_run:
                break

            # 2. Schedule the ready methods and update the state
            for method in ready_to_run:
                scheduled_order.append(
                    method
                )

                # Update the set of produced keys
                if method.get('return_key'):
                    produced_keys.add(method['return_key'])

                # Remove the method from the remaining list
                remaining_methods.remove(method)

        return scheduled_order
