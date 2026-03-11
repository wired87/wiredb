from .file_lib import handle_set_file
from .types import SetFileItemData, ReqDataSetFile, OutSetFile, RelayCaseStruct

# Case struct - req_struct.data uses exact datatypes (ReqDataSetFile)
SET_FILE_CASE: RelayCaseStruct = {
    "case": "SET_FILE",
    "desc": "Set File (Module from File)",
    "func": handle_set_file,
    "req_struct": {
        "data": {"id": str, "files": list, "name": str, "description": str, "prompt": str, "msg": str},  # ReqDataSetFile
        "auth": {"user_id": str, "original_id": str}
    },
    "out_struct": {
        "type": "LIST_USERS_MODULES",
        "data": {"modules": list}  # OutSetFile
    }
}

RELAY_FILE = [SET_FILE_CASE]
