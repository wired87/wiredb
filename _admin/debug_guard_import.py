"""Debug guard imports step by step."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

def try_import(name, mod):
    try:
        __import__(mod)
        print(f"  OK: {name}")
        return True
    except Exception as e:
        print(f"  FAIL: {name}: {e}")
        return False

print("1. stdlib")
try_import("base64", "base64")
try_import("os", "os")
try_import("itertools", "itertools")
try_import("numpy", "numpy")
try_import("networkx", "networkx")
try_import("asyncio", "asyncio")
try_import("json", "json")
try_import("websockets", "websockets")

print("2. _admin")
try_import("ArtifactAdmin", "_admin.bob_builder.artifact_registry.artifact_admin")

print("3. cloud")
try_import("VertexTrainerManager", "cloud.gcp.vertex_trainer.manager")

print("4. qbrain")
try_import("StructInspector", "qbrain.code_manipulation.graph_creator")
try_import("GUtils", "qbrain.graph.local_graph_utils")
try_import("QFUtils", "qbrain.qf_utils.qf_utils")
try_import("get_qbrain_table_manager", "qbrain.core.qbrain_manager")
try_import("ModuleCreator", "qbrain.core.module_manager.mcreator")
try_import("EqExtractor", "qbrain.utils.math.operator_handler")
try_import("ALL_SUBS", "qbrain.qf_utils.all_subs")
try_import("expand_structure", "qbrain.utils._np.expand_array")
try_import("get_shape", "qbrain.utils.get_shape")
try_import("extract_trailing_numbers", "qbrain.utils.xtract_trailing_numbers")
try_import("DeploymentHandler", "qbrain.workflows.deploy_sim")
try_import("pop_cmd", "qbrain.utils.run_subprocess")
try_import("FieldsManager", "qbrain.core.fields_manager.fields_lib")
try_import("MethodManager", "qbrain.core.method_manager.method_lib")
try_import("InjectionManager", "qbrain.core.injection_manager")
try_import("ModuleWsManager", "qbrain.core.module_manager.ws_modules_manager")
try_import("ParamsManager", "qbrain.core.param_manager.params_lib")
try_import("EnvManager", "qbrain.core.env_manager.env_lib")

print("5. full guard")
try_import("guard", "qbrain.core.guard")

print("Done.")
