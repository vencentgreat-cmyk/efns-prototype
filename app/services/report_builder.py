# ============================================================
# EFNS Prototype v0.1 — Report Builder Service
# ============================================================
"""Build customizable reports by joining normalized tables.

All joins are PROVISIONAL and will be revised after Dataverse
metadata is obtained.
"""

from __future__ import annotations

import pandas as pd

from data.repositories import BaseRepository
from app.services.report_relationships import report_relationships
from data.producer_identity import production_identities
from data.source_scope import scope_production


REPORT_FIELDS = {
    "Account": [
        ("ACCOUNT_NAME", "Account Name", "ORGANIZATION_NAME"),
        ("REGISTRATION_NUMBER", "Registration Number", "REGISTRATION_NUMBER"),
        ("ADDRESS", "Address", "ADDRESS_LINE1"),
        ("CITY", "City", "CITY"),
        ("PROVINCE", "Province", "PROVINCE"),
        ("POSTAL_CODE", "Postal Code", "POSTAL_CODE"),
        ("COUNTRY_REGION", "Country/Region", "COUNTRY_REGION"),
        ("PROVINCE_OF_REGISTRATION", "Province of Registration", "PROVINCE_OF_REGISTRATION"),
        ("WEBSITE", "Website", "WEBSITE"),
        ("DESCRIPTION", "Description", "DESCRIPTION"),
        ("DEFAULT_ON_REPORTS", "Default on Reports", "DEFAULT_ON_REPORTS"),
        ("NO_SVG", "No SVG", "NO_SVG"),
        ("ACCOUNT_STATUS", "Account Status", "STATUS_ACCT"),
    ],
    "Contact": [
        ("CONTACT_NAME", "Primary Contact", "CONTACT_NAME"),
        ("CONTACT_PHONE", "Phone", "CONTACT_PHONE"),
        ("CONTACT_EMAIL", "Email", "CONTACT_EMAIL"),
        ("FAX", "Fax", "FAX"),
    ],
    "Facility": [
        ("FACILITY_ACCOUNT", "Facility Account", "FACILITY_ACCOUNT_NAME"),
        ("FACILITY_ACCOUNT_ID", "Facility Account ID", "FACILITY_ACCOUNT_ID"),
        ("FACILITY_NAME", "Facility Name", "FACILITY_NAME"),
        ("FACILITY_TYPE", "Facility Type", "FACILITY_TYPE"),
        ("FACILITY_STATUS", "Facility Status", "STATUS_FAC"),
        ("ACTIVATION_DATE", "Activation Date", "ACTIVATION_DATE"),
        ("CLOSURE_DATE", "Closure Date", "CLOSURE_DATE"),
    ],
    "Flock": [
        ("FLOCK_ACCOUNT", "Flock Account", "FLOCK_ACCOUNT_NAME"),
        ("FLOCK_ACCOUNT_ID", "Flock Account ID", "FLOCK_ACCOUNT_ID"),
        ("FLOCK_NUMBER", "Flock Number", "FLOCK_NUMBER"),
        ("BIRD_COUNT", "Bird Count", "BIRD_COUNT"),
        ("PLACEMENT_DATE", "Placement Date", "PLACEMENT_DATE"),
        ("HATCH_DATE", "Hatch Date", "HATCH_DATE"),
        ("EGG_COLOUR", "Egg Colour", "EGG_COLOUR_FLOCK"),
        (
            "EST_PROD_COMPLETION",
            "Estimated Disposal Date",
            "EST_DISPOSAL",
        ),
        ("DISPOSAL_DATE", "Actual Disposal Date", "DISPOSAL_DATE"),
        ("DISPOSAL_METHOD", "Disposal Method", "DISPOSAL_METHOD"),
        ("FLOCK_STATUS", "Flock Status", "STATUS_FLOCK"),
    ],
    "Quota": [
        ("QUOTA_NAME", "Quota Name", "QUOTA_NAME"),
        (
            "QUOTA_REGISTRATION_NUMBER",
            "Quota Registration Number",
            "REGISTRATION_NUMBER_QUOTA",
        ),
        ("QUOTA_TYPE", "Quota Type", "QUOTA_TYPE"),
        ("QUOTA_STATUS", "Quota Status", "STATUS_QUOTA"),
        (
            "QUOTA_EFFECTIVE_DATE",
            "Quota Effective Date",
            "EFFECTIVE_DATE_QUOTA",
        ),
        ("QUOTA_END_DATE", "Quota End Date", "END_DATE_QUOTA"),
        ("QUOTA_COMMENTS", "Quota Comments", "COMMENTS_QUOTA"),
        ("QUOTA_CREATED_ON", "Quota Created On", "CREATED_AT_QUOTA"),
        ("QUOTA_UPDATED_ON", "Quota Updated On", "UPDATED_AT_QUOTA"),
    ],
    "Quota Transaction": [
        (
            "QUOTA_TRANSACTION_ID",
            "Quota Transaction ID",
            "QUOTA_TRANSACTION_ID",
        ),
        (
            "QUOTA_TRANSACTION_TYPE",
            "Quota Transaction Type",
            "TRANSACTION_TYPE",
        ),
        ("QUOTA_COUNT", "Quota Count", "QUOTA_COUNT"),
        (
            "QUOTA_TRANSACTION_DATE",
            "Quota Transaction Date",
            "EFFECTIVE_DATE_TRANSACTION",
        ),
        (
            "QUOTA_TRANSACTION_END_DATE",
            "Quota Transaction End Date",
            "END_DATE_TRANSACTION",
        ),
        ("QUOTA_PRICE", "Quota Price", "PRICE"),
        (
            "QUOTA_LEASE_TYPE",
            "Quota Lease Type",
            "QUOTA_LEASE_TYPE",
        ),
        (
            "QUOTA_OWNER_ACCOUNT",
            "Quota Owner Account",
            "OWNER_ACCOUNT_NAME",
        ),
        (
            "QUOTA_RELATED_ACCOUNT",
            "Related Account",
            "RELATED_ACCOUNT_NAME",
        ),
        (
            "RELATED_QUOTA_ID",
            "Related Quota ID",
            "RELATED_QUOTA_ID",
        ),
        (
            "RELATED_TRANSACTION_ID",
            "Related Transaction ID",
            "RELATED_TRANSACTION_ID",
        ),
        (
            "QUOTA_TRANSACTION_COMMENTS",
            "Quota Transaction Comments",
            "COMMENTS_TRANSACTION",
        ),
        (
            "QUOTA_TRANSACTION_CREATED_ON",
            "Quota Transaction Created On",
            "CREATED_AT_TRANSACTION",
        ),
        (
            "QUOTA_TRANSACTION_UPDATED_ON",
            "Quota Transaction Updated On",
            "UPDATED_AT_TRANSACTION",
        ),
    ],
    "Salmonella": [
        (
            "SALMONELLA_PERMIT_NUMBER",
            "Test Permit Number",
            "PERMIT_NUMBER_TEST",
        ),
        ("TESTING_DATE", "Testing Date", "TESTING_DATE"),
        ("TEST_RESULT", "Salmonella Test Result", "TEST_RESULT"),
        ("INSPECTOR", "Inspector", "INSPECTOR"),
        (
            "NUMBER_OF_SAMPLES",
            "Number of Samples",
            "NUMBER_OF_SAMPLES",
        ),
        ("CASE_FILE_NUMBER", "Case/File Number", "CASE_FILE_NUMBER"),
        ("INVOICE_NUMBER", "Invoice Number", "INVOICE_NUMBER"),
    ],
    "Production": [
        ("SOURCE_SCOPE", "Source scope", "SOURCE_SCOPE"),
        ("PRODUCER_IDENTITY_LABEL", "Producer identity", "PRODUCER_IDENTITY_LABEL"),
        ("PRODUCER_IDENTITY_KEY", "Producer identity key", "PRODUCER_IDENTITY_KEY"),
        ("PRODUCER_IDENTITY_STATUS", "Producer identity status", "PRODUCER_IDENTITY_STATUS"),
        ("SOURCE_TOTAL", "Source Total", "TOTAL"),
        ("PRODUCTION_FACILITY_ID", "Production Facility ID", "FACILITY_ID"),
        ("FLOCK_FACILITY_ID", "Flock Facility ID", "FLOCK_FACILITY_ID"),
        ("REPORT_FACILITY_ID", "Report Facility ID", "REPORT_FACILITY_ID"),
        ("FACILITY_SOURCE", "Facility Source", "REPORT_FACILITY_SOURCE"),
        ("FACILITY_REFERENCE_COMPARISON", "Facility Reference Comparison", "FACILITY_REFERENCE_DIFFERENCE"),
        ("PRODUCER_ACCOUNT", "Producer Account", "PRODUCER_ACCOUNT_NAME"),
        ("PRODUCER_ACCOUNT_ID", "Producer Account ID", "PRODUCER_ACCOUNT_ID"),
        ("PRODUCER_NUMBER", "Producer Number", "PRODUCER_NUMBER"),
        ("GRADER_NUMBER", "Grader Number", "GRADER_NUMBER"),
        ("BARN_IDENTITY", "Barn Identity", "BARN_IDENTITY"),
        ("FLOCK_AGE", "Flock Age", "FLOCK_AGE"),
        ("NET_WEIGHT", "Net Weight", "NET_WEIGHT"),
        ("NET_BOXES", "Net Boxes", "NET_BOXES"),
        ("NET_PER_BOX", "Net Per Box", "NET_PER_BOX"),
        ("TOTAL_RECEIVED", "Total Received", "TOTAL_RECEIVED"),
        ("REJECTED", "Rejected", "REJECTED"),
        ("LOSS", "Loss", "LOSS"),
        (
            "LEGACY_REJECT_LOSS_TOTAL",
            "Legacy Reject/Loss",
            "LEGACY_REJECT_LOSS_TOTAL",
        ),
        ("TOTAL_ACCEPTED", "Total Accepted", "TOTAL_ACCEPTED"),
        ("REPORTING_YEAR", "Reporting Year", "REPORTING_YEAR"),
        ("REPORTING_WEEK", "Reporting Week", "REPORTING_WEEK"),
        ("SOURCE_TYPE", "Source Type", "SOURCE_TYPE"),
        ("MATCH_STATUS", "Match Status", "MATCH_STATUS"),
        (
            "SOURCE_ROW_NUMBER",
            "Source Row Number",
            "SOURCE_ROW_NUMBER",
        ),
        (
            "SOURCE_WEEK_CODE",
            "Source Week Code",
            "SOURCE_WEEK_CODE",
        ),
    ],
}


