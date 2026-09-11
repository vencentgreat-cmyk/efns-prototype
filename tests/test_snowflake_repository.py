"""Offline contract checks for parameterized Snowflake reads."""

import pandas as pd

from data.repositories.snowflake import SnowflakeRepository


def repository_without_connection():
    repo = SnowflakeRepository.__new__(SnowflakeRepository)
    repo.database = "EFNS_DEV"
    repo.schema_core = "CORE"
    repo.schema_raw = "RAW"
    repo.schema_reporting = "REPORTING"
    return repo


def test_flock_filters_are_passed_as_query_parameters():
    repo = repository_without_connection()
    captured = {}

    def query(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return pd.DataFrame()

    repo._query = query
    repo.get_flocks(account_id="account'quoted", facility_id="facility'quoted")

    assert "account'quoted" not in captured["sql"]
    assert "facility'quoted" not in captured["sql"]
    assert captured["sql"].count("%s") == 2
    assert captured["params"] == ("account'quoted", "facility'quoted")
