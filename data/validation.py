"""Business validation for provisional EFNS operational records."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

import pandas as pd

from data.constants import (
    FARM_LOCATION_STATUSES,
    QUOTA_TRANSACTION_TYPES,
    QUOTA_TYPES,
    SALMONELLA_RESULTS,
)


def validate_farm_location(repo, record: dict) -> list[str]:
    """Validate the provisional Account-owned Farm Location contract."""
    errors = []
    account_id = record.get("ACCOUNT_ID")
    if not account_id or repo.get_account(account_id) is None:
        errors.append("Farm Location requires an existing Account.")
    if not str(record.get("LOCATION_NAME") or "").strip():
        errors.append("Location Name is required.")
    if record.get("STATUS") not in FARM_LOCATION_STATUSES:
        errors.append("Status must be Active or Inactive.")
    return errors

if TYPE_CHECKING:
    from data.repositories.base import BaseRepository


FLOCK_DATE_FIELDS = (
    "PERMIT_DATE",
    "HATCH_DATE",
    "DATE_ORDERED",
    "PLACEMENT_DATE",
    "EST_DISPOSAL",
    "DISPOSAL_DATE",
)
_NULL_DATE_TEXT = {"", "none", "null", "nat"}


def normalize_flock_dates(record: dict) -> dict:
    """Return a copy whose Flock dates are Python ``date`` values or ``None``."""
    normalized = dict(record)
    for field in FLOCK_DATE_FIELDS:
        if field not in normalized:
            continue
        value = normalized[field]
        if value is None or (isinstance(value, str) and value.strip().casefold() in _NULL_DATE_TEXT):
            normalized[field] = None
            continue
        if not isinstance(value, str):
            try:
                if pd.isna(value):
                    normalized[field] = None
                    continue
            except (TypeError, ValueError):
                pass
        if isinstance(value, dt.datetime):
            normalized[field] = value.date()
        elif isinstance(value, dt.date):
            normalized[field] = value
        else:
            converted = pd.to_datetime(value, errors="coerce")
            if pd.isna(converted):
                raise ValueError(f"{field.replace('_', ' ').title()} is not a valid date.")
            normalized[field] = converted.date()
    return normalized


def _date(value):
    if value is None or value == "" or pd.isna(value):
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return pd.to_datetime(value).date()


def validate_flock(repo: "BaseRepository", record: dict) -> list[str]:
    record = normalize_flock_dates(record)
    errors: list[str] = []
    required = {
        "ACCOUNT_ID": "Account",
        "FACILITY_ID": "Facility",
        "FLOCK_NUMBER": "Flock Number",
        "PERMIT_NUMBER": "Permit Number",
        "HATCH_DATE": "Hatch Date",
        "BIRD_COUNT": "Bird Count",
    }
    for field, label in required.items():
        if record.get(field) is None or str(record.get(field)).strip() == "":
            errors.append(f"{label} is required.")

    account_id = record.get("ACCOUNT_ID")
    facility_id = record.get("FACILITY_ID")
    if account_id and facility_id:
        facilities = repo.get_facilities(account_id=account_id)
        if facilities.empty or facility_id not in set(facilities["FACILITY_ID"]):
            errors.append("Facility must belong to the selected account.")

    detail_id = record.get("FACILITY_DETAIL_ID")
    if detail_id and facility_id:
        details = repo.get_facility_details(facility_id=facility_id)
        if details.empty or detail_id not in set(details["FACILITY_DETAIL_ID"]):
            errors.append("Facility Detail must belong to the selected facility.")

    quota_id = record.get("QUOTA_ID")
    if quota_id and account_id:
        quotas = repo.get_quota_registrations(account_id=account_id, active_only=True)
        if quotas.empty or quota_id not in set(quotas["QUOTA_ID"]):
            errors.append("Quota Registration must be active and belong to the selected account.")

    bird_count = int(record.get("BIRD_COUNT") or 0)
    birds_disposed = int(record.get("BIRDS_DISPOSED") or 0)
    if bird_count < 0 or birds_disposed < 0:
        errors.append("Bird Count and Birds Disposed cannot be negative.")
    if birds_disposed > bird_count:
        errors.append("Birds Disposed cannot exceed Bird Count.")

    disposal = _date(record.get("DISPOSAL_DATE"))
    hatch = _date(record.get("HATCH_DATE"))
    placement = _date(record.get("PLACEMENT_DATE"))
    if disposal and hatch and disposal < hatch:
        errors.append("Disposal Date cannot be earlier than Hatch Date.")
    if disposal and placement and disposal < placement:
        errors.append("Disposal Date cannot be earlier than Placement Date.")
    return errors


def validate_quota_registration(repo: "BaseRepository", record: dict) -> list[str]:
    errors: list[str] = []
    if not record.get("ACCOUNT_ID"):
        errors.append("Account is required.")
    elif repo.get_account(record["ACCOUNT_ID"]) is None:
        errors.append("Account does not exist.")
    if not str(record.get("REGISTRATION_NUMBER") or "").strip():
        errors.append("Registration Number is required.")
    if record.get("QUOTA_TYPE") not in QUOTA_TYPES:
        errors.append("Quota Type must use a supported provisional choice.")
    start, end = _date(record.get("EFFECTIVE_DATE")), _date(record.get("END_DATE"))
    if start and end and end < start:
        errors.append("End Date cannot be earlier than Effective Date.")
    return errors


def validate_quota_transaction(repo: "BaseRepository", record: dict) -> list[str]:
    errors: list[str] = []
    quota_id = record.get("QUOTA_ID")
    quota = repo.get_quota_registration(quota_id) if quota_id else None
    if quota is None:
        errors.append("Quota Registration is required.")
    if record.get("TRANSACTION_TYPE") not in QUOTA_TRANSACTION_TYPES:
        errors.append("Transaction Type is required.")
    if float(record.get("QUOTA_COUNT") or 0) <= 0:
        errors.append("Quota Count must be greater than zero.")
    if not record.get("RELATED_ACCOUNT_ID"):
        errors.append("Related Account is required for quota transactions.")
    elif repo.get_account(record["RELATED_ACCOUNT_ID"]) is None:
        errors.append("Related Account does not exist.")
    start, end = _date(record.get("EFFECTIVE_DATE")), _date(record.get("END_DATE"))
    if start and end and end < start:
        errors.append("End Date cannot be earlier than Effective Date.")
    return errors


def validate_salmonella_test(repo: "BaseRepository", record: dict) -> list[str]:
    errors: list[str] = []
    flock_id = record.get("FLOCK_ID")
    flock = repo.get_flock(flock_id) if flock_id else None
    if flock is None:
        errors.append("Flock is required.")
    else:
        if record.get("ACCOUNT_ID") != flock.get("ACCOUNT_ID"):
            errors.append("Account must match the selected flock.")
        if str(record.get("PERMIT_NUMBER") or "") != str(flock.get("PERMIT_NUMBER") or ""):
            errors.append("Permit Number must match the selected flock.")
    testing = _date(record.get("TESTING_DATE"))
    if testing is None:
        errors.append("Testing Date is required.")
    if int(record.get("NUMBER_OF_SAMPLES") or 0) <= 0:
        errors.append("Number of Samples must be greater than zero.")
    for field, label in (("DATE_RECEIVED", "Date Received"), ("DATE_RESULT_SENT", "Date Result Sent")):
        value = _date(record.get(field))
        if value and testing and value < testing:
            errors.append(f"{label} cannot be earlier than Testing Date.")
    if record.get("TEST_RESULT") not in SALMONELLA_RESULTS:
        errors.append("Test Result must use a supported provisional choice.")
    return errors
