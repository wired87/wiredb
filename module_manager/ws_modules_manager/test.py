
import sys
import os
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Mock dependencies
sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.bigquery"] = MagicMock()
mock_bq_module = MagicMock()
sys.modules["a_b_c.bq_agent._bq_core.bq_handler"] = mock_bq_module

# Ensure BQCore matches what we want
mock_bq_core_class = MagicMock()
mock_bq_module.BQCore = mock_bq_core_class

try:
    from qbrain.core.handler_utils import flatten_payload
    from qbrain.core.module_manager.ws_modules_manager import modules_lib
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

class TestWSModules(unittest.TestCase):
    def test_workflows(self):
        print("Testing WS Modules Handlers (Mocked)...")
        
        manager = modules_lib.module_manager
        
        # Setup mocks
        manager.bq_insert = MagicMock()
        manager.run_query = MagicMock()
        
        # 1. SET
        print("--- Testing SET ---")
        user_id = "user_test"
        files = [{"code": "print('hello')", "type": "py"}]
        payload_set = {
            "auth": {"user_id": user_id},
            "data": {"files": files}
        }
        
        # Important: set return value for run_query
        manager.run_query.return_value = [
            {"id": "1001", "file_type": "py", "created_at": "2025-01-01"}
        ]
        
        resp = modules_lib.handle_set_module(**flatten_payload(payload_set))
        print("Set Resp:", resp)
        
        self.assertEqual(resp["type"], "LIST_USERS_MODULES")
        self.assertTrue(manager.run_query.called, "run_query should be called")
        self.assertIn("1001", resp.get("data", {}).get("modules", []), f"Modules missing 1001. Data: {resp.get('data')}")
        
        # 2. GET
        print("\n--- Testing GET ---")
        manager.run_query.return_value = [
            {"id": "1001", "code": "print('hello')", "binary_data": None}
        ]
        payload_get = {"auth": {"module_id": "1001"}}
        resp_get = modules_lib.handle_get_module(**flatten_payload(payload_get))
        print("Get Resp:", resp_get)
        self.assertEqual(resp_get["type"], "GET_MODULE")
        self.assertEqual(resp_get["data"]["code"], "print('hello')")
        
        # 3. LINK
        print("\n--- Testing LINK ---")
        payload_link = {
            "auth": {
                "user_id": user_id, 
                "session_id": "sess_1", 
                "module_id": "1001"
            }
        }
        manager.run_query.return_value = [
            {"id": "1001", "code": "print('hello')"}
        ]
        resp_link = modules_lib.handle_link_session_module(**flatten_payload(payload_link))
        self.assertEqual(resp_link["type"], "GET_SESSIONS_MODULES")
        self.assertEqual(len(resp_link["data"]["modules"]), 1)
        
        # 4. DEL
        print("\n--- Testing DEL ---")
        payload_del = {"auth": {"user_id": user_id, "module_id": "1001"}}
        manager.run_query.return_value = [] 
        resp_del = modules_lib.handle_del_module(**flatten_payload(payload_del))
        self.assertEqual(resp_del["type"], "LIST_USERS_MODULES")
        self.assertEqual(len(resp_del["data"]["modules"]), 0)

if __name__ == "__main__":
    unittest.main()
