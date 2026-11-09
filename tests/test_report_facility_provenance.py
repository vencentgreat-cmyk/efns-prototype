"""Synthetic production periods/provenance; no live data or approval changes."""

import sqlite3
import re
from pathlib import Path

import pandas as pd
import pytest

from app.services.report_builder import build_report
from data.repositories.mock import MockRepository
from tests.auth_support import authenticated_app
from tests.test_report_account_roles import repo, run, assert_exports_match


@pytest.mark.parametrize("empty_batches", [False, True])
def test_missing_import_keeps_row_period_and_filters(repo, empty_batches):
    repo._production["REPORTING_YEAR"] = [2026, 2025, 2026, None]
    repo._production["REPORTING_WEEK"] = [2, 3, 4, None]
    if empty_batches:
        repo._import_batches = []
    original = repo._production.copy(deep=True)
    filtered = repo.get_production_records(reporting_year=2026, reporting_week=2)
    assert filtered.PRODUCTION_ID.tolist() == ["p1"]
    result = run(repo, "Production Records", ["PRODUCTION_ID", "REPORTING_YEAR", "REPORTING_WEEK", "TOTAL_RECEIVED"],
        filters={"reporting_year": 2026, "reporting_week": 2})
    assert result["Production ID"].tolist() == ["p1"]
    assert result["Reporting Year"].tolist() == [2026]
    assert result["Reporting Week"].tolist() == [2]
    assert_exports_match(result)
    pd.testing.assert_frame_equal(original, repo._production)


def test_unknown_period_not_inferred_from_batch(repo):
    batch = repo._import_batches[0]
    repo._production.loc[3, "IMPORT_ID"] = batch["IMPORT_ID"]
    repo._production["REPORTING_YEAR"] = None
    repo._production["REPORTING_WEEK"] = None
    records = repo.get_production_records()
    assert records.REPORTING_YEAR.isna().all() and records.REPORTING_WEEK.isna().all()
    assert repo.get_production_records(reporting_year=batch["REPORTING_YEAR"]).empty


def provenance_fixture(repo):
    repo._facilities = pd.concat([repo._facilities, pd.DataFrame([
        {"FACILITY_ID": "other-facility", "ACCOUNT_ID": "c", "FACILITY_NAME": "Synthetic alternative"}
    ])], ignore_index=True)
    repo._production.loc[0, "FACILITY_ID"] = "other-facility"
    return repo


def test_provenance_conflicts_and_exports_preserve_both_original_references(repo):
    provenance_fixture(repo)
    repo._production["TOTAL"] = [10, 20, 30, -5]
    original = repo._production.copy(deep=True)
    fields = ["PRODUCTION_ID", "FACILITY_ID", "FLOCK_FACILITY_ID", "REPORT_FACILITY_ID",
              "REPORT_FACILITY_SOURCE", "FACILITY_REFERENCE_DIFFERENCE", "PRODUCER_ACCOUNT_NAME",
              "FLOCK_ACCOUNT_NAME", "FACILITY_ACCOUNT_NAME", "TOTAL_RECEIVED", "TOTAL"]
    result = run(repo, "Production Records", fields)
    assert result["Facility Source"].tolist() == ["Production record", "Linked Flock", "Production record", "No available reference"]
    assert result["Facility Reference Comparison"].tolist() == ["Different references - review", "Not comparable", "Not comparable", "Not comparable"]
    first = result.iloc[0]
    assert first["Production Facility ID"] == "other-facility"
    assert first["Flock Facility ID"] == "facility"
    assert first["Report Facility ID"] == "other-facility"
    assert first["Flock Account"] == "Synthetic flock owner"
    assert first["Producer Account"] == first["Facility Account"] == "Synthetic producer"
    assert result["Total Received"].sum() == 55
    assert result["Source Total"].sum() == 55 and result.iloc[3]["Source Total"] == -5
    assert_exports_match(result)
    legacy = build_report(repo, ["PRODUCTION_FACILITY_ID", "FLOCK_FACILITY_ID", "FACILITY_SOURCE", "FACILITY_REFERENCE_COMPARISON"])
    assert legacy.iloc[0]["Facility Reference Comparison"] == "Different references - review"
    pd.testing.assert_frame_equal(original, repo._production)
    filtered = run(repo, "Production Records", fields, filters={"account_id": "c", "flock_account_id": "a", "facility_account_id": "c"})
    assert filtered["Production ID"].tolist() == ["p1"]
    assert_exports_match(filtered)


def test_same_guid_case_is_not_reported_as_conflicting(repo):
    repo._production.loc[0, "FACILITY_ID"] = "FACILITY"
    result = run(repo, "Production Records", ["FACILITY_REFERENCE_DIFFERENCE", "FACILITY_ID", "FLOCK_FACILITY_ID"])
    assert result.iloc[0]["Facility Reference Comparison"] == "Same reference"
    assert result.iloc[0]["Production Facility ID"] == "FACILITY"
    assert result.iloc[0]["Flock Facility ID"] == "facility"


def test_production_does_not_silently_ignore_calendar_date_filters(repo):
    with pytest.raises(ValueError, match="Reporting Year and Reporting Week"):
        run(repo, "Production Records", ["PRODUCTION_ID"], filters={"date_from": "2026-01-01"})


