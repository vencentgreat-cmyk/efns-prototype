"""Regression tests for the phase 1/2 validation and reporting fixes."""

from app.services.report_builder import build_report
from data.repositories.mock import MockRepository


def test_week_filter_uses_production_record_week():
    repo = MockRepository(seed=42)
    all_records = repo.get_production_records()
    expected = all_records[all_records["REPORTING_WEEK"] == 5]

    assert not expected.empty
    filtered = repo.get_production_records(reporting_week=5)

    assert len(filtered) == len(expected)
    assert (filtered["REPORTING_WEEK"] == 5).all()


def test_account_production_report_joins_through_flock():
    repo = MockRepository(seed=42)

    report = build_report(repo, ["ACCOUNT_NAME", "TOTAL_RECEIVED"])

    assert len(report) == len(repo.get_production_records())
    assert report["Account Name"].notna().all()
    assert report["Total Received"].notna().all()


def test_flock_egg_colour_survives_production_merge():
    repo = MockRepository(seed=42)

    report = build_report(
        repo,
        ["FLOCK_NUMBER", "EGG_COLOUR", "TOTAL_RECEIVED"],
    )

    assert "Egg Colour" in report.columns
    assert "[Missing: Egg Colour]" not in report.columns
    assert report["Egg Colour"].notna().all()


def test_flock_without_facility_is_retained_and_marked_unassigned():
    repo = MockRepository(seed=42)
    account_id = repo.get_accounts().iloc[0]["ACCOUNT_ID"]
    repo.upsert_flock(
        {
            "ACCOUNT_ID": account_id,
            "FLOCK_NUMBER": "F-NO-FACILITY",
        }
    )

    report = build_report(repo, ["FLOCK_NUMBER", "FACILITY_NAME"])
    row = report[report["Flock Number"] == "F-NO-FACILITY"]

    assert len(row) == 1
    assert row.iloc[0]["Facility Name"] == "Unassigned"


def test_account_update_preserves_created_at():
    repo = MockRepository(seed=42)
    original = repo.get_accounts().iloc[0]

    repo.upsert_account(
        {
            "ACCOUNT_ID": original["ACCOUNT_ID"],
            "ORGANIZATION_NAME": "Updated Organization Name",
        }
    )

    updated = repo.get_account(original["ACCOUNT_ID"])
    assert updated["CREATED_AT"] == original["CREATED_AT"]
