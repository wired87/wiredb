"""
User Management Package

Handles dataset and table management for the QBRAIN ecosystem including:
- Users, payment records, injections, environments, metadata, and modules

Uses QBrainTableManager (qb) for all DB operations. Pass qb instance or use default.
"""

from typing import Optional, Dict, Any

from qbrain.core.qbrain_manager import get_qbrain_table_manager
from qbrain._db import queries as db_queries
from qbrain.utils.id_gen import generate_id

_USER_DEBUG = "[UserManager]"


class UserManager:
    """
    Manages user data and records via QBrainTableManager.
    All DB access goes through the given qb instance (run_query, set_item).
    """

    DATASET_ID = "QBRAIN"
    TABLES = {
        "users": "users",
        "payment": "payment",
        "injections": "injections",
        "environments": "environments",
        "metadata": "metadata",
        "modules": "modules"
    }

    _tables_verified = False

    def __init__(self, qb=None):
        """Initialize with QBrainTableManager instance. If None, uses default from get_qbrain_table_manager()."""
        self.qb = qb if qb is not None else get_qbrain_table_manager()
        self.pid = self.qb.pid
        print(f"{_USER_DEBUG} initialized with dataset: {self.DATASET_ID}")

    def initialize_qbrain_workflow(self, uid: str, email: Optional[str] = None) -> Dict[str, Any]:
        """
        Main workflow orchestrator.

        Args:
            uid: User unique identifier
            email: User email address

        Returns:
            Dictionary containing initialization results
        """
        results = {"user_created": False, "errors": []}
        try:
            print(f"{_USER_DEBUG} initialize_qbrain_workflow: id={uid}")
            results["user_created"] = self._ensure_user_record(uid, email)
            print(f"{_USER_DEBUG} initialize_qbrain_workflow: done, user_created={results['user_created']}")
        except Exception as e:
            error_msg = f"Error in initialize_qbrain_workflow: {e}"
            print(f"{_USER_DEBUG} initialize_qbrain_workflow: error: {error_msg}")
            results["errors"].append(error_msg)
            import traceback
            traceback.print_exc()
        return results

    def get_or_create_user(
        self,
        received_key: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[str]:
        """
        Check users table for id = received_key. If not found, create user entry.
        If received_key is empty, generate with generate_id().
        Returns the user's id (for local storage) or None on failure.
        """
        uid = (received_key or "").strip()
        if not uid:
            uid = generate_id()
            print(f"{_USER_DEBUG} get_or_create_user: no key received, generated uid={uid}")

        try:
            if self.qb.db.local:
                query, params = db_queries.duck_get_user(uid)
                result = self.qb.db.run_query(query, conv_to_dict=True, params=params)
            else:
                query, job_config = self.qb.bqcore.q_get_user(self.pid, self.DATASET_ID, uid)
                result = self.qb.db.run_query(query, conv_to_dict=True, job_config=job_config)
            if result and len(result) > 0:
                row = result[0]
                user_id = row.get("id") or row.get("uid") or uid
                print(f"{_USER_DEBUG} get_or_create_user: found existing user id={user_id}")
                return user_id

            user_data = {"id": uid, "email": email or None, "status": "active"}
            print(f"{_USER_DEBUG} get_or_create_user: creating user id={uid}")
            self.qb.set_item("users", user_data, keys={"id": uid})
            print(f"{_USER_DEBUG} get_or_create_user: created")
            return uid
        except Exception as e:
            print(f"{_USER_DEBUG} get_or_create_user: error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user record.
        
        Args:
            uid: User unique identifier
            
        Returns:
            User record dictionary or None if not found
        """
        try:
            print(f"{_USER_DEBUG} get_user: uid={uid}")
            if self.qb.db.local:
                query, params = db_queries.duck_get_user(uid)
                result = self.qb.db.run_query(query, conv_to_dict=True, params=params)
            else:
                query, job_config = self.qb.bqcore.q_get_user(self.pid, self.DATASET_ID, uid)
                result = self.qb.db.run_query(query, conv_to_dict=True, job_config=job_config)
            print(f"{_USER_DEBUG} get_user: found={bool(result)}")
            return result[0] if result else None
        except Exception as e:
            print(f"{_USER_DEBUG} get_user: error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_payment_record(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve payment record for a user.
        
        Args:
            uid: User unique identifier
            
        Returns:
            Payment record dictionary or None if not found
        """
        try:
            print(f"{_USER_DEBUG} get_payment_record: uid={uid}")
            if self.qb.db.local:
                query, params = db_queries.duck_get_payment_record(uid)
                result = self.qb.db.run_query(query, conv_to_dict=True, params=params)
            else:
                query, job_config = self.qb.bqcore.q_get_payment_record(self.pid, self.DATASET_ID, uid)
                result = self.qb.db.run_query(query, conv_to_dict=True, job_config=job_config)
            print(f"{_USER_DEBUG} get_payment_record: found={bool(result)}")
            return result[0] if result else None
        except Exception as e:
            print(f"{_USER_DEBUG} get_payment_record: error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_standard_stack(self, user_id: str):
        try:
            print(f"{_USER_DEBUG} get_standard_stack: user_id={user_id}")
            self._ensure_user_record(user_id)
            if self.qb.db.local:
                query, params = db_queries.duck_get_standard_stack(user_id)
                result = self.qb.db.run_query(query, params=params, conv_to_dict=True)
            else:
                query, job_config = self.qb.bqcore.q_get_standard_stack(self.pid, self.DATASET_ID, user_id)
                result = self.qb.db.run_query(query, job_config=job_config, conv_to_dict=True)
            if not result:
                print(f"{_USER_DEBUG} get_standard_stack: no result")
                return False
            sm_stack_status = result[0].get("sm_stack_status")
            ok = sm_stack_status == "created"
            print(f"{_USER_DEBUG} get_standard_stack: sm_stack_status={sm_stack_status}, ok={ok}")
            return ok
        except Exception as e:
            print(f"{_USER_DEBUG} get_standard_stack: error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def ensure_user(self, uid, email=None) -> bool:
        try:
            print(f"ensure_user")

            # ensure user table
            table_item: dict = next(
                item
                for item in self.qb.MANAGERS_INFO
                if "users" == item["default_table"]
            )

            schema = self.qb.db.create_sql_schema(table_item["schema"])

            self.qb.db.create_table("users", schema_sql=schema)
            query, params = db_queries.duck_ensure_user_exists(uid)
            result = self.qb.db.run_query(query, conv_to_dict=True, params=params)
            if not result or not len(result):
                user_data = {"id": uid, "email": email or None, "status": "active"}
                print(f"_ensure_user_record: creating user")
                self.qb.set_item("users", user_data)
            print(f"_ensure_user_record: created")
            return True
        except Exception as e:
            print(f"_ensure_user_record: error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def set_standard_stack(self, user_id):
        try:
            print(f"{_USER_DEBUG} set_standard_stack: user_id={user_id}")
            self.ensure_user(user_id)

            print(f"{_USER_DEBUG} set_standard_stack: done")
        except Exception as e:
            print(f"{_USER_DEBUG} set_standard_stack: error: {e}")
            import traceback
            traceback.print_exc()
            raise


    def _ensure_payment_record(self, uid: str) -> bool:
        """
        Create free payment record for user if it doesn't exist.
        
        Args:
            uid: User unique identifier
            
        Returns:
            True if payment record was created or already exists
        """
        try:
            print(f"{_USER_DEBUG} _ensure_payment_record: uid={uid}")
            if self.qb.db.local:
                query, params = db_queries.duck_ensure_payment_exists(uid)
                result = self.qb.db.run_query(query, conv_to_dict=True, params=params)
            else:
                query, job_config = self.qb.bqcore.q_ensure_payment_exists(self.pid, self.DATASET_ID, uid)
                result = self.qb.db.run_query(query, conv_to_dict=True, job_config=job_config)
            if result and len(result) > 0:
                print(f"{_USER_DEBUG} _ensure_payment_record: already exists")
                return True
            from qbrain.utils.id_gen import generate_id
            payment_data = {
                "id": generate_id(),
                "uid": uid,
                "payment_type": "free",
                "stripe_customer_id": None,
                "stripe_subscription_id": None,
                "stripe_payment_intent_id": None,
                "stripe_payment_method_id": None
            }
            # Ensure one payment record per user (key by uid, not random payment id)
            self.qb.set_item("payment", payment_data, keys={"uid": uid})
            print(f"{_USER_DEBUG} _ensure_payment_record: created")
            return True
        except Exception as e:
            print(f"{_USER_DEBUG} _ensure_payment_record: error: {e}")
            import traceback
            traceback.print_exc()
            raise


    def update_payment_stripe_info(
        self,
        uid: str,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
        stripe_payment_intent_id: Optional[str] = None,
        stripe_payment_method_id: Optional[str] = None,
        payment_type: Optional[str] = None
    ) -> bool:
        """
        Update Stripe payment information for a user.
        
        Args:
            uid: User unique identifier
            stripe_customer_id: Stripe customer ID
            stripe_subscription_id: Stripe subscription ID
            stripe_payment_intent_id: Stripe payment intent ID
            stripe_payment_method_id: Stripe payment method ID
            payment_type: Payment type (e.g., "free", "premium", "enterprise")
            
        Returns:
            True if update was successful
        """
        try:
            print(f"{_USER_DEBUG} update_payment_stripe_info: uid={uid}")
            updates = {}
            if stripe_customer_id is not None:
                updates["stripe_customer_id"] = stripe_customer_id
            if stripe_subscription_id is not None:
                updates["stripe_subscription_id"] = stripe_subscription_id
            if stripe_payment_intent_id is not None:
                updates["stripe_payment_intent_id"] = stripe_payment_intent_id
            if stripe_payment_method_id is not None:
                updates["stripe_payment_method_id"] = stripe_payment_method_id
            if payment_type is not None:
                updates["payment_type"] = payment_type
            if not updates:
                print(f"{_USER_DEBUG} update_payment_stripe_info: no fields to update")
                return False
            out = self.qb.set_item("payment", updates, keys={"id": uid})
            print(f"{_USER_DEBUG} update_payment_stripe_info: done")
            return out
        except Exception as e:
            print(f"{_USER_DEBUG} update_payment_stripe_info: error: {e}")
            import traceback
            traceback.print_exc()
            return False


# Default instance for standalone use (no orchestrator context)
_default_user_manager = UserManager()