def _prepare_accounts(repo: BaseRepository) -> pd.DataFrame:
    return repo.get_accounts().rename(
        columns={
            "STATUS": "STATUS_ACCT",
        }
    )


def _prepare_facilities(repo: BaseRepository) -> pd.DataFrame:
    return repo.get_facilities().rename(
        columns={
            "STATUS": "STATUS_FAC",
        }
    )


def _prepare_flocks(repo: BaseRepository) -> pd.DataFrame:
    return repo.get_flocks().rename(
        columns={
            "STATUS": "STATUS_FLOCK",
            "EGG_COLOUR": "EGG_COLOUR_FLOCK",
        }
    )


def _prepare_quotas(repo: BaseRepository) -> pd.DataFrame:
    """Disambiguate quota fields before joining other entities."""
    return repo.get_quota_registrations().rename(
        columns={
            "REGISTRATION_NUMBER": "REGISTRATION_NUMBER_QUOTA",
            "STATUS": "STATUS_QUOTA",
            "EFFECTIVE_DATE": "EFFECTIVE_DATE_QUOTA",
            "END_DATE": "END_DATE_QUOTA",
            "COMMENTS": "COMMENTS_QUOTA",
            "CREATED_AT": "CREATED_AT_QUOTA",
            "UPDATED_AT": "UPDATED_AT_QUOTA",
        }
    )


