"""Snowflake persistence using fixed identifiers and bound data values."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from typing import Optional
import uuid
import pandas as pd

from data.repositories.base import BaseRepository, RepositoryError
from data.validation import validate_flock, validate_quota_registration, validate_quota_transaction, validate_salmonella_test

MODEL = {
 "ACCOUNT": ("ACCOUNT_ID", "REGISTRATION_NUMBER ORGANIZATION_NAME ADDRESS_LINE1 ADDRESS_LINE2 CITY PROVINCE POSTAL_CODE CONTACT_NAME CONTACT_PHONE CONTACT_EMAIL LICENCE_NUMBER PRODUCER_ROLE BREEDER_ROLE HATCHERY_ROLE GRADER_ROLE STATUS"),
 "FACILITY": ("FACILITY_ID", "ACCOUNT_ID FACILITY_NAME FACILITY_TYPE STATUS ACTIVATION_DATE CONSTRUCTION_DATE CLOSURE_DATE DESTRUCTION_DATE INACTIVE_DATE"),
 "FACILITY_DETAIL": ("FACILITY_DETAIL_ID", "FACILITY_ID DETAIL_NAME DETAIL_TYPE STATUS COMMENTS"),
 "FLOCK": ("FLOCK_ID", "FLOCK_NUMBER ACCOUNT_ID FACILITY_ID FACILITY_DETAIL_ID QUOTA_ID FLOCK_QUOTA_TYPE STATUS CREATE_DELIVERY_TRANSACTION PERMIT_NUMBER PERMIT_DATE HATCH_DATE DATE_ORDERED BIRD_COUNT EGG_COLOUR BIRD_STRAIN PLACEMENT_DATE EST_DISPOSAL DISPOSAL_DATE BIRDS_DISPOSED BREEDER HATCHERY PULLET_GROWER DISPOSAL_PLANT DISPOSAL_METHOD COMMENTS"),
 "FLOCK_TRANSACTION": ("FLOCK_TRANSACTION_ID", "FLOCK_ID TRANSACTION_TYPE QUANTITY TRANSACTION_DATE NOTES"),
 "QUOTA_REGISTRATION": ("QUOTA_ID", "REGISTRATION_NUMBER ACCOUNT_ID QUOTA_NAME QUOTA_TYPE STATUS EFFECTIVE_DATE END_DATE COMMENTS"),
 "QUOTA_TRANSACTION": ("QUOTA_TRANSACTION_ID", "TRANSACTION_TYPE QUOTA_ID EFFECTIVE_DATE END_DATE QUOTA_COUNT OWNER_ACCOUNT_ID RELATED_ACCOUNT_ID RELATED_QUOTA_ID RELATED_TRANSACTION_ID PRICE QUOTA_LEASE_TYPE COMMENTS"),
 "SALMONELLA_TEST": ("SALMONELLA_TEST_ID", "FLOCK_ID ACCOUNT_ID PERMIT_NUMBER TESTING_DATE INSPECTOR NUMBER_OF_SAMPLES TEST_RESULT DATE_RESULT_SENT DATE_RECEIVED CASE_FILE_NUMBER INVOICE_NUMBER INVOICE_DATE COMMENTS"),
}
PRODUCTION_COLUMNS = "PRODUCER_ACCOUNT_ID GRADER_ACCOUNT_ID FACILITY_ID FLOCK_ID GRADER_NAME PRODUCER_NUMBER GRADER_NUMBER BARN_IDENTITY SOURCE_WEEK_CODE REPORTING_YEAR REPORTING_WEEK MARKETING_TYPE HOUSING_SYSTEM EGG_TYPE EGG_COLOUR FLOCK_AGE NET_WEIGHT NET_BOXES NET_PER_BOX JUMBO EXTRA_LARGE LARGE MEDIUM SMALL PEEWEE GRADE_B GRADE_C CRACKS NEST_RUN NEST_RUN_25_PLUS NEST_RUN_24_PLUS NEST_RUN_23_PLUS NEST_RUN_22_PLUS NEST_RUN_21_PLUS NEST_RUN_20_PLUS NEST_RUN_19_PLUS NEST_RUN_18_PLUS NEST_RUN_17_PLUS OTHER_LEVIABLE OTHER_NON_LEVIABLE FARM_GATE_SALES ON_FARM_CONSUMPTION SUBTOTAL REJECTS LEAKERS TOTAL TOTAL_RECEIVED REJECTED LOSS LEGACY_REJECT_LOSS_TOTAL TOTAL_ACCEPTED SOURCE_TYPE MATCH_STATUS SOURCE_ROW_NUMBER MATCH_CONFIRMED_AT MATCH_CONFIRMED_BY".split()


class SnowflakeRepository(BaseRepository):
 def __init__(self):
  self._conn = None
  self.account, self.user, self.password = (os.getenv(x) for x in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"))
  self.warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "EFNS_DEV_WH")
  self.database = os.getenv("SNOWFLAKE_DATABASE", "EFNS_DEV")
  self.role = os.getenv("SNOWFLAKE_ROLE", "EFNS_DEV_ROLE")
  self.schema_raw, self.schema_core, self.schema_reporting = (os.getenv(k, v) for k, v in (("SNOWFLAKE_SCHEMA_RAW", "RAW"), ("SNOWFLAKE_SCHEMA_CORE", "CORE"), ("SNOWFLAKE_SCHEMA_REPORTING", "REPORTING")))

 def _connect(self):
  import snowflake.connector
  if self._conn is None:
   self._conn = snowflake.connector.connect(account=self.account, user=self.user, password=self.password, warehouse=self.warehouse, database=self.database, role=self.role, autocommit=False)
  return self._conn

 @contextmanager
 def _cursor(self, transaction=False):
  conn, cursor = self._connect(), self._connect().cursor()
  try:
   yield cursor
   if transaction: conn.commit()
  except Exception as exc:
   if transaction: conn.rollback()
   raise RepositoryError(str(exc)) from exc
  finally: cursor.close()

 def _query(self, sql, params=None):
  with self._cursor() as cursor:
   cursor.execute(sql, params or ())
   return pd.DataFrame.from_records(cursor.fetchall(), columns=[c[0] for c in (cursor.description or [])])

 def _one(self, table, column, value, schema=None):
  frame = self._query(f"SELECT * FROM {self.database}.{schema or self.schema_core}.{table} WHERE {column} = %s", (value,))
  return frame.iloc[0].to_dict() if len(frame) else None

 def _upsert(self, table, record):
  key, allowed_text = MODEL[table]; allowed = allowed_text.split()
  entity_id = record.get(key) or str(uuid.uuid4())
  values = {k: v for k, v in record.items() if k in allowed}
  if not values: raise RepositoryError(f"No writable fields supplied for {table}.")
  update = f"UPDATE {self.database}.{self.schema_core}.{table} SET " + ", ".join(f"{k} = %s" for k in values) + f", UPDATED_AT = CURRENT_TIMESTAMP() WHERE {key} = %s"
  columns = [key, *values]
  insert = f"INSERT INTO {self.database}.{self.schema_core}.{table} ({', '.join(columns)}, CREATED_AT, UPDATED_AT) VALUES ({', '.join(['%s'] * len(columns))}, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())"
  with self._cursor(True) as cursor:
   cursor.execute(update, (*values.values(), entity_id))
   if cursor.rowcount == 0: cursor.execute(insert, (entity_id, *values.values()))
  return entity_id

 def _delete(self, table, key, entity_id, references=()):
  with self._cursor(True) as cursor:
   for ref_table, ref_col in references:
    cursor.execute(f"SELECT COUNT(*) FROM {self.database}.{self.schema_core}.{ref_table} WHERE {ref_col} = %s", (entity_id,))
    if (cursor.fetchone() or (0,))[0]: raise RepositoryError(f"{table} is referenced by {ref_table}.")
   cursor.execute(f"DELETE FROM {self.database}.{self.schema_core}.{table} WHERE {key} = %s", (entity_id,))
   return cursor.rowcount > 0

 def _filtered(self, table, filters, schema=None, prefix=""):
  conditions, params = [], []
  for column, value in filters:
   if value is not None and value != "": conditions.append(f"{prefix}{column} = %s"); params.append(value)
  sql = f"SELECT * FROM {self.database}.{schema or self.schema_core}.{table}" + ((" WHERE " + " AND ".join(conditions)) if conditions else "")
  return self._query(sql, tuple(params) if params else None)

 def get_accounts(self): return self._filtered("ACCOUNT", [])
 def get_account(self, account_id): return self._one("ACCOUNT", "ACCOUNT_ID", account_id)
 def find_accounts_by_registration_number(self, registration_number): return self._query(f"SELECT * FROM {self.database}.{self.schema_core}.ACCOUNT WHERE UPPER(TRIM(REGISTRATION_NUMBER)) = UPPER(TRIM(%s))", (registration_number,))
 def upsert_account(self, record): return self._upsert("ACCOUNT", record)
 def delete_account(self, value): return self._delete("ACCOUNT", "ACCOUNT_ID", value, (("FACILITY", "ACCOUNT_ID"), ("FLOCK", "ACCOUNT_ID"), ("QUOTA_REGISTRATION", "ACCOUNT_ID"), ("SALMONELLA_TEST", "ACCOUNT_ID")))
 def get_facilities(self, account_id=None): return self._filtered("FACILITY", (("ACCOUNT_ID", account_id),))
 def upsert_facility(self, record): return self._upsert("FACILITY", record)
 def delete_facility(self, value): return self._delete("FACILITY", "FACILITY_ID", value, (("FACILITY_DETAIL", "FACILITY_ID"), ("FLOCK", "FACILITY_ID")))
 def get_facility_details(self, facility_id=None): return self._filtered("FACILITY_DETAIL", (("FACILITY_ID", facility_id),))
 def upsert_facility_detail(self, record): return self._upsert("FACILITY_DETAIL", record)
 def get_flocks(self, account_id=None, facility_id=None): return self._filtered("FLOCK", (("ACCOUNT_ID", account_id), ("FACILITY_ID", facility_id)))
 def get_flock(self, flock_id): return self._one("FLOCK", "FLOCK_ID", flock_id)
 def upsert_flock(self, record):
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
  for col, val in filters:
   if val is not None: conditions.append(f"{col} = %s"); params.append(val)
  return self._query(f"SELECT * FROM {self.database}.{self.schema_core}.QUOTA_REGISTRATION WHERE " + " AND ".join(conditions), tuple(params))
 def get_quota_registration(self, value): return self._one("QUOTA_REGISTRATION", "QUOTA_ID", value)
 def upsert_quota_registration(self, record):
  errors = validate_quota_registration(self, record)
  if errors: raise RepositoryError(" ".join(errors))
  return self._upsert("QUOTA_REGISTRATION", record)
 def delete_quota_registration(self, value): return self._delete("QUOTA_REGISTRATION", "QUOTA_ID", value, (("QUOTA_TRANSACTION", "QUOTA_ID"), ("FLOCK", "QUOTA_ID")))
 def get_quota_transactions(self, account_id=None, quota_id=None, quota_type=None, transaction_type=None, date_from=None, date_to=None):
  join = f" JOIN {self.database}.{self.schema_core}.QUOTA_REGISTRATION qr ON qr.QUOTA_ID = qt.QUOTA_ID" if quota_type else ""
  conditions, params = [], []
  if account_id: conditions.append("(qt.OWNER_ACCOUNT_ID = %s OR qt.RELATED_ACCOUNT_ID = %s)"); params += [account_id, account_id]
  for col, op, val in (("qt.QUOTA_ID", "=", quota_id), ("qr.QUOTA_TYPE", "=", quota_type), ("qt.TRANSACTION_TYPE", "=", transaction_type), ("qt.EFFECTIVE_DATE", ">=", date_from), ("qt.EFFECTIVE_DATE", "<=", date_to)):
   if val is not None: conditions.append(f"{col} {op} %s"); params.append(val)
  return self._query(f"SELECT qt.* FROM {self.database}.{self.schema_core}.QUOTA_TRANSACTION qt{join}" + ((" WHERE " + " AND ".join(conditions)) if conditions else ""), tuple(params) if params else None)
 def upsert_quota_transaction(self, record):
  errors = validate_quota_transaction(self, record)
  if errors: raise RepositoryError(" ".join(errors))
  stored = dict(record)
  stored["OWNER_ACCOUNT_ID"] = self.get_quota_registration(record["QUOTA_ID"])["ACCOUNT_ID"]
  return self._upsert("QUOTA_TRANSACTION", stored)
 def delete_quota_transaction(self, value): return self._delete("QUOTA_TRANSACTION", "QUOTA_TRANSACTION_ID", value)

 def get_salmonella_tests(self, account_id=None, facility_id=None, flock_id=None, permit_number=None, test_result=None, inspector=None, case_number=None, invoice_number=None, date_from=None, date_to=None):
  join = f" JOIN {self.database}.{self.schema_core}.FLOCK f ON f.FLOCK_ID = st.FLOCK_ID" if facility_id else ""
  conditions, params = [], []
  for col, val in (("st.ACCOUNT_ID", account_id), ("f.FACILITY_ID", facility_id), ("st.FLOCK_ID", flock_id), ("st.PERMIT_NUMBER", permit_number), ("st.TEST_RESULT", test_result), ("st.INSPECTOR", inspector), ("st.CASE_FILE_NUMBER", case_number), ("st.INVOICE_NUMBER", invoice_number)):
   if val: conditions.append(f"{col} = %s"); params.append(val)
  for op, val in ((">=", date_from), ("<=", date_to)):
   if val is not None: conditions.append(f"st.TESTING_DATE {op} %s"); params.append(val)
  return self._query(f"SELECT st.* FROM {self.database}.{self.schema_core}.SALMONELLA_TEST st{join}" + ((" WHERE " + " AND ".join(conditions)) if conditions else ""), tuple(params) if params else None)
 def get_salmonella_test(self, value): return self._one("SALMONELLA_TEST", "SALMONELLA_TEST_ID", value)
 def upsert_salmonella_test(self, record):
  errors = validate_salmonella_test(self, record)
  if errors: raise RepositoryError(" ".join(errors))
  return self._upsert("SALMONELLA_TEST", record)
 def delete_salmonella_test(self, value): return self._delete("SALMONELLA_TEST", "SALMONELLA_TEST_ID", value, (("SALMONELLA_TEST_SAMPLE", "SALMONELLA_TEST_ID"),))
 def get_salmonella_test_samples(self, test_id=None): return self._filtered("SALMONELLA_TEST_SAMPLE", (("SALMONELLA_TEST_ID", test_id),))

 def _insert_batch(self, cursor, import_id, record):
  allowed = "FILENAME SOURCE FILE_HASH FILE_SIZE_BYTES WORKSHEET_NAME REPORTING_YEAR REPORTING_WEEK SOURCE_RECORD_COUNT ROW_COUNT ERROR_COUNT STATUS NOTES".split()
  values = {k: record[k] for k in allowed if k in record}; columns = ["IMPORT_ID", *values]
  cursor.execute(f"INSERT INTO {self.database}.{self.schema_raw}.IMPORT_BATCH ({', '.join(columns)}, UPLOAD_TIMESTAMP, CREATED_AT, UPDATED_AT) VALUES ({', '.join(['%s'] * len(columns))}, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())", (import_id, *values.values()))
 def create_import_batch(self, record):
  import_id = record.get("IMPORT_ID") or str(uuid.uuid4())
  with self._cursor(True) as cursor: self._insert_batch(cursor, import_id, record)
  return import_id
 def get_import_batches(self): return self._filtered("IMPORT_BATCH", [], self.schema_raw)
 def find_import_by_hash(self, file_hash): return self._one("IMPORT_BATCH", "FILE_HASH", file_hash, self.schema_raw) if file_hash else None
 def _insert_raw(self, cursor, import_id, rows):
  sql = f"INSERT INTO {self.database}.{self.schema_raw}.IMPORT_RAW_ROW (RAW_ROW_ID, IMPORT_ID, SOURCE_ROW_NUMBER, RAW_DATA, VALIDATION_STATUS, MATCH_STATUS, VALIDATION_MESSAGES, CREATED_AT, UPDATED_AT) SELECT %s, %s, %s, PARSE_JSON(%s), %s, %s, PARSE_JSON(%s), CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()"
  params = []
  for index, row in enumerate(rows, 1):
   params.append((row.get("RAW_ROW_ID") or str(uuid.uuid4()), import_id, row.get("SOURCE_ROW_NUMBER", index), json.dumps(row.get("RAW_DATA", row.get("ROW_DATA", row)), default=str), row.get("VALIDATION_STATUS", "PENDING"), row.get("MATCH_STATUS", "UNMATCHED"), json.dumps(row.get("VALIDATION_MESSAGES", row.get("MESSAGES", [])), default=str)))
  if params: cursor.executemany(sql, params)
  return len(params)
 def insert_raw_rows(self, import_id, rows):
  with self._cursor(True) as cursor: return self._insert_raw(cursor, import_id, rows)
 def get_raw_rows(self, import_id): return self._query(f"SELECT * FROM {self.database}.{self.schema_raw}.IMPORT_RAW_ROW WHERE IMPORT_ID = %s ORDER BY SOURCE_ROW_NUMBER", (import_id,))
 def _insert_production(self, cursor, records, import_id):
  rows = records.to_dict("records") if isinstance(records, pd.DataFrame) else list(records); columns = ["PRODUCTION_ID", "IMPORT_ID", *PRODUCTION_COLUMNS]
  sql = f"INSERT INTO {self.database}.{self.schema_core}.PRODUCTION_RECORD ({', '.join(columns)}, CREATED_AT, UPDATED_AT) VALUES ({', '.join(['%s'] * len(columns))}, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())"
  params = []
  for row in rows:
   item = dict(row); item.setdefault("SOURCE_TYPE", "EIMS_IMPORT"); item.setdefault("MATCH_STATUS", "UNMATCHED")
   params.append((item.get("PRODUCTION_ID") or str(uuid.uuid4()), import_id, *(item.get(c) for c in PRODUCTION_COLUMNS)))
  if params: cursor.executemany(sql, params)
  return len(params)
 def insert_production_records(self, records, import_id):
  with self._cursor(True) as cursor: return self._insert_production(cursor, records, import_id)
 def import_production_bundle(self, batch, raw_rows, records, allow_duplicate=False):
  import_id, file_hash = batch.get("IMPORT_ID") or str(uuid.uuid4()), batch.get("FILE_HASH")
  with self._cursor(True) as cursor:
   if file_hash and not allow_duplicate:
    cursor.execute(f"SELECT IMPORT_ID FROM {self.database}.{self.schema_raw}.IMPORT_BATCH WHERE FILE_HASH = %s LIMIT 1", (file_hash,))
    if cursor.fetchone(): raise RepositoryError("This exact file has already been imported.")
   self._insert_batch(cursor, import_id, batch); self._insert_raw(cursor, import_id, raw_rows); count = self._insert_production(cursor, records, import_id)
   cursor.execute(f"UPDATE {self.database}.{self.schema_raw}.IMPORT_BATCH SET ROW_COUNT = %s, STATUS = %s, UPDATED_AT = CURRENT_TIMESTAMP() WHERE IMPORT_ID = %s", (count, "Committed", import_id))
  return import_id, count

 def get_production_records(self, reporting_year=None, reporting_week=None, grader_number=None, barn_identity=None, egg_colour=None):
  return self._filtered("VW_PRODUCTION_SUMMARY", (("REPORTING_YEAR", reporting_year), ("REPORTING_WEEK", reporting_week), ("GRADER_NUMBER", grader_number), ("BARN_IDENTITY", barn_identity), ("EGG_COLOUR", egg_colour)), self.schema_reporting)
 def get_production_summary_metrics(self):
  row = self._query(f"SELECT COUNT(*) PRODUCTION_RECORD_COUNT, COALESCE(SUM(TOTAL_RECEIVED),0) TOTAL_RECEIVED, COALESCE(SUM(TOTAL_ACCEPTED),0) TOTAL_ACCEPTED, COALESCE(SUM(REJECTED),0) TOTAL_REJECTED, COALESCE(SUM(LOSS),0) TOTAL_LOSS FROM {self.database}.{self.schema_reporting}.VW_PRODUCTION_SUMMARY").iloc[0]
  counts = {name: int(self._query(f"SELECT COUNT(*) RECORD_COUNT FROM {self.database}.{schema}.{table}").iloc[0]["RECORD_COUNT"] or 0) for name, schema, table in (("import_count", self.schema_raw, "IMPORT_BATCH"), ("account_count", self.schema_core, "ACCOUNT"), ("flock_count", self.schema_core, "FLOCK"))}
  return {**counts, "production_record_count": int(row["PRODUCTION_RECORD_COUNT"] or 0), "total_received": float(row["TOTAL_RECEIVED"] or 0), "total_accepted": float(row["TOTAL_ACCEPTED"] or 0), "total_rejected": float(row["TOTAL_REJECTED"] or 0), "total_loss": float(row["TOTAL_LOSS"] or 0)}
 def get_dashboard_metrics(self):
  production = self.get_production_summary_metrics()
  count = lambda table, condition, params: len(self._query(f"SELECT 1 FROM {self.database}.{self.schema_core}.{table} WHERE {condition}", params))
  return {"active_account_count": count("ACCOUNT", "STATUS = %s", ("Active",)), "active_facility_count": count("FACILITY", "STATUS = %s", ("Active",)), "active_flock_count": count("FLOCK", "STATUS = %s", ("Active",)), "active_quota_count": len(self.get_quota_registrations(active_only=True)), "recent_quota_transaction_count": len(self.get_quota_transactions()), "pending_salmonella_count": len(self.get_salmonella_tests(test_result="Pending")), "attention_salmonella_count": count("SALMONELLA_TEST", "TEST_RESULT IN (%s, %s)", ("Positive", "Inconclusive")), "production_record_count": production["production_record_count"]}
