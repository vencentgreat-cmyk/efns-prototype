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


class BaseRepository(ABC):
    """Abstract repository interface for EFNS data access."""

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    @abstractmethod
    def get_accounts(self) -> pd.DataFrame:
        """Return all accounts."""
        ...

    @abstractmethod
    def get_account(self, account_id: str) -> Optional[dict]:
        """Return a single account by ID."""
        ...

    @abstractmethod
    def upsert_account(self, record: dict) -> str:
        """Insert or update an account. Returns account_id."""
        ...

    @abstractmethod
    def delete_account(self, account_id: str) -> bool:
        """Soft or hard delete. Returns True if deleted."""
        ...

    # ------------------------------------------------------------------
    # Facilities
    # ------------------------------------------------------------------

    @abstractmethod
    def get_facilities(self, account_id: Optional[str] = None) -> pd.DataFrame:
        ...

    @abstractmethod
    def upsert_facility(self, record: dict) -> str:
        ...

    @abstractmethod
    def delete_facility(self, facility_id: str) -> bool:
        ...

    # ------------------------------------------------------------------
    # Flocks
    # ------------------------------------------------------------------

    @abstractmethod
    def get_flocks(
        self, account_id: Optional[str] = None, facility_id: Optional[str] = None
    ) -> pd.DataFrame:
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
    def get_flock_transactions(self, flock_id: Optional[str] = None) -> pd.DataFrame:
        ...

    @abstractmethod
    def upsert_flock_transaction(self, record: dict) -> str:
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
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_production_summary_metrics(self) -> dict:
        """Return aggregate summary metrics for the home page."""
        ...