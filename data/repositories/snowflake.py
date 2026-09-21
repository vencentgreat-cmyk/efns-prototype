"""Snowflake repository backed only by the shared SQL executor contract."""

from __future__ import annotations

import json
import os
import re
from typing import Optional
import uuid

import pandas as pd

from data.connection import ConnectorExecutor, SqlExecutor, create_executor
from data.repositories.base import BaseRepository, ConcurrencyError, RepositoryError
from data.validation import normalize_flock_dates, validate_flock, validate_quota_registration, validate_quota_transaction, validate_salmonella_test


MODEL = {
    "ACCOUNT": ("ACCOUNT_ID", "REGISTRATION_NUMBER ORGANIZATION_NAME ADDRESS_LINE1 ADDRESS_LINE2 ADDRESS_LINE3 CITY PROVINCE POSTAL_CODE COUNTRY_REGION LATITUDE LONGITUDE CONTACT_NAME CONTACT_PHONE CONTACT_EMAIL FAX WEBSITE LICENCE_NUMBER PARENT_ACCOUNT_ID GRADING_STATION_ACCOUNT_ID PULLET_GROWER_ACCOUNT_ID PROVINCE_OF_REGISTRATION SPENT_FOWL_PLANS DEFAULT_ON_REPORTS NO_SVG DESCRIPTION PRODUCER_ROLE BREEDER_ROLE HATCHERY_ROLE PULLET_GROWER_ROLE GRADER_ROLE PROCESSOR_BREAKER_ROLE DISPOSAL_PLANT_ROLE UNREGULATED_ROLE PROV_BOARD_EFC_ROLE GOVERNMENT_ROLE VENDOR_ROLE RESEARCH_EXEMPT_ROLE SHIPPER_ROLE OTHER_ROLE STATUS"),
    "FACILITY": ("FACILITY_ID", "ACCOUNT_ID FACILITY_NAME FACILITY_TYPE STATUS ACTIVATION_DATE CONSTRUCTION_DATE CLOSURE_DATE DESTRUCTION_DATE INACTIVE_DATE"),
    "FACILITY_DETAIL": ("FACILITY_DETAIL_ID", "FACILITY_ID DETAIL_NAME DETAIL_TYPE STATUS COMMENTS"),
    "FLOCK": ("FLOCK_ID", "FLOCK_NUMBER ACCOUNT_ID FACILITY_ID FACILITY_DETAIL_ID QUOTA_ID FLOCK_QUOTA_TYPE STATUS CREATE_DELIVERY_TRANSACTION PERMIT_NUMBER PERMIT_DATE HATCH_DATE DATE_ORDERED BIRD_COUNT EGG_COLOUR BIRD_STRAIN PLACEMENT_DATE EST_DISPOSAL DISPOSAL_DATE BIRDS_DISPOSED BREEDER HATCHERY PULLET_GROWER DISPOSAL_PLANT DISPOSAL_METHOD COMMENTS"),
    "FLOCK_TRANSACTION": ("FLOCK_TRANSACTION_ID", "FLOCK_ID TRANSACTION_TYPE QUANTITY TRANSACTION_DATE NOTES"),
    "QUOTA_REGISTRATION": ("QUOTA_ID", "REGISTRATION_NUMBER ACCOUNT_ID QUOTA_NAME QUOTA_TYPE STATUS EFFECTIVE_DATE END_DATE COMMENTS"),
    "QUOTA_TRANSACTION": ("QUOTA_TRANSACTION_ID", "TRANSACTION_TYPE QUOTA_ID EFFECTIVE_DATE END_DATE QUOTA_COUNT OWNER_ACCOUNT_ID RELATED_ACCOUNT_ID RELATED_QUOTA_ID RELATED_TRANSACTION_ID PRICE QUOTA_LEASE_TYPE COMMENTS"),
    "SALMONELLA_TEST": ("SALMONELLA_TEST_ID", "FLOCK_ID ACCOUNT_ID PERMIT_NUMBER TESTING_DATE INSPECTOR NUMBER_OF_SAMPLES TEST_RESULT DATE_RESULT_SENT DATE_RECEIVED CASE_FILE_NUMBER INVOICE_NUMBER INVOICE_DATE COMMENTS"),
}
PRODUCTION_COLUMNS = "PRODUCER_ACCOUNT_ID GRADER_ACCOUNT_ID FACILITY_ID FLOCK_ID GRADER_NAME PRODUCER_NUMBER GRADER_NUMBER BARN_IDENTITY SOURCE_WEEK_CODE REPORTING_YEAR REPORTING_WEEK MARKETING_TYPE HOUSING_SYSTEM EGG_TYPE EGG_COLOUR FLOCK_AGE NET_WEIGHT NET_BOXES NET_PER_BOX JUMBO EXTRA_LARGE LARGE MEDIUM SMALL PEEWEE GRADE_B GRADE_C CRACKS NEST_RUN NEST_RUN_25_PLUS NEST_RUN_24_PLUS NEST_RUN_23_PLUS NEST_RUN_22_PLUS NEST_RUN_21_PLUS NEST_RUN_20_PLUS NEST_RUN_19_PLUS NEST_RUN_18_PLUS NEST_RUN_17_PLUS OTHER_LEVIABLE OTHER_NON_LEVIABLE FARM_GATE_SALES ON_FARM_CONSUMPTION SUBTOTAL REJECTS LEAKERS TOTAL TOTAL_RECEIVED REJECTED LOSS LEGACY_REJECT_LOSS_TOTAL TOTAL_ACCEPTED SOURCE_TYPE MATCH_STATUS SOURCE_ROW_NUMBER MATCH_CONFIRMED_AT MATCH_CONFIRMED_BY".split()
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


