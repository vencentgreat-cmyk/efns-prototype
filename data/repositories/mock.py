# ============================================================
# EFNS Prototype v0.1 — Mock Repository
# ============================================================
"""In-memory repository using pandas DataFrames for local development."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Optional

import pandas as pd

from data.repositories.base import BaseRepository, ConcurrencyError
from data.synthetic import generate_all
from data.validation import (
    validate_flock,
    validate_quota_registration,
    validate_quota_transaction,
    validate_salmonella_test,
)


def _stamp(value) -> Optional[str]:
    """Normalise an UPDATED_AT value to a comparable string.

    Records read back through pandas surface as ``pd.Timestamp`` while
    freshly written values are ``datetime.datetime``; comparing their ISO
    strings keeps optimistic-locking checks reliable across both types.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return pd.Timestamp(value).isoformat()
    except (ValueError, TypeError):
        return str(value)


class MockRepository(BaseRepository):
    """
    In-memory data store for prototyping without Snowflake.

    Uses synthetic data generated on init. Data is ephemeral (resets on restart).
    """

    def __init__(self, seed: int = 42):
        data = generate_all(seed=seed)
        self._accounts = data["accounts"].copy()
        self._facilities = data["facilities"].copy()
        self._facility_details = data["facility_details"].copy()
        self._flocks = data["flocks"].copy()
        self._flock_transactions = data["flock_transactions"].copy()
        self._quota_registrations = data["quota_registrations"].copy()
        self._quota_transactions = data["quota_transactions"].copy()
        self._salmonella_tests = data["salmonella_tests"].copy()
        self._salmonella_test_samples = data["salmonella_test_samples"].copy()
        self._production = data["production"].copy()
        self._size_breakdown = data["size_breakdown"].copy()
        self._import_batches: list[dict] = []
        self._raw_rows: list[dict] = []
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
            "CREATED_AT": dt.datetime.now(),
            "UPDATED_AT": dt.datetime.now(),
            "STATUS": "Committed",
            "ROW_COUNT": len(self._production),
            "ERROR_COUNT": 0,
            "NOTES": "Synthetic baseline data generated for prototyping.",
        }
        self._import_batches.append(batch)
        self._production["IMPORT_ID"] = import_id

    def _upsert_frame(self, attribute: str, key: str, record: dict) -> str:
        """Apply one timestamped, optimistic-locking upsert to a data frame."""
        values = dict(record)
        expected = values.pop("EXPECTED_UPDATED_AT", None)
        entity_id = values.get(key) or str(uuid.uuid4())
        values[key] = entity_id
        frame = getattr(self, attribute)
        for column in values:
            if column not in frame.columns:
                frame[column] = None
        matches = frame[frame[key] == entity_id].index
        if len(matches):
            index = matches[0]
            if expected is not None and _stamp(frame.loc[index].get("UPDATED_AT")) != _stamp(expected):
                raise ConcurrencyError(
                    "This record changed after it was opened. Reload it before saving again."
                )
            values["UPDATED_AT"] = dt.datetime.now()
            for column, value in values.items():
                frame.loc[index, column] = value
        else:
            if expected is not None:
                raise ConcurrencyError("This record no longer exists. Return to the list and reload.")
            now = dt.datetime.now()
            values.setdefault("CREATED_AT", now)
            values["UPDATED_AT"] = now
            frame = pd.concat([frame, pd.DataFrame([values])], ignore_index=True)
            setattr(self, attribute, frame)
        return entity_id

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    def get_accounts(self) -> pd.DataFrame:
        return self._accounts.copy()

    def get_account(self, account_id: str) -> Optional[dict]:
        match = self._accounts[self._accounts["ACCOUNT_ID"] == account_id]
        return match.iloc[0].to_dict() if len(match) else None

    def find_accounts_by_registration_number(
        self, registration_number: str
    ) -> pd.DataFrame:
        value = str(registration_number).strip().casefold()
        if not value:
            return self._accounts.iloc[0:0].copy()
        matches = (
            self._accounts["REGISTRATION_NUMBER"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.casefold()
            == value
        )
        return self._accounts[matches].copy()

    def upsert_account(self, record: dict) -> str:
        record = dict(record)
        aid = record.get("ACCOUNT_ID") or str(uuid.uuid4())
        registration = str(record.get("REGISTRATION_NUMBER") or "").strip()
        if registration:
            duplicates = self.find_accounts_by_registration_number(registration)
            duplicates = duplicates[duplicates["ACCOUNT_ID"] != aid]
            if not duplicates.empty:
                raise ValueError("Registration Number is already used by another Account.")
        for field, label in (
            ("PARENT_ACCOUNT_ID", "Parent Account"),
            ("GRADING_STATION_ACCOUNT_ID", "Grading Station"),
            ("PULLET_GROWER_ACCOUNT_ID", "Pullet Grower Account"),
        ):
            related_id = record.get(field)
            if related_id == aid:
                raise ValueError(f"Account cannot reference itself as {label}.")
            if related_id and self.get_account(related_id) is None:
                raise ValueError(f"{label} must reference an existing Account.")
        record["ACCOUNT_ID"] = aid
        return self._upsert_frame("_accounts", "ACCOUNT_ID", record)

    def delete_account(self, account_id: str) -> bool:
        lookup_columns = (
            "PARENT_ACCOUNT_ID",
            "GRADING_STATION_ACCOUNT_ID",
            "PULLET_GROWER_ACCOUNT_ID",
        )
        lookup_reference = any(
            column in self._accounts.columns
            and bool((self._accounts[column] == account_id).any())
            for column in lookup_columns
        )
        references = (
            lookup_reference
            or not self.get_facilities(account_id=account_id).empty
            or not self.get_flocks(account_id=account_id).empty
            or not self.get_quota_registrations(account_id=account_id).empty
            or not self.get_salmonella_tests(account_id=account_id).empty
        )
        if references:
            raise ValueError("Account cannot be deleted while related records exist.")
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
        return self._upsert_frame("_facilities", "FACILITY_ID", record)

    def delete_facility(self, facility_id: str) -> bool:
        if not self.get_flocks(facility_id=facility_id).empty or not self.get_facility_details(facility_id).empty:
            raise ValueError("Facility cannot be deleted while related records exist.")
        before = len(self._facilities)
        self._facilities = self._facilities[self._facilities["FACILITY_ID"] != facility_id]
        return len(self._facilities) < before

    def get_facility_details(self, facility_id: Optional[str] = None) -> pd.DataFrame:
        frame = self._facility_details.copy()
        if facility_id:
            frame = frame[frame["FACILITY_ID"] == facility_id]
        return frame

    def get_facility_detail(self, detail_id: str) -> Optional[dict]:
        matches = self._facility_details[
            self._facility_details["FACILITY_DETAIL_ID"] == detail_id
        ]
        return matches.iloc[0].to_dict() if not matches.empty else None

    def upsert_facility_detail(self, record: dict) -> str:
        facility_id = record.get("FACILITY_ID")
        if not facility_id or facility_id not in set(self._facilities["FACILITY_ID"]):
            raise ValueError("Facility Detail requires an existing Facility.")
        return self._upsert_frame("_facility_details", "FACILITY_DETAIL_ID", record)

    def delete_facility_detail(self, detail_id: str) -> bool:
        if "FACILITY_DETAIL_ID" in self._flocks and bool(
            (self._flocks["FACILITY_DETAIL_ID"] == detail_id).any()
        ):
            raise ValueError("Facility Detail cannot be deleted while a Flock references it.")
        before = len(self._facility_details)
        self._facility_details = self._facility_details[
            self._facility_details["FACILITY_DETAIL_ID"] != detail_id
        ]
        return len(self._facility_details) < before

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

    def get_flock(self, flock_id: str) -> Optional[dict]:
        match = self._flocks[self._flocks["FLOCK_ID"] == flock_id]
        return match.iloc[0].to_dict() if len(match) else None

    def upsert_flock(self, record: dict) -> str:
        errors = validate_flock(self, record)
        if errors:
            raise ValueError(" ".join(errors))
        return self._upsert_frame("_flocks", "FLOCK_ID", record)

    def delete_flock(self, flock_id: str) -> bool:
        production = self._production
        has_production = "FLOCK_ID" in production and bool((production["FLOCK_ID"] == flock_id).any())
        if (
            not self.get_flock_transactions(flock_id).empty
            or not self.get_salmonella_tests(flock_id=flock_id).empty
            or has_production
        ):
            raise ValueError("Flock cannot be deleted while related records exist.")
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
        if self.get_flock(record.get("FLOCK_ID", "")) is None:
            raise ValueError("Flock Transaction requires an existing Flock.")
        if float(record.get("QUANTITY") or 0) <= 0:
            raise ValueError("Transaction Quantity must be greater than zero.")
        return self._upsert_frame("_flock_transactions", "FLOCK_TRANSACTION_ID", record)

    def delete_flock_transaction(self, transaction_id: str) -> bool:
        before = len(self._flock_transactions)
        self._flock_transactions = self._flock_transactions[
            self._flock_transactions["FLOCK_TRANSACTION_ID"] != transaction_id
        ]
        return len(self._flock_transactions) < before

    # ------------------------------------------------------------------
    # Quota management
    # ------------------------------------------------------------------

    def get_quota_registrations(
        self,
        account_id: Optional[str] = None,
        status: Optional[str] = None,
        quota_type: Optional[str] = None,
        active_only: bool = False,
    ) -> pd.DataFrame:
        frame = self._quota_registrations.copy()
        if account_id:
            frame = frame[frame["ACCOUNT_ID"] == account_id]
        if status:
            frame = frame[frame["STATUS"] == status]
        if quota_type:
            frame = frame[frame["QUOTA_TYPE"] == quota_type]
        if active_only:
            today = pd.Timestamp(dt.date.today())
            frame = frame[frame["STATUS"] == "Active"]
            if "EFFECTIVE_DATE" in frame:
                frame = frame[
                    frame["EFFECTIVE_DATE"].isna()
                    | (pd.to_datetime(frame["EFFECTIVE_DATE"]) <= today)
                ]
            if "END_DATE" in frame:
                frame = frame[
                    frame["END_DATE"].isna()
                    | (pd.to_datetime(frame["END_DATE"]) >= today)
                ]
        return frame

    def get_quota_registration(self, quota_id: str) -> Optional[dict]:
        match = self._quota_registrations[self._quota_registrations["QUOTA_ID"] == quota_id]
        return match.iloc[0].to_dict() if len(match) else None

    def upsert_quota_registration(self, record: dict) -> str:
        errors = validate_quota_registration(self, record)
        if errors:
            raise ValueError(" ".join(errors))
        return self._upsert_frame("_quota_registrations", "QUOTA_ID", record)

    def delete_quota_registration(self, quota_id: str) -> bool:
        if (
            not self.get_quota_transactions(quota_id=quota_id).empty
            or bool((self._flocks["QUOTA_ID"] == quota_id).any())
        ):
            raise ValueError("Quota Registration cannot be deleted while related records exist.")
        before = len(self._quota_registrations)
        self._quota_registrations = self._quota_registrations[
            self._quota_registrations["QUOTA_ID"] != quota_id
        ]
        return len(self._quota_registrations) < before

    def get_quota_transactions(
        self,
        account_id: Optional[str] = None,
        quota_id: Optional[str] = None,
        quota_type: Optional[str] = None,
        transaction_type: Optional[str] = None,
        date_from=None,
        date_to=None,
    ) -> pd.DataFrame:
        frame = self._quota_transactions.copy()
        if account_id:
            frame = frame[
                (frame["OWNER_ACCOUNT_ID"] == account_id)
                | (frame["RELATED_ACCOUNT_ID"] == account_id)
            ]
        if quota_id:
            frame = frame[frame["QUOTA_ID"] == quota_id]
        if transaction_type:
            frame = frame[frame["TRANSACTION_TYPE"] == transaction_type]
        if quota_type:
            quota_ids = set(
                self.get_quota_registrations(quota_type=quota_type)["QUOTA_ID"]
            )
            frame = frame[frame["QUOTA_ID"].isin(quota_ids)]
        dates = pd.to_datetime(frame["EFFECTIVE_DATE"], errors="coerce")
        if date_from is not None:
            frame = frame[dates >= pd.Timestamp(date_from)]
            dates = pd.to_datetime(frame["EFFECTIVE_DATE"], errors="coerce")
        if date_to is not None:
            frame = frame[dates <= pd.Timestamp(date_to)]
        return frame

    def upsert_quota_transaction(self, record: dict) -> str:
        errors = validate_quota_transaction(self, record)
        if errors:
            raise ValueError(" ".join(errors))
        quota = self.get_quota_registration(record["QUOTA_ID"])
        stored = dict(record, OWNER_ACCOUNT_ID=quota["ACCOUNT_ID"])
        return self._upsert_frame("_quota_transactions", "QUOTA_TRANSACTION_ID", stored)

    def get_quota_transaction(self, transaction_id: str) -> Optional[dict]:
        matches = self._quota_transactions[
            self._quota_transactions["QUOTA_TRANSACTION_ID"] == transaction_id
        ]
        return matches.iloc[0].to_dict() if not matches.empty else None

    def delete_quota_transaction(self, transaction_id: str) -> bool:
        if "RELATED_TRANSACTION_ID" in self._quota_transactions and bool(
            (self._quota_transactions["RELATED_TRANSACTION_ID"] == transaction_id).any()
        ):
            raise ValueError("Quota Transaction cannot be deleted while another transaction references it.")
        before = len(self._quota_transactions)
        self._quota_transactions = self._quota_transactions[
            self._quota_transactions["QUOTA_TRANSACTION_ID"] != transaction_id
        ]
        return len(self._quota_transactions) < before

    # ------------------------------------------------------------------
    # Salmonella tests
    # ------------------------------------------------------------------

    def get_salmonella_tests(
        self,
        account_id: Optional[str] = None,
        facility_id: Optional[str] = None,
        flock_id: Optional[str] = None,
        permit_number: Optional[str] = None,
        test_result: Optional[str] = None,
        inspector: Optional[str] = None,
        case_number: Optional[str] = None,
        invoice_number: Optional[str] = None,
        date_from=None,
        date_to=None,
    ) -> pd.DataFrame:
        frame = self._salmonella_tests.copy()
        if account_id:
            frame = frame[frame["ACCOUNT_ID"] == account_id]
        if flock_id:
            frame = frame[frame["FLOCK_ID"] == flock_id]
        if facility_id:
            flock_ids = set(self.get_flocks(facility_id=facility_id)["FLOCK_ID"])
            frame = frame[frame["FLOCK_ID"].isin(flock_ids)]
        text_filters = (
            ("PERMIT_NUMBER", permit_number),
            ("TEST_RESULT", test_result),
            ("INSPECTOR", inspector),
            ("CASE_FILE_NUMBER", case_number),
            ("INVOICE_NUMBER", invoice_number),
        )
        for column, value in text_filters:
            if value:
                frame = frame[frame[column] == value]
        dates = pd.to_datetime(frame["TESTING_DATE"], errors="coerce")
        if date_from is not None:
            frame = frame[dates >= pd.Timestamp(date_from)]
            dates = pd.to_datetime(frame["TESTING_DATE"], errors="coerce")
        if date_to is not None:
            frame = frame[dates <= pd.Timestamp(date_to)]
        return frame

    def get_salmonella_test(self, test_id: str) -> Optional[dict]:
        match = self._salmonella_tests[
            self._salmonella_tests["SALMONELLA_TEST_ID"] == test_id
        ]
        return match.iloc[0].to_dict() if len(match) else None

    def upsert_salmonella_test(self, record: dict) -> str:
        errors = validate_salmonella_test(self, record)
        if errors:
            raise ValueError(" ".join(errors))
        return self._upsert_frame("_salmonella_tests", "SALMONELLA_TEST_ID", record)

    def delete_salmonella_test(self, test_id: str) -> bool:
        before = len(self._salmonella_tests)
        self._salmonella_tests = self._salmonella_tests[
            self._salmonella_tests["SALMONELLA_TEST_ID"] != test_id
        ]
        return len(self._salmonella_tests) < before

    def get_salmonella_test_samples(self, test_id: Optional[str] = None) -> pd.DataFrame:
        frame = self._salmonella_test_samples.copy()
        if test_id and not frame.empty:
            frame = frame[frame["SALMONELLA_TEST_ID"] == test_id]
        return frame

    # ------------------------------------------------------------------
    # Imports & Production
    # ------------------------------------------------------------------

    def create_import_batch(self, record: dict) -> str:
        """Create an import batch record. Returns import_id."""
        import_id = record.get("IMPORT_ID", str(uuid.uuid4()))
        record["IMPORT_ID"] = import_id
        record.setdefault("UPLOAD_TIMESTAMP", dt.datetime.now())
        record.setdefault("CREATED_AT", dt.datetime.now())
        record.setdefault("UPDATED_AT", dt.datetime.now())
        record.setdefault("STATUS", "Uploaded")
        record.setdefault("ROW_COUNT", 0)
        record.setdefault("ERROR_COUNT", 0)
        self._import_batches.append(record)
        return import_id

    def get_import_batches(self) -> pd.DataFrame:
        return pd.DataFrame(self._import_batches)

    def find_import_by_hash(self, file_hash: str) -> Optional[dict]:
        for batch in self._import_batches:
            if batch.get("FILE_HASH") == file_hash:
                return dict(batch)
        return None

    def import_production_bundle(
        self,
        batch: dict,
        raw_rows: list[dict],
        records: pd.DataFrame,
        allow_duplicate: bool = False,
    ) -> tuple[str, int]:
        file_hash = batch.get("FILE_HASH")
        if file_hash and self.find_import_by_hash(file_hash) and not allow_duplicate:
            raise ValueError("This exact file has already been imported.")
        snapshots = (
            [dict(item) for item in self._import_batches],
            [dict(item) for item in self._raw_rows],
            self._production.copy(deep=True),
        )
        try:
            import_id = self.create_import_batch(dict(batch))
            self.insert_raw_rows(import_id, raw_rows)
            count = self.insert_production_records(records, import_id)
            return import_id, count
        except Exception:
            self._import_batches, self._raw_rows, self._production = snapshots
            raise

    def insert_raw_rows(self, import_id: str, rows: list[dict]) -> int:
        for row in rows:
            stored = dict(row)
            stored.setdefault("RAW_ROW_ID", str(uuid.uuid4()))
            stored["IMPORT_ID"] = import_id
            stored.setdefault("VALIDATION_STATUS", "PENDING")
            stored.setdefault("MATCH_STATUS", "UNMATCHED")
            stored.setdefault("VALIDATION_MESSAGES", [])
            self._raw_rows.append(stored)
        return len(rows)

    def get_raw_rows(self, import_id: str) -> pd.DataFrame:
        rows = [row for row in self._raw_rows if row["IMPORT_ID"] == import_id]
        return pd.DataFrame(rows)

    def insert_production_records(self, records: pd.DataFrame, import_id: str) -> int:
        """Insert production records. Returns count inserted."""
        records = records.copy()
        records["IMPORT_ID"] = import_id
        now = dt.datetime.now()
        if "CREATED_AT" not in records.columns:
            records["CREATED_AT"] = now
        else:
            records["CREATED_AT"] = records["CREATED_AT"].fillna(now)
        if "UPDATED_AT" not in records.columns:
            records["UPDATED_AT"] = now
        else:
            records["UPDATED_AT"] = records["UPDATED_AT"].fillna(now)
        if "PRODUCTION_ID" not in records.columns:
            records["PRODUCTION_ID"] = [str(uuid.uuid4()) for _ in range(len(records))]
        # Transitional union model: preserve every incoming field until the
        # Dataverse-to-target model is finalized.
        all_columns = list(dict.fromkeys([*self._production.columns, *records.columns]))
        self._production = self._production.reindex(columns=all_columns)
        records = records.reindex(columns=all_columns)
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

    def get_dashboard_metrics(self) -> dict:
        today = dt.date.today()
        recent_cutoff = today - dt.timedelta(days=30)
        quota_dates = pd.to_datetime(
            self._quota_transactions["EFFECTIVE_DATE"], errors="coerce"
        ).dt.date
        return {
            "active_account_count": int((self._accounts["STATUS"] == "Active").sum()),
            "active_facility_count": int((self._facilities["STATUS"] == "Active").sum()),
            "active_flock_count": int((self._flocks["STATUS"] == "Active").sum()),
            "active_quota_count": len(self.get_quota_registrations(active_only=True)),
            "recent_quota_transaction_count": int((quota_dates >= recent_cutoff).sum()),
            "pending_salmonella_count": int(
                (self._salmonella_tests["TEST_RESULT"] == "Pending").sum()
            ),
            "attention_salmonella_count": int(
                self._salmonella_tests["TEST_RESULT"].isin(["Positive", "Inconclusive"]).sum()
            ),
            "production_record_count": len(self._production),
        }
