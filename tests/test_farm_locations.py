from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import pytest

from app.security import Role, User
from app.services.authorized_repository import AuthorizedRepository
from data.constants import ACCOUNT_ROLE_FIELDS, SAVED_VIEW_STATUS_GROUPS
from data.repositories.mock import MockRepository
from data.repositories.snowflake import MODEL, SnowflakeRepository, UTC_NOW_NTZ


def test_mock_farm_location_crud_views_search_and_optimistic_locking():
    repo = MockRepository(seed=77)
    account = repo.get_accounts(statuses=("Active",)).iloc[0]
    location_id = repo.upsert_farm_location({
        "ACCOUNT_ID": account.ACCOUNT_ID, "LOCATION_NAME": "DEV Test Location",
        "CITY": "Halifax", "POSTAL_CODE": "B3H 0A1", "PHONE": "902-555-0199",
        "STATUS": "Inactive",
    })
    stored = repo.get_farm_location(location_id)
    assert pd.Timestamp(stored["CREATED_AT"]).tzinfo is not None
    found = repo.get_farm_locations(statuses=("Inactive",), keyword="halifax")
    assert location_id in set(found["FARM_LOCATION_ID"])
    assert repo.get_farm_locations(statuses=("Active",))["STATUS"].eq("Active").all()
    created_at = stored["CREATED_AT"]
    repo.upsert_farm_location({**stored, "PHONE": "902-555-0100", "EXPECTED_UPDATED_AT": stored["UPDATED_AT"]})
    assert repo.get_farm_location(location_id)["CREATED_AT"] == created_at


def test_farm_location_validation_and_account_delete_protection():
    repo = MockRepository()
    account_id = repo.get_accounts().iloc[0]["ACCOUNT_ID"]
    with pytest.raises(ValueError, match="Location Name"):
        repo.upsert_farm_location({"ACCOUNT_ID": account_id, "LOCATION_NAME": "", "STATUS": "Active"})
    with pytest.raises(ValueError, match="existing Account"):
        repo.upsert_farm_location({"ACCOUNT_ID": "missing", "LOCATION_NAME": "X", "STATUS": "Active"})
    with pytest.raises(ValueError, match="related records"):
        repo.delete_account(account_id)


def test_saved_views_and_dynamic_roles_are_repository_driven():
    repo = MockRepository()
    assert SAVED_VIEW_STATUS_GROUPS["FLOCK"]["inactive"] == ("Planned", "Depopulated")
    for role_field, _label in ACCOUNT_ROLE_FIELDS:
        result = repo.get_accounts(statuses=("Active",), role_field=role_field)
        if not result.empty:
            assert result[role_field].fillna(False).all()
            assert not result["ACCOUNT_ID"].duplicated().any()
    with pytest.raises(ValueError, match="Unknown Account role"):
        repo.get_accounts(role_field="UNSAFE_SQL")


def test_ddl_model_grant_and_page_navigation_contracts():
    ddl = Path("sql/02_core_tables.sql").read_text(encoding="utf-8").upper()
    grants = Path("sql/06_least_privilege_grants.sql").read_text(encoding="utf-8").upper()
    page = Path("app/pages/18_Farm_Locations.py").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS EFNS_DEV.CORE.FARM_LOCATION" in ddl
    key, columns = MODEL["FARM_LOCATION"]
    assert key == "FARM_LOCATION_ID"
    for column in columns.split(): assert column in ddl
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE EFNS_DEV.CORE.FARM_LOCATION TO ROLE EFNS_DEV_APP_OWNER;" in grants
    assert "open_module(\"Accounts_&_Facilities\"" in page
    for forbidden in ("LinkColumn", "href=", "query_params", "snowflake.app"):
        assert forbidden not in page


class AuditStore:
    def __init__(self): self.events = []
    def record_action(self, actor, action, entity, entity_id, details=None):
        self.events.append((actor.email, action, entity, entity_id))


def test_authorized_repository_enforces_and_audits_farm_location():
    repo = MockRepository()
    account_id = repo.get_accounts().iloc[0]["ACCOUNT_ID"]
    store = AuditStore()
    editor = User("u1", "editor@nsegg.ca", "Editor", Role.DATA_EDITOR, True, False, "now", "now", None)
    protected = AuthorizedRepository(repo, store, editor)
    location_id = protected.upsert_farm_location({
        "ACCOUNT_ID": account_id, "LOCATION_NAME": "Audited Location", "STATUS": "Active"
    })
    assert store.events[-1][1:3] == ("CREATE", "FARM_LOCATION")
    assert protected.get_farm_location(location_id)["ACCOUNT_ID"] == account_id


def test_snowflake_farm_location_insert_order_and_server_timestamps():
    class Tx:
        def __init__(self): self.calls = []; self.location_exists = False
        def query(self, sql, params=None):
            self.calls.append(("query", sql, params))
            if "FROM EFNS_DEV.CORE.ACCOUNT" in sql:
                return pd.DataFrame([{"ACCOUNT_ID": "A1"}])
            if "SELECT CREATED_AT, UPDATED_AT FROM EFNS_DEV.CORE.FARM_LOCATION" in sql and self.location_exists:
                return pd.DataFrame([{"CREATED_AT": "2026-01-01", "UPDATED_AT": "2026-01-02"}])
            return pd.DataFrame()
        def execute(self, sql, params=None): self.calls.append(("execute", sql, params)); return 1
        def transaction(self):
            outer = self
            class C:
                def __enter__(self): return outer
                def __exit__(self, *_): return False
            return C()
    tx = Tx()
    repo = SnowflakeRepository(executor=tx)
    record = {"FARM_LOCATION_ID": "L1", "ACCOUNT_ID": "A1", "LOCATION_NAME": "Test", "ADDRESS_2": None, "STATUS": "Active"}
    assert repo.upsert_farm_location(record) == "L1"
    insert = next(call for call in tx.calls if call[0] == "execute" and "INSERT INTO EFNS_DEV.CORE.FARM_LOCATION" in call[1])
    assert UTC_NOW_NTZ in insert[1]
    assert "CREATED_AT" in insert[1] and "UPDATED_AT" in insert[1]
    assert "(FARM_LOCATION_ID, ACCOUNT_ID, LOCATION_NAME, ADDRESS_2, STATUS, CREATED_AT, UPDATED_AT)" in insert[1]
    assert insert[2] == ("L1", "A1", "Test", None, "Active")
    tx.location_exists = True
    repo.upsert_farm_location({**record, "LOCATION_NAME": "Updated", "EXPECTED_UPDATED_AT": "2026-01-02"})
    update = next(call for call in reversed(tx.calls) if call[0] == "execute" and "UPDATE EFNS_DEV.CORE.FARM_LOCATION" in call[1])
    assert "CREATED_AT" not in update[1]
    assert update[2] == ("A1", "Updated", None, "Active", "L1", "2026-01-02")
