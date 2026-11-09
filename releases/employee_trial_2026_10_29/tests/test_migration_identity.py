"""Source identity is a batch/row pair, not a GUID or target date."""

import datetime as dt

import pandas as pd
import pytest

from data.migration_identity import identifier_text, scoped_raw_rows, validate_correction_sources
from data.historical_corrections import build_historical_correction_preview


def raw(batch="batch-a", row_id="raw-1"):
    return {
        "MIGRATION_BATCH_ID": batch, "MIGRATION_RAW_ROW_ID": row_id,
        "SOURCE_FILENAME": "DateConverter$.csv", "SOURCE_ENTITY": "DIM_EFC_DATE",
        "SOURCE_ROW_NUMBER": 1, "SOURCE_ID": dt.date(2020, 1, 1),
        "VALIDATION_STATUS": "READY",
    }


def test_identity_accepts_same_raw_id_in_separate_batches():
    assert scoped_raw_rows("batch-a", [raw()])[0]["MIGRATION_BATCH_ID"] == "batch-a"
    assert scoped_raw_rows("batch-b", [raw("batch-b")])[0]["MIGRATION_BATCH_ID"] == "batch-b"


@pytest.mark.parametrize("rows", [[raw(), raw()], [raw(), raw("batch-b")]])
def test_preview_rejects_duplicate_or_mixed_batch_sources(rows):
    with pytest.raises(ValueError):
        build_historical_correction_preview("batch-a", rows, {})


def test_unassigned_analyzer_rows_only_allowed_at_preparation_boundary():
    row = raw()
    del row["MIGRATION_BATCH_ID"]
    with pytest.raises(ValueError):
        scoped_raw_rows("batch-a", [row])
    assert scoped_raw_rows("batch-a", [row], allow_unassigned=True)[0]["MIGRATION_BATCH_ID"] == "batch-a"
    assert "MIGRATION_BATCH_ID" not in row


def test_correction_validates_batch_and_source_metadata():
    source = raw()
    correction = {**source, "ORIGINAL_MIGRATION_BATCH_ID": "batch-a", "SOURCE_ID": "2020-01-01"}
    validate_correction_sources("batch-a", [correction], pd.DataFrame([source]))
    for field, invalid in [("ORIGINAL_MIGRATION_BATCH_ID", "batch-b"), ("SOURCE_ROW_NUMBER", 2), ("SOURCE_ID", "wrong")]:
        with pytest.raises(ValueError):
            validate_correction_sources("batch-a", [{**correction, field: invalid}], [source])
    with pytest.raises(ValueError, match="Duplicate correction"):
        validate_correction_sources("batch-a", [correction, correction], [source])


def test_date_identity_serialization_preserves_iso_and_null():
    assert identifier_text(dt.date(2020, 1, 1)) == "2020-01-01"
    assert identifier_text(None) is None
    assert identifier_text(pd.NA) is None


def test_retry_restores_each_date_lineage_not_only_the_shared_target():
    from tests.test_eims_migration import _v3_sources
    from data.migration import analyze_migration_files
    from data.repositories.mock import MockRepository
    sources, mapping, _ids = _v3_sources()
    analysis = analyze_migration_files(sources, mapping)
    batch = {
        "MIGRATION_BATCH_ID": analysis.batch_id, "PACKAGE_HASH": analysis.package_hash,
        "SCHEMA_VERSION": analysis.schema_version, "STATUS": "FAILED",
    }
    repo = MockRepository()
    repo.prepare_migration_batch(batch, analysis.files, analysis.raw_rows)
    date_maps = [r for r in repo._migration_id_map if r["SOURCE_ENTITY"] == "DIM_EFC_DATE"]
    assert len(date_maps) == 2 and len({r["TARGET_ID"] for r in date_maps}) == 1
    repo._migration_id_map.remove(date_maps[0])
    assert not repo.get_migration_retry_status(analysis.batch_id)["complete"]
    repo.repair_migration_batch(batch, analysis.files, analysis.raw_rows)
    repo.repair_migration_batch(batch, analysis.files, analysis.raw_rows)
    restored = [r for r in repo._migration_id_map if r["SOURCE_ENTITY"] == "DIM_EFC_DATE"]
    assert len(restored) == 2 and len({r["MIGRATION_RAW_ROW_ID"] for r in restored}) == 2
    assert repo.get_migration_retry_status(analysis.batch_id)["complete"]
