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

    def _query(self, sql: str) -> pd.DataFrame:
        conn = self._connect()
        return pd.read_sql(sql, conn)

    # --- Accounts ---
    def get_accounts(self) -> pd.DataFrame:
        return self._query(f"SELECT * FROM {self.database}.{self.schema_core}.ACCOUNT")

    def get_account(self, account_id: str) -> Optional[dict]:
        df = self._query(
            f"SELECT * FROM {self.database}.{self.schema_core}.ACCOUNT WHERE ACCOUNT_ID = %s"
        )
        return df.iloc[0].to_dict() if len(df) else None

    def upsert_account(self, record: dict) -> str:
        # PROVISIONAL MERGE; not used in v0.1
        raise NotImplementedError("Snowflake upsert not implemented in v0.1")

    def delete_account(self, account_id: str) -> bool:
        raise NotImplementedError("Snowflake delete not implemented in v0.1")

    # --- Facilities ---
    def get_facilities(self, account_id: Optional[str] = None) -> pd.DataFrame:
        sql = f"SELECT * FROM {self.database}.{self.schema_core}.FACILITY"
        if account_id:
            sql += f" WHERE ACCOUNT_ID = %s"
        return self._query(sql)

    def upsert_facility(self, record: dict) -> str:
        raise NotImplementedError("Snowflake upsert not implemented in v0.1")

    def delete_facility(self, facility_id: str) -> bool:
        raise NotImplementedError("Snowflake delete not implemented in v0.1")

    # --- Flocks ---
    def get_flocks(
        self, account_id: Optional[str] = None, facility_id: Optional[str] = None
    ) -> pd.DataFrame:
        sql = f"SELECT * FROM {self.database}.{self.schema_core}.FLOCK"
        conds = []
        if account_id:
            conds.append(f"ACCOUNT_ID = '{account_id}'")
        if facility_id:
            conds.append(f"FACILITY_ID = '{facility_id}'")
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        return self._query(sql)

    def upsert_flock(self, record: dict) -> str:
        raise NotImplementedError("Snowflake upsert not implemented in v0.1")

    def delete_flock(self, flock_id: str) -> bool:
        raise NotImplementedError("Snowflake delete not implemented in v0.1")

    # --- Flock Transactions ---
    def get_flock_transactions(self, flock_id: Optional[str] = None) -> pd.DataFrame:
        sql = f"SELECT * FROM {self.database}.{self.schema_core}.FLOCK_TRANSACTION"
        if flock_id:
            sql += f" WHERE FLOCK_ID = '{flock_id}'"
        return self._query(sql)

    def upsert_flock_transaction(self, record: dict) -> str:
        raise NotImplementedError("Snowflake upsert not implemented in v0.1")

    # --- Imports & Production ---
    def create_import_batch(self, record: dict) -> str:
        raise NotImplementedError("Snowflake import not implemented in v0.1")

    def get_import_batches(self) -> pd.DataFrame:
        return self._query(f"SELECT * FROM {self.database}.{self.schema_raw}.IMPORT_BATCH")

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
            f"SELECT COUNT(*) AS cnt, "
            f"SUM(TOTAL_RECEIVED) AS rcv, SUM(TOTAL_ACCEPTED) AS acc, "
            f"SUM(REJECTED) AS rej, SUM(LOSS) AS loss "
            f"FROM {self.database}.{self.schema_reporting}.VW_PRODUCTION_SUMMARY"
        )
        row = df.iloc[0]
        return {
            "import_count": 0,
            "production_record_count": int(row["cnt"] or 0),
            "account_count": 0,
            "flock_count": 0,
            "total_received": float(row["rcv"] or 0),
            "total_accepted": float(row["acc"] or 0),
            "total_rejected": float(row["rej"] or 0),
            "total_loss": float(row["loss"] or 0),
        }