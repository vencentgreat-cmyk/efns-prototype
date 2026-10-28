"""Application authorization and audit boundary around an existing repository."""

from __future__ import annotations

from functools import wraps

from app.security import AuthStore, Permission, User, Role, require_permission
from data.repositories.base import RepositoryError


UPSERT_METHODS = {
    "upsert_account": ("ACCOUNT", "ACCOUNT_ID"),
    "upsert_farm_location": ("FARM_LOCATION", "FARM_LOCATION_ID"),
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
    "delete_farm_location": "FARM_LOCATION",
    "delete_facility": "FACILITY",
    "delete_facility_detail": "FACILITY_DETAIL",
    "delete_flock": "FLOCK",
    "delete_flock_transaction": "FLOCK_TRANSACTION",
    "delete_quota_registration": "QUOTA_REGISTRATION",
    "delete_quota_transaction": "QUOTA_TRANSACTION",
    "delete_salmonella_test": "SALMONELLA_TEST",
    "cleanup_synthetic_migration": "MIGRATION_BATCH",
}

IMPORT_METHODS = {
    "archive_source_file": "SOURCE_FILE",
    "record_source_parse": "SOURCE_FILE",
    "stage_production_upload": "IMPORT_BATCH",
    "commit_staged_production": "IMPORT_BATCH",
    "stage_operational_review": "IMPORT_BATCH",
    "commit_staged_operational": "FLOCK_QUOTA_IMPORT",
    "create_import_batch": "IMPORT_BATCH",
    "import_production_bundle": "IMPORT_BATCH",
    "import_flock_quota_batch": "FLOCK_QUOTA_IMPORT",
    "import_operational_flock_quota_batch": "FLOCK_QUOTA_IMPORT",
    "insert_raw_rows": "RAW_PRODUCTION",
    "insert_production_records": "PRODUCTION_RECORD",
    "stage_migration_file": "MIGRATION_FILE",
    "prepare_migration_batch": "MIGRATION_BATCH",
    "repair_migration_batch": "MIGRATION_BATCH",
    "commit_migration_batch": "MIGRATION_BATCH",
    "commit_historical_corrections": "MIGRATION_CORRECTION_BATCH",
}


