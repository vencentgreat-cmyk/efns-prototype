from __future__ import annotations

import io
import uuid

import pandas as pd
import pytest

from data.operational_flock_quota_import import analyze_operational_files
from data.repositories.mock import MockRepository


class Upload:
    def __init__(self, name: str, content: bytes):
        self.name = name
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


def csv_upload(name: str, rows: list[dict]) -> Upload:
    return Upload(name, pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"))


def xlsx_upload(name: str, rows: list[dict]) -> Upload:
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, index=False)
    return Upload(name, stream.getvalue())


def references(repo: MockRepository) -> dict:
    facility = repo.get_facilities().iloc[0].to_dict()
    account = repo.get_account(facility["ACCOUNT_ID"])
    flock = repo.get_flocks(facility_id=facility["FACILITY_ID"]).iloc[0].to_dict()
    quota = repo.get_quota_registrations(account_id=account["ACCOUNT_ID"]).iloc[0].to_dict()
    return {"account": account, "facility": facility, "flock": flock, "quota": quota}


def quota_row(repo: MockRepository, suffix: str = "1") -> dict:
    ref = references(repo)
    return {
        "Registration Number": f"DAILY-QUOTA-{suffix}",
        "Account": ref["account"]["ACCOUNT_ID"],
        "Quota Type": ref["quota"]["QUOTA_TYPE"],
        "Effective Date": "2026-09-01",
    }


def flock_row(repo: MockRepository, suffix: str = "1") -> dict:
    ref = references(repo)
    return {
        "Flock Number": f"DAILY-FLOCK-{suffix}",
        "Account": ref["account"]["ACCOUNT_ID"],
        "Facility": ref["facility"]["FACILITY_ID"],
        "Permit Number": f"DAILY-PERMIT-{suffix}",
        "Hatch Date": "2026-08-01",
        "Bird Count": "1250",
    }


def test_single_csv_auto_detects_and_validates_quota_registration():
    repo = MockRepository()
    report = analyze_operational_files([csv_upload("ordinary-name.csv", [quota_row(repo)])], "Auto-detect", repo)

    assert report.files[0].entity == "QUOTA_REGISTRATION"
    assert len(report.ready_rows) == 1
    assert report.ready_rows[0].write_record["ACTION"] == "CREATE"


def test_multiple_files_may_contain_different_operational_entities():
    repo = MockRepository()
    ref = references(repo)
    uploads = [
        xlsx_upload("quota.xlsx", [quota_row(repo, "MULTI")]),
        csv_upload("movement.csv", [{
            "Flock": ref["flock"]["FLOCK_ID"], "Transaction Type": "Delivery",
            "Quantity": "20", "Transaction Date": "2026-09-20",
        }]),
    ]

    report = analyze_operational_files(uploads, "Auto-detect", repo)

    assert {item.entity for item in report.files} == {"QUOTA_REGISTRATION", "FLOCK_TRANSACTION"}
    assert len(report.ready_rows) == 2


def test_dataverse_logical_columns_are_mapped_without_historical_package():
    repo = MockRepository()
    ref = references(repo)
    row = {
        "new_flocksid": str(uuid.uuid4()), "new_account": ref["account"]["ACCOUNT_ID"],
        "new_facilityidid": ref["facility"]["FACILITY_ID"], "efc_flocknumber": "DV-FLOCK-1",
        "new_name": "DV-PERMIT-1", "new_hatchdate": "2026-08-01", "new_birdcount": "300",
    }

    report = analyze_operational_files([csv_upload("jensen-style.csv", [row])], "Auto-detect", repo)

    assert report.files[0].entity == "FLOCK"
    assert report.ready_rows[0].write_record["FLOCK_NUMBER"] == "DV-FLOCK-1"


def test_missing_database_parent_rejects_row_clearly():
    repo = MockRepository()
    row = quota_row(repo, "MISSING")
    row["Account"] = "account-that-does-not-exist"

    report = analyze_operational_files([csv_upload("missing-parent.csv", [row])], "Quota Registrations", repo)

    assert len(report.rejected_rows) == 1
    assert "Account was not found" in " ".join(report.rejected_rows[0].messages)


def test_account_export_is_reported_as_unsupported_account_data():
    repo = MockRepository()
    upload = csv_upload("account.csv", [{
        "accountid": str(uuid.uuid4()), "name": "Synthetic account",
        "address1_city": "Synthetic city", "statuscode_displayname": "Active",
    }])

    report = analyze_operational_files([upload], "Auto-detect", repo)

    assert report.files[0].entity is None
    assert report.files[0].unsupported_entity == "ACCOUNT"
    assert report.files[0].errors == ["Unsupported entity: Account data."]
    assert len(report.unsupported_rows) == 1
    assert not report.rejected_rows
    assert not any(report.records_by_entity.values())