class _LegacyCursorExecutor(SqlExecutor):
    """Compatibility adapter for existing offline cursor-based test doubles."""

    runtime_name = "Offline cursor double"

    def __init__(self, cursor_context):
        self.cursor_context = cursor_context
        self.cursor = None

    def query(self, sql, params=None):
        self.cursor.execute(sql, tuple(params or ()))
        rows = self.cursor.fetchall() if hasattr(self.cursor, "fetchall") else []
        columns = [column[0] for column in (getattr(self.cursor, "description", None) or [])]
        return pd.DataFrame.from_records(rows, columns=columns)

    def execute(self, sql, params=None):
        self.cursor.execute(sql, tuple(params or ()))
        return int(getattr(self.cursor, "rowcount", -1))

    def executemany(self, sql, rows, *, batch_size=500):
        del batch_size
        values = list(rows)
        self.cursor.executemany(sql, values)
        return len(values)

    def commit(self): pass
    def rollback(self): pass

    def transaction(self):
        repository_executor = self

        class Context:
            def __enter__(inner):
                inner.context = repository_executor.cursor_context(True)
                repository_executor.cursor = inner.context.__enter__()
                return repository_executor

            def __exit__(inner, *args):
                repository_executor.cursor = None
                return inner.context.__exit__(*args)

        return Context()


