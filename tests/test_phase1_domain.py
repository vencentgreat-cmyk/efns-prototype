"""Domain-contract tests for connected production import groundwork."""

import io
from pathlib import Path

import pandas as pd

from app.services.report_builder import build_report
from data.constants import (
    EIMS_SOURCE_COLUMNS,
    MATCH_STATUS_UNMATCHED,
    SOURCE_TYPE_EIMS_IMPORT,
    SOURCE_TYPE_SYNTHETIC,
)
from data.importing import build_raw_rows, normalize_eims_records, read_eims_workbook
from data.repositories.mock import MockRepository


def sanitized_eims_source() -> pd.DataFrame:
    row = {column: 0 for column in EIMS_SOURCE_COLUMNS}
    row.update(
        {
            "Grader": "Sanitized Grader",
            "Producer #": "NS-1000",
            "Grader#": "G-101",
            "Week": "202635",
            "MarketingType": "Conventional",
            "Housing system": "Enriched",
            "Egg Type": "Table",
            "Colour": "White",
            "Subtotal": 98,
            "RJ": 1,
            "LK": 1,
            "Total": 100,
        }
    )
    return pd.DataFrame([row], columns=EIMS_SOURCE_COLUMNS)


def test_all_35_source_columns_are_read_from_sanitized_workbook():
    workbook = io.BytesIO()
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        sanitized_eims_source().to_excel(
            writer, sheet_name="EIMS 3", index=False, startrow=9
        )
    workbook.seek(0)

    loaded = read_eims_workbook(workbook)

    assert len(EIMS_SOURCE_COLUMNS) == 35
    assert set(EIMS_SOURCE_COLUMNS).issubset(loaded.columns)
    assert loaded.iloc[0]["SOURCE_ROW_NUMBER"] == 11


def test_imported_fields_survive_repository_round_trip():
    repo = MockRepository(seed=42)
    normalized = normalize_eims_records(sanitized_eims_source())
    normalized["UNMAPPED_SOURCE_FIELD"] = "preserve me"
    import_id = repo.create_import_batch({"FILENAME": "sanitized.xlsx"})

    repo.insert_production_records(normalized, import_id)
    stored = repo.get_production_records()
    imported = stored[stored["IMPORT_ID"] == import_id].iloc[0]

    assert imported["UNMAPPED_SOURCE_FIELD"] == "preserve me"
    assert imported["PRODUCER_NUMBER"] == "NS-1000"
    assert imported["SOURCE_WEEK_CODE"] == "202635"
    assert imported["SOURCE_TYPE"] == SOURCE_TYPE_EIMS_IMPORT
    assert imported["MATCH_STATUS"] == MATCH_STATUS_UNMATCHED
    assert pd.isna(imported["FLOCK_ID"])
    assert pd.isna(imported["FACILITY_ID"])
    assert pd.isna(imported["PRODUCER_ACCOUNT_ID"])
    assert pd.isna(imported["GRADER_ACCOUNT_ID"])


def test_account_candidate_lookup_supports_zero_one_and_multiple_results():
    repo = MockRepository(seed=42)
    registration = repo.get_accounts().iloc[0]["REGISTRATION_NUMBER"]

    assert repo.find_accounts_by_registration_number("missing").empty
    assert len(repo.find_accounts_by_registration_number(registration)) == 1
    repo.upsert_account(
        {
            "ORGANIZATION_NAME": "Second sanitized candidate",
            "REGISTRATION_NUMBER": registration,
        }
    )
    assert len(repo.find_accounts_by_registration_number(registration.lower())) == 2


def test_raw_rows_preserve_source_values_and_status():
    repo = MockRepository(seed=42)
    import_id = repo.create_import_batch({"FILENAME": "sanitized.xlsx"})
    raw_rows = build_raw_rows(sanitized_eims_source(), "VALID")

    assert repo.insert_raw_rows(import_id, raw_rows) == 1
    stored = repo.get_raw_rows(import_id).iloc[0]
    assert stored["SOURCE_ROW_NUMBER"] == 11
    assert stored["RAW_DATA"]["Producer #"] == "NS-1000"
    assert stored["VALIDATION_STATUS"] == "VALID"
    assert stored["MATCH_STATUS"] == MATCH_STATUS_UNMATCHED


def test_synthetic_records_have_explicit_source_and_nullable_match_status():
    production = MockRepository(seed=42).get_production_records()
    synthetic = production[production["SOURCE_TYPE"] == SOURCE_TYPE_SYNTHETIC]

    assert len(synthetic) == 200
    assert synthetic["MATCH_STATUS"].isna().all()


def test_source_traceability_fields_are_available_in_reports():
    report = build_report(
        MockRepository(seed=42),
        ["PRODUCER_NUMBER", "SOURCE_TYPE", "MATCH_STATUS", "SOURCE_WEEK_CODE"],
    )

    assert list(report.columns) == [
        "Producer Number",
        "Source Type",
        "Match Status",
        "Source Week Code",
    ]
    assert report["Source Type"].eq(SOURCE_TYPE_SYNTHETIC).all()


def test_ui_and_services_do_not_access_private_production_storage():
    source_files = [
        *Path("app").rglob("*.py"),
        *Path("data").glob("*.py"),
    ]
    offenders = [
        str(path)
        for path in source_files
        if "repo._production" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
