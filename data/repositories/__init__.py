# ============================================================
# EFNS Prototype v0.1 — Repository Factory
# ============================================================
"""Repository factory. Returns Mock or Snowflake repository based on config."""

import os

try:
    from dotenv import load_dotenv
except ImportError:  # Streamlit in Snowflake does not require python-dotenv.
    def load_dotenv() -> bool:
        return False

from app.runtime import RuntimeMode, current_runtime_mode
from data.repositories.base import BaseRepository
from data.repositories.base import RepositoryConfigurationError
from data.repositories.mock import MockRepository

load_dotenv()


def get_repository() -> BaseRepository:
    """Return the configured repository.
    
    Set REPOSITORY_MODE in .env to 'snowflake' for Snowflake, else defaults to mock.
    """
    default_mode = "snowflake" if current_runtime_mode() == RuntimeMode.SNOWFLAKE else "mock"
    mode = os.getenv("REPOSITORY_MODE", default_mode).strip().lower()
    if mode == "snowflake":
        # Lazy import so Snowflake connector is only required when used
        from data.repositories.snowflake import SnowflakeRepository
        return SnowflakeRepository()
    if mode == "mock":
        return MockRepository()
    raise RepositoryConfigurationError(
        "REPOSITORY_MODE must be either 'mock' or 'snowflake'."
    )
