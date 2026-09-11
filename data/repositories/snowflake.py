# ============================================================
# EFNS Prototype v0.1 — Snowflake Repository (stub)
# ============================================================
"""Snowflake-backed repository. Not yet populated; design placeholder.

This module documents the intended Snowflake integration but is intentionally
left as a stub for v0.1. The Streamlit UI talks to BaseRepository, so swapping
from MockRepository to SnowflakeRepository requires no UI changes.
"""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd

from data.repositories.base import BaseRepository


class SnowflakeRepository(BaseRepository):
    """Snowflake implementation of the repository interface (stub for v0.1)."""

    def __init__(self):
        import snowflake.connector  # noqa: F401  (validates dependency present)
        self._conn = None
        self.account = os.getenv("SNOWFLAKE_ACCOUNT")
        self.user = os.getenv("SNOWFLAKE_USER")
        self.password = os.getenv("SNOWFLAKE_PASSWORD")
        self.warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "EFNS_DEV_WH")
        self.database = os.getenv("SNOWFLAKE_DATABASE", "EFNS_DEV")
        self.role = os.getenv("SNOWFLAKE_ROLE", "EFNS_DEV_ROLE")
        self.schema_raw = os.getenv("SNOWFLAKE_SCHEMA_RAW", "RAW")
        self.schema_core = os.getenv("SNOWFLAKE_SCHEMA_CORE", "CORE")
        self.schema_reporting = os.getenv("SNOWFLAKE_SCHEMA_REPORTING", "REPORTING")

    def _connect(self):
        import snowflake.connector
        if self._conn is None:
            self._conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database=self.database,
                role=self.role,
            )
        return self._conn

    def _query(self, sql: str, params: tuple | None = None) -> pd.DataFrame:
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params or ())
            columns = [column[0] for column in cursor.description]
            return pd.DataFrame.from_records(cursor.fetchall(), columns=columns)
        finally:
            cursor.close()

    # --- Accounts ---
    def get_accounts(self) -> pd.DataFrame:
        return self._query(f"SELECT * FROM {self.database}.{self.schema_core}.ACCOUNT")

    def get_account(self, account_id: str) -> Optional[dict]:
        df = self._query(
            f"SELECT * FROM {self.database}.{self.schema_core}.ACCOUNT WHERE ACCOUNT_ID = %s",
            (account_id,),
        )
        return df.iloc[0].to_dict() if len(df) else None

    def find_accounts_by_registration_number(
        self, registration_number: str
    ) -> pd.DataFrame:
        return self._query(
            f"SELECT * FROM {self.database}.{self.schema_core}.ACCOUNT "
            "WHERE UPPER(TRIM(REGISTRATION_NUMBER)) = UPPER(TRIM(%s))",
            (registration_number,),
        )

    def upsert_account(self, record: dict) -> str:
        # PROVISIONAL MERGE; not used in v0.1
        raise NotImplementedError("Snowflake upsert not implemented in v0.1")

    def delete_account(self, account_id: str) -> bool:
        raise NotImplementedError("Snowflake delete not implemented in v0.1")

    # --- Facilities ---
    def get_facilities(self, account_id: Optional[str] = None) -> pd.DataFrame:
        sql = f"SELECT * FROM {self.database}.{self.schema_core}.FACILITY"
        params = None
        if account_id:
            sql += " WHERE ACCOUNT_ID = %s"
            params = (account_id,)
        return self._query(sql, params)

    def upsert_facility(self, record: dict) -> str:
        raise NotImplementedError("Snowflake upsert not implemented in v0.1")

    def delete_facility(self, facility_id: str) -> bool:
        raise NotImplementedError("Snowflake delete not implemented in v0.1")

    def get_facility_details(self, facility_id: Optional[str] = None) -> pd.DataFrame:
        sql = f"SELECT * FROM {self.database}.{self.schema_core}.FACILITY_DETAIL"
        params = None
        if facility_id:
            sql += " WHERE FACILITY_ID = %s"
            params = (facility_id,)
        return self._query(sql, params)

    def upsert_facility_detail(self, record: dict) -> str:
        raise NotImplementedError("Snowflake writes await schema alignment")

    # --- Flocks ---
    def get_flocks(
        self, account_id: Optional[str] = None, facility_id: Optional[str] = None
    ) -> pd.DataFrame:
        sql = f"SELECT * FROM {self.database}.{self.schema_core}.FLOCK"
        conds = []
        params = []
        if account_id:
            conds.append("ACCOUNT_ID = %s")
            params.append(account_id)
        if facility_id:
            conds.append("FACILITY_ID = %s")
            params.append(facility_id)
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        return self._query(sql, tuple(params) if params else None)

    def get_flock(self, flock_id: str) -> Optional[dict]:
        frame = self._query(
            f"SELECT * FROM {self.database}.{self.schema_core}.FLOCK WHERE FLOCK_ID = %s",
            (flock_id,),
        )
        return frame.iloc[0].to_dict() if len(frame) else None

    def upsert_flock(self, record: dict) -> str:
        raise NotImplementedError("Snowflake upsert not implemented in v0.1")

    def delete_flock(self, flock_id: str) -> bool:
        raise NotImplementedError("Snowflake delete not implemented in v0.1")

    # --- Flock Transactions ---
    def get_flock_transactions(self, flock_id: Optional[str] = None) -> pd.DataFrame:
        sql = f"SELECT * FROM {self.database}.{self.schema_core}.FLOCK_TRANSACTION"
        params = None
        if flock_id:
            sql += " WHERE FLOCK_ID = %s"
            params = (flock_id,)
        return self._query(sql, params)

    def upsert_flock_transaction(self, record: dict) -> str:
        raise NotImplementedError("Snowflake upsert not implemented in v0.1")

    def delete_flock_transaction(self, transaction_id: str) -> bool:
        raise NotImplementedError("Snowflake writes await schema alignment")

    # --- Provisional quota and testing reads ---
    def get_quota_registrations(
        self, account_id=None, status=None, quota_type=None, active_only=False
    ) -> pd.DataFrame:
        sql = f"SELECT * FROM {self.database}.{self.schema_core}.QUOTA_REGISTRATION"
        conditions, params = [], []
        if account_id:
            conditions.append("ACCOUNT_ID = %s")
            params.append(account_id)
        if status:
            conditions.append("STATUS = %s")
            params.append(status)
        if quota_type:
            conditions.append("QUOTA_TYPE = %s")
            params.append(quota_type)
        if active_only:
            conditions.append("STATUS = %s")
            params.append("Active")
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        return self._query(sql, tuple(params) if params else None)

    def get_quota_registration(self, quota_id: str) -> Optional[dict]:
        frame = self._query(
            f"SELECT * FROM {self.database}.{self.schema_core}.QUOTA_REGISTRATION WHERE QUOTA_ID = %s",
            (quota_id,),
        )
        return frame.iloc[0].to_dict() if len(frame) else None

    def upsert_quota_registration(self, record: dict) -> str:
        raise NotImplementedError("Snowflake writes await schema alignment")

    def delete_quota_registration(self, quota_id: str) -> bool:
        raise NotImplementedError("Snowflake writes await schema alignment")

    def get_quota_transactions(
        self, account_id=None, quota_id=None, quota_type=None,
        transaction_type=None, date_from=None, date_to=None
    ) -> pd.DataFrame:
        sql = f"SELECT * FROM {self.database}.{self.schema_core}.QUOTA_TRANSACTION"
        conditions, params = [], []
        if account_id:
            conditions.append("(OWNER_ACCOUNT_ID = %s OR RELATED_ACCOUNT_ID = %s)")
            params.extend([account_id, account_id])
        if quota_id:
            conditions.append("QUOTA_ID = %s")
            params.append(quota_id)
        if transaction_type:
            conditions.append("TRANSACTION_TYPE = %s")
            params.append(transaction_type)
        if date_from is not None:
            conditions.append("EFFECTIVE_DATE >= %s")
            params.append(date_from)
        if date_to is not None:
            conditions.append("EFFECTIVE_DATE <= %s")
            params.append(date_to)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        frame = self._query(sql, tuple(params) if params else None)
        if quota_type and not frame.empty:
            quota_ids = set(self.get_quota_registrations(quota_type=quota_type)["QUOTA_ID"])
            frame = frame[frame["QUOTA_ID"].isin(quota_ids)]
        return frame

    def upsert_quota_transaction(self, record: dict) -> str:
        raise NotImplementedError("Snowflake writes await schema alignment")

    def delete_quota_transaction(self, transaction_id: str) -> bool:
        raise NotImplementedError("Snowflake writes await schema alignment")

    def get_salmonella_tests(
        self, account_id=None, facility_id=None, flock_id=None, permit_number=None,
        test_result=None, inspector=None, case_number=None, invoice_number=None,
        date_from=None, date_to=None,
    ) -> pd.DataFrame:
        sql = f"SELECT * FROM {self.database}.{self.schema_core}.SALMONELLA_TEST"
        conditions, params = [], []
        for column, value in (
            ("ACCOUNT_ID", account_id), ("FLOCK_ID", flock_id),
            ("PERMIT_NUMBER", permit_number), ("TEST_RESULT", test_result),
            ("INSPECTOR", inspector), ("CASE_FILE_NUMBER", case_number),
            ("INVOICE_NUMBER", invoice_number),
        ):
            if value:
                conditions.append(f"{column} = %s")
                params.append(value)
        if date_from is not None:
            conditions.append("TESTING_DATE >= %s")
            params.append(date_from)
        if date_to is not None:
            conditions.append("TESTING_DATE <= %s")
            params.append(date_to)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        frame = self._query(sql, tuple(params) if params else None)
        if facility_id and not frame.empty:
            flock_ids = set(self.get_flocks(facility_id=facility_id)["FLOCK_ID"])
            frame = frame[frame["FLOCK_ID"].isin(flock_ids)]
        return frame

    def get_salmonella_test(self, test_id: str) -> Optional[dict]:
        frame = self._query(
            f"SELECT * FROM {self.database}.{self.schema_core}.SALMONELLA_TEST WHERE SALMONELLA_TEST_ID = %s",
            (test_id,),
        )
        return frame.iloc[0].to_dict() if len(frame) else None

    def upsert_salmonella_test(self, record: dict) -> str:
        raise NotImplementedError("Snowflake writes await schema alignment")

    def delete_salmonella_test(self, test_id: str) -> bool:
        raise NotImplementedError("Snowflake writes await schema alignment")

    def get_salmonella_test_samples(self, test_id: Optional[str] = None) -> pd.DataFrame:
        sql = f"SELECT * FROM {self.database}.{self.schema_core}.SALMONELLA_TEST_SAMPLE"
        return self._query(sql + (" WHERE SALMONELLA_TEST_ID = %s" if test_id else ""), (test_id,) if test_id else None)

    # --- Imports & Production ---
    def create_import_batch(self, record: dict) -> str:
        raise NotImplementedError("Snowflake import not implemented in v0.1")

    def get_import_batches(self) -> pd.DataFrame:
        return self._query(f"SELECT * FROM {self.database}.{self.schema_raw}.IMPORT_BATCH")

    def insert_raw_rows(self, import_id: str, rows: list[dict]) -> int:
        raise NotImplementedError("Snowflake raw-row insert is deferred until schema alignment")

    def get_raw_rows(self, import_id: str) -> pd.DataFrame:
        raise NotImplementedError("Snowflake raw-row reads are deferred until schema alignment")

    def insert_production_records(self, records: pd.DataFrame, import_id: str) -> int:
        raise NotImplementedError("Snowflake production insert not implemented in v0.1")

    def get_production_records(
        self,
        reporting_year: Optional[int] = None,
        reporting_week: Optional[int] = None,
        grader_number: Optional[str] = None,
        barn_identity: Optional[str] = None,
        egg_colour: Optional[str] = None,
    ) -> pd.DataFrame:
        df = self._query(
            f"SELECT * FROM {self.database}.{self.schema_reporting}.VW_PRODUCTION_SUMMARY"
        )
        if reporting_year is not None:
            df = df[df["REPORTING_YEAR"] == reporting_year]
        if reporting_week is not None:
            df = df[df["REPORTING_WEEK"] == reporting_week]
        if grader_number:
            df = df[df["GRADER_NUMBER"] == grader_number]
        if barn_identity:
            df = df[df["BARN_IDENTITY"] == barn_identity]
        if egg_colour:
            df = df[df["EGG_COLOUR"] == egg_colour]
        return df

    def get_production_summary_metrics(self) -> dict:
        df = self._query(
            f"SELECT COUNT(*) AS PRODUCTION_RECORD_COUNT, "
            f"SUM(TOTAL_RECEIVED) AS TOTAL_RECEIVED, "
            f"SUM(TOTAL_ACCEPTED) AS TOTAL_ACCEPTED, "
            f"SUM(REJECTED) AS TOTAL_REJECTED, SUM(LOSS) AS TOTAL_LOSS "
            f"FROM {self.database}.{self.schema_reporting}.VW_PRODUCTION_SUMMARY"
        )
        row = df.iloc[0]
        import_count = self._query(
            f"SELECT COUNT(*) AS RECORD_COUNT "
            f"FROM {self.database}.{self.schema_raw}.IMPORT_BATCH"
        ).iloc[0]["RECORD_COUNT"]
        account_count = self._query(
            f"SELECT COUNT(*) AS RECORD_COUNT "
            f"FROM {self.database}.{self.schema_core}.ACCOUNT"
        ).iloc[0]["RECORD_COUNT"]
        flock_count = self._query(
            f"SELECT COUNT(*) AS RECORD_COUNT "
            f"FROM {self.database}.{self.schema_core}.FLOCK"
        ).iloc[0]["RECORD_COUNT"]
        return {
            "import_count": int(import_count or 0),
            "production_record_count": int(row["PRODUCTION_RECORD_COUNT"] or 0),
            "account_count": int(account_count or 0),
            "flock_count": int(flock_count or 0),
            "total_received": float(row["TOTAL_RECEIVED"] or 0),
            "total_accepted": float(row["TOTAL_ACCEPTED"] or 0),
            "total_rejected": float(row["TOTAL_REJECTED"] or 0),
            "total_loss": float(row["TOTAL_LOSS"] or 0),
        }

    def get_dashboard_metrics(self) -> dict:
        production = self.get_production_summary_metrics()
        return {
            "active_account_count": len(self.get_accounts().query("STATUS == 'Active'")),
            "active_facility_count": len(self.get_facilities().query("STATUS == 'Active'")),
            "active_flock_count": len(self.get_flocks().query("STATUS == 'Active'")),
            "active_quota_count": len(self.get_quota_registrations(active_only=True)),
            "recent_quota_transaction_count": len(self.get_quota_transactions()),
            "pending_salmonella_count": len(self.get_salmonella_tests(test_result="Pending")),
            "attention_salmonella_count": len(
                pd.concat(
                    [
                        self.get_salmonella_tests(test_result="Positive"),
                        self.get_salmonella_tests(test_result="Inconclusive"),
                    ],
                    ignore_index=True,
                )
            ),
            "production_record_count": production["production_record_count"],
        }
