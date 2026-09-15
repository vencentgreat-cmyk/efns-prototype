# ============================================================
# EFNS Prototype v0.1 — Repository Abstract Base
# ============================================================
"""Abstract base for data access. Implementations: Mock, Snowflake."""

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd


class RepositoryError(Exception):
    """Base exception for repository errors."""
    pass


class RepositoryConfigurationError(RepositoryError):
    """Raised when a persistent repository is not configured for use."""


class RepositoryConnectionError(RepositoryError):
    """Raised when a configured data service cannot be reached safely."""


class RepositoryOperationError(RepositoryError):
    """Safe, correlatable Snowflake operation failure.

    Bound values and raw server messages are deliberately excluded. Snowflake's
    query ID, error code, and SQLSTATE are safe operational references that an
    administrator can correlate with query history.
    """

    def __init__(
        self,
        operation: str,
        entity: str,
        *,
        query_id: str | None = None,
        error_code: str | None = None,
        sql_state: str | None = None,
        error_type: str | None = None,
    ) -> None:
        self.operation = str(operation or "SQL").upper()
        self.entity = str(entity or "Snowflake object").upper()
        self.query_id = query_id
        self.error_code = error_code
        self.sql_state = sql_state
        self.error_type = error_type
        references = []
        if query_id:
            references.append(f"query ID {query_id}")
        if error_code:
            references.append(f"code {error_code}")
        if sql_state:
            references.append(f"SQLSTATE {sql_state}")
        suffix = f" Reference: {', '.join(references)}." if references else ""
        super().__init__(
            f"Snowflake {self.operation} failed for {self.entity}.{suffix} "
            "Ask an administrator to correlate this reference with Snowflake query history."
        )


class ConcurrencyError(RepositoryError):
    """Raised when a record changed since the editor last loaded it.

    Signals an optimistic-locking conflict: the caller supplied an
    ``EXPECTED_UPDATED_AT`` stamp that no longer matches the stored row,
    meaning another editor saved first. The caller should reload and
    reapply, rather than silently overwriting the newer version.
    """
    pass


