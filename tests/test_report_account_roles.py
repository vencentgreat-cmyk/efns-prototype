"""Report-only cross-Account fixtures; no migration or ownership approval."""

from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.services.report_builder import build_report
from app.services.report_center import build_custom_report, report_csv, report_xlsx
from data.repositories.mock import MockRepository
from tests.test_report_center import user
from tests.auth_support import authenticated_app


@pytest.fixture
def repo():
    repository = MockRepository()
    repository._accounts = pd.DataFrame([
        {"ACCOUNT_ID": "a", "ORGANIZATION_NAME": "Synthetic flock owner"},
        {"ACCOUNT_ID": "b", "ORGANIZATION_NAME": "Synthetic facility owner"},
        {"ACCOUNT_ID": "c", "ORGANIZATION_NAME": "Synthetic producer"},
    ])
    repository._facilities = pd.DataFrame([
        {"FACILITY_ID": "facility", "ACCOUNT_ID": "b", "FACILITY_NAME": "Synthetic shared facility", "STATUS": "Active"},
    ])
    repository._flocks = pd.DataFrame([
        {"FLOCK_ID": "f1", "FLOCK_NUMBER": "Synthetic F1", "ACCOUNT_ID": "a", "FACILITY_ID": "facility", "BIRD_COUNT": 10},
        {"FLOCK_ID": "f2", "FLOCK_NUMBER": "Synthetic F2", "ACCOUNT_ID": "a", "FACILITY_ID": "facility", "BIRD_COUNT": 20},
        {"FLOCK_ID": "f3", "FLOCK_NUMBER": "Synthetic F3", "ACCOUNT_ID": "a", "FACILITY_ID": None, "BIRD_COUNT": 30},
    ])
    repository._flock_transactions = pd.DataFrame([
        {"FLOCK_TRANSACTION_ID": "t1", "FLOCK_ID": "f1", "QUANTITY": 5},
        {"FLOCK_TRANSACTION_ID": "t2", "FLOCK_ID": "f2", "QUANTITY": -2},
        {"FLOCK_TRANSACTION_ID": "t3", "FLOCK_ID": "missing", "QUANTITY": 4},
    ])
    repository._flock_transactions["TRANSACTION_DATE"] = "2026-01-01"
    # A missing import, unlinked production, and an independent direct Facility
    # reference all remain visible. Producer never falls back to another role.
    repository._production = pd.DataFrame([
        {"PRODUCTION_ID": "p1", "IMPORT_ID": "missing-import", "PRODUCER_ACCOUNT_ID": "c", "FLOCK_ID": "f1", "FACILITY_ID": "facility", "TOTAL_RECEIVED": 10},
        {"PRODUCTION_ID": "p2", "IMPORT_ID": None, "PRODUCER_ACCOUNT_ID": "c", "FLOCK_ID": "f2", "FACILITY_ID": None, "TOTAL_RECEIVED": 20},
        {"PRODUCTION_ID": "p3", "IMPORT_ID": None, "PRODUCER_ACCOUNT_ID": "a", "FLOCK_ID": None, "FACILITY_ID": "facility", "TOTAL_RECEIVED": 30},
        {"PRODUCTION_ID": "p4", "IMPORT_ID": None, "PRODUCER_ACCOUNT_ID": None, "FLOCK_ID": "missing", "FACILITY_ID": None, "TOTAL_RECEIVED": -5},
    ])
    return repository


def run(repo, dataset, fields, **kwargs):
    return build_custom_report(repo, user=user(), dataset=dataset, selected_fields=fields, **kwargs)


def assert_exports_match(frame):
    for exported in (pd.read_csv(BytesIO(report_csv(user(), frame))),
                     pd.read_excel(BytesIO(report_xlsx(user(), frame)))):
        pd.testing.assert_frame_equal(exported.fillna(""), frame.fillna(""), check_dtype=False)