def test_size_view_actual_select_preserves_period_and_size_grain():
    sql = (Path(__file__).parents[1] / "sql" / "04_reporting_views.sql").read_text(encoding="utf-8")
    statement = sql.split("VW_PRODUCTION_SIZE_DETAIL COPY GRANTS AS", 1)[1].split(";", 1)[0]
    assert "ib.REPORTING_YEAR" not in statement and "ib.REPORTING_WEEK" not in statement
    statement = statement.replace("EFNS_DEV.CORE.", "core_")
    with sqlite3.connect(":memory:") as connection:
        connection.execute("CREATE TABLE core_PRODUCTION_RECORD(PRODUCTION_ID TEXT,GRADER_NUMBER TEXT,BARN_IDENTITY TEXT,EGG_COLOUR TEXT,REPORTING_YEAR INTEGER,REPORTING_WEEK INTEGER)")
        connection.execute("CREATE TABLE core_PRODUCTION_SIZE_BREAKDOWN(SIZE_BREAKDOWN_ID TEXT,PRODUCTION_ID TEXT,SIZE_BAND TEXT,QUANTITY NUMERIC)")
        connection.executemany("INSERT INTO core_PRODUCTION_RECORD VALUES(?,?,?,?,?,?)", [("p1",None,None,None,2026,2),("p2",None,None,None,2025,3)])
        connection.executemany("INSERT INTO core_PRODUCTION_SIZE_BREAKDOWN VALUES(?,?,?,?)", [("s1","p1","Large",10),("s2","p1","Small",-2)])
        rows = pd.read_sql_query(statement, connection)
    assert len(rows) == 3  # Two actual size records + one no-size placeholder.
    assert rows.SIZE_BREAKDOWN_ID.notna().sum() == 2
    assert rows.loc[rows.PRODUCTION_ID == "p1", "REPORTING_WEEK"].tolist() == [2, 2]
    assert rows.loc[rows.PRODUCTION_ID == "p2", "REPORTING_YEAR"].tolist() == [2025]
    assert rows.QUANTITY.sum() == 8
    assert_exports_match(rows)


def test_summary_actual_select_retains_missing_imports_and_signed_source_total():
    sql = (Path(__file__).parents[1] / "sql" / "04_reporting_views.sql").read_text(encoding="utf-8")
    statement = sql.split("VW_PRODUCTION_SUMMARY COPY GRANTS AS", 1)[1].split(";", 1)[0]
    fields = list(dict.fromkeys(re.findall(r"\bpr\.([A-Z_]+)\b", statement)))
    statement = statement.replace("EFNS_DEV.CORE.", "core_").replace("EFNS_DEV.RAW.", "raw_")
    with sqlite3.connect(":memory:") as connection:
        connection.execute("CREATE TABLE core_PRODUCTION_RECORD(" + ",".join(f"{field} NUMERIC" for field in fields) + ")")
        connection.execute("CREATE TABLE raw_IMPORT_BATCH(IMPORT_ID TEXT,FILENAME TEXT,SOURCE TEXT,UPLOAD_TIMESTAMP TEXT)")
        records = [{"PRODUCTION_ID": "p1", "IMPORT_ID": "missing", "REPORTING_YEAR": 2026, "REPORTING_WEEK": 2, "TOTAL": 10},
                   {"PRODUCTION_ID": "p2", "IMPORT_ID": None, "REPORTING_YEAR": 2025, "REPORTING_WEEK": 3, "TOTAL": -2}]
        connection.executemany("INSERT INTO core_PRODUCTION_RECORD VALUES(" + ",".join("?" for _ in fields) + ")",
                               [[record.get(field) for field in fields] for record in records])
        rows = pd.read_sql_query(statement, connection)
    assert rows.PRODUCTION_ID.tolist() == ["p1", "p2"]
    assert rows.REPORTING_YEAR.tolist() == [2026, 2025]
    assert rows.REPORTING_WEEK.tolist() == [2, 3]
    assert rows.TOTAL.sum() == 8 and (rows.TOTAL < 0).sum() == 1
    assert rows.FILENAME.isna().all()


def test_deployment_verification_sql_is_read_only_and_size_grain_specific():
    path = Path(__file__).parents[1] / "sql" / "reporting_deployment_checks.sql"
    source = "\n".join(line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("--"))
    statements = [statement.strip() for statement in source.split(";") if statement.strip()]
    assert all(statement.upper().startswith(("SELECT", "WITH", "SHOW")) for statement in statements)
    assert "SIZE_BREAKDOWN_ID IS NOT DISTINCT FROM" in source
    assert "EXPECTED_SIZE_VIEW_ROWS" in source
    assert "MISSING_NO_SIZE_PLACEHOLDERS" in source
    assert "SIZE_PERIOD_MISMATCHES" in source


def test_page_displays_provenance_and_row_period_filters(repo, tmp_path, monkeypatch):
    provenance_fixture(repo)
    repo._production["REPORTING_YEAR"] = [2026, 2025, 2026, None]
    repo._production["REPORTING_WEEK"] = [2, 3, 4, None]
    app = authenticated_app(Path(__file__).parents[1] / "app" / "Home.py", tmp_path, monkeypatch)
    app.session_state._base_repo = repo
    app.session_state.repo = repo
    app.switch_page("pages/4_Reports.py").run()
    app.radio(key="report_center_section").set_value("Customize Report").run()
    app.selectbox(key="custom_report_dataset").set_value("Production Records").run()
    assert not app.exception
    assert app.checkbox(key="custom_filter_use_dates").disabled
    app.selectbox(key="custom_filter_reporting_year").set_value(2026).run()
    app.selectbox(key="custom_filter_reporting_week").set_value(2)
    next(button for button in app.button if button.label == "Run Report").click().run()
    assert not app.exception and not app.error
    result = app.session_state.custom_report_result
    assert result["Production ID"].tolist() == ["p1"]
    assert result.iloc[0]["Facility Source"] == "Production record"
    assert result.iloc[0]["Facility Reference Comparison"] == "Different references - review"
    assert result.iloc[0]["Flock Facility ID"] == "facility"
    assert any(isinstance(table.value, pd.DataFrame) and table.value.equals(result) for table in app.dataframe)
    assert_exports_match(result)
