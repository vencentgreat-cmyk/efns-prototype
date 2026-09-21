"""Application authorization and audit boundary around an existing repository."""

from __future__ import annotations

from functools import wraps

from app.security import AuthStore, Permission, User, require_permission
from data.repositories.base import RepositoryError


UPSERT_METHODS = {
    "upsert_account": ("ACCOUNT", "ACCOUNT_ID"),
    "upsert_facility": ("FACILITY", "FACILITY_ID"),
    "upsert_facility_detail": ("FACILITY_DETAIL", "FACILITY_DETAIL_ID"),
    "upsert_flock": ("FLOCK", "FLOCK_ID"),
    "upsert_flock_transaction": ("FLOCK_TRANSACTION", "FLOCK_TRANSACTION_ID"),
    "upsert_quota_registration": ("QUOTA_REGISTRATION", "QUOTA_ID"),
    "upsert_quota_transaction": ("QUOTA_TRANSACTION", "QUOTA_TRANSACTION_ID"),
    "upsert_salmonella_test": ("SALMONELLA_TEST", "SALMONELLA_TEST_ID"),
}

DELETE_METHODS = {
    "delete_account": "ACCOUNT",
    "delete_facility": "FACILITY",
    "delete_facility_detail": "FACILITY_DETAIL",
    "delete_flock": "FLOCK",
    "delete_flock_transaction": "FLOCK_TRANSACTION",
    "delete_quota_registration": "QUOTA_REGISTRATION",
    "delete_quota_transaction": "QUOTA_TRANSACTION",
    "delete_salmonella_test": "SALMONELLA_TEST",
}

IMPORT_METHODS = {
    "create_import_batch": "IMPORT_BATCH",
    "import_production_bundle": "IMPORT_BATCH",
    "import_flock_quota_batch": "FLOCK_QUOTA_IMPORT",
    "insert_raw_rows": "RAW_PRODUCTION",
    "insert_production_records": "PRODUCTION_RECORD",
}


class AuthorizedRepository:
    """Transparent proxy that enforces permissions independently of page UI."""

    def __init__(self, repository, auth_store: AuthStore, actor: User):
        self.repository = repository
        self.auth_store = auth_store
        self.actor = actor
        self.repository_name = type(repository).__name__.replace("Repository", "")

    def __getattr__(self, name):
        attribute = getattr(self.repository, name)
        if not callable(attribute):
            return attribute
        if name in UPSERT_METHODS:
            return self._authorized_upsert(name, attribute)
        if name in DELETE_METHODS:
            return self._authorized_delete(name, attribute)
        if name in IMPORT_METHODS:
            return self._authorized_import(name, attribute)
        if name == "check_connection":
            return self._authorized_call(attribute, Permission.VIEW_DIAGNOSTICS)
        if name.startswith(("get_", "find_")):
            return self._authorized_call(attribute, Permission.VIEW_DATA)
        return attribute

    def _authorized_call(self, method, permission: Permission):
        @wraps(method)
        def call(*args, **kwargs):
            self._require(permission)
            return method(*args, **kwargs)

        return call

    def _authorized_upsert(self, name, method):
        entity_type, id_field = UPSERT_METHODS[name]

        @wraps(method)
        def call(record, *args, **kwargs):
            action = "UPDATE" if record.get(id_field) else "CREATE"
            permission = Permission.UPDATE_DATA if action == "UPDATE" else Permission.CREATE_DATA
            self._require(permission)
            result = method(record, *args, **kwargs)
            self.auth_store.record_action(self.actor, action, entity_type, str(result))
            return result

        return call

    def _authorized_delete(self, name, method):
        entity_type = DELETE_METHODS[name]

        @wraps(method)
        def call(record_id, *args, **kwargs):
            self._require(Permission.DELETE_DATA)
            result = method(record_id, *args, **kwargs)
            if result:
                self.auth_store.record_action(self.actor, "DELETE", entity_type, str(record_id))
            return result

        return call

    def _authorized_import(self, name, method):
        entity_type = IMPORT_METHODS[name]

        @wraps(method)
        def call(*args, **kwargs):
            self._require(Permission.IMPORT_DATA)
            result = method(*args, **kwargs)
            if isinstance(result, dict):
                entity_id = result.get("import_id")
            else:
                entity_id = result[0] if name == "import_production_bundle" and isinstance(result, tuple) else result
            details = {"operation": name}
            if name == "import_production_bundle" and isinstance(result, tuple) and len(result) > 1:
                details["record_count"] = int(result[1])
            elif name == "import_flock_quota_batch" and isinstance(result, dict):
                details.update(
                    {
                        key: result[key]
                        for key in ("batch_id", "filename", "file_hash", "total_count", "quota_count", "flock_count", "created_count", "updated_count", "rejected_count", "status")
                        if key in result
                    }
                )
            if name == "import_flock_quota_batch" and isinstance(result, dict):
                try:
                    self.auth_store.record_action(self.actor, "IMPORT", entity_type, str(entity_id), details)
                    result["audit_recorded"] = True
                except Exception:
                    # Core rows are already committed by the repository transaction.
                    # Audit uses a separate store/transaction and is reported independently.
                    result["audit_recorded"] = False
            else:
                self.auth_store.record_action(self.actor, "IMPORT", entity_type, str(entity_id), details)
            return result

        return call

    def _require(self, permission: Permission) -> None:
        try:
            require_permission(self.actor, permission)
        except Exception as exc:
            raise RepositoryError("You do not have permission to perform this data operation.") from exc