def test_flock_report_keeps_both_accounts_and_unassigned_flock(repo):
    result = run(repo, "Flocks", ["FLOCK_ID", "FLOCK_ACCOUNT_NAME", "FACILITY_ACCOUNT_NAME", "BIRD_COUNT"])
    assert len(result) == 3 and result["Bird Count"].sum() == 60
    hosted = result[result["Flock ID"] == "f1"].iloc[0]
    assert hosted["Flock Account"] == "Synthetic flock owner"
    assert hosted["Facility Account"] == "Synthetic facility owner"
    assert pd.isna(result.iloc[2]["Facility Account"])
    assert_exports_match(result)
    legacy = build_report(repo, ["FLOCK_NUMBER", "FACILITY_NAME", "FLOCK_ACCOUNT", "FACILITY_ACCOUNT"])
    assert len(legacy) == 3
    assert legacy.iloc[0]["Facility Name"] == "Synthetic shared facility"
    assert legacy.iloc[0]["Flock Account"] != legacy.iloc[0]["Facility Account"]


def test_production_preserves_producer_ownership_and_all_records(repo):
    result = run(repo, "Production Records", ["PRODUCTION_ID", "PRODUCER_ACCOUNT_ID", "PRODUCER_ACCOUNT_NAME",
        "FLOCK_ACCOUNT_NAME", "FACILITY_ACCOUNT_NAME", "TOTAL_RECEIVED"])
    assert result["Production ID"].tolist() == ["p1", "p2", "p3", "p4"]
    assert result["Total Received"].sum() == 55
    assert result.iloc[0]["Producer Account"] == "Synthetic producer"
    assert result.iloc[0]["Flock Account"] == "Synthetic flock owner"
    assert result.iloc[0]["Facility Account"] == "Synthetic facility owner"
    assert pd.isna(result.iloc[3]["Producer Account"])
    assert_exports_match(result)
    legacy = build_report(repo, ["ACCOUNT_NAME", "FLOCK_ACCOUNT", "FACILITY_ACCOUNT", "TOTAL_RECEIVED"])
    assert len(legacy) == 4 and legacy["Total Received"].sum() == 55
    assert legacy.iloc[0]["Account Name"] == "Synthetic producer"
    assert pd.isna(legacy.iloc[3]["Account Name"])


@pytest.mark.parametrize("dataset, quantity, expected", [
    ("Flocks", "BIRD_COUNT", 30), ("Flock Transactions", "QUANTITY", 3),
    ("Production Records", "TOTAL_RECEIVED", 30),
])
def test_filters_grouping_and_exports_use_the_same_owner_and_grain(repo, dataset, quantity, expected):
    filters = {"facility_account_id": "b", "facility_id": "facility"}
    filters["account_id"] = "c" if dataset == "Production Records" else "a"
    detail = run(repo, dataset, ["FLOCK_ACCOUNT_NAME", "FACILITY_ACCOUNT_NAME", quantity], filters=filters)
    assert len(detail) == 2
    assert detail.iloc[:, -1].sum() == expected
    summary = run(repo, dataset, ["FACILITY_ACCOUNT_NAME", quantity], filters=filters,
        group_by=["FACILITY_ACCOUNT_NAME"], aggregations={quantity: "sum"})
    assert summary.iloc[0, -1] == expected
    assert_exports_match(detail)
    assert_exports_match(summary)
    wrong_owner = run(repo, dataset, [quantity], filters={"account_id": "b"})
    assert wrong_owner.empty


def test_producer_and_flock_owner_filters_are_independent(repo):
    fields = ["PRODUCTION_ID", "TOTAL_RECEIVED", "FLOCK_ACCOUNT_ID"]
    assert run(repo, "Production Records", fields, filters={"account_id": "c", "flock_account_id": "a"})["Production ID"].tolist() == ["p1", "p2"]
    assert run(repo, "Production Records", fields, filters={"account_id": "a", "flock_account_id": "a"}).empty


def test_transactions_keep_missing_parent_and_signed_values(repo):
    result = run(repo, "Flock Transactions", ["FLOCK_TRANSACTION_ID", "FLOCK_ACCOUNT_NAME", "FACILITY_ACCOUNT_NAME", "QUANTITY"])
    assert len(result) == 3 and result.Quantity.sum() == 7
    assert pd.isna(result.iloc[2]["Flock Account"])
    assert_exports_match(result)


@pytest.mark.parametrize("parent", ["_accounts", "_facilities", "_flocks"])
def test_duplicate_parent_keys_do_not_inflate_totals(repo, parent):
    frame = getattr(repo, parent)
    setattr(repo, parent, pd.concat([frame, frame.iloc[[0]]], ignore_index=True))
    if parent == "_accounts":
        # Mock's normal Account listing de-duplicates; exercise a repository
        # response that exposes corrupt parent keys to the report boundary.
        repo.get_accounts = lambda: repo._accounts.copy()
    with pytest.raises(pd.errors.MergeError):
        run(repo, "Production Records", ["FACILITY_ACCOUNT_NAME", "TOTAL_RECEIVED"])


