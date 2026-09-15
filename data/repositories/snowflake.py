"""Snowflake repository backed only by the shared SQL executor contract."""

from __future__ import annotations

import json
import io
import os
import re
import datetime as dt
from decimal import Decimal, InvalidOperation
from typing import Optional
import uuid

import pandas as pd

from data.connection import ConnectorExecutor, SqlExecutor, create_executor
from data.repositories.base import BaseRepository, ConcurrencyError, RepositoryError
from data.validation import validate_farm_location, validate_flock, validate_quota_registration, validate_quota_transaction, validate_salmonella_test


MODEL = {
    "ACCOUNT": ("ACCOUNT_ID", "REGISTRATION_NUMBER ORGANIZATION_NAME ADDRESS_LINE1 ADDRESS_LINE2 ADDRESS_LINE3 CITY PROVINCE POSTAL_CODE COUNTRY_REGION LATITUDE LONGITUDE CONTACT_NAME CONTACT_PHONE CONTACT_EMAIL FAX WEBSITE LICENCE_NUMBER PARENT_ACCOUNT_ID GRADING_STATION_ACCOUNT_ID PULLET_GROWER_ACCOUNT_ID PROVINCE_OF_REGISTRATION SPENT_FOWL_PLANS DEFAULT_ON_REPORTS NO_SVG DESCRIPTION PRODUCER_ROLE BREEDER_ROLE HATCHERY_ROLE PULLET_GROWER_ROLE GRADER_ROLE PROCESSOR_BREAKER_ROLE DISPOSAL_PLANT_ROLE UNREGULATED_ROLE PROV_BOARD_EFC_ROLE GOVERNMENT_ROLE VENDOR_ROLE RESEARCH_EXEMPT_ROLE SHIPPER_ROLE OTHER_ROLE STATUS"),
    "FARM_LOCATION": ("FARM_LOCATION_ID", "ACCOUNT_ID LOCATION_NAME ADDRESS_1 ADDRESS_2 CITY PROVINCE POSTAL_CODE PHONE STATUS"),
    "FACILITY": ("FACILITY_ID", "ACCOUNT_ID FACILITY_NAME FACILITY_TYPE STATUS ACTIVATION_DATE CONSTRUCTION_DATE CLOSURE_DATE DESTRUCTION_DATE INACTIVE_DATE"),
    "FACILITY_DETAIL": ("FACILITY_DETAIL_ID", "FACILITY_ID DETAIL_NAME DETAIL_TYPE STATUS COMMENTS"),
    "FLOCK": ("FLOCK_ID", "FLOCK_NUMBER ACCOUNT_ID FACILITY_ID FACILITY_DETAIL_ID QUOTA_ID FLOCK_QUOTA_TYPE STATUS CREATE_DELIVERY_TRANSACTION PERMIT_NUMBER PERMIT_DATE HATCH_DATE DATE_ORDERED BIRD_COUNT EGG_COLOUR BIRD_STRAIN PLACEMENT_DATE EST_DISPOSAL DISPOSAL_DATE BIRDS_DISPOSED BREEDER HATCHERY PULLET_GROWER DISPOSAL_PLANT DISPOSAL_METHOD COMMENTS"),
    "FLOCK_TRANSACTION": ("FLOCK_TRANSACTION_ID", "FLOCK_ID TRANSACTION_TYPE QUANTITY TRANSACTION_DATE NOTES"),
    "QUOTA_REGISTRATION": ("QUOTA_ID", "REGISTRATION_NUMBER ACCOUNT_ID QUOTA_NAME QUOTA_TYPE STATUS EFFECTIVE_DATE END_DATE COMMENTS"),
    "QUOTA_TRANSACTION": ("QUOTA_TRANSACTION_ID", "TRANSACTION_TYPE QUOTA_ID EFFECTIVE_DATE END_DATE QUOTA_COUNT OWNER_ACCOUNT_ID RELATED_ACCOUNT_ID RELATED_QUOTA_ID RELATED_TRANSACTION_ID PRICE QUOTA_LEASE_TYPE COMMENTS"),
    "SALMONELLA_TEST": ("SALMONELLA_TEST_ID", "FLOCK_ID ACCOUNT_ID PERMIT_NUMBER TESTING_DATE INSPECTOR NUMBER_OF_SAMPLES TEST_RESULT DATE_RESULT_SENT DATE_RECEIVED CASE_FILE_NUMBER INVOICE_NUMBER INVOICE_DATE COMMENTS"),
}
PRODUCTION_COLUMNS = "PRODUCER_ACCOUNT_ID GRADER_ACCOUNT_ID FACILITY_ID FLOCK_ID GRADER_NAME PRODUCER_NUMBER GRADER_NUMBER BARN_IDENTITY SOURCE_WEEK_CODE REPORTING_YEAR REPORTING_WEEK MARKETING_TYPE HOUSING_SYSTEM EGG_TYPE EGG_COLOUR FLOCK_AGE NET_WEIGHT NET_BOXES NET_PER_BOX JUMBO EXTRA_LARGE LARGE MEDIUM SMALL PEEWEE GRADE_B GRADE_C CRACKS NEST_RUN NEST_RUN_25_PLUS NEST_RUN_24_PLUS NEST_RUN_23_PLUS NEST_RUN_22_PLUS NEST_RUN_21_PLUS NEST_RUN_20_PLUS NEST_RUN_19_PLUS NEST_RUN_18_PLUS NEST_RUN_17_PLUS OTHER_LEVIABLE OTHER_NON_LEVIABLE FARM_GATE_SALES ON_FARM_CONSUMPTION SUBTOTAL REJECTS LEAKERS TOTAL TOTAL_RECEIVED REJECTED LOSS LEGACY_REJECT_LOSS_TOTAL TOTAL_ACCEPTED SOURCE_TYPE MATCH_STATUS SOURCE_ROW_NUMBER MATCH_CONFIRMED_AT MATCH_CONFIRMED_BY".split()
PRODUCTION_INTEGER_COLUMNS = frozenset({
    "REPORTING_YEAR", "REPORTING_WEEK", "FLOCK_AGE", "SOURCE_ROW_NUMBER",
})
PRODUCTION_DECIMAL_COLUMNS = frozenset({
    "NET_WEIGHT", "NET_BOXES", "NET_PER_BOX", "JUMBO", "EXTRA_LARGE",
    "LARGE", "MEDIUM", "SMALL", "PEEWEE", "GRADE_B", "GRADE_C",
    "CRACKS", "NEST_RUN", "NEST_RUN_25_PLUS", "NEST_RUN_24_PLUS",
    "NEST_RUN_23_PLUS", "NEST_RUN_22_PLUS", "NEST_RUN_21_PLUS",
    "NEST_RUN_20_PLUS", "NEST_RUN_19_PLUS", "NEST_RUN_18_PLUS",
    "NEST_RUN_17_PLUS", "OTHER_LEVIABLE", "OTHER_NON_LEVIABLE",
    "FARM_GATE_SALES", "ON_FARM_CONSUMPTION", "SUBTOTAL", "REJECTS",
    "LEAKERS", "TOTAL", "TOTAL_RECEIVED", "REJECTED", "LOSS",
    "LEGACY_REJECT_LOSS_TOTAL", "TOTAL_ACCEPTED",
})
IMPORT_BATCH_COLUMNS = "FILENAME SOURCE FILE_HASH FILE_SIZE_BYTES WORKSHEET_NAME REPORTING_YEAR REPORTING_WEEK SOURCE_RECORD_COUNT ROW_COUNT ERROR_COUNT STATUS NOTES".split()
RAW_ROW_COLUMNS = "RAW_ROW_ID IMPORT_ID SOURCE_ROW_NUMBER RAW_DATA VALIDATION_STATUS MATCH_STATUS VALIDATION_MESSAGES".split()
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
UTC_NOW_NTZ = "CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ"
DATE_FIELDS = {
    "FACILITY": frozenset({"ACTIVATION_DATE", "CONSTRUCTION_DATE", "CLOSURE_DATE", "DESTRUCTION_DATE", "INACTIVE_DATE"}),
    "FLOCK": frozenset({"PERMIT_DATE", "HATCH_DATE", "DATE_ORDERED", "PLACEMENT_DATE", "EST_DISPOSAL", "DISPOSAL_DATE"}),
    "FLOCK_TRANSACTION": frozenset({"TRANSACTION_DATE"}),
    "QUOTA_REGISTRATION": frozenset({"EFFECTIVE_DATE", "END_DATE"}),
    "QUOTA_TRANSACTION": frozenset({"EFFECTIVE_DATE", "END_DATE"}),
    "SALMONELLA_TEST": frozenset({"TESTING_DATE", "DATE_RESULT_SENT", "DATE_RECEIVED", "INVOICE_DATE"}),
}
_NULL_DATE_TEXT = frozenset({"", "none", "nat", "null"})
_NULL_NUMERIC_TEXT = frozenset({"", "none", "nan", "nat", "null"})
_NUMERIC_TEXT = re.compile(
    r"^[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$"
)


