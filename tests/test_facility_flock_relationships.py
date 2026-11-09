"""Synthetic coverage for Sara's confirmed sequential/concurrent facility use."""

import datetime as dt
import io
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest

from app.services.report_builder import build_report
from app.services.report_center import build_custom_report
from data.migration import MigrationSourceFile, analyze_migration_files
from data.repositories.mock import MockRepository
from data.validation import validate_flock
from tests.auth_support import authenticated_app
from tests.test_eims_migration import _v3_sources
from tests.test_operational_flock_quota_import import csv_upload, flock_row
from data.operational_flock_quota_import import analyze_operational_files
from tests.test_report_center import user


def flock(repo, number, placement=None, disposal=None):
    facility = repo.get_facilities().iloc[0]
    return {
        "FLOCK_ID": str(uuid4()), "FLOCK_NUMBER": number, "PERMIT_NUMBER": number,
        "ACCOUNT_ID": facility.ACCOUNT_ID, "FACILITY_ID": facility.FACILITY_ID,
        "HATCH_DATE": dt.date(2025, 1, 1), "BIRD_COUNT": 10, "BIRDS_DISPOSED": 0,
        "STATUS": "Active", "PLACEMENT_DATE": placement, "DISPOSAL_DATE": disposal,
        "EST_DISPOSAL": dt.date(2026, 1, 1),
    }


def test_sequential_flocks_preserve_old_record_and_unknown_actual_end():
    repo = MockRepository()
    old = flock(repo, "SYN-OLD", dt.date(2025, 1, 2), dt.date(2025, 6, 1))
    first_id = repo.upsert_flock(old)
    original = repo.get_flock(first_id)
    new = flock(repo, "SYN-NEXT", dt.date(2025, 6, 2))
    second_id = repo.upsert_flock(new)
    assert repo.get_flock(first_id) == original
    assert pd.isna(repo.get_flock(second_id)["DISPOSAL_DATE"])
    assert repo.get_flock(second_id)["EST_DISPOSAL"] == new["EST_DISPOSAL"]
    assert {first_id, second_id} <= set(repo.get_flocks(facility_id=old["FACILITY_ID"]).FLOCK_ID)


def test_concurrent_flocks_have_no_implicit_two_flock_limit():
    repo = MockRepository()
    records = [flock(repo, f"SYN-CONCURRENT-{i}", dt.date(2025, 2, 1)) for i in range(3)]
    for record in records:
        assert validate_flock(repo, record) == []
        repo.upsert_flock(record)
    assert {r["FLOCK_ID"] for r in records} <= set(repo.get_flocks(facility_id=records[0]["FACILITY_ID"]).FLOCK_ID)


def test_sharing_does_not_authorize_cross_account_facility_use():
    repo = MockRepository()
    record = flock(repo, "SYN-WRONG-ACCOUNT")
    record["ACCOUNT_ID"] = next(value for value in repo.get_accounts().ACCOUNT_ID if value != record["ACCOUNT_ID"])
    with pytest.raises(ValueError, match="Facility must belong"):
        repo.upsert_flock(record)


def test_daily_import_accepts_overlapping_flocks_in_occupied_facility():
    repo = MockRepository()
    before = repo.get_flocks().copy(deep=True)
    rows = [{**flock_row(repo, f"SHARED-{i}"), "Placement Date": "2026-08-02",
             "Estimated Disposal Date": "2027-08-02"} for i in range(3)]
    report = analyze_operational_files([csv_upload("shared.csv", rows)], "Flocks", repo)
    assert len(report.ready_rows) == 3
    assert not report.rejected_rows
    assert all(row.write_record.get("DISPOSAL_DATE") is None for row in report.ready_rows)
    pd.testing.assert_frame_equal(before, repo.get_flocks())


def test_reports_include_all_flocks_without_multiplying_production():
    repo = MockRepository()
    repo._flocks = pd.DataFrame([flock(repo, f"SYN-REPORT-{i}") for i in range(3)])
    repo._production = pd.DataFrame([
        {"PRODUCTION_ID": f"SYN-P-{i}", "IMPORT_ID": repo._import_batches[0]["IMPORT_ID"],
         "FLOCK_ID": row.FLOCK_ID, "TOTAL_RECEIVED": 10 + i}
        for i, row in enumerate(repo._flocks.itertuples())
    ])
    result = build_report(repo, ["FACILITY_NAME", "FLOCK_NUMBER", "TOTAL_RECEIVED"])
    assert len(result) == 3
    assert result["Total Received"].sum() == 33
    dates = build_report(repo, ["FLOCK_NUMBER", "EST_PROD_COMPLETION", "DISPOSAL_DATE"])
    assert dates["Actual Disposal Date"].isna().all()
    assert dates["Estimated Disposal Date"].notna().all()
    grouped = build_custom_report(repo, user=user(), dataset="Flocks",
        selected_fields=["FACILITY_ID", "BIRD_COUNT"], group_by=["FACILITY_ID"],
        aggregations={"BIRD_COUNT": "sum"})
    assert grouped["Bird Count"].tolist() == [30]
    # Corrupt parent-key duplicates must fail, not silently inflate sums.
    repo._flocks = pd.concat([repo._flocks, repo._flocks.iloc[[0]]], ignore_index=True)
    with pytest.raises(pd.errors.MergeError):
        build_report(repo, ["FLOCK_NUMBER", "TOTAL_RECEIVED"])