def test_salmonella_export_is_never_auto_detected_as_flock():
    repo = MockRepository()
    upload = csv_upload("new_flocksalmonellatesting.csv", [{
        "new_flocksalmonellatestingid": str(uuid.uuid4()),
        "new_permitnumberid": str(uuid.uuid4()),
        "new_testingdate": "2026-09-01", "new_setestresult": "Negative",
        "efc_salmonellaid": "TEST-1",
    }])

    report = analyze_operational_files([upload], "Auto-detect", repo)

    assert report.files[0].entity is None
    assert report.files[0].unsupported_entity == "SALMONELLA_TEST"
    assert report.files[0].errors == ["Unsupported entity: Salmonella Tests."]
    assert len(report.unsupported_rows) == 1
    assert not report.rejected_rows
    assert not report.records_by_entity["FLOCK"]


def test_account_id_reference_does_not_make_a_flock_file_unsupported_account_data():
    repo = MockRepository()
    row = flock_row(repo, "ACCOUNT-ID-REFERENCE")
    row["ACCOUNT_ID"] = row.pop("Account")

    report = analyze_operational_files([csv_upload("flock.csv", [row])], "Auto-detect", repo)

    assert report.files[0].entity == "FLOCK"
    assert report.files[0].unsupported_entity is None
    assert len(report.ready_rows) == 1


def test_validation_only_does_not_write_to_repository():
    repo = MockRepository()
    before = (len(repo.get_import_batches()), len(repo.get_quota_registrations()), len(repo.get_raw_rows("none")))

    report = analyze_operational_files([csv_upload("validation-only.csv", [quota_row(repo, "VALIDATE")])], "Auto-detect", repo)

    assert report.ready_rows
    assert before == (len(repo.get_import_batches()), len(repo.get_quota_registrations()), len(repo.get_raw_rows("none")))


def test_commit_prevents_repeated_upload_hash():
    repo = MockRepository()
    report = analyze_operational_files([csv_upload("duplicate.csv", [quota_row(repo, "DUP")])], "Auto-detect", repo)
    batch = {"FILENAME": "duplicate.csv", "FILE_HASH": report.package_hash}
    repo.import_operational_flock_quota_batch(batch, report.records_by_entity, report.raw_rows)

    with pytest.raises(ValueError, match="already been imported"):
        repo.import_operational_flock_quota_batch(batch, report.records_by_entity, report.raw_rows)


def test_commit_rolls_back_all_entities_and_tracking_on_failure():
    class FailingRepository(MockRepository):
        def upsert_flock(self, record):
            raise RuntimeError("injected failure")

    repo = FailingRepository()
    uploads = [
        csv_upload("quota.csv", [quota_row(repo, "ROLLBACK")]),
        csv_upload("flock.csv", [flock_row(repo, "ROLLBACK")]),
    ]
    report = analyze_operational_files(uploads, "Auto-detect", repo)
    before = (len(repo.get_quota_registrations()), len(repo.get_flocks()), len(repo.get_import_batches()), len(repo._raw_rows))

    with pytest.raises(RuntimeError, match="injected failure"):
        repo.import_operational_flock_quota_batch(
            {"FILENAME": "two files", "FILE_HASH": report.package_hash},
            report.records_by_entity,
            report.raw_rows,
        )

    assert before == (len(repo.get_quota_registrations()), len(repo.get_flocks()), len(repo.get_import_batches()), len(repo._raw_rows))


def test_successful_commit_tracks_raw_rows_and_all_four_entities():
    repo = MockRepository()
    ref = references(repo)
    uploads = [
        csv_upload("new-quota.csv", [quota_row(repo, "ALL")]),
        csv_upload("new-flock.csv", [flock_row(repo, "ALL")]),
        csv_upload("flock-tx.csv", [{
            "Flock": ref["flock"]["FLOCK_ID"], "Transaction Type": "Delivery",
            "Quantity": "5", "Transaction Date": "2026-09-20",
        }]),
        csv_upload("quota-tx.csv", [{
            "Quota Registration": ref["quota"]["QUOTA_ID"], "Transaction Type": "Adjustment",
            "Effective Date": "2026-09-20", "Quota Count": "-3",
        }]),
    ]
    report = analyze_operational_files(uploads, "Auto-detect", repo)

    result = repo.import_operational_flock_quota_batch(
        {"FILENAME": "four files", "FILE_HASH": report.package_hash},
        report.records_by_entity,
        report.raw_rows,
    )

    assert not report.rejected_rows
    assert result["total_count"] == 4
    assert all(result["entity_counts"][entity] == 1 for entity in result["entity_counts"])
    assert len(repo.get_raw_rows(result["import_id"])) == 4