class SnowflakeRepository(BaseRepository):
    def __init__(self, executor: SqlExecutor | None = None):
        self.executor = executor or create_executor()
        self.database = self._identifier(os.getenv("SNOWFLAKE_DATABASE", "EFNS_DEV"), "database")
        self.schema_raw = self._identifier(os.getenv("SNOWFLAKE_SCHEMA_RAW", "RAW"), "RAW schema")
        self.schema_core = self._identifier(os.getenv("SNOWFLAKE_SCHEMA_CORE", "CORE"), "CORE schema")
        self.schema_reporting = self._identifier(os.getenv("SNOWFLAKE_SCHEMA_REPORTING", "REPORTING"), "REPORTING schema")

    @staticmethod
    def _identifier(value: str, label: str) -> str:
        if not _IDENTIFIER.fullmatch(value or ""):
            raise RepositoryError(f"Invalid Snowflake {label} identifier in configuration.")
        return value

    def _executor(self) -> SqlExecutor:
        # Compatibility for offline callers that construct with __new__ and a
        # fake _connect function; normal application code always injects or
        # creates an executor in __init__.
        executor = getattr(self, "executor", None)
        if executor is None and "_cursor" in getattr(self, "__dict__", {}) and callable(self.__dict__["_cursor"]):
            executor = _LegacyCursorExecutor(self.__dict__["_cursor"])
            self.executor = executor
        if executor is None and callable(getattr(self, "_connect", None)):
            executor = ConnectorExecutor(self._connect)
            self.executor = executor
        if executor is None:
            executor = create_executor()
            self.executor = executor
        return executor

    @property
    def runtime_name(self) -> str:
        return self._executor().runtime_name

    def check_connection(self) -> None:
        self._executor().check_connection()

    def _table(self, table: str, schema: str | None = None) -> str:
        if table not in MODEL and table not in {"SALMONELLA_TEST_SAMPLE", "IMPORT_BATCH", "IMPORT_RAW_ROW", "PRODUCTION_RECORD", "VW_PRODUCTION_SUMMARY"}:
            raise RepositoryError("Unsupported Snowflake table identifier.")
        return f"{self.database}.{schema or self.schema_core}.{table}"

    def _query(self, sql, params=None):
        return self._executor().query(sql, params)

    def _one(self, table, column, value, schema=None):
        frame = self._query(f"SELECT * FROM {self._table(table, schema)} WHERE {column} = %s", (value,))
        return frame.iloc[0].to_dict() if not frame.empty else None

    def _upsert_with_executor(self, executor: SqlExecutor, table: str, record: dict) -> str:
        key, allowed_text = MODEL[table]
        expected = record.get("EXPECTED_UPDATED_AT")
        entity_id = record.get(key) or str(uuid.uuid4())
        allowed = allowed_text.split()
        values = {name: record[name] for name in allowed if name in record}
        if not values:
            raise RepositoryError(f"No writable fields supplied for {table}.")
        lock = " AND UPDATED_AT = %s" if expected is not None else ""
        update_sql = (
            f"UPDATE {self._table(table)} SET "
            + ", ".join(f"{name} = %s" for name in values)
            + f", UPDATED_AT = CURRENT_TIMESTAMP() WHERE {key} = %s{lock}"
        )
        update_params = [*values.values(), entity_id]
        if expected is not None:
            update_params.append(expected)
        columns = [key, *values]
        insert_sql = (
            f"INSERT INTO {self._table(table)} ({', '.join(columns)}, CREATED_AT, UPDATED_AT) "
            f"VALUES ({', '.join(['%s'] * len(columns))}, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())"
        )
        affected = executor.execute(update_sql, tuple(update_params))
        if expected is not None and affected < 0:
            raise RepositoryError("The active Snowflake runtime did not report an affected-row count; the protected update was not accepted.")
        if affected == 0:
            existing = executor.query(f"SELECT UPDATED_AT FROM {self._table(table)} WHERE {key} = %s", (entity_id,))
            if not existing.empty:
                if expected is not None:
                    raise ConcurrencyError("This record changed after it was opened. Reload it before saving again.")
                return entity_id
            if expected is not None:
                raise ConcurrencyError("This record no longer exists. Return to the list and reload.")
            executor.execute(insert_sql, (entity_id, *values.values()))
        return entity_id

    def _upsert(self, table: str, record: dict) -> str:
        with self._executor().transaction() as tx:
            return self._upsert_with_executor(tx, table, record)

    def _delete(self, table, key, entity_id, references=()):
        with self._executor().transaction() as tx:
            for ref_table, ref_col in references:
                schema = self.schema_core
                existing = tx.query(f"SELECT 1 AS FOUND FROM {self._table(ref_table, schema)} WHERE {ref_col} = %s LIMIT 1", (entity_id,))
                if not existing.empty:
                    raise RepositoryError(f"This {table.replace('_', ' ').title()} still has related records and cannot be deleted.")
            return tx.execute(f"DELETE FROM {self._table(table)} WHERE {key} = %s", (entity_id,)) > 0

    def _filtered(self, table, filters, schema=None):
        conditions, params = [], []
        for column, value in filters:
            if value is not None and value != "":
                conditions.append(f"{column} = %s")
                params.append(value)
        sql = f"SELECT * FROM {self._table(table, schema)}"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        return self._query(sql, tuple(params) if params else None)

    def get_accounts(self): return self._filtered("ACCOUNT", ())
    def get_account(self, account_id): return self._one("ACCOUNT", "ACCOUNT_ID", account_id)
    def find_accounts_by_registration_number(self, registration_number): return self._query(f"SELECT * FROM {self._table('ACCOUNT')} WHERE UPPER(TRIM(REGISTRATION_NUMBER)) = UPPER(TRIM(%s))", (registration_number,))
    def upsert_account(self, record):
        account_id = record.get("ACCOUNT_ID")
        registration = str(record.get("REGISTRATION_NUMBER") or "").strip()
        if registration:
            matches = self.find_accounts_by_registration_number(registration)
            if not matches.empty and any(matches["ACCOUNT_ID"].astype(str) != str(account_id)):
                raise RepositoryError("Registration Number is already used by another Account.")
        for field in ("PARENT_ACCOUNT_ID", "GRADING_STATION_ACCOUNT_ID", "PULLET_GROWER_ACCOUNT_ID"):
            if account_id and record.get(field) == account_id:
                raise RepositoryError("Account cannot reference itself in an Account lookup.")
        return self._upsert("ACCOUNT", record)
    def delete_account(self, value): return self._delete("ACCOUNT", "ACCOUNT_ID", value, (("ACCOUNT", "PARENT_ACCOUNT_ID"), ("ACCOUNT", "GRADING_STATION_ACCOUNT_ID"), ("ACCOUNT", "PULLET_GROWER_ACCOUNT_ID"), ("FACILITY", "ACCOUNT_ID"), ("FLOCK", "ACCOUNT_ID"), ("QUOTA_REGISTRATION", "ACCOUNT_ID"), ("SALMONELLA_TEST", "ACCOUNT_ID")))

    def get_facilities(self, account_id=None): return self._filtered("FACILITY", (("ACCOUNT_ID", account_id),))
    def upsert_facility(self, record): return self._upsert("FACILITY", record)
    def delete_facility(self, value): return self._delete("FACILITY", "FACILITY_ID", value, (("FACILITY_DETAIL", "FACILITY_ID"), ("FLOCK", "FACILITY_ID")))
    def get_facility_details(self, facility_id=None): return self._filtered("FACILITY_DETAIL", (("FACILITY_ID", facility_id),))
    def get_facility_detail(self, value): return self._one("FACILITY_DETAIL", "FACILITY_DETAIL_ID", value)
    def upsert_facility_detail(self, record): return self._upsert("FACILITY_DETAIL", record)
    def delete_facility_detail(self, value): return self._delete("FACILITY_DETAIL", "FACILITY_DETAIL_ID", value, (("FLOCK", "FACILITY_DETAIL_ID"),))

    def get_flocks(self, account_id=None, facility_id=None): return self._filtered("FLOCK", (("ACCOUNT_ID", account_id), ("FACILITY_ID", facility_id)))
    def get_flock(self, flock_id): return self._one("FLOCK", "FLOCK_ID", flock_id)
    def upsert_flock(self, record):
        record = normalize_flock_dates(record)
        errors = validate_flock(self, record)
        if errors: raise RepositoryError(" ".join(errors))
        return self._upsert("FLOCK", record)
    def delete_flock(self, value): return self._delete("FLOCK", "FLOCK_ID", value, (("FLOCK_TRANSACTION", "FLOCK_ID"), ("SALMONELLA_TEST", "FLOCK_ID"), ("PRODUCTION_RECORD", "FLOCK_ID")))

    def get_flock_transactions(self, flock_id=None): return self._filtered("FLOCK_TRANSACTION", (("FLOCK_ID", flock_id),))
    def upsert_flock_transaction(self, record): return self._upsert("FLOCK_TRANSACTION", record)
    def delete_flock_transaction(self, value): return self._delete("FLOCK_TRANSACTION", "FLOCK_TRANSACTION_ID", value)

    def get_quota_registrations(self, account_id=None, status=None, quota_type=None, active_only=False):
        filters = [("ACCOUNT_ID", account_id), ("STATUS", status), ("QUOTA_TYPE", quota_type)]
        if not active_only: return self._filtered("QUOTA_REGISTRATION", filters)
        conditions, params = ["STATUS = %s", "(EFFECTIVE_DATE IS NULL OR EFFECTIVE_DATE <= CURRENT_DATE())", "(END_DATE IS NULL OR END_DATE >= CURRENT_DATE())"], ["Active"]
        for column, value in filters:
            if value is not None: conditions.append(f"{column} = %s"); params.append(value)
        return self._query(f"SELECT * FROM {self._table('QUOTA_REGISTRATION')} WHERE " + " AND ".join(conditions), tuple(params))
    def get_quota_registration(self, value): return self._one("QUOTA_REGISTRATION", "QUOTA_ID", value)
    def upsert_quota_registration(self, record):
        errors = validate_quota_registration(self, record)
        if errors: raise RepositoryError(" ".join(errors))
        return self._upsert("QUOTA_REGISTRATION", record)
    def delete_quota_registration(self, value): return self._delete("QUOTA_REGISTRATION", "QUOTA_ID", value, (("QUOTA_TRANSACTION", "QUOTA_ID"), ("FLOCK", "QUOTA_ID")))

    def get_quota_transactions(self, account_id=None, quota_id=None, quota_type=None, transaction_type=None, date_from=None, date_to=None):
        join = f" JOIN {self._table('QUOTA_REGISTRATION')} qr ON qr.QUOTA_ID = qt.QUOTA_ID" if quota_type else ""
        conditions, params = [], []
        if account_id: conditions.append("(qt.OWNER_ACCOUNT_ID = %s OR qt.RELATED_ACCOUNT_ID = %s)"); params += [account_id, account_id]
        for column, operator, value in (("qt.QUOTA_ID", "=", quota_id), ("qr.QUOTA_TYPE", "=", quota_type), ("qt.TRANSACTION_TYPE", "=", transaction_type), ("qt.EFFECTIVE_DATE", ">=", date_from), ("qt.EFFECTIVE_DATE", "<=", date_to)):
            if value is not None: conditions.append(f"{column} {operator} %s"); params.append(value)
        sql = f"SELECT qt.* FROM {self._table('QUOTA_TRANSACTION')} qt{join}"
        if conditions: sql += " WHERE " + " AND ".join(conditions)
        return self._query(sql, tuple(params) if params else None)
    def upsert_quota_transaction(self, record):
        errors = validate_quota_transaction(self, record)
        if errors: raise RepositoryError(" ".join(errors))
        stored = dict(record); stored["OWNER_ACCOUNT_ID"] = self.get_quota_registration(record["QUOTA_ID"])["ACCOUNT_ID"]
        return self._upsert("QUOTA_TRANSACTION", stored)
    def get_quota_transaction(self, value): return self._one("QUOTA_TRANSACTION", "QUOTA_TRANSACTION_ID", value)
    def delete_quota_transaction(self, value): return self._delete("QUOTA_TRANSACTION", "QUOTA_TRANSACTION_ID", value, (("QUOTA_TRANSACTION", "RELATED_TRANSACTION_ID"),))

    def get_salmonella_tests(self, account_id=None, facility_id=None, flock_id=None, permit_number=None, test_result=None, inspector=None, case_number=None, invoice_number=None, date_from=None, date_to=None):
        join = f" JOIN {self._table('FLOCK')} f ON f.FLOCK_ID = st.FLOCK_ID" if facility_id else ""
        conditions, params = [], []
        for column, value in (("st.ACCOUNT_ID", account_id), ("f.FACILITY_ID", facility_id), ("st.FLOCK_ID", flock_id), ("st.PERMIT_NUMBER", permit_number), ("st.TEST_RESULT", test_result), ("st.INSPECTOR", inspector), ("st.CASE_FILE_NUMBER", case_number), ("st.INVOICE_NUMBER", invoice_number)):
            if value: conditions.append(f"{column} = %s"); params.append(value)
        for operator, value in ((">=", date_from), ("<=", date_to)):
            if value is not None: conditions.append(f"st.TESTING_DATE {operator} %s"); params.append(value)
        sql = f"SELECT st.* FROM {self._table('SALMONELLA_TEST')} st{join}"
        if conditions: sql += " WHERE " + " AND ".join(conditions)
        return self._query(sql, tuple(params) if params else None)
    def get_salmonella_test(self, value): return self._one("SALMONELLA_TEST", "SALMONELLA_TEST_ID", value)
    def upsert_salmonella_test(self, record):
        errors = validate_salmonella_test(self, record)
        if errors: raise RepositoryError(" ".join(errors))
        return self._upsert("SALMONELLA_TEST", record)
    def delete_salmonella_test(self, value): return self._delete("SALMONELLA_TEST", "SALMONELLA_TEST_ID", value, (("SALMONELLA_TEST_SAMPLE", "SALMONELLA_TEST_ID"),))
    def get_salmonella_test_samples(self, test_id=None): return self._filtered("SALMONELLA_TEST_SAMPLE", (("SALMONELLA_TEST_ID", test_id),))

    def _insert_batch(self, executor, import_id, record):
        allowed = "FILENAME SOURCE FILE_HASH FILE_SIZE_BYTES WORKSHEET_NAME REPORTING_YEAR REPORTING_WEEK SOURCE_RECORD_COUNT ROW_COUNT ERROR_COUNT STATUS NOTES".split()
        values = {key: record[key] for key in allowed if key in record}; columns = ["IMPORT_ID", *values]
        sql = f"INSERT INTO {self._table('IMPORT_BATCH', self.schema_raw)} ({', '.join(columns)}, UPLOAD_TIMESTAMP, CREATED_AT, UPDATED_AT) VALUES ({', '.join(['%s'] * len(columns))}, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())"
        executor.execute(sql, (import_id, *values.values()))

    def create_import_batch(self, record):
        import_id = record.get("IMPORT_ID") or str(uuid.uuid4())
        with self._executor().transaction() as tx: self._insert_batch(tx, import_id, record)
        return import_id
    def get_import_batches(self): return self._filtered("IMPORT_BATCH", (), self.schema_raw)
    def find_import_by_hash(self, file_hash): return self._one("IMPORT_BATCH", "FILE_HASH", file_hash, self.schema_raw) if file_hash else None

    def _insert_raw(self, executor, import_id, rows):
        sql = f"INSERT INTO {self._table('IMPORT_RAW_ROW', self.schema_raw)} (RAW_ROW_ID, IMPORT_ID, SOURCE_ROW_NUMBER, RAW_DATA, VALIDATION_STATUS, MATCH_STATUS, VALIDATION_MESSAGES, CREATED_AT, UPDATED_AT) VALUES (%s, %s, %s, PARSE_JSON(%s), %s, %s, PARSE_JSON(%s), CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())"
        params = [(row.get("RAW_ROW_ID") or str(uuid.uuid4()), import_id, row.get("SOURCE_ROW_NUMBER", index), json.dumps(row.get("RAW_DATA", row.get("ROW_DATA", row)), default=str), row.get("VALIDATION_STATUS", "PENDING"), row.get("MATCH_STATUS", "UNMATCHED"), json.dumps(row.get("VALIDATION_MESSAGES", row.get("MESSAGES", [])), default=str)) for index, row in enumerate(rows, 1)]
        return executor.executemany(sql, params) if params else 0
    def insert_raw_rows(self, import_id, rows):
        with self._executor().transaction() as tx: return self._insert_raw(tx, import_id, rows)
    def get_raw_rows(self, import_id): return self._query(f"SELECT * FROM {self._table('IMPORT_RAW_ROW', self.schema_raw)} WHERE IMPORT_ID = %s ORDER BY SOURCE_ROW_NUMBER", (import_id,))

    def _insert_production(self, executor, records, import_id):
        rows = records.to_dict("records") if isinstance(records, pd.DataFrame) else list(records)
        columns = ["PRODUCTION_ID", "IMPORT_ID", *PRODUCTION_COLUMNS]
        sql = f"INSERT INTO {self._table('PRODUCTION_RECORD')} ({', '.join(columns)}, CREATED_AT, UPDATED_AT) VALUES ({', '.join(['%s'] * len(columns))}, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())"
        params = []
        for row in rows:
            item = dict(row); item.setdefault("SOURCE_TYPE", "EIMS_IMPORT"); item.setdefault("MATCH_STATUS", "UNMATCHED")
            params.append((item.get("PRODUCTION_ID") or str(uuid.uuid4()), import_id, *(item.get(column) for column in PRODUCTION_COLUMNS)))
        return executor.executemany(sql, params) if params else 0
    def insert_production_records(self, records, import_id):
        with self._executor().transaction() as tx: return self._insert_production(tx, records, import_id)

    def import_production_bundle(self, batch, raw_rows, records, allow_duplicate=False):
        import_id, file_hash = batch.get("IMPORT_ID") or str(uuid.uuid4()), batch.get("FILE_HASH")
        with self._executor().transaction() as tx:
            if file_hash and not allow_duplicate:
                existing = tx.query(f"SELECT IMPORT_ID FROM {self._table('IMPORT_BATCH', self.schema_raw)} WHERE FILE_HASH = %s LIMIT 1", (file_hash,))
                if not existing.empty: raise RepositoryError("This exact file has already been imported.")
            self._insert_batch(tx, import_id, batch)
            self._insert_raw(tx, import_id, raw_rows)
            count = self._insert_production(tx, records, import_id)
            tx.execute(f"UPDATE {self._table('IMPORT_BATCH', self.schema_raw)} SET ROW_COUNT = %s, STATUS = %s, UPDATED_AT = CURRENT_TIMESTAMP() WHERE IMPORT_ID = %s", (count, "Committed", import_id))
        return import_id, count

    def import_flock_quota_batch(self, batch, quota_records, flock_records):
        """Recheck and commit one mixed Flock and Quota batch transactionally."""
        import_id = batch.get("IMPORT_ID") or str(uuid.uuid4())
        file_hash = batch.get("FILE_HASH")
        created_count = 0
        updated_count = 0
        with self._executor().transaction() as tx:
            if file_hash:
                existing = tx.query(
                    f"SELECT IMPORT_ID FROM {self._table('IMPORT_BATCH', self.schema_raw)} WHERE FILE_HASH = %s LIMIT 1",
                    (file_hash,),
                )
                if not existing.empty:
                    raise RepositoryError("This exact file has already been imported.")

            quota_ids: dict[str, str] = {}
            for source in quota_records:
                record = dict(source)
                action = record.pop("ACTION")
                registration = str(record.get("REGISTRATION_NUMBER") or "").strip()
                if action not in {"CREATE", "UPDATE"}:
                    raise RepositoryError("Unsupported quota import action.")
                if not registration.startswith("DEV_DEMO_"):
                    raise RepositoryError("Quota import is restricted to DEV_DEMO_ identifiers.")
                matches = tx.query(
                    f"SELECT * FROM {self._table('QUOTA_REGISTRATION')} WHERE UPPER(TRIM(REGISTRATION_NUMBER)) = UPPER(TRIM(%s))",
                    (registration,),
                )
                if action == "CREATE" and not matches.empty:
                    raise RepositoryError("Registration Number already exists and cannot be created.")
                if action == "UPDATE" and len(matches) != 1:
                    raise RepositoryError("Registration Number does not resolve to one existing record.")
                if action == "UPDATE" and str(matches.iloc[0]["QUOTA_ID"]) != str(record.get("QUOTA_ID")):
                    raise RepositoryError("Quota target changed after validation.")
                account = tx.query(
                    f"SELECT ACCOUNT_ID FROM {self._table('ACCOUNT')} WHERE ACCOUNT_ID = %s",
                    (record.get("ACCOUNT_ID"),),
                )
                if account.empty:
                    raise RepositoryError("Account no longer exists.")
                quota_id = self._upsert_with_executor(tx, "QUOTA_REGISTRATION", record)
                quota_ids[registration.casefold()] = quota_id
                created_count += int(action == "CREATE")
                updated_count += int(action == "UPDATE")

            for source in flock_records:
                record = dict(source)
                action = record.pop("ACTION")
                quota_registration = str(record.pop("QUOTA_REGISTRATION_NUMBER", "") or "").strip()
                if quota_registration and quota_registration.casefold() in quota_ids:
                    record["QUOTA_ID"] = quota_ids[quota_registration.casefold()]
                record = normalize_flock_dates(record)
                flock_number = str(record.get("FLOCK_NUMBER") or "").strip()
                if action not in {"CREATE", "UPDATE"}:
                    raise RepositoryError("Unsupported flock import action.")
                if not flock_number.startswith("DEV_DEMO_"):
                    raise RepositoryError("Flock import is restricted to DEV_DEMO_ identifiers.")
                matches = tx.query(
                    f"SELECT FLOCK_ID FROM {self._table('FLOCK')} WHERE UPPER(TRIM(FLOCK_NUMBER)) = UPPER(TRIM(%s))",
                    (flock_number,),
                )
                if action == "CREATE" and not matches.empty:
                    raise RepositoryError("Flock Number already exists and cannot be created.")
                if action == "UPDATE" and len(matches) != 1:
                    raise RepositoryError("Flock Number does not resolve to one existing record.")
                if action == "UPDATE" and str(matches.iloc[0]["FLOCK_ID"]) != str(record.get("FLOCK_ID")):
                    raise RepositoryError("Flock target changed after validation.")
                if record.get("HATCH_DATE") is None:
                    raise RepositoryError("Hatch Date is required.")
                permit = str(record.get("PERMIT_NUMBER") or "").strip()
                permit_matches = tx.query(
                    f"SELECT FLOCK_ID FROM {self._table('FLOCK')} WHERE UPPER(TRIM(PERMIT_NUMBER)) = UPPER(TRIM(%s))",
                    (permit,),
                )
                if record.get("FLOCK_ID") and not permit_matches.empty:
                    permit_matches = permit_matches[permit_matches["FLOCK_ID"].astype(str) != str(record["FLOCK_ID"])]
                if not permit_matches.empty:
                    raise RepositoryError("Permit Number is already used by another Flock.")
                facility = tx.query(
                    f"SELECT ACCOUNT_ID FROM {self._table('FACILITY')} WHERE FACILITY_ID = %s",
                    (record.get("FACILITY_ID"),),
                )
                if facility.empty or str(facility.iloc[0]["ACCOUNT_ID"]) != str(record.get("ACCOUNT_ID")):
                    raise RepositoryError("Facility no longer belongs to the selected Account.")
                detail_id = record.get("FACILITY_DETAIL_ID")
                if detail_id:
                    detail = tx.query(
                        f"SELECT FACILITY_ID FROM {self._table('FACILITY_DETAIL')} WHERE FACILITY_DETAIL_ID = %s",
                        (detail_id,),
                    )
                    if detail.empty or str(detail.iloc[0]["FACILITY_ID"]) != str(record.get("FACILITY_ID")):
                        raise RepositoryError("Facility Detail no longer belongs to the selected Facility.")
                quota_id = record.get("QUOTA_ID")
                if quota_id:
                    quota = tx.query(
                        f"SELECT ACCOUNT_ID FROM {self._table('QUOTA_REGISTRATION')} WHERE QUOTA_ID = %s",
                        (quota_id,),
                    )
                    if quota.empty or str(quota.iloc[0]["ACCOUNT_ID"]) != str(record.get("ACCOUNT_ID")):
                        raise RepositoryError("Quota Registration no longer belongs to the selected Account.")
                self._upsert_with_executor(tx, "FLOCK", record)
                created_count += int(action == "CREATE")
                updated_count += int(action == "UPDATE")

            total_count = len(quota_records) + len(flock_records)
            self._insert_batch(
                tx,
                import_id,
                {
                    **batch,
                    "SOURCE": "Flock & Quota Import",
                    "WORKSHEET_NAME": "Batch Import",
                    "SOURCE_RECORD_COUNT": total_count,
                    "ROW_COUNT": total_count,
                    "ERROR_COUNT": int(batch.get("ERROR_COUNT", 0)),
                    "STATUS": "Committed",
                },
            )
        return {
            "import_id": import_id,
            "batch_id": batch.get("BATCH_ID"),
            "filename": batch.get("FILENAME"),
            "file_hash": file_hash,
            "total_count": len(quota_records) + len(flock_records),
            "quota_count": len(quota_records),
            "flock_count": len(flock_records),
            "created_count": created_count,
            "updated_count": updated_count,
            "rejected_count": int(batch.get("ERROR_COUNT", 0)),
            "status": "Committed",
        }

    def get_production_records(self, reporting_year=None, reporting_week=None, grader_number=None, barn_identity=None, egg_colour=None): return self._filtered("VW_PRODUCTION_SUMMARY", (("REPORTING_YEAR", reporting_year), ("REPORTING_WEEK", reporting_week), ("GRADER_NUMBER", grader_number), ("BARN_IDENTITY", barn_identity), ("EGG_COLOUR", egg_colour)), self.schema_reporting)
    def get_production_summary_metrics(self):
        row = self._query(f"SELECT COUNT(*) PRODUCTION_RECORD_COUNT, COALESCE(SUM(TOTAL_RECEIVED),0) TOTAL_RECEIVED, COALESCE(SUM(TOTAL_ACCEPTED),0) TOTAL_ACCEPTED, COALESCE(SUM(REJECTED),0) TOTAL_REJECTED, COALESCE(SUM(LOSS),0) TOTAL_LOSS FROM {self._table('VW_PRODUCTION_SUMMARY', self.schema_reporting)}").iloc[0]
        counts = {name: int(self._query(f"SELECT COUNT(*) RECORD_COUNT FROM {self._table(table, schema)}").iloc[0]["RECORD_COUNT"] or 0) for name, schema, table in (("import_count", self.schema_raw, "IMPORT_BATCH"), ("account_count", self.schema_core, "ACCOUNT"), ("flock_count", self.schema_core, "FLOCK"))}
        return {**counts, "production_record_count": int(row["PRODUCTION_RECORD_COUNT"] or 0), "total_received": float(row["TOTAL_RECEIVED"] or 0), "total_accepted": float(row["TOTAL_ACCEPTED"] or 0), "total_rejected": float(row["TOTAL_REJECTED"] or 0), "total_loss": float(row["TOTAL_LOSS"] or 0)}
    def get_dashboard_metrics(self):
        production = self.get_production_summary_metrics()
        count = lambda table, condition, params: len(self._query(f"SELECT 1 FROM {self._table(table)} WHERE {condition}", params))
        return {"active_account_count": count("ACCOUNT", "STATUS = %s", ("Active",)), "active_facility_count": count("FACILITY", "STATUS = %s", ("Active",)), "active_flock_count": count("FLOCK", "STATUS = %s", ("Active",)), "active_quota_count": len(self.get_quota_registrations(active_only=True)), "recent_quota_transaction_count": len(self.get_quota_transactions()), "pending_salmonella_count": len(self.get_salmonella_tests(test_result="Pending")), "attention_salmonella_count": count("SALMONELLA_TEST", "TEST_RESULT IN (%s, %s)", ("Positive", "Inconclusive")), "production_record_count": production["production_record_count"]}