def test_flock_form_allows_occupied_facility_and_leaves_dates_unknown(tmp_path, monkeypatch):
    app = authenticated_app(Path(__file__).parents[1] / "app" / "Home.py", tmp_path, monkeypatch)
    app.switch_page("pages/5_Flocks.py").run()
    next(button for button in app.button if button.label == "New").click().run()
    facility_id = app.session_state.repo.get_facilities(
        account_id=app.session_state.repo.get_accounts().iloc[0].ACCOUNT_ID).iloc[0].FACILITY_ID
    before = app.session_state.repo.get_flocks().copy(deep=True)
    assert not app.session_state.repo.get_flocks(facility_id=facility_id).empty
    app.text_input(key="flock_form_number").set_value("SYN-FORM-SHARED")
    app.text_input(key="flock_form_permit").set_value("SYN-PERMIT-SHARED")
    next(button for button in app.button if button.label == "Save").click().run()
    assert not app.exception
    assert not app.error
    saved = app.session_state.repo.get_flocks().query("FLOCK_NUMBER == 'SYN-FORM-SHARED'").iloc[0]
    assert saved.FACILITY_ID == facility_id
    assert pd.isna(saved.PLACEMENT_DATE) and pd.isna(saved.DISPOSAL_DATE)
    existing = app.session_state.repo.get_flocks()
    pd.testing.assert_frame_equal(before.reset_index(drop=True), existing[existing.FLOCK_ID.isin(before.FLOCK_ID)].reset_index(drop=True), check_dtype=False)


def test_v3_historical_package_preserves_shared_facility_dates_and_ids():
    sources, mapping, ids = _v3_sources()
    spec = mapping["entities"]["FLOCK"]
    updated = []
    flock_ids = []
    for source in sources:
        if source.name != spec["filename"]:
            updated.append(source)
            continue
        frame = pd.read_csv(io.BytesIO(source.content), dtype=str, keep_default_na=False)
        rows = []
        for index in range(3):
            row = frame.iloc[0].to_dict()
            flock_id = ids["FLOCK"] if index == 0 else str(uuid4())
            flock_ids.append(flock_id)
            row[spec["field_map"]["FLOCK_ID"]] = flock_id
            row[spec["fallbacks"]["FLOCK_NUMBER"][0]] = f"SYN-HISTORY-{index}"
            row[spec["field_map"]["PLACEMENT_DATE"]] = "2026-01-03"
            row[spec["field_map"]["EST_DISPOSAL"]] = "2027-01-03"
            row[spec["field_map"]["DISPOSAL_DATE"]] = ""
            rows.append(row)
        updated.append(MigrationSourceFile(source.name, pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")))
    analysis = analyze_migration_files(updated, mapping)
    assert analysis.rejected_count == 0
    assert {r["FLOCK_ID"] for r in analysis.records["FLOCK"]} == set(flock_ids)
    assert all(r["FACILITY_ID"] == ids["FACILITY"] for r in analysis.records["FLOCK"])
    assert all(r["DISPOSAL_DATE"] is None for r in analysis.records["FLOCK"])
    assert all(r["PLACEMENT_DATE"] == dt.date(2026, 1, 3) for r in analysis.records["FLOCK"])
    repo = MockRepository()
    original_ids = set(repo.get_flocks().FLOCK_ID)
    repo.prepare_migration_batch({"MIGRATION_BATCH_ID": analysis.batch_id,
        "PACKAGE_HASH": analysis.package_hash, "SCHEMA_VERSION": analysis.schema_version,
        "STATUS": "READY"}, analysis.files, analysis.raw_rows)
    repo.commit_migration_batch(analysis.batch_id)
    assert original_ids <= set(repo.get_flocks().FLOCK_ID)
    assert set(repo.get_flocks(facility_id=ids["FACILITY"]).FLOCK_ID) == set(flock_ids)
    assert repo.commit_migration_batch(analysis.batch_id)["idempotent"] is True
