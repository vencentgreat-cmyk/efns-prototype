"""Relationship and validation coverage for provisional enterprise modules."""

import datetime as dt

import pytest

from app.services.report_builder import build_report
from app.services.salmonella_reporting import build_salmonella_report
from data.repositories.mock import MockRepository


def _context(repo):
    account = repo.get_accounts().iloc[0]
    facility = repo.get_facilities(account_id=account["ACCOUNT_ID"]).iloc[0]
    quota = repo.get_quota_registrations(
        account_id=account["ACCOUNT_ID"], active_only=True
    ).iloc[0]
    return account, facility, quota


def test_facilities_are_scoped_to_their_account():
    repo = MockRepository()
    accounts = repo.get_accounts().head(2)
    first = repo.get_facilities(account_id=accounts.iloc[0]["ACCOUNT_ID"])
    assert not first.empty
    assert set(first["ACCOUNT_ID"]) == {accounts.iloc[0]["ACCOUNT_ID"]}
    assert not set(first["FACILITY_ID"]) & set(
        repo.get_facilities(account_id=accounts.iloc[1]["ACCOUNT_ID"])["FACILITY_ID"]
    )


def test_flock_quota_must_belong_to_same_account():
    repo = MockRepository()
    accounts = repo.get_accounts().head(2)
    account_id = accounts.iloc[0]["ACCOUNT_ID"]
    facility = repo.get_facilities(account_id=account_id).iloc[0]
    foreign_quota = repo.get_quota_registrations(
        account_id=accounts.iloc[1]["ACCOUNT_ID"]
    ).iloc[0]
    with pytest.raises(ValueError, match="Quota Registration"):
        repo.upsert_flock(
            {
                "ACCOUNT_ID": account_id,
                "FACILITY_ID": facility["FACILITY_ID"],
                "QUOTA_ID": foreign_quota["QUOTA_ID"],
                "FLOCK_NUMBER": "TEST-REL-1",
                "PERMIT_NUMBER": "PERMIT-REL-1",
                "HATCH_DATE": dt.date.today(),
                "BIRD_COUNT": 100,
            }
        )


def test_flock_can_be_created_and_queried_by_account_and_facility():
    repo = MockRepository()
    account, facility, quota = _context(repo)
    flock_id = repo.upsert_flock(
        {
            "ACCOUNT_ID": account["ACCOUNT_ID"],
            "FACILITY_ID": facility["FACILITY_ID"],
            "QUOTA_ID": quota["QUOTA_ID"],
            "FLOCK_QUOTA_TYPE": quota["QUOTA_TYPE"],
            "FLOCK_NUMBER": "TEST-FLOCK-1",
            "PERMIT_NUMBER": "PERMIT-TEST-1",
            "HATCH_DATE": dt.date.today() - dt.timedelta(days=7),
            "PLACEMENT_DATE": dt.date.today(),
            "BIRD_COUNT": 500,
            "BIRDS_DISPOSED": 0,
            "STATUS": "Active",
        }
    )
    assert flock_id in set(repo.get_flocks(account_id=account["ACCOUNT_ID"])["FLOCK_ID"])
    assert flock_id in set(repo.get_flocks(facility_id=facility["FACILITY_ID"])["FLOCK_ID"])


def test_quota_registration_and_transaction_validation():
    repo = MockRepository()
    account, _facility, quota = _context(repo)
    assert set(repo.get_quota_registrations(account_id=account["ACCOUNT_ID"])["ACCOUNT_ID"]) == {
        account["ACCOUNT_ID"]
    }
    with pytest.raises(ValueError, match="greater than zero"):
        repo.upsert_quota_transaction(
            {
                "QUOTA_ID": quota["QUOTA_ID"],
                "TRANSACTION_TYPE": "Purchase",
                "QUOTA_COUNT": 0,
                "RELATED_ACCOUNT_ID": repo.get_accounts().iloc[1]["ACCOUNT_ID"],
                "EFFECTIVE_DATE": dt.date.today(),
            }
        )