class AuthorizedRepository:
    """Transparent proxy that enforces permissions independently of page UI."""

    def __init__(self, repository, auth_store: AuthStore, actor: User):
        self.repository = repository
        self.auth_store = auth_store
        self.actor = actor
        self.repository_name = type(repository).__name__.replace("Repository", "")
        self.last_audit_warning = None

    def __getattr__(self, name):
        attribute = getattr(self.repository, name)
        if not callable(attribute):
            return attribute
        if name == 'record_current_flock_quantity':
            @wraps(attribute)
            def quantity_call(*args,**kwargs):
                self._require(Permission.CREATE_DATA)
                self._require(Permission.UPDATE_DATA)
                kwargs['actor']={'user_id':self.actor.user_id,'email':self.actor.email}
                return attribute(*args,**kwargs)
            return quantity_call
        if name in {'diagnose_flock_date_repair_context','preview_flock_date_repair','commit_flock_date_repair','preview_flock_date_reversal','commit_flock_date_reversal'}:
            @wraps(attribute)
            def date_repair_call(*args,**kwargs):
                self._require(Permission.IMPORT_DATA)
                if self.actor.role != Role.ADMIN:
                    raise RepositoryError('Date mapping repairs require an EFNS Admin.')
                if name.startswith('commit_'):
                    kwargs['actor']={'user_id':self.actor.user_id,'email':self.actor.email}
                return attribute(*args,**kwargs)
            return date_repair_call
        if name in {'preview_flock_transaction_supplement','commit_flock_transaction_supplement'}:
            @wraps(attribute)
            def supplement_call(*args,**kwargs):
                self._require(Permission.IMPORT_DATA)
                if self.actor.role != Role.ADMIN:
                    raise RepositoryError('Historical supplements require an EFNS Admin.')
                if name=='commit_flock_transaction_supplement':
                    kwargs['actor']={'user_id':self.actor.user_id,'email':self.actor.email}
                return attribute(*args,**kwargs)
            return supplement_call
        if name in {'save_historical_correction_decision','commit_historical_correction_review'}:
            @wraps(attribute)
            def correction_call(*args,**kwargs):
                self._require(Permission.IMPORT_DATA)
                kwargs['actor']={'user_id':self.actor.user_id,'email':self.actor.email}
                # Mandatory audit is inside the same repository transaction;
                # never issue a second audit transaction after the CORE commit.
                return attribute(*args,**kwargs)
            return correction_call
        if name == 'preview_historical_correction_review':
            return self._authorized_call(attribute,Permission.IMPORT_DATA)
        if name in {"record_flock_event", "revise_record", "match_production_producer", "create_manual_production", "create_flock_with_initial_position"}:
            @wraps(attribute)
            def continuity_call(*args, **kwargs):
                self._require(Permission.CREATE_DATA if name in {"create_manual_production", "create_flock_with_initial_position"} else Permission.UPDATE_DATA)
                kwargs["actor"] = self.actor.user_id
                result = attribute(*args, **kwargs)
                entity_id = args[0] if name == "match_production_producer" else result
                try:
                    self.auth_store.record_action(self.actor, "CREATE" if name in {"create_manual_production", "create_flock_with_initial_position"} else "UPDATE", name, str(entity_id))
                except Exception:
                    self.last_audit_warning="The business change committed with its history; secondary audit logging was unavailable."
                return result
            return continuity_call
        if name in {"get_source_file_bytes", "get_source_review_rows", "get_source_raw_rows"}:
            return self._authorized_call(attribute, Permission.IMPORT_DATA)
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
            if name in {"archive_source_file", "record_source_parse", "commit_staged_production", "commit_staged_operational"}:
                kwargs["actor"] = self.actor.user_id
            result = method(*args, **kwargs)
            if name in {"import_flock_quota_batch", "import_operational_flock_quota_batch", "commit_staged_operational"} and isinstance(result, dict):
                entity_id = result.get("import_id")
            elif name == "commit_migration_batch" and isinstance(result, dict):
                entity_id = result.get("batch_id")
            elif name == "commit_historical_corrections" and isinstance(result, dict):
                entity_id = result.get("correction_batch_id")
            elif name in {"import_production_bundle", "commit_staged_production"} and isinstance(result, tuple):
                entity_id = result[0]
            elif name == "archive_source_file" and isinstance(result, dict):
                entity_id = result.get("SOURCE_FILE_ID")
            elif name=='record_source_parse':
                entity_id=args[0]
            else:
                entity_id = result
            details = {"operation": name}
            if name == "import_production_bundle" and isinstance(result, tuple) and len(result) > 1:
                details["record_count"] = int(result[1])
            elif name in {"import_flock_quota_batch", "import_operational_flock_quota_batch"} and isinstance(result, dict):
                details.update(
                    {
                        key: result[key]
                        for key in ("batch_id", "filename", "file_hash", "total_count", "quota_count", "flock_count", "created_count", "updated_count", "rejected_count", "status")
                        if key in result
                    }
                )
            if name in {"import_flock_quota_batch", "import_operational_flock_quota_batch", "commit_staged_operational"} and isinstance(result, dict):
                try:
                    self.auth_store.record_action(self.actor, "IMPORT", entity_type, str(entity_id), details)
                    result["audit_recorded"] = True
                except Exception:
                    # Core rows are already committed by the repository transaction.
                    # Audit uses a separate store/transaction and is reported independently.
                    result["audit_recorded"] = False
            elif name=='commit_staged_production':
                try: self.auth_store.record_action(self.actor,"IMPORT",entity_type,str(entity_id),details)
                except Exception: self.last_audit_warning="The production commit succeeded; secondary audit logging was unavailable."
            else:
                self.auth_store.record_action(self.actor, "IMPORT", entity_type, str(entity_id), details)
            return result

        return call

    def _require(self, permission: Permission) -> None:
        try:
            require_permission(self.actor, permission)
        except Exception as exc:
            raise RepositoryError("You do not have permission to perform this data operation.") from exc