def normalize_date_bind(value, field: str = "Date") -> dt.date | None:
    """Return a Snowflake DATE-compatible value without stringifying nulls."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.lower() in _NULL_DATE_TEXT:
            return None
        try:
            # Existing repository callers may supply ISO strings. Convert them
            # to a typed date so Connector and Snowpark bind the same value.
            return dt.date.fromisoformat(text)
        except ValueError as exc:
            raise RepositoryError(f"{field.replace('_', ' ').title()} must be a valid ISO date.") from exc
    raise RepositoryError(f"{field.replace('_', ' ').title()} must be a date value.")


def _is_missing_bind(value) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def normalize_numeric_bind(
    value,
    field: str,
    source_row: int,
    *,
    integer: bool,
) -> int | Decimal | None:
    """Return a typed Snowflake NUMBER bind or a safe field/row error."""
    if _is_missing_bind(value):
        return None
    if isinstance(value, bool):
        raise RepositoryError(f"{field} has an invalid numeric value at source row {source_row}.")
    if isinstance(value, str):
        text = value.strip()
        if text.casefold() in _NULL_NUMERIC_TEXT:
            return None
        if not _NUMERIC_TEXT.fullmatch(text):
            raise RepositoryError(f"{field} has an invalid numeric value at source row {source_row}.")
        value = text.replace(",", "")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise RepositoryError(
            f"{field} has an invalid numeric value at source row {source_row}."
        ) from exc
    if not number.is_finite():
        if number.is_nan():
            return None
        raise RepositoryError(f"{field} has an invalid numeric value at source row {source_row}.")
    if integer:
        if number != number.to_integral_value():
            raise RepositoryError(f"{field} must be a whole number at source row {source_row}.")
        return int(number)
    return number


def _source_row_number(item: dict, ordinal: int) -> int:
    value = item.get("SOURCE_ROW_NUMBER")
    try:
        if _is_missing_bind(value):
            return ordinal
        number = Decimal(str(value).replace(",", ""))
        return int(number) if number == number.to_integral_value() else ordinal
    except (InvalidOperation, TypeError, ValueError):
        return ordinal


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
        if table not in MODEL and table not in {"SALMONELLA_TEST_SAMPLE", "IMPORT_BATCH", "IMPORT_RAW_ROW", "PRODUCTION_RECORD", "VW_PRODUCTION_SUMMARY", "MIGRATION_BATCH", "MIGRATION_FILE", "MIGRATION_RAW_ROW", "MIGRATION_ID_MAP"}:
            raise RepositoryError("Unsupported Snowflake table identifier.")
        return f"{self.database}.{schema or self.schema_core}.{table}"

    def _query(self, sql, params=None):
        return self._executor().query(sql, params)

    def _one(self, table, column, value, schema=None):
        frame = self._query(f"SELECT * FROM {self._table(table, schema)} WHERE {column} = %s", (value,))
        return frame.iloc[0].to_dict() if not frame.empty else None

    @staticmethod
    def _normalize_date_fields(table: str, record: dict) -> dict:
        normalized = dict(record)
        for field in DATE_FIELDS.get(table, ()):
            if field in normalized:
                normalized[field] = normalize_date_bind(normalized[field], field)
        return normalized

    def _upsert(self, table: str, record: dict) -> str:
        record = self._normalize_date_fields(table, record)
        key, allowed_text = MODEL[table]
        expected = record.get("EXPECTED_UPDATED_AT")
        supplied_id = record.get(key)
        entity_id = supplied_id or str(uuid.uuid4())
        allowed = allowed_text.split()
        values = {name: record[name] for name in allowed if name in record}
        if not values:
            raise RepositoryError(f"No writable fields supplied for {table}.")
        lock = " AND UPDATED_AT = %s" if expected is not None else ""
        update_sql = (
            f"UPDATE {self._table(table)} SET "
            + ", ".join(f"{name} = %s" for name in values)
            + f", UPDATED_AT = {UTC_NOW_NTZ} WHERE {key} = %s{lock}"
        )
        update_params = [*values.values(), entity_id]
        if expected is not None:
            update_params.append(expected)
        columns = [key, *values]
        insert_sql = (
            f"INSERT INTO {self._table(table)} ({', '.join(columns)}, CREATED_AT, UPDATED_AT) "
            f"VALUES ({', '.join(['%s'] * len(columns))}, {UTC_NOW_NTZ}, {UTC_NOW_NTZ})"
        )
        with self._executor().transaction() as tx:
            existing = pd.DataFrame()
            if supplied_id is not None:
                existing = tx.query(
                    f"SELECT CREATED_AT, UPDATED_AT FROM {self._table(table)} WHERE {key} = %s",
                    (entity_id,),
                )
            if existing.empty:
                if expected is not None:
                    raise ConcurrencyError("This record no longer exists. Return to the list and reload.")
                inserted = tx.execute(insert_sql, (entity_id, *values.values()))
                if inserted == 0:
                    raise RepositoryError(f"Snowflake did not insert the new {table.replace('_', ' ').title()} record.")
                if inserted < 0:
                    confirmed = tx.query(
                        f"SELECT CREATED_AT, UPDATED_AT FROM {self._table(table)} WHERE {key} = %s",
                        (entity_id,),
                    )
                    if confirmed.empty:
                        raise RepositoryError(f"Snowflake could not confirm the new {table.replace('_', ' ').title()} record.")
                return entity_id

            affected = tx.execute(update_sql, tuple(update_params))
            if expected is not None and affected < 0:
                raise RepositoryError(
                    "The active Snowflake runtime did not report an affected-row count; "
                    "the protected update was not accepted."
                )
            if affected == 0:
                if expected is not None:
                    raise ConcurrencyError("This record changed after it was opened. Reload it before saving again.")
                raise RepositoryError(f"Snowflake did not update the {table.replace('_', ' ').title()} record.")
        return entity_id

    def _delete(self, table, key, entity_id, references=()):
        with self._executor().transaction() as tx:
            for ref_table, ref_col in references:
                schema = self.schema_core
                existing = tx.query(f"SELECT 1 AS FOUND FROM {self._table(ref_table, schema)} WHERE {ref_col} = %s LIMIT 1", (entity_id,))
                if not existing.empty:
                    raise RepositoryError(f"This {table.replace('_', ' ').title()} still has related records and cannot be deleted.")
            affected = tx.execute(f"DELETE FROM {self._table(table)} WHERE {key} = %s", (entity_id,))
            if affected >= 0:
                return affected > 0
            remaining = tx.query(
                f"SELECT 1 AS FOUND FROM {self._table(table)} WHERE {key} = %s LIMIT 1",
                (entity_id,),
            )
            return remaining.empty

    def _filtered(self, table, filters, schema=None):
        conditions, params = [], []
        for column, value in filters:
            if value is not None and value != "":
                if isinstance(value, (tuple, list, set, frozenset)):
                    values = tuple(value)
                    if not values:
                        conditions.append("1 = 0")
                    else:
                        conditions.append(f"{column} IN ({', '.join(['%s'] * len(values))})")
                        params.extend(values)
                else:
                    conditions.append(f"{column} = %s")
                    params.append(value)
        sql = f"SELECT * FROM {self._table(table, schema)}"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        return self._query(sql, tuple(params) if params else None)

    def get_accounts(self, statuses=None, role_field=None, keyword=None):
        from data.constants import ACCOUNT_ROLE_FIELDS
        conditions, params = [], []
        if statuses is not None:
            conditions.append(f"STATUS IN ({', '.join(['%s'] * len(statuses))})"); params.extend(statuses)
        if role_field:
            if role_field not in {field for field, _ in ACCOUNT_ROLE_FIELDS}:
                raise RepositoryError("Unknown Account role view.")
            conditions.append(f"COALESCE({role_field}, FALSE) = TRUE")
        if keyword:
            conditions.append("(ORGANIZATION_NAME ILIKE %s OR REGISTRATION_NUMBER ILIKE %s OR CITY ILIKE %s OR CONTACT_PHONE ILIKE %s OR CONTACT_EMAIL ILIKE %s)")
            params.extend([f"%{keyword}%"] * 5)
        sql = f"SELECT DISTINCT * FROM {self._table('ACCOUNT')}"
        if conditions: sql += " WHERE " + " AND ".join(conditions)
        return self._query(sql, tuple(params) if params else None)
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
    def delete_account(self, value): return self._delete("ACCOUNT", "ACCOUNT_ID", value, (("ACCOUNT", "PARENT_ACCOUNT_ID"), ("ACCOUNT", "GRADING_STATION_ACCOUNT_ID"), ("ACCOUNT", "PULLET_GROWER_ACCOUNT_ID"), ("FARM_LOCATION", "ACCOUNT_ID"), ("FACILITY", "ACCOUNT_ID"), ("FLOCK", "ACCOUNT_ID"), ("QUOTA_REGISTRATION", "ACCOUNT_ID"), ("SALMONELLA_TEST", "ACCOUNT_ID")))

    def get_farm_locations(self, farm_location_id=None, account_id=None, statuses=None, keyword=None):
        conditions, params = [], []
        if farm_location_id: conditions.append("fl.FARM_LOCATION_ID = %s"); params.append(farm_location_id)
        if account_id: conditions.append("fl.ACCOUNT_ID = %s"); params.append(account_id)
        if statuses is not None:
            conditions.append(f"fl.STATUS IN ({', '.join(['%s'] * len(statuses))})"); params.extend(statuses)
        if keyword:
            conditions.append("(fl.LOCATION_NAME ILIKE %s OR a.ORGANIZATION_NAME ILIKE %s OR fl.CITY ILIKE %s OR fl.POSTAL_CODE ILIKE %s OR fl.PHONE ILIKE %s)")
            params.extend([f"%{keyword}%"] * 5)
        sql = f"SELECT DISTINCT fl.* FROM {self._table('FARM_LOCATION')} fl JOIN {self._table('ACCOUNT')} a ON a.ACCOUNT_ID = fl.ACCOUNT_ID"
        if conditions: sql += " WHERE " + " AND ".join(conditions)
        return self._query(sql, tuple(params) if params else None)
    def get_farm_location(self, value): return self._one("FARM_LOCATION", "FARM_LOCATION_ID", value)
    def upsert_farm_location(self, record):
        errors = validate_farm_location(self, record)
        if errors: raise RepositoryError(" ".join(errors))
        return self._upsert("FARM_LOCATION", record)
    def delete_farm_location(self, value): return self._delete("FARM_LOCATION", "FARM_LOCATION_ID", value)

    def get_facilities(self, account_id=None, statuses=None): return self._filtered("FACILITY", (("ACCOUNT_ID", account_id), ("STATUS", statuses)))
    def upsert_facility(self, record): return self._upsert("FACILITY", record)
    def delete_facility(self, value): return self._delete("FACILITY", "FACILITY_ID", value, (("FACILITY_DETAIL", "FACILITY_ID"), ("FLOCK", "FACILITY_ID")))
    def get_facility_details(self, facility_id=None, account_id=None, statuses=None):
        if account_id:
            conditions, params = ["f.ACCOUNT_ID = %s"], [account_id]
            if facility_id: conditions.append("fd.FACILITY_ID = %s"); params.append(facility_id)
            if statuses is not None: conditions.append(f"fd.STATUS IN ({', '.join(['%s'] * len(statuses))})"); params.extend(statuses)
            return self._query(f"SELECT DISTINCT fd.* FROM {self._table('FACILITY_DETAIL')} fd JOIN {self._table('FACILITY')} f ON f.FACILITY_ID = fd.FACILITY_ID WHERE " + " AND ".join(conditions), tuple(params))
        return self._filtered("FACILITY_DETAIL", (("FACILITY_ID", facility_id), ("STATUS", statuses)))
    def get_facility_detail(self, value): return self._one("FACILITY_DETAIL", "FACILITY_DETAIL_ID", value)
    def upsert_facility_detail(self, record): return self._upsert("FACILITY_DETAIL", record)
    def delete_facility_detail(self, value): return self._delete("FACILITY_DETAIL", "FACILITY_DETAIL_ID", value, (("FLOCK", "FACILITY_DETAIL_ID"),))

    def get_flocks(self, account_id=None, facility_id=None, facility_detail_id=None, statuses=None): return self._filtered("FLOCK", (("ACCOUNT_ID", account_id), ("FACILITY_ID", facility_id), ("FACILITY_DETAIL_ID", facility_detail_id), ("STATUS", statuses)))
    def get_flock(self, flock_id): return self._one("FLOCK", "FLOCK_ID", flock_id)
    def upsert_flock(self, record):
        record = self._normalize_date_fields("FLOCK", record)
        errors = validate_flock(self, record)
        if errors: raise RepositoryError(" ".join(errors))
        return self._upsert("FLOCK", record)
    def delete_flock(self, value): return self._delete("FLOCK", "FLOCK_ID", value, (("FLOCK_TRANSACTION", "FLOCK_ID"), ("SALMONELLA_TEST", "FLOCK_ID"), ("PRODUCTION_RECORD", "FLOCK_ID")))

    def get_flock_transactions(self, flock_id=None, account_id=None, transaction_type=None, date_from=None, date_to=None):
        join = f" JOIN {self._table('FLOCK')} f ON f.FLOCK_ID = ft.FLOCK_ID" if account_id else ""
        conditions, params = [], []
        for column, operator, value in (("ft.FLOCK_ID", "=", flock_id), ("f.ACCOUNT_ID", "=", account_id), ("ft.TRANSACTION_TYPE", "=", transaction_type), ("ft.TRANSACTION_DATE", ">=", date_from), ("ft.TRANSACTION_DATE", "<=", date_to)):
            if value is not None: conditions.append(f"{column} {operator} %s"); params.append(value)
        sql = f"SELECT DISTINCT ft.* FROM {self._table('FLOCK_TRANSACTION')} ft{join}"
        if conditions: sql += " WHERE " + " AND ".join(conditions)
        return self._query(sql, tuple(params) if params else None)
    def upsert_flock_transaction(self, record):
        record = self._normalize_date_fields("FLOCK_TRANSACTION", record)
        if record.get("TRANSACTION_DATE") is None:
            raise RepositoryError("Transaction Date is required.")
        return self._upsert("FLOCK_TRANSACTION", record)
    def delete_flock_transaction(self, value): return self._delete("FLOCK_TRANSACTION", "FLOCK_TRANSACTION_ID", value)

    def get_quota_registrations(self, account_id=None, status=None, quota_type=None, active_only=False, statuses=None):
        filters = [("ACCOUNT_ID", account_id), ("STATUS", status), ("QUOTA_TYPE", quota_type), ("STATUS", statuses)]
        if not active_only: return self._filtered("QUOTA_REGISTRATION", filters)
        conditions, params = ["STATUS = %s", "(EFFECTIVE_DATE IS NULL OR EFFECTIVE_DATE <= CURRENT_DATE())", "(END_DATE IS NULL OR END_DATE >= CURRENT_DATE())"], ["Active"]
        for column, value in filters:
            if value is not None: conditions.append(f"{column} = %s"); params.append(value)
        return self._query(f"SELECT * FROM {self._table('QUOTA_REGISTRATION')} WHERE " + " AND ".join(conditions), tuple(params))
    def get_quota_registration(self, value): return self._one("QUOTA_REGISTRATION", "QUOTA_ID", value)
    def upsert_quota_registration(self, record):
        record = self._normalize_date_fields("QUOTA_REGISTRATION", record)
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
        record = self._normalize_date_fields("QUOTA_TRANSACTION", record)
        if record.get("EFFECTIVE_DATE") is None:
            raise RepositoryError("Effective Date is required.")
        errors = validate_quota_transaction(self, record)
        if errors: raise RepositoryError(" ".join(errors))
        stored = dict(record); stored["OWNER_ACCOUNT_ID"] = self.get_quota_registration(record["QUOTA_ID"])["ACCOUNT_ID"]
        return self._upsert("QUOTA_TRANSACTION", stored)
    def get_quota_transaction(self, value): return self._one("QUOTA_TRANSACTION", "QUOTA_TRANSACTION_ID", value)
    def get_quota_summary(self, as_of_date, quota_type, account_id=None, status="Active"):
        conditions = ["qr.QUOTA_TYPE = %s", "(qr.EFFECTIVE_DATE IS NULL OR qr.EFFECTIVE_DATE <= %s)", "(qr.END_DATE IS NULL OR qr.END_DATE >= %s)"]
        params = [quota_type, as_of_date, as_of_date]
        if account_id: conditions.append("qr.ACCOUNT_ID = %s"); params.append(account_id)
        if status: conditions.append("qr.STATUS = %s"); params.append(status)
        sql = f"""