class BaseRepository(ABC):
    """Abstract repository interface for EFNS data access."""

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    @abstractmethod
    def get_accounts(
        self, statuses: tuple[str, ...] | None = None,
        role_field: str | None = None, keyword: str | None = None,
    ) -> pd.DataFrame:
        """Return all accounts."""
        ...

    @abstractmethod
    def get_account(self, account_id: str) -> Optional[dict]:
        """Return a single account by ID."""
        ...

    @abstractmethod
    def find_accounts_by_registration_number(
        self, registration_number: str
    ) -> pd.DataFrame:
        """Return every account matching an external registration number."""
        ...

    @abstractmethod
    def upsert_account(self, record: dict) -> str:
        """Insert or update an account. Returns account_id."""
        ...

    @abstractmethod
    def delete_account(self, account_id: str) -> bool:
        """Soft or hard delete. Returns True if deleted."""
        ...

    # Farm Locations / Dynamics "Other Addresses" (provisional)

    @abstractmethod
    def get_farm_locations(
        self, farm_location_id: Optional[str] = None,
        account_id: Optional[str] = None,
        statuses: tuple[str, ...] | None = None,
        keyword: str | None = None,
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_farm_location(self, farm_location_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    def upsert_farm_location(self, record: dict) -> str:
        ...

    @abstractmethod
    def delete_farm_location(self, farm_location_id: str) -> bool:
        ...

    # ------------------------------------------------------------------
    # Facilities
    # ------------------------------------------------------------------

    @abstractmethod
    def get_facilities(
        self, account_id: Optional[str] = None,
        statuses: tuple[str, ...] | None = None,
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def upsert_facility(self, record: dict) -> str:
        ...

    @abstractmethod
    def delete_facility(self, facility_id: str) -> bool:
        ...

    @abstractmethod
    def get_facility_details(
        self, facility_id: Optional[str] = None,
        account_id: Optional[str] = None,
        statuses: tuple[str, ...] | None = None,
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_facility_detail(self, detail_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    def upsert_facility_detail(self, record: dict) -> str:
        ...

    @abstractmethod
    def delete_facility_detail(self, detail_id: str) -> bool:
        ...

    # ------------------------------------------------------------------
    # Flocks
    # ------------------------------------------------------------------

    @abstractmethod
    def get_flocks(
        self, account_id: Optional[str] = None, facility_id: Optional[str] = None,
        facility_detail_id: Optional[str] = None,
        statuses: tuple[str, ...] | None = None,
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_flock(self, flock_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    def upsert_flock(self, record: dict) -> str:
        ...

    @abstractmethod
    def delete_flock(self, flock_id: str) -> bool:
        ...

    # ------------------------------------------------------------------
    # Flock Transactions
    # ------------------------------------------------------------------

    @abstractmethod
    def get_flock_transactions(
        self, flock_id: Optional[str] = None, account_id: Optional[str] = None,
        transaction_type: Optional[str] = None, date_from=None, date_to=None,
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def upsert_flock_transaction(self, record: dict) -> str:
        ...

    @abstractmethod
    def delete_flock_transaction(self, transaction_id: str) -> bool:
        ...

    # Quota management (provisional)
    @abstractmethod
    def get_quota_registrations(
        self,
        account_id: Optional[str] = None,
        status: Optional[str] = None,
        quota_type: Optional[str] = None,
        active_only: bool = False,
        statuses: tuple[str, ...] | None = None,
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_quota_registration(self, quota_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    def upsert_quota_registration(self, record: dict) -> str:
        ...

    @abstractmethod
    def delete_quota_registration(self, quota_id: str) -> bool:
        ...

    @abstractmethod
    def get_quota_transactions(
        self,
        account_id: Optional[str] = None,
        quota_id: Optional[str] = None,
        quota_type: Optional[str] = None,
        transaction_type: Optional[str] = None,
        date_from=None,
        date_to=None,
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_quota_transaction(self, transaction_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    def get_quota_summary(
        self, as_of_date, quota_type: str,
        account_id: Optional[str] = None, status: Optional[str] = "Active",
    ) -> pd.DataFrame:
        """Return one row per qualifying Quota Registration."""
        ...

    @abstractmethod
    def upsert_quota_transaction(self, record: dict) -> str:
        ...

    @abstractmethod
    def delete_quota_transaction(self, transaction_id: str) -> bool:
        ...

    # Salmonella testing (provisional)
    @abstractmethod
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
        ...

    @abstractmethod
    def get_salmonella_test(self, test_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    def upsert_salmonella_test(self, record: dict) -> str:
        ...

    @abstractmethod
    def delete_salmonella_test(self, test_id: str) -> bool:
        ...

    @abstractmethod
    def get_salmonella_test_samples(self, test_id: Optional[str] = None) -> pd.DataFrame:
        """Extension point; sample fields await Dataverse metadata."""
        ...

    # ------------------------------------------------------------------
    # Imports & Production
    # ------------------------------------------------------------------

    @abstractmethod
    def create_import_batch(self, record: dict) -> str:
        """Create an import batch record. Returns import_id."""
        ...

    @abstractmethod
    def get_import_batches(self) -> pd.DataFrame:
        ...

    @abstractmethod
    def find_import_by_hash(self, file_hash: str) -> Optional[dict]:
        """Return an existing import batch for an exact SHA-256 hash."""
        ...

    @abstractmethod
    def import_production_bundle(
        self,
        batch: dict,
        raw_rows: list[dict],
        records: pd.DataFrame,
        allow_duplicate: bool = False,
    ) -> tuple[str, int]:
        """Persist batch, raw rows, and normalized rows atomically."""
        ...

    @abstractmethod
    def insert_raw_rows(self, import_id: str, rows: list[dict]) -> int:
        """Preserve source rows and their technical validation state."""
        ...

    @abstractmethod
    def get_raw_rows(self, import_id: str) -> pd.DataFrame:
        """Return source rows stored for one import batch."""
        ...

    # Historical EIMS migration (provisional metadata contract)

    @abstractmethod
    def find_migration_by_hash(self, package_hash: str) -> Optional[dict]:
        ...

    @abstractmethod
    def get_migration_batches(self) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_migration_raw_rows(self, batch_id: str) -> pd.DataFrame:
        ...

    @abstractmethod
    def stage_migration_file(self, batch_id: str, filename: str, content: bytes) -> str:
        ...

    @abstractmethod
    def prepare_migration_batch(self, batch: dict, files: list[dict], raw_rows: list[dict]) -> str:
        ...

    @abstractmethod
    def commit_migration_batch(self, batch_id: str) -> dict:
        ...

    @abstractmethod
    def cleanup_synthetic_migration(self, batch_id: str) -> bool:
        ...

    @abstractmethod
    def insert_production_records(self, records: pd.DataFrame, import_id: str) -> int:
        """Insert production records. Returns count inserted."""
        ...

    @abstractmethod
    def get_production_records(
        self,
        reporting_year: Optional[int] = None,
        reporting_week: Optional[int] = None,
        grader_number: Optional[str] = None,
        barn_identity: Optional[str] = None,
        egg_colour: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_production_summary_metrics(self) -> dict:
        """Return aggregate summary metrics for the home page."""
        ...

    @abstractmethod
    def get_dashboard_metrics(self) -> dict:
        """Return operational counts used by the dashboard."""
        ...
