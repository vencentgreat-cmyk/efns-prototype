# ============================================================
# EFNS Prototype v0.1 — Report Builder Service
# ============================================================
"""Builds customizable reports by joining normalized tables.

All joins are PROVISIONAL and will be revised after Dataverse metadata is obtained.
"""

from __future__ import annotations

import pandas as pd

from data.repositories import BaseRepository


# Field definitions for the report builder UI
REPORT_FIELDS = {
    "Account": [
        ("ACCOUNT_NAME", "Account Name", "ORGANIZATION_NAME"),
        ("REGISTRATION_NUMBER", "Registration Number", "REGISTRATION_NUMBER"),
        ("ADDRESS", "Address", "ADDRESS_LINE1"),
        ("CITY", "City", "CITY"),
        ("PROVINCE", "Province", "PROVINCE"),
        ("POSTAL_CODE", "Postal Code", "POSTAL_CODE"),
        ("ACCOUNT_STATUS", "Account Status", "STATUS_ACCT"),
    ],
    "Contact": [
        ("CONTACT_NAME", "Primary Contact", "CONTACT_NAME"),
        ("CONTACT_PHONE", "Phone", "CONTACT_PHONE"),
        ("CONTACT_EMAIL", "Email", "CONTACT_EMAIL"),
    ],
    "Facility": [
        ("FACILITY_NAME", "Facility Name", "FACILITY_NAME"),
        ("FACILITY_TYPE", "Facility Type", "FACILITY_TYPE"),
        ("FACILITY_STATUS", "Facility Status", "STATUS_FAC"),
        ("ACTIVATION_DATE", "Activation Date", "ACTIVATION_DATE"),
        ("CLOSURE_DATE", "Closure Date", "CLOSURE_DATE"),
    ],
    "Flock": [
        ("FLOCK_NUMBER", "Flock Number", "FLOCK_NUMBER"),
        ("BIRD_COUNT", "Bird Count", "BIRD_COUNT"),
        ("PLACEMENT_DATE", "Placement Date", "PLACEMENT_DATE"),
        ("HATCH_DATE", "Hatch Date", "HATCH_DATE"),
        ("EGG_COLOUR", "Egg Colour", "EGG_COLOUR_FLOCK"),
        ("EST_PROD_COMPLETION", "Est. Completion", "EST_PROD_COMPLETION"),
        ("DISPOSAL_METHOD", "Disposal Method", "DISPOSAL_METHOD"),
        ("FLOCK_STATUS", "Flock Status", "STATUS_FLOCK"),
    ],
    "Production": [
        ("GRADER_NUMBER", "Grader Number", "GRADER_NUMBER"),
        ("BARN_IDENTITY", "Barn Identity", "BARN_IDENTITY"),
        ("FLOCK_AGE", "Flock Age", "FLOCK_AGE"),
        ("NET_WEIGHT", "Net Weight", "NET_WEIGHT"),
        ("NET_BOXES", "Net Boxes", "NET_BOXES"),
        ("NET_PER_BOX", "Net Per Box", "NET_PER_BOX"),
        ("TOTAL_RECEIVED", "Total Received", "TOTAL_RECEIVED"),
        ("REJECTED", "Rejected", "REJECTED"),
        ("LOSS", "Loss", "LOSS"),
        ("LEGACY_REJECT_LOSS_TOTAL", "Legacy Reject/Loss", "LEGACY_REJECT_LOSS_TOTAL"),
        ("TOTAL_ACCEPTED", "Total Accepted", "TOTAL_ACCEPTED"),
        ("REPORTING_YEAR", "Reporting Year", "REPORTING_YEAR"),
        ("REPORTING_WEEK", "Reporting Week", "REPORTING_WEEK"),
    ],
}


