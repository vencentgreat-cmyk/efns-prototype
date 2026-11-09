import pandas as pd
import pytest

from data.validation import normalize_optional_account_links
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository


@pytest.mark.parametrize("value", [None, pd.NA, "", "None", "null", " NONE "])
def test_account_self_link_null_placeholders_are_true_null(value):
    record = {"PARENT_ACCOUNT_ID": value}
    assert normalize_optional_account_links(record)["PARENT_ACCOUNT_ID"] is None


def test_unknown_real_account_reference_is_not_cleared():
    value = "unknown-account-guid"
    assert normalize_optional_account_links({"PARENT_ACCOUNT_ID": value})["PARENT_ACCOUNT_ID"] == value
    repo = MockRepository()
    with pytest.raises(ValueError, match="existing Account"):
        repo.upsert_account({"ORGANIZATION_NAME": "Synthetic", "PARENT_ACCOUNT_ID": value})


def test_snowflake_account_write_normalizes_and_checks_links(monkeypatch):
    repo = SnowflakeRepository(executor=object())
    monkeypatch.setattr(repo, "get_account", lambda value: None)
    captured = []
    monkeypatch.setattr(repo, "_upsert", lambda table, record: captured.append(record) or "synthetic-id")
    repo.upsert_account({"ORGANIZATION_NAME": "Synthetic", "PARENT_ACCOUNT_ID": "None"})
    assert captured[0]["PARENT_ACCOUNT_ID"] is None
    with pytest.raises(Exception, match="existing Account"):
        repo.upsert_account({"PARENT_ACCOUNT_ID": "unknown-guid"})
    assert len(captured) == 1