WITH ranked_location AS (
  SELECT fl.*, ROW_NUMBER() OVER (
    PARTITION BY fl.ACCOUNT_ID
    ORDER BY IFF(fl.STATUS = 'Active', 0, 1), fl.FARM_LOCATION_ID
  ) AS LOCATION_RANK
  FROM {self._table('FARM_LOCATION')} fl
)
SELECT DISTINCT qr.QUOTA_ID, qr.ACCOUNT_ID,
       a.REGISTRATION_NUMBER, a.ORGANIZATION_NAME AS ACCOUNT_NAME,
       fl.ADDRESS_1 AS ADDRESS, fl.CITY, fl.PROVINCE, fl.POSTAL_CODE,
       COALESCE(fl.PHONE, a.CONTACT_PHONE) AS PHONE, a.FAX,
       a.PRODUCER_ROLE, CAST(NULL AS NUMBER(18,2)) AS ISSUANCE
FROM {self._table('QUOTA_REGISTRATION')} qr
JOIN {self._table('ACCOUNT')} a ON a.ACCOUNT_ID = qr.ACCOUNT_ID
LEFT JOIN ranked_location fl ON fl.ACCOUNT_ID = qr.ACCOUNT_ID AND fl.LOCATION_RANK = 1
WHERE {" AND ".join(conditions)}
ORDER BY a.ORGANIZATION_NAME, qr.REGISTRATION_NUMBER, qr.QUOTA_ID
"""
        return self._query(sql, tuple(params))
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
        record = self._normalize_date_fields("SALMONELLA_TEST", record)
        errors = validate_salmonella_test(self, record)
        if errors: raise RepositoryError(" ".join(errors))
        return self._upsert("SALMONELLA_TEST", record)
    def delete_salmonella_test(self, value): return self._delete("SALMONELLA_TEST", "SALMONELLA_TEST_ID", value, (("SALMONELLA_TEST_SAMPLE", "SALMONELLA_TEST_ID"),))
    def get_salmonella_test_samples(self, test_id=None): return self._filtered("SALMONELLA_TEST_SAMPLE", (("SALMONELLA_TEST_ID", test_id),))

    def _insert_batch(self, executor, import_id, record):
        values = {key: record[key] for key in IMPORT_BATCH_COLUMNS if key in record}; columns = ["IMPORT_ID", *values]
        sql = f"INSERT INTO {self._table('IMPORT_BATCH', self.schema_raw)} ({', '.join(columns)}, UPLOAD_TIMESTAMP, CREATED_AT, UPDATED_AT) VALUES ({', '.join(['%s'] * len(columns))}, {UTC_NOW_NTZ}, {UTC_NOW_NTZ}, {UTC_NOW_NTZ})"
        affected = executor.execute(sql, (import_id, *values.values()))
        if affected == 0:
            raise RepositoryError("Snowflake did not create the Import Batch record.")

    def create_import_batch(self, record):
        import_id = record.get("IMPORT_ID") or str(uuid.uuid4())
        with self._executor().transaction() as tx: self._insert_batch(tx, import_id, record)
        return import_id
    def get_import_batches(self): return self._filtered("IMPORT_BATCH", (), self.schema_raw)
    def find_import_by_hash(self, file_hash): return self._one("IMPORT_BATCH", "FILE_HASH", file_hash, self.schema_raw) if file_hash else None

    def _insert_raw(self, executor, import_id, rows):
        sql = f"INSERT INTO {self._table('IMPORT_RAW_ROW', self.schema_raw)} (RAW_ROW_ID, IMPORT_ID, SOURCE_ROW_NUMBER, RAW_DATA, VALIDATION_STATUS, MATCH_STATUS, VALIDATION_MESSAGES, CREATED_AT, UPDATED_AT) SELECT %s, %s, %s, PARSE_JSON(%s), %s, %s, PARSE_JSON(%s), {UTC_NOW_NTZ}, {UTC_NOW_NTZ}"
        params = [(row.get("RAW_ROW_ID") or str(uuid.uuid4()), import_id, row.get("SOURCE_ROW_NUMBER", index), json.dumps(row.get("RAW_DATA", row.get("ROW_DATA", row)), default=str), row.get("VALIDATION_STATUS", "PENDING"), row.get("MATCH_STATUS", "UNMATCHED"), json.dumps(row.get("VALIDATION_MESSAGES", row.get("MESSAGES", [])), default=str)) for index, row in enumerate(rows, 1)]
        return executor.executemany(sql, params) if params else 0
    def insert_raw_rows(self, import_id, rows):
        with self._executor().transaction() as tx: return self._insert_raw(tx, import_id, rows)
    def get_raw_rows(self, import_id): return self._query(f"SELECT * FROM {self._table('IMPORT_RAW_ROW', self.schema_raw)} WHERE IMPORT_ID = %s ORDER BY SOURCE_ROW_NUMBER", (import_id,))

    def find_migration_by_hash(self, package_hash):
        return self._one("MIGRATION_BATCH", "PACKAGE_HASH", package_hash, self.schema_raw) if package_hash else None

    def get_migration_batches(self):
        return self._query(f"SELECT * FROM {self._table('MIGRATION_BATCH', self.schema_raw)} ORDER BY CREATED_AT DESC")

    def get_migration_raw_rows(self, batch_id):
        return self._query(
            f"SELECT * FROM {self._table('MIGRATION_RAW_ROW', self.schema_raw)} WHERE MIGRATION_BATCH_ID = %s ORDER BY SOURCE_ENTITY, SOURCE_ROW_NUMBER",
            (batch_id,),
        )

    def stage_migration_file(self, batch_id, filename, content):
        from data.migration import migration_stage_path
        path = migration_stage_path(batch_id, filename)
        self._executor().put_stream(io.BytesIO(bytes(content)), path)
        return path

    def prepare_migration_batch(self, batch, files, raw_rows):
        batch_id = batch["MIGRATION_BATCH_ID"]
        with self._executor().transaction() as tx:
            if batch.get("PACKAGE_HASH"):
                existing = tx.query(
                    f"SELECT MIGRATION_BATCH_ID FROM {self._table('MIGRATION_BATCH', self.schema_raw)} WHERE PACKAGE_HASH = %s LIMIT 1",
                    (batch["PACKAGE_HASH"],),
                )
                if not existing.empty:
                    raise RepositoryError("This exact migration package has already been prepared.")
            tx.execute(
                f"INSERT INTO {self._table('MIGRATION_BATCH', self.schema_raw)} "
                f"(MIGRATION_BATCH_ID, PACKAGE_HASH, SCHEMA_VERSION, STATUS, SOURCE_FILE_COUNT, SOURCE_ROW_COUNT, READY_ROW_COUNT, REJECTED_ROW_COUNT, CREATED_BY, CREATED_AT, UPDATED_AT) "
                f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, {UTC_NOW_NTZ}, {UTC_NOW_NTZ})",
                (batch_id, batch.get("PACKAGE_HASH"), batch.get("SCHEMA_VERSION"), batch.get("STATUS", "READY"),
                 len(files), len(raw_rows), sum(r.get("VALIDATION_STATUS") == "READY" for r in raw_rows),
                 sum(r.get("VALIDATION_STATUS") == "REJECTED" for r in raw_rows), batch.get("CREATED_BY")),
            )
            file_sql = (
                f"INSERT INTO {self._table('MIGRATION_FILE', self.schema_raw)} "
                f"(MIGRATION_FILE_ID, MIGRATION_BATCH_ID, SOURCE_FILENAME, SOURCE_ENTITY, FILE_HASH, FILE_SIZE_BYTES, SOURCE_ROW_COUNT, STAGE_PATH, CREATED_AT) "
                f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, {UTC_NOW_NTZ})"
            )
            tx.executemany(file_sql, [(
                str(uuid.uuid4()), batch_id, row["SOURCE_FILENAME"], row["SOURCE_ENTITY"], row["FILE_HASH"],
                row.get("FILE_SIZE_BYTES"), row.get("SOURCE_ROW_COUNT"), row.get("STAGE_PATH"),
            ) for row in files])
            raw_sql = (
                f"INSERT INTO {self._table('MIGRATION_RAW_ROW', self.schema_raw)} "
                f"(MIGRATION_RAW_ROW_ID, MIGRATION_BATCH_ID, SOURCE_FILENAME, SOURCE_ENTITY, SOURCE_ROW_NUMBER, SOURCE_ID, TARGET_ID, RAW_DATA, NORMALIZED_DATA, VALIDATION_STATUS, MATCH_STATUS, VALIDATION_MESSAGES, CREATED_AT, UPDATED_AT) "
                f"SELECT %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s), PARSE_JSON(%s), %s, %s, PARSE_JSON(%s), {UTC_NOW_NTZ}, {UTC_NOW_NTZ}"
            )
            tx.executemany(raw_sql, [(
                row["MIGRATION_RAW_ROW_ID"], batch_id, row["SOURCE_FILENAME"], row["SOURCE_ENTITY"],
                row["SOURCE_ROW_NUMBER"], row.get("SOURCE_ID"), row.get("TARGET_ID"),
                json.dumps(row.get("RAW_DATA"), default=str), json.dumps(row.get("NORMALIZED_DATA"), default=str),
                row["VALIDATION_STATUS"], row.get("MATCH_STATUS"), json.dumps(row.get("VALIDATION_MESSAGES", []), default=str),
            ) for row in raw_rows])
            map_sql = (
                f"INSERT INTO {self._table('MIGRATION_ID_MAP', self.schema_raw)} "
                f"(MIGRATION_ID_MAP_ID, MIGRATION_BATCH_ID, SOURCE_ENTITY, SOURCE_ID, TARGET_ID, STATUS, CREATED_AT, UPDATED_AT) "
                f"VALUES (%s, %s, %s, %s, %s, %s, {UTC_NOW_NTZ}, {UTC_NOW_NTZ})"
            )
            ready = [row for row in raw_rows if row["VALIDATION_STATUS"] == "READY" and row.get("TARGET_ID")]
            tx.executemany(map_sql, [(str(uuid.uuid4()), batch_id, row["SOURCE_ENTITY"], row.get("SOURCE_ID"), row["TARGET_ID"], "READY") for row in ready])
        return batch_id

    @staticmethod
    def _variant_dict(value):
        if isinstance(value, dict): return dict(value)
        if value is None: return {}
        return json.loads(value) if isinstance(value, str) else dict(value)

    def _insert_migration_core(self, tx, table, records):
        key, allowed_text = MODEL[table]
        allowed = allowed_text.split()
        normalized = [self._normalize_date_fields(table, self._variant_dict(record)) for record in records]
        if not normalized: return 0
        columns = [key, *allowed]
        sql = (
            f"INSERT INTO {self._table(table)} ({', '.join(columns)}, CREATED_AT, UPDATED_AT) "
            f"SELECT {', '.join(['%s'] * len(columns))}, {UTC_NOW_NTZ}, {UTC_NOW_NTZ} "
            f"WHERE NOT EXISTS (SELECT 1 FROM {self._table(table)} WHERE {key} = %s)"
        )
        params = [tuple([row.get(key), *[row.get(column) for column in allowed], row.get(key)]) for row in normalized]
        return tx.executemany(sql, params)

    def commit_migration_batch(self, batch_id):
        from data.migration import load_mapping_for_version
        batch = self._one("MIGRATION_BATCH", "MIGRATION_BATCH_ID", batch_id, self.schema_raw)
        if not batch: raise RepositoryError("Migration batch was not found.")
        if str(batch.get("STATUS", "")).upper() == "COMMITTED":
            return {"batch_id": batch_id, "counts": {}, "idempotent": True}
        try:
            counts = {}
            with self._executor().transaction() as tx:
                rows = tx.query(
                    f"SELECT SOURCE_ENTITY, NORMALIZED_DATA FROM {self._table('MIGRATION_RAW_ROW', self.schema_raw)} WHERE MIGRATION_BATCH_ID = %s AND VALIDATION_STATUS = %s ORDER BY SOURCE_ENTITY, SOURCE_ROW_NUMBER",
                    (batch_id, "READY"),
                )
                for entity in load_mapping_for_version(batch.get("SCHEMA_VERSION"))["entity_order"]:
                    records = [row["NORMALIZED_DATA"] for row in rows.to_dict("records") if row["SOURCE_ENTITY"] == entity]
                    if entity == "PRODUCTION_RECORD":
                        existing_batch = tx.query(f"SELECT IMPORT_ID FROM {self._table('IMPORT_BATCH', self.schema_raw)} WHERE IMPORT_ID = %s", (batch_id,))
                        if existing_batch.empty:
                            self._insert_batch(tx, batch_id, {"FILENAME": "Synthetic EIMS migration", "SOURCE": "EIMS_MIGRATION", "STATUS": "Validated", "SOURCE_RECORD_COUNT": len(records)})
                        counts[entity] = self._insert_production(tx, [self._variant_dict(record) for record in records], batch_id)
                    else:
                        counts[entity] = self._insert_migration_core(tx, entity, records)
                tx.execute(f"UPDATE {self._table('MIGRATION_ID_MAP', self.schema_raw)} SET STATUS = %s, UPDATED_AT = {UTC_NOW_NTZ} WHERE MIGRATION_BATCH_ID = %s", ("COMMITTED", batch_id))
                tx.execute(f"UPDATE {self._table('MIGRATION_BATCH', self.schema_raw)} SET STATUS = %s, COMMITTED_AT = {UTC_NOW_NTZ}, UPDATED_AT = {UTC_NOW_NTZ} WHERE MIGRATION_BATCH_ID = %s", ("COMMITTED", batch_id))
            return {"batch_id": batch_id, "counts": counts, "idempotent": False}
        except Exception:
            with self._executor().transaction() as tx:
                tx.execute(f"UPDATE {self._table('MIGRATION_BATCH', self.schema_raw)} SET STATUS = %s, UPDATED_AT = {UTC_NOW_NTZ} WHERE MIGRATION_BATCH_ID = %s", ("FAILED", batch_id))
            raise

    def cleanup_synthetic_migration(self, batch_id):
        if not str(batch_id).startswith("DEV_MIGRATION_"):
            raise RepositoryError("Cleanup is restricted to DEV_MIGRATION_ batches.")
        result = self._query(
            f"CALL {self.database}.{self.schema_raw}.CLEANUP_SYNTHETIC_MIGRATION(%s)",
            (batch_id,),
        )
        if result.empty or str(result.iloc[0, 0]).upper() != "CLEANED":
            raise RepositoryError("Snowflake did not confirm the selected synthetic migration cleanup.")
        from data.migration import migration_stage_prefix
        self._executor().execute(f"REMOVE {migration_stage_prefix(batch_id)}")
        return True

    def _insert_production(self, executor, records, import_id):
        rows = records.to_dict("records") if isinstance(records, pd.DataFrame) else list(records)
        columns = ["PRODUCTION_ID", "IMPORT_ID", *PRODUCTION_COLUMNS]
        sql = f"INSERT INTO {self._table('PRODUCTION_RECORD')} ({', '.join(columns)}, CREATED_AT, UPDATED_AT) VALUES ({', '.join(['%s'] * len(columns))}, {UTC_NOW_NTZ}, {UTC_NOW_NTZ})"
        params = []
        for ordinal, row in enumerate(rows, 1):
            item = dict(row); item.setdefault("SOURCE_TYPE", "EIMS_IMPORT"); item.setdefault("MATCH_STATUS", "UNMATCHED")
            source_row = _source_row_number(item, ordinal)
            bound_values = []
            for column in PRODUCTION_COLUMNS:
                value = item.get(column)
                if column in PRODUCTION_INTEGER_COLUMNS:
                    value = normalize_numeric_bind(value, column, source_row, integer=True)
                elif column in PRODUCTION_DECIMAL_COLUMNS:
                    value = normalize_numeric_bind(value, column, source_row, integer=False)
                elif _is_missing_bind(value):
                    value = None
                bound_values.append(value)
            production_id = item.get("PRODUCTION_ID")
            if _is_missing_bind(production_id) or not str(production_id).strip():
                production_id = str(uuid.uuid4())
            params.append((production_id, import_id, *bound_values))
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
            updated = tx.execute(f"UPDATE {self._table('IMPORT_BATCH', self.schema_raw)} SET ROW_COUNT = %s, STATUS = %s, UPDATED_AT = {UTC_NOW_NTZ} WHERE IMPORT_ID = %s", (count, "Committed", import_id))
            if updated == 0:
                raise RepositoryError("Snowflake did not finalize the Import Batch record.")
        return import_id, count

    def get_production_records(self, reporting_year=None, reporting_week=None, grader_number=None, barn_identity=None, egg_colour=None, account_id=None): return self._filtered("VW_PRODUCTION_SUMMARY", (("REPORTING_YEAR", reporting_year), ("REPORTING_WEEK", reporting_week), ("GRADER_NUMBER", grader_number), ("BARN_IDENTITY", barn_identity), ("EGG_COLOUR", egg_colour), ("PRODUCER_ACCOUNT_ID", account_id)), self.schema_reporting)
    def get_production_summary_metrics(self):
        row = self._query(f"SELECT COUNT(*) PRODUCTION_RECORD_COUNT, COALESCE(SUM(TOTAL_RECEIVED),0) TOTAL_RECEIVED, COALESCE(SUM(TOTAL_ACCEPTED),0) TOTAL_ACCEPTED, COALESCE(SUM(REJECTED),0) TOTAL_REJECTED, COALESCE(SUM(LOSS),0) TOTAL_LOSS FROM {self._table('VW_PRODUCTION_SUMMARY', self.schema_reporting)}").iloc[0]
        counts = {name: int(self._query(f"SELECT COUNT(*) RECORD_COUNT FROM {self._table(table, schema)}").iloc[0]["RECORD_COUNT"] or 0) for name, schema, table in (("import_count", self.schema_raw, "IMPORT_BATCH"), ("account_count", self.schema_core, "ACCOUNT"), ("flock_count", self.schema_core, "FLOCK"))}
        return {**counts, "production_record_count": int(row["PRODUCTION_RECORD_COUNT"] or 0), "total_received": float(row["TOTAL_RECEIVED"] or 0), "total_accepted": float(row["TOTAL_ACCEPTED"] or 0), "total_rejected": float(row["TOTAL_REJECTED"] or 0), "total_loss": float(row["TOTAL_LOSS"] or 0)}
    def get_dashboard_metrics(self):
        production = self.get_production_summary_metrics()
        count = lambda table, condition, params: len(self._query(f"SELECT 1 FROM {self._table(table)} WHERE {condition}", params))
        return {"active_account_count": count("ACCOUNT", "STATUS = %s", ("Active",)), "active_facility_count": count("FACILITY", "STATUS = %s", ("Active",)), "active_flock_count": count("FLOCK", "STATUS = %s", ("Active",)), "active_quota_count": len(self.get_quota_registrations(active_only=True)), "recent_quota_transaction_count": len(self.get_quota_transactions()), "pending_salmonella_count": len(self.get_salmonella_tests(test_result="Pending")), "attention_salmonella_count": count("SALMONELLA_TEST", "TEST_RESULT IN (%s, %s)", ("Positive", "Inconclusive")), "production_record_count": production["production_record_count"]}