def build_report(
    repo: BaseRepository,
    selected_keys: list[str],
) -> pd.DataFrame:
    """Build a joined report DataFrame from selected field keys.

    Field keys are the first element of each tuple in REPORT_FIELDS.

    Joins:
        ACCOUNT ←1:N— FACILITY ←1:N— FLOCK
        PRODUCTION —PROVISIONAL— FLOCK (on FLOCK_ID, unconfirmed).

    Returns:
        DataFrame with columns for each selected key, using display names as headers.
    """
    _ = selected_keys  # May be used for column subsetting later
    key_to_column = {}
    key_to_section = {}
    for section, fields in REPORT_FIELDS.items():
        for key, display, col in fields:
            key_to_column[key] = col
            key_to_section[key] = section

    # Determine which sections are needed
    sections_needed = set()
    for k in selected_keys:
        if k in key_to_section:
            sections_needed.add(key_to_section[k])

    has_account = "Account" in sections_needed or "Contact" in sections_needed
    has_facility = "Facility" in sections_needed
    has_flock = "Flock" in sections_needed
    has_production = "Production" in sections_needed

    # --- Load and disambiguate source entities ---
    accounts = repo.get_accounts().rename(columns={"STATUS": "STATUS_ACCT"})
    facilities = repo.get_facilities().rename(columns={"STATUS": "STATUS_FAC"})
    flocks = repo.get_flocks().rename(
        columns={"STATUS": "STATUS_FLOCK", "EGG_COLOUR": "EGG_COLOUR_FLOCK"}
    )
    prod = None
    if has_production:
        prod = repo.get_production_records().rename(
            columns={"EGG_COLOUR": "EGG_COLOUR_PROD"}
        )

    # FLOCK is the bridge between production and the operational hierarchy.
    # Starting mixed reports from production gives each production row its
    # related flock/account values instead of concatenating unrelated rows.
    df = None
    if has_production and (has_account or has_facility or has_flock):
        hierarchy = flocks.copy()
        if has_facility:
            hierarchy = hierarchy.merge(
                facilities,
                on=["ACCOUNT_ID", "FACILITY_ID"],
                how="left",
                suffixes=("_FLOCK", "_FAC"),
            )
            hierarchy["FACILITY_NAME"] = hierarchy["FACILITY_NAME"].fillna(
                "Unassigned"
            )
            hierarchy["STATUS_FAC"] = hierarchy["STATUS_FAC"].fillna(
                "Unassigned"
            )
        if has_account:
            hierarchy = hierarchy.merge(
                accounts, on="ACCOUNT_ID", how="left", suffixes=("_HIER", "_ACCT")
            )
        df = prod.merge(hierarchy, on="FLOCK_ID", how="left")
    elif has_production:
        df = prod.copy()
    elif has_flock:
        df = flocks.copy()
        if has_facility:
            df = df.merge(
                facilities,
                on=["ACCOUNT_ID", "FACILITY_ID"],
                how="left",
                suffixes=("_FLOCK", "_FAC"),
            )
            df["FACILITY_NAME"] = df["FACILITY_NAME"].fillna("Unassigned")
            df["STATUS_FAC"] = df["STATUS_FAC"].fillna("Unassigned")
        if has_account:
            df = df.merge(
                accounts, on="ACCOUNT_ID", how="left", suffixes=("_HIER", "_ACCT")
            )
    elif has_facility:
        df = facilities.copy()
        if has_account:
            df = df.merge(
                accounts, on="ACCOUNT_ID", how="left", suffixes=("_FAC", "_ACCT")
            )
    elif has_account:
        df = accounts.copy()

    if df is None or df.empty:
        return pd.DataFrame({"Message": ["No data for selected fields."]})

    # --- Select and rename columns ---
    # Build {field_key: display_name} map
    key_to_display = {}
    for section, fields in REPORT_FIELDS.items():
        for key, display, col in fields:
            key_to_display[key] = display

    display_map = {}
    for k in selected_keys:
        if k in key_to_column:
            col_name = key_to_column[k]
            display_map[col_name] = key_to_display.get(k, k)

    # Find which selected columns are in df
    available_cols = {}
    missing = []
    for k in selected_keys:
        if k in key_to_column:
            col_name = key_to_column[k]
            if col_name in df.columns:
                display_name = display_map[col_name]
                available_cols[col_name] = display_name
            else:
                missing.append(display_map.get(col_name, k))

    # Build result
    result_cols = list(available_cols.keys())
    result = df[result_cols].rename(columns=available_cols)

    if missing:
        for m in missing:
            result[f"[Missing: {m}]"] = None

    return result
