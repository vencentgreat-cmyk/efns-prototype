"""Registered-page navigation must never depend on browser URLs."""

from pathlib import Path
from types import SimpleNamespace

import pytest

import app.navigation as navigation


class RerunRequested(Exception):
    pass


def fake_streamlit():
    def rerun():
        raise RerunRequested

    return SimpleNamespace(session_state={}, rerun=rerun, switch_page=lambda page: None)


def test_record_selection_is_kept_in_page_local_session_state(monkeypatch):
    fake = fake_streamlit()
    monkeypatch.setattr(navigation, "st", fake)
    monkeypatch.setattr(navigation, "_caller_scope", lambda: "3_Accounts_Facilities_Flocks")

    assert navigation.read_record_view() == navigation.RecordView("list", None)
    with pytest.raises(RerunRequested):
        navigation.open_view("detail", "account-123")
    assert navigation.read_record_view() == navigation.RecordView("detail", "account-123")

    with pytest.raises(RerunRequested):
        navigation.open_view("list")
    assert navigation.read_record_view() == navigation.RecordView("list", None)


def test_registered_page_switch_sets_target_state_without_url(monkeypatch):
    switched = []
    fake = fake_streamlit()
    fake.switch_page = switched.append
    monkeypatch.setattr(navigation, "st", fake)

    navigation.open_module("Quota_Transactions", "new", quota_id="quota-1")

    scope = "8_Quota_Transactions"
    assert fake.session_state[navigation._view_key(scope, "view")] == "new"
    assert fake.session_state[navigation._view_key(scope, "parameter_quota_id")] == "quota-1"
    assert switched == ["pages/8_Quota_Transactions.py"]


def test_operational_pages_do_not_generate_browser_record_links():
    root = Path(__file__).parents[1]
    pages = [
        root / "app/pages/3_Accounts_Facilities_Flocks.py",
        root / "app/pages/5_Flocks.py",
        root / "app/pages/6_Flock_Transactions.py",
        root / "app/pages/7_Quota_Registrations.py",
        root / "app/pages/8_Quota_Transactions.py",
        root / "app/pages/9_Salmonella_Tests.py",
        root / "app/pages/11_Facilities.py",
        root / "app/pages/13_Facility_Details.py",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in pages)
    for forbidden in (
        "LinkColumn",
        "current_page_url",
        "module_url",
        "module_view_url",
        "snowflake.app",
        "href=",
    ):
        assert forbidden not in source


def test_account_list_uses_selection_and_plain_account_name():
    source = (
        Path(__file__).parents[1] / "app/pages/3_Accounts_Facilities_Flocks.py"
    ).read_text(encoding="utf-8")
    assert 'selection_mode="single-row"' in source
    assert 'st.session_state["account_selected_id"] = selected_id' in source
    assert 'open_view("detail", selected_id)' in source
    assert '"ORGANIZATION_NAME": st.column_config.TextColumn("Account Name"' in source
