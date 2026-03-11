import os
try:
    from ray import get_actor
    from _admin._ray_core.base.base import BaseActor
    from _admin._ray_core.globacs.state_handler.main import StateHandler
except ImportError:
    def get_actor(*args, **kwargs):
        pass
    class BaseActor:
        pass
    class StateHandler:
        pass
from qbrain.core.app_utils import ARSENAL_PATH
from qbrain.core.module_manager.modulator import Modulator
from qbrain.graph.local_graph_utils import GUtils

import dotenv
dotenv.load_dotenv()

class ModuleCreator(
    StateHandler,
    BaseActor,
):

    """
    Worker for loading, processing and building of single Module
    """

    def __init__(
            self,
            G,
            qfu,
    ):
        """
        attrs: extracted module content in frmat:
        id=module_name,
        type="MODULE",
        parent=["FILE"],
        content=mcontent # code str
        """
        #print("======== INIT MODULE CREATOR ========")
        super().__init__()
        self.g = GUtils(
            G=G
        )
        self.mmap = []
        self.qfu=qfu
        self.arsenal_struct: list[dict] = None


    def load_sm(self):
        print("load_sm...")
        new_modules = []
        for module_file in os.listdir(ARSENAL_PATH):
            if os.path.isdir(os.path.join(ARSENAL_PATH, module_file)) or module_file.startswith("__"):
                continue

            print("load_sm:", module_file)

            if not self.g.G.has_node(module_file):
                mod_id = module_file.split(".")[0].upper()
                new_modules.append(mod_id)

                self.create_modulator(
                    mod_id,
                    code=open(
                        os.path.join(
                            ARSENAL_PATH,
                            module_file
                        ),
                        "r",
                        encoding="utf-8"
                    ).read()
                )
        print("sm load successfully modules:", new_modules)


    def main(self, temp_path):
        print("=========== MODULATOR CREATOR ===========")
        """
        LOOP (TMP) DIR -> CREATE MODULES FORM MEDIA
        """
        # todo load modules form files
        for root, dirs, files in os.walk(temp_path):
            for module in dirs:
                if not self.g.G.has_node(module):
                    self.create_modulator(
                        module,
                    )

            for f in files:
                if not self.g.G.has_node(f):
                    self.create_modulator(
                        f,
                    )
        print("modules updated")


    def trigger_buildup_all_modules(self, module_names):
        for module in module_names:
            ref = get_actor(module)
            ref.module_build_process.remote()


    def create_modulator(self, mid, code=None):
        try:
            mref = Modulator(
                G=self.g.G,
                mid=mid,
                qfu=self.qfu,
            )

            # save ref
            self.g.add_node(
                dict(
                    id=mid,
                    type="MODULE",
                    code=code
                )
            )

            print("MODULATORS CREATED")
            mref.module_conversion_process()
        except Exception as e:
            print(f"Err create_modulator: {e}")
        print("create_modulator finished")