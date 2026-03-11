"""Debug guard imports - minimal."""
import sys
print("0. start")
from pathlib import Path
print("1. pathlib")
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
print("2. path setup done")
import base64, os
print("3. stdlib")
import numpy
print("4. numpy")
import _admin.bob_builder.artifact_registry.artifact_admin
print("5. artifact_admin")
import cloud.gcp.vertex_trainer.manager
print("6. vertex_trainer")
print("Done")