def test_duplicate_primary_records_cannot_be_silently_summed(repo):
    repo._production = pd.concat([repo._production, repo._production.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate report record identifiers"):
        run(repo, "Production Records", ["PRODUCER_ACCOUNT_ID", "TOTAL_RECEIVED"],
            group_by=["PRODUCER_ACCOUNT_ID"], aggregations={"TOTAL_RECEIVED": "sum"})


def test_empty_filtered_relationship_report_preserves_export_columns(repo):
    result = run(repo, "Flocks", ["FLOCK_ID", "FLOCK_ACCOUNT_NAME", "FACILITY_ACCOUNT_NAME"], filters={"account_id": "missing"})
    assert result.empty
    assert list(result.columns) == ["Flock ID", "Flock Account", "Facility Account"]
    assert_exports_match(result)


def test_null_references_do_not_match_null_parent_records(repo):
    repo._flocks = pd.concat([repo._flocks, pd.DataFrame([
        {"FLOCK_ID": None, "FLOCK_NUMBER": "Must not match null", "ACCOUNT_ID": "a", "FACILITY_ID": "facility"}
    ])], ignore_index=True)
    result = run(repo, "Production Records", ["PRODUCTION_ID", "FLOCK_ACCOUNT_NAME", "FACILITY_ACCOUNT_NAME", "TOTAL_RECEIVED"])
    unlinked = result[result["Production ID"] == "p3"].iloc[0]
    assert pd.isna(unlinked["Flock Account"])
    assert unlinked["Facility Account"] == "Synthetic facility owner"
    assert len(result) == 4 and result["Total Received"].sum() == 55


def test_reporting_view_sql_retains_records_and_exposes_account_roles():
    sql = (Path(__file__).parents[1] / "sql" / "04_reporting_views.sql").read_text(encoding="utf-8")
    assert sql.count("LEFT JOIN EFNS_DEV.RAW.IMPORT_BATCH ib ON pr.IMPORT_ID = ib.IMPORT_ID") == 1
    assert "fl.ACCOUNT_ID            AS FLOCK_ACCOUNT_ID" in sql
    assert "f.ACCOUNT_ID             AS FACILITY_ACCOUNT_ID" in sql
    assert "ON fl.FACILITY_ID = f.FACILITY_ID" in sql


def test_report_page_filters_grouping_and_display_share_same_result(repo, tmp_path, monkeypatch):
    app = authenticated_app(Path(__file__).parents[1] / "app" / "Home.py", tmp_path, monkeypatch)
    app.session_state._base_repo = repo
    app.session_state.repo = repo
    app.switch_page("pages/4_Reports.py").run()
    app.radio(key="report_center_section").set_value("Customize Report").run()
    app.selectbox(key="custom_report_dataset").set_value("Production Records").run()
    assert not app.exception
    assert app.selectbox(key="custom_filter_account").label == "Producer Account"
    app.multiselect(key="custom_report_columns").set_value(["Producer Account", "Flock Account", "Facility Account", "Total Received"]).run()
    for key, name in [("custom_filter_account", "Synthetic producer"),
                      ("custom_filter_facility_account", "Synthetic facility owner"),
                      ("custom_filter_flock_account", "Synthetic flock owner")]:
        widget = app.selectbox(key=key)
        widget.set_value(next(option for option in widget.options if option.startswith(name)))
    app.multiselect(key="custom_report_group").set_value(["Producer Account", "Flock Account", "Facility Account"])
    app.selectbox(key="custom_report_aggregate_field").set_value("Total Received").run()
    app.selectbox(key="custom_report_aggregate").set_value("sum")
    next(button for button in app.button if button.label == "Run Report").click().run()
    assert not app.exception and not app.error
    result = app.session_state.custom_report_result
    assert result.to_dict("records") == [{"Producer Account": "Synthetic producer", "Flock Account": "Synthetic flock owner",
        "Facility Account": "Synthetic facility owner", "Total Received": 30}]
    assert any(isinstance(table.value, pd.DataFrame) and table.value.equals(result) for table in app.dataframe)
    assert_exports_match(result)
