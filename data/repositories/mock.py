# ============================================================
# EFNS Prototype v0.1 — Mock Repository
# ============================================================
"""In-memory repository using pandas DataFrames for local development."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Optional

import pandas as pd

from data.repositories.base import BaseRepository
from data.synthetic import generate_all


class MockRepository(BaseRepository):
    """
    In-memory data store for prototyping without Snowflake.

    Uses synthetic data generated on init. Data is ephemeral (resets on restart).
    """

    def __init__(self, seed: int = 42):
        data = generate_all(seed=seed)
        self._accounts = data["accounts"].copy()
        self._facilities = data["facilities"].copy()
        self._flocks = data["flocks"].copy()
        self._flock_transactions = data["flock_transactions"].copy()
        self._production = data["production"].copy()
        self._size_breakdown = data["size_breakdown"].copy()
        self._import_batches: list[dict] = []
        # Link production to a synthetic import batch
        self._ensure_default_batch()

    def _ensure_default_batch(self):
        import_id = str(uuid.uuid4())
        batch = {
            "IMPORT_ID": import_id,
            "FILENAME": "synthetic_baseline.csv",
            "SOURCE": "Synthetic Generator",
            "REPORTING_YEAR": dt.date.today().year,
            "REPORTING_WEEK": 1,
            "UPLOAD_TIMESTAMP": dt.datetime.now(),
            "STATUS": "Committed",
            "ROW_COUNT": len(self._production),
            "ERROR_COUNT": 0,
            "NOTES": "Synthetic baseline data generated for prototyping.",
        }
        self._import_batches.append(batch)
        self._production["IMPORT_ID"] = import_id

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    def get_accounts(self) -> pd.DataFrame:
        return self._accounts.copy()

    def get_account(self, account_id: str) -> Optional[dict]:
        match = self._accounts[self._accounts["ACCOUNT_ID"] == account_id]
        return match.iloc[0].to_dict() if len(match) else None

    def upsert_account(self, record: dict) -> str:
        aid = record.get("ACCOUNT_ID", str(uuid.uuid4()))
        record["ACCOUNT_ID"] = aid
        record["UPDATED_AT"] = dt.datetime.now()
        idx = self._accounts[self._accounts["ACCOUNT_ID"] == aid].index
        if len(idx):
            for col in record:
                if col in self._accounts.columns:
                    self._accounts.loc[idx[0], col] = record[col]
        else:
            record.setdefault("CREATED_AT", dt.datetime.now())
            self._accounts = pd.concat(
                [self._accounts, pd.DataFrame([record])], ignore_index=True
            )
        return aid

    def delete_account(self, account_id: str) -> bool:
        before = len(self._accounts)
        self._accounts = self._accounts[self._accounts["ACCOUNT_ID"] != account_id]
        return len(self._accounts) < before

    # ------------------------------------------------------------------
    # Facilities
    # ------------------------------------------------------------------

    def get_facilities(self, account_id: Optional[str] = None) -> pd.DataFrame:
        df = self._facilities.copy()
        if account_id:
            df = df[df["ACCOUNT_ID"] == account_id]
        return df

    def upsert_facility(self, record: dict) -> str:
        fid = record.get("FACILITY_ID", str(uuid.uuid4()))
        record["FACILITY_ID"] = fid
        record["UPDATED_AT"] = dt.datetime.now()
        idx = self._facilities[self._facilities["FACILITY_ID"] == fid].index
        if len(idx):
            for col in record:
                if col in self._facilities.columns:
                    self._facilities.loc[idx[0], col] = record[col]
        else:
            record.setdefault("CREATED_AT", dt.datetime.now())
            self._facilities = pd.concat(
                [self._facilities, pd.DataFrame([record])], ignore_index=True
            )
        return fid

    def delete_facility(self, facility_id: str) -> bool:
        before = len(self._facilities)
        self._facilities = self._facilities[self._facilities["FACILITY_ID"] != facility_id]
        return len(self._facilities) < before

    # ------------------------------------------------------------------
    # Flocks
    # ------------------------------------------------------------------

    def get_flocks(
        self, account_id: Optional[str] = None, facility_id: Optional[str] = None
    ) -> pd.DataFrame:
        df = self._flocks.copy()
        if account_id:
            df = df[df["ACCOUNT_ID"] == account_id]
        if facility_id:
            df = df[df["FACILITY_ID"] == facility_id]
        return df

    def upsert_flock(self, record: dict) -> str:
        fid = record.get("FLOCK_ID", str(uuid.uuid4()))
        record["FLOCK_ID"] = fid
        record["UPDATED_AT"] = dt.datetime.now()
        idx = self._flocks[self._flocks["FLOCK_ID"] == fid].index
        if len(idx):
            for col in record:
                if col in self._flocks.columns:
                    self._flocks.loc[idx[0], col] = record[col]
        else:
            record.setdefault("CREATED_AT", dt.datetime.now())
            self._flocks = pd.concat(
                [self._flocks, pd.DataFrame([record])], ignore_index=True
            )
        return fid

    def delete_flock(self, flock_id: str) -> bool:
        before = len(self._flocks)
        self._flocks = self._flocks[self._flocks["FLOCK_ID"] != flock_id]
        return len(self._flocks) < before

    # ------------------------------------------------------------------
    # Flock Transactions
    # ------------------------------------------------------------------

    def get_flock_transactions(self, flock_id: Optional[str] = None) -> pd.DataFrame:
        df = self._flock_transactions.copy()
        if flock_id:
            df = df[df["FLOCK_ID"] == flock_id]
        return df

    def upsert_flock_transaction(self, record: dict) -> str:
        tid = record.get("FLOCK_TRANSACTION_ID", str(uuid.uuid4()))
        record["FLOCK_TRANSACTION_ID"] = tid
        idx = self._flock_transactions[
            self._flock_transactions["FLOCK_TRANSACTION_ID"] == tid
        ].index
        if len(idx):
            for col in record:
                if col in self._flock_transactions.columns:
                    self._flock_transactions.loc[idx[0], col] = record[col]
        else:
            record.setdefault("CREATED_AT", dt.datetime.now())
            self._flock_transactions = pd.concat(
                [self._flock_transactions, pd.DataFrame([record])], ignore_index=True
            )
        return tid

    # ------------------------------------------------------------------
    # Imports & Production
    # ------------------------------------------------------------------

    def create_import_batch(self, record: dict) -> str:
        """Create an import batch record. Returns import_id."""
        import_id = record.get("IMPORT_ID", str(uuid.uuid4()))
        record["IMPORT_ID"] = import_id
        record.setdefault("UPLOAD_TIMESTAMP", dt.datetime.now())
        record.setdefault("STATUS", "Uploaded")
        record.setdefault("ROW_COUNT", 0)
        record.setdefault("ERROR_COUNT", 0)
        self._import_batches.append(record)
        return import_id

    def get_import_batches(self) -> pd.DataFrame:
        return pd.DataFrame(self._import_batches)

    def insert_production_records(self, records: pd.DataFrame, import_id: str) -> int:
        """Insert production records. Returns count inserted."""
        records = records.copy()
        records["IMPORT_ID"] = import_id
        records["CREATED_AT"] = dt.datetime.now()
        if "PRODUCTION_ID" not in records.columns:
            records["PRODUCTION_ID"] = [str(uuid.uuid4()) for _ in range(len(records))]
        # Ensure column alignment
        for col in self._production.columns:
            if col not in records.columns and col not in ("SIZE_BREAKDOWN_ID",):
                records[col] = None
        # Only keep columns in _production, dropping extras from uploaded CSV
        keep_cols = [c for c in self._production.columns if c in records.columns]
        records = records[keep_cols]
        self._production = pd.concat([self._production, records], ignore_index=True)
        # Update batch
        for i, batch in enumerate(self._import_batches):
            if batch["IMPORT_ID"] == import_id:
                self._import_batches[i]["ROW_COUNT"] = len(records)
                self._import_batches[i]["STATUS"] = "Committed"
                break
        return len(records)

    def get_production_records(
        self,
        reporting_year: Optional[int] = None,
        reporting_week: Optional[int] = None,
        grader_number: Optional[str] = None,
        barn_identity: Optional[str] = None,
        egg_colour: Optional[str] = None,
    ) -> pd.DataFrame:
        # Join production to import batches for year/week
        ib = pd.DataFrame(self._import_batches)
        if ib.empty:
            return self._production.copy()
        df = self._production.merge(
            ib[["IMPORT_ID", "REPORTING_YEAR", "REPORTING_WEEK", "FILENAME", "SOURCE"]],
            on="IMPORT_ID",
            how="left",
            suffixes=("", "_IB"),
        )
        # Use the row-level reporting period, with its import batch as fallback,
        # so the displayed values and filters have the same meaning.
        for period_col in ("REPORTING_YEAR", "REPORTING_WEEK"):
            batch_col = f"{period_col}_IB"
            if period_col not in df.columns and batch_col in df.columns:
                df[period_col] = df[batch_col]
            elif batch_col in df.columns:
                df[period_col] = df[period_col].where(
                    df[period_col].notna(), df[batch_col]
                )
        if reporting_year is not None:
            if "REPORTING_YEAR" in df.columns:
                df = df[df["REPORTING_YEAR"] == reporting_year]
        if reporting_week is not None:
            if "REPORTING_WEEK" in df.columns:
                df = df[df["REPORTING_WEEK"] == reporting_week]
        if grader_number:
            df = df[df["GRADER_NUMBER"] == grader_number]
        if barn_identity:
            df = df[df["BARN_IDENTITY"] == barn_identity]
        if egg_colour:
            df = df[df["EGG_COLOUR"] == egg_colour]
        return df

    def get_production_summary_metrics(self) -> dict:
        pr = self._production
        ib = pd.DataFrame(self._import_batches)
        n_imports = len(ib)
        n_records = len(pr)
        n_accounts = len(self._accounts)
        n_flocks = len(self._flocks)
        total_received = pr["TOTAL_RECEIVED"].sum() if "TOTAL_RECEIVED" in pr.columns else 0
        total_accepted = pr["TOTAL_ACCEPTED"].sum() if "TOTAL_ACCEPTED" in pr.columns else 0
        total_rejected = pr["REJECTED"].sum() if "REJECTED" in pr.columns and pr["REJECTED"].notna().any() else 0
        total_loss = pr["LOSS"].sum() if "LOSS" in pr.columns and pr["LOSS"].notna().any() else 0
        return {
            "import_count": n_imports,
            "production_record_count": n_records,
            "account_count": n_accounts,
            "flock_count": n_flocks,
            "total_received": float(total_received),
            "total_accepted": float(total_accepted),
            "total_rejected": float(total_rejected),
            "total_loss": float(total_loss),
        }
