"""Pure helpers for reading and normalizing provisional EIMS workbooks."""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
import re
from typing import BinaryIO

import pandas as pd

from data.constants import (
    EIMS_COLUMN_MAPPING,
    EIMS_NUMERIC_COLUMNS,
    EIMS_REQUIRED_COLUMNS,
    EIMS_WORKSHEET_NAME,
    MATCH_STATUS_UNMATCHED,
    SOURCE_TYPE_EIMS_IMPORT,
)


_NULL_NUMERIC_TEXT = frozenset({"", "none", "nan", "nat", "null"})
_NUMERIC_TEXT = re.compile(r"^[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$")


def _source_number(value):
    """Preserve invalid source text so validation cannot silently drop it."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        text = value.strip()
        if text.casefold() in _NULL_NUMERIC_TEXT:
            return None
        if not _NUMERIC_TEXT.fullmatch(text):
            return text
        value = text.replace(",", "")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value


def read_eims_workbook(file: BinaryIO) -> pd.DataFrame:
    """Read the 35 source columns saved in the EIMS 3 worksheet."""
    frame = pd.read_excel(
        file,
        sheet_name=EIMS_WORKSHEET_NAME,
        header=9,
        usecols="A:AI",
        engine="openpyxl",
    )
    frame.columns = [str(column).strip() for column in frame.columns]
    frame = frame.dropna(how="all").copy()
    frame["SOURCE_ROW_NUMBER"] = frame.index + 11
    if "Producer #" in frame.columns:
        frame = frame[frame["Producer #"].notna()].copy()
    return frame.reset_index(drop=True)


def normalize_eims_records(raw: pd.DataFrame) -> pd.DataFrame:
    """Map source columns without inventing Dataverse relationships."""
    normalized = raw.copy()
    normalized.columns = [str(column).strip() for column in normalized.columns]

    if "SOURCE_ROW_NUMBER" not in normalized.columns:
        normalized["SOURCE_ROW_NUMBER"] = normalized.index + 11

    for column in ("Week", "Producer #", "Grader#"):
        if column in normalized.columns:
            normalized[column] = (
                normalized[column]
                .astype("string")
                .str.replace(r"\.0$", "", regex=True)
                .str.strip()
            )

    week = normalized.get("Week", pd.Series(pd.NA, index=normalized.index)).astype(
        "string"
    )
    normalized["REPORTING_YEAR"] = pd.to_numeric(
        week.str.extract(r"^(\d{4})", expand=False), errors="coerce"
    )
    normalized["REPORTING_WEEK"] = pd.to_numeric(
        week.str.extract(r"(\d{1,2})$", expand=False), errors="coerce"
    )

    for column in EIMS_NUMERIC_COLUMNS:
        if column in normalized.columns:
            normalized[column] = normalized[column].map(_source_number)

    normalized = normalized.rename(columns=EIMS_COLUMN_MAPPING)
    normalized["PRODUCTION_ID"] = [str(uuid.uuid4()) for _ in range(len(normalized))]
    normalized["SOURCE_TYPE"] = SOURCE_TYPE_EIMS_IMPORT
    normalized["MATCH_STATUS"] = MATCH_STATUS_UNMATCHED
    for relationship in (
        "PRODUCER_ACCOUNT_ID",
        "GRADER_ACCOUNT_ID",
        "FACILITY_ID",
        "FLOCK_ID",
    ):
        normalized[relationship] = None
    return normalized


def validate_eims_records(raw: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Return blocking technical errors and non-blocking warnings."""
    errors: list[str] = []
    warnings: list[str] = []
    missing = set(EIMS_REQUIRED_COLUMNS) - set(raw.columns)
    if missing:
        return ["Missing required columns: " + ", ".join(sorted(missing))], warnings

    normalized = normalize_eims_records(raw)
    for index, row in normalized.iterrows():
        source_row = int(row["SOURCE_ROW_NUMBER"])
        producer_number = row.get("PRODUCER_NUMBER")
        if pd.isna(producer_number) or not str(producer_number).strip():
            errors.append(f"Excel row {source_row}: Producer # is missing.")
        year = row.get("REPORTING_YEAR")
        week = row.get("REPORTING_WEEK")
        if pd.isna(year):
            errors.append(f"Excel row {source_row}: Week has no valid year.")
        if pd.isna(week) or not 1 <= int(week) <= 53:
            errors.append(f"Excel row {source_row}: Week must be between 1 and 53.")
        for source_column, target_column in EIMS_COLUMN_MAPPING.items():
            if source_column in EIMS_NUMERIC_COLUMNS:
                value = row.get(target_column)
                if isinstance(value, str):
                    errors.append(
                        f"Excel row {source_row}: {source_column} must contain a valid number."
                    )
                elif pd.notna(value) and value < 0:
                    errors.append(
                        f"Excel row {source_row}: {source_column} cannot be negative."
                    )
        if pd.isna(row.get("TOTAL")):
            warnings.append(f"Excel row {source_row}: Total is empty or invalid.")
    return errors, warnings


def build_raw_rows(
    raw: pd.DataFrame,
    validation_status: str,
    validation_messages: list[str] | None = None,
) -> list[dict]:
    """Create source-preserving RAW records from an imported frame."""
    messages = validation_messages or []
    rows: list[dict] = []
    for index, source in raw.iterrows():
        source_row = source.get("SOURCE_ROW_NUMBER", index + 11)
        values = source.drop(labels=["SOURCE_ROW_NUMBER"], errors="ignore").to_dict()
        rows.append(
            {
                "SOURCE_ROW_NUMBER": int(source_row),
                "RAW_DATA": values,
                "VALIDATION_STATUS": validation_status,
                "MATCH_STATUS": MATCH_STATUS_UNMATCHED,
                "VALIDATION_MESSAGES": messages,
            }
        )
    return rows
