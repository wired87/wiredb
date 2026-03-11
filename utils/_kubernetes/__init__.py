import os

from google.cloud.aiplatform.utils.yaml_utils import load_yaml

MANAGED_CERTIFICATE_PATH = r"C:\Users\wired\OneDrive\Desktop\qfs\utils\_kubernetes\managed_certificate.yaml" if os.name == "nt" else "utils/_kubernetes/managed_certificate.yaml"
MANAGED_CERTIFICATE = load_yaml(MANAGED_CERTIFICATE_PATH)


