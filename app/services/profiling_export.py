"""Exports for schema-agnostic profiling results; raw source rows are omitted."""

from __future__ import annotations

from io import BytesIO
import re

import pandas as pd

from app.services.export import spreadsheet_safe
from data.profiling import ProfileResult


INVALID_SHEET_CHARACTERS = re.compile(r"[\\/*?:\[\]]")


def safe_worksheet_names(names, *, reserved=()) -> dict[str, str]:
    """Normalize worksheet names and resolve case-insensitive collisions."""
    result: dict[str, str] = {}
    used: set[str] = {str(value).casefold() for value in reserved}
    for index, value in enumerate(names, start=1):
        source = str(value)
        base = INVALID_SHEET_CHARACTERS.sub("_", source).strip(" '") or f"Sheet {index}"
        base = base[:31]
        candidate = base
        suffix = 2
        while candidate.casefold() in used:
            marker = f"_{suffix}"
            candidate = f"{base[:31 - len(marker)]}{marker}"
            suffix += 1
        used.add(candidate.casefold())
        result[source] = candidate
    return result


def profile_csv(profile: ProfileResult) -> bytes:
    """Return a formula-safe UTF-8 CSV for one column profile."""
    return spreadsheet_safe(profile.column_profile).to_csv(index=False).encode("utf-8-sig")


def profiles_excel(
    profiles: dict[str, ProfileResult],
    primary_keys: dict[str, list[str]] | None = None,
    relationship_columns: dict[str, list[str]] | None = None,
) -> bytes:
    """Return a summary plus one formula-safe profile worksheet per source sheet."""
    primary_keys = primary_keys or {}
    relationship_columns = relationship_columns or {}
    summary = pd.DataFrame(
        [
            {
                "SOURCE_SHEET": name,
                "ROW_COUNT": profile.row_count,
                "COLUMN_COUNT": profile.column_count,
                "DUPLICATE_ROW_COUNT": profile.duplicate_row_count,
                "PRIMARY_KEY_SUGGESTIONS": ", ".join(primary_keys.get(name, [])),
                "RELATIONSHIP_COLUMN_SUGGESTIONS": ", ".join(relationship_columns.get(name, [])),
            }
            for name, profile in profiles.items()
        ]
    )
    names = safe_worksheet_names(profiles.keys(), reserved=["Workbook Summary"])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        spreadsheet_safe(summary).to_excel(writer, sheet_name="Workbook Summary", index=False)
        for source_name, profile in profiles.items():
            spreadsheet_safe(profile.column_profile).to_excel(
                writer, sheet_name=names[source_name], index=False
            )
    return output.getvalue()