def _prepare_quota_transactions(
    repo: BaseRepository,
    account_names: dict,
) -> pd.DataFrame:
    """Disambiguate transaction audit and date fields."""
    transactions = repo.get_quota_transactions().rename(
        columns={
            "EFFECTIVE_DATE": "EFFECTIVE_DATE_TRANSACTION",
            "END_DATE": "END_DATE_TRANSACTION",
            "COMMENTS": "COMMENTS_TRANSACTION",
            "CREATED_AT": "CREATED_AT_TRANSACTION",
            "UPDATED_AT": "UPDATED_AT_TRANSACTION",
        }
    )

    if transactions.empty:
        return transactions

    if "OWNER_ACCOUNT_ID" in transactions.columns:
        transactions["OWNER_ACCOUNT_NAME"] = (
            transactions["OWNER_ACCOUNT_ID"].map(account_names)
        )
    else:
        transactions["OWNER_ACCOUNT_NAME"] = None

    if "RELATED_ACCOUNT_ID" in transactions.columns:
        transactions["RELATED_ACCOUNT_NAME"] = (
            transactions["RELATED_ACCOUNT_ID"].map(account_names)
        )
    else:
        transactions["RELATED_ACCOUNT_NAME"] = None

    return transactions


def build_report(
    repo: BaseRepository,
    selected_keys: list[str],
    source_scope='All DEV records (mixed sources)',
) -> pd.DataFrame:
    """Build a provisional joined report from selected field keys."""

    key_to_column = {}
    key_to_section = {}
    key_to_display = {}

    for section, fields in REPORT_FIELDS.items():
        for key, display, column in fields:
            key_to_column[key] = column
            key_to_section[key] = section
            key_to_display[key] = display

    sections_needed = {
        key_to_section[key]
        for key in selected_keys
        if key in key_to_section
    }

    has_account = (
        "Account" in sections_needed
        or "Contact" in sections_needed
    )
    has_facility = "Facility" in sections_needed
    has_flock = "Flock" in sections_needed
    has_production = "Production" in sections_needed
    has_quota = "Quota" in sections_needed
    has_quota_transaction = "Quota Transaction" in sections_needed
    has_salmonella = "Salmonella" in sections_needed

    accounts = _prepare_accounts(repo)
    facilities = _prepare_facilities(repo)
    flocks = _prepare_flocks(repo)

    account_names = {}

    if not accounts.empty:
        account_names = dict(
            zip(
                accounts["ACCOUNT_ID"],
                accounts["ORGANIZATION_NAME"],
            )
        )

    prod = None

    if has_production:
        prod = scope_production(repo.get_production_records(),source_scope).rename(
            columns={
                "EGG_COLOUR": "EGG_COLOUR_PROD",
            }
        )

    df = None

    # Salmonella is the primary row grain.
    if has_salmonella:
        df = repo.get_salmonella_tests().rename(
            columns={
                "PERMIT_NUMBER": "PERMIT_NUMBER_TEST",
            }
        )

        df = report_relationships(repo, df, "SALMONELLA_TEST")

        if has_account:
            df = df.merge(
                accounts,
                on="ACCOUNT_ID",
                how="left",
            )

    # Quota Transaction is the primary row grain.
    elif has_quota_transaction:
        quotas = _prepare_quotas(repo)
        transactions = _prepare_quota_transactions(
            repo,
            account_names,
        )

        df = transactions.merge(
            quotas,
            on="QUOTA_ID",
            how="left",
        )

        if has_account:
            df = df.merge(
                accounts,
                on="ACCOUNT_ID",
                how="left",
            )

    # Quota Registration is the primary row grain.
    elif has_quota:
        df = _prepare_quotas(repo)

        if has_account:
            df = df.merge(
                accounts,
                on="ACCOUNT_ID",
                how="left",
            )

    elif has_production:
        df = report_relationships(repo, prod, "PRODUCTION_RECORD")
        df = production_identities(df)
        if has_account:
            # Generic Account fields on a production report always refer to
            # the recorded producer, never the Flock or Facility Account.
            if "PRODUCER_ACCOUNT_ID" not in df:
                df["PRODUCER_ACCOUNT_ID"] = None
            df = df.merge(accounts.rename(columns={"ACCOUNT_ID": "PRODUCER_ACCOUNT_ID"}),
                          on="PRODUCER_ACCOUNT_ID", how="left", validate="many_to_one")

    elif has_flock:
        df = report_relationships(repo, flocks, "FLOCK")

        if has_account:
            df = df.merge(
                accounts,
                on="ACCOUNT_ID",
                how="left",
                suffixes=("_HIER", "_ACCT"),
            )

    elif has_facility:
        df = report_relationships(repo, facilities, "FACILITY")

        if has_account:
            df = df.merge(
                accounts,
                on="ACCOUNT_ID",
                how="left",
                suffixes=("_FAC", "_ACCT"),
            )

    elif has_account:
        df = accounts.copy()

    if df is None or df.empty:
        return pd.DataFrame(
            {"Message": ["No data for selected fields."]}
        )

    selected_columns = {}
    missing_fields = []

    for key in selected_keys:
        if key not in key_to_column:
            continue

        column_name = key_to_column[key]
        display_name = key_to_display[key]

        if column_name in df.columns:
            selected_columns[column_name] = display_name
        else:
            missing_fields.append(display_name)

    if not selected_columns:
        return pd.DataFrame(
            {"Message": ["No available fields were selected."]}
        )

    result = df[
        list(selected_columns.keys())
    ].rename(columns=selected_columns)

    for missing_field in missing_fields:
        result[f"[Missing: {missing_field}]"] = None

    return result
