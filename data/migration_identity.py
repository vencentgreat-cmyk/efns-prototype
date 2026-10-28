"""Batch-scoped source identities shared by migration and correction paths."""

from __future__ import annotations

import datetime as dt

import pandas as pd


def identifier_text(value):
    if value is None or pd.isna(value):
        return None
    return value.isoformat() if isinstance(value, (dt.date, dt.datetime)) else str(value)


def scoped_raw_rows(batch_id, rows, *, allow_unassigned=False):
    records = rows.to_dict("records") if isinstance(rows, pd.DataFrame) else list(rows)
    result = []
    seen = set()
    for record in records:
        row = dict(record)
        supplied_batch = identifier_text(row.get("MIGRATION_BATCH_ID"))
        if supplied_batch != batch_id and not (allow_unassigned and supplied_batch is None):
            raise ValueError("RAW source rows must belong to the requested migration batch.")
        raw_id = identifier_text(row.get("MIGRATION_RAW_ROW_ID"))
        if not raw_id or not raw_id.strip():
            raise ValueError("RAW source row identity is missing.")
        if raw_id in seen:
            raise ValueError("Duplicate RAW source row identity within the migration batch.")
        seen.add(raw_id)
        row["MIGRATION_BATCH_ID"] = batch_id
        result.append(row)
    return result


def validate_correction_sources(batch_id, correction_rows, raw_rows):
    sources = {
        identifier_text(row["MIGRATION_RAW_ROW_ID"]): row
        for row in scoped_raw_rows(batch_id, raw_rows)
    }
    seen = set()
    for row in correction_rows:
        raw_id = identifier_text(row.get("MIGRATION_RAW_ROW_ID"))
        if row.get("ORIGINAL_MIGRATION_BATCH_ID") != batch_id or raw_id not in sources:
            raise ValueError("Correction source does not resolve in the original migration batch.")
        if raw_id in seen:
            raise ValueError("Duplicate correction source identity.")
        seen.add(raw_id)
        source = sources[raw_id]
        for field in ("SOURCE_FILENAME", "SOURCE_ENTITY", "SOURCE_ROW_NUMBER", "SOURCE_ID"):
            if identifier_text(row.get(field)) != identifier_text(source.get(field)):
                raise ValueError(f"Correction source metadata does not match RAW: {field}.")
