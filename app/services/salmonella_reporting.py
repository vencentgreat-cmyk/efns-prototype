"""Build the dedicated Salmonella Test report."""

from __future__ import annotations

import pandas as pd

from data.constants import UNASSIGNED_LABEL
from data.repositories.base import BaseRepository


def build_salmonella_report(repo: BaseRepository, **filters) -> pd.DataFrame:
    tests = repo.get_salmonella_tests(**filters)
    columns = [
        "Account",
        "Facility",
        "Flock Number",
        "Permit Number",
        "Testing Date",
        "Test Result",
        "Inspector",
        "Number of Samples",
        "Date Received",
        "Date Result Sent",
        "Case/File Number",
        "Invoice Number",
        "Invoice Date",
        "Comments",
    ]
    if tests.empty:
        return pd.DataFrame(columns=columns)

    flocks = repo.get_flocks()[
        ["FLOCK_ID", "FACILITY_ID", "FLOCK_NUMBER"]
    ]
    accounts = repo.get_accounts()[["ACCOUNT_ID", "ORGANIZATION_NAME"]]
    facilities = repo.get_facilities()[["FACILITY_ID", "FACILITY_NAME"]]
    result = tests.merge(flocks, on="FLOCK_ID", how="left")
    result = result.merge(accounts, on="ACCOUNT_ID", how="left")
    result = result.merge(facilities, on="FACILITY_ID", how="left")
    result["FACILITY_NAME"] = result["FACILITY_NAME"].fillna(UNASSIGNED_LABEL)
    mapping = {
        "ORGANIZATION_NAME": "Account",
        "FACILITY_NAME": "Facility",
        "FLOCK_NUMBER": "Flock Number",
        "PERMIT_NUMBER": "Permit Number",
        "TESTING_DATE": "Testing Date",
        "TEST_RESULT": "Test Result",
        "INSPECTOR": "Inspector",
        "NUMBER_OF_SAMPLES": "Number of Samples",
        "DATE_RECEIVED": "Date Received",
        "DATE_RESULT_SENT": "Date Result Sent",
        "CASE_FILE_NUMBER": "Case/File Number",
        "INVOICE_NUMBER": "Invoice Number",
        "INVOICE_DATE": "Invoice Date",
        "COMMENTS": "Comments",
    }
    result = result.rename(columns=mapping)
    for column in columns:
        if column not in result:
            result[column] = None
    return result[columns]
