# ============================================================
# EFNS Prototype v0.1 — Repository Factory
# ============================================================
"""Repository factory. Returns Mock or Snowflake repository based on config."""

import os

from dotenv import load_dotenv
from data.repositories.base import BaseRepository
from data.repositories.base import RepositoryConfigurationError
from data.repositories.mock import MockRepository

load_dotenv()


def get_repository() -> BaseRepository:
    """Return the configured repository.
    
    Set REPOSITORY_MODE in .env to 'snowflake' for Snowflake, else defaults to mock.
    """
    mode = os.getenv("REPOSITORY_MODE", "mock").strip().lower()
    if mode == "snowflake":
        # Lazy import so Snowflake connector is only required when used
        from data.repositories.snowflake import SnowflakeRepository
        return SnowflakeRepository()
    if mode == "mock":
        return MockRepository()
    raise RepositoryConfigurationError(
        "REPOSITORY_MODE must be either 'mock' or 'snowflake'."
    )