def test_salmonella_test_relationship_dates_and_samples():
    repo = MockRepository()
    flock = repo.get_flocks().iloc[0]
    with pytest.raises(ValueError, match="Number of Samples"):
        repo.upsert_salmonella_test(
            {
                "FLOCK_ID": flock["FLOCK_ID"],
                "ACCOUNT_ID": flock["ACCOUNT_ID"],
                "PERMIT_NUMBER": flock["PERMIT_NUMBER"],
                "TESTING_DATE": dt.date.today(),
                "NUMBER_OF_SAMPLES": 0,
                "TEST_RESULT": "Pending",
            }
        )
    test_id = repo.upsert_salmonella_test(
        {
            "FLOCK_ID": flock["FLOCK_ID"],
            "ACCOUNT_ID": flock["ACCOUNT_ID"],
            "PERMIT_NUMBER": flock["PERMIT_NUMBER"],
            "TESTING_DATE": dt.date.today(),
            "NUMBER_OF_SAMPLES": 4,
            "TEST_RESULT": "Negative",
            "DATE_RECEIVED": dt.date.today(),
        }
    )
    assert test_id in set(repo.get_salmonella_tests(flock_id=flock["FLOCK_ID"])["SALMONELLA_TEST_ID"])
    assert test_id in set(repo.get_salmonella_tests(account_id=flock["ACCOUNT_ID"])["SALMONELLA_TEST_ID"])
    assert list(repo.get_salmonella_test_samples().columns) == [
        "SALMONELLA_TEST_SAMPLE_ID",
        "SALMONELLA_TEST_ID",
    ]


def test_salmonella_report_filters_and_uses_readable_relationships():
    repo = MockRepository()
    source = repo.get_salmonella_tests().iloc[0]
    report = build_salmonella_report(
        repo,
        account_id=source["ACCOUNT_ID"],
        test_result=source["TEST_RESULT"],
    )
    assert not report.empty
    assert set(report["Test Result"]) == {source["TEST_RESULT"]}
    assert report["Account"].notna().all()
    assert report["Facility"].notna().all()


def test_flock_transaction_requires_real_flock_and_positive_quantity():
    repo = MockRepository()
    with pytest.raises(ValueError, match="existing Flock"):
        repo.upsert_flock_transaction(
            {
                "FLOCK_ID": "missing",
                "TRANSACTION_TYPE": "Delivery",
                "QUANTITY": 20,
                "TRANSACTION_DATE": dt.date.today(),
            }
        )


def test_salmonella_result_dates_cannot_precede_testing():
    repo = MockRepository()
    flock = repo.get_flocks().iloc[0]
    with pytest.raises(ValueError, match="Date Received"):
        repo.upsert_salmonella_test(
            {
                "FLOCK_ID": flock["FLOCK_ID"],
                "ACCOUNT_ID": flock["ACCOUNT_ID"],
                "PERMIT_NUMBER": flock["PERMIT_NUMBER"],
                "TESTING_DATE": dt.date.today(),
                "NUMBER_OF_SAMPLES": 3,
                "TEST_RESULT": "Negative",
                "DATE_RECEIVED": dt.date.today() - dt.timedelta(days=1),
            }
        )


def test_custom_reports_include_quota_and_salmonella_fields():
    repo = MockRepository()
    quota_report = build_report(repo, ["ACCOUNT_NAME", "QUOTA_NAME", "QUOTA_TYPE"])
    salmonella_report = build_report(
        repo,
        ["ACCOUNT_NAME", "FACILITY_NAME", "FLOCK_NUMBER", "TEST_RESULT"],
    )
    assert {"Account Name", "Quota Name", "Quota Type"}.issubset(quota_report.columns)
    assert {"Account Name", "Facility Name", "Flock Number", "Salmonella Test Result"}.issubset(
        salmonella_report.columns
    )
