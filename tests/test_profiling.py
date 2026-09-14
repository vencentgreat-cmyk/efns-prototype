"""Offline tests for schema-agnostic source profiling and exports."""

from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app.services.profiling_export import profile_csv, profiles_excel, safe_worksheet_names
from app.security import Role
from data.profiling import (
    ProfilingError,
    candidate_primary_keys,
    candidate_relationship_columns,
    profile_dataframe,
    read_tabular,
)
from tests.auth_support import authenticated_app


def test_read_csv_preserves_leading_zero_values_and_stream_position():
    source = BytesIO(b"record_id,amount\n001,1.5\n002,2.5\n")
    source.name = "source.csv"
    source.seek(4)
    frames = read_tabular(source)
    assert source.tell() == 4
    assert list(frames) == ["source"]
    assert frames["source"]["record_id"].tolist() == ["001", "002"]
    assert read_tabular(source)["source"].shape == (2, 2)


def test_read_multisheet_excel_and_xlsm_without_macro_execution():
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame({"A": [1]}).to_excel(writer, sheet_name="First", index=False)
        pd.DataFrame({"B": [2]}).to_excel(writer, sheet_name="Second", index=False)
    frames = read_tabular(BytesIO(output.getvalue()), "sample.xlsm")
    assert list(frames) == ["First", "Second"]
    assert frames["Second"].iloc[0, 0] == 2


@pytest.mark.parametrize("filename", ["data.json", "data.txt", "data.xls"])
def test_read_tabular_rejects_unsupported_formats(filename):
    with pytest.raises(ProfilingError, match="Unsupported format"):
        read_tabular(BytesIO(b"anything"), filename)


@pytest.mark.parametrize("content", [b"", b"\n"])
def test_read_tabular_rejects_empty_or_unreadable_files(content):
    with pytest.raises(ProfilingError):
        read_tabular(BytesIO(content), "empty.csv")


def test_empty_dataframe_profile_is_stable():
    result = profile_dataframe(pd.DataFrame(columns=["A"]))
    assert (result.row_count, result.column_count, result.duplicate_row_count) == (0, 1, 0)
    row = result.column_profile.iloc[0]
    assert row["INFERRED_TYPE"] == "empty/unknown"
    assert row["NULL_RATIO"] == 0
    assert row["UNIQUE_RATIO"] == 0


def test_all_null_and_categorical_columns():
    frame = pd.DataFrame({"EMPTY": [None] * 4, "CATEGORY": ["A", "A", "B", None]})
    result = profile_dataframe(frame).column_profile.set_index("COLUMN_NAME")
    assert result.loc["EMPTY", "INFERRED_TYPE"] == "empty/unknown"
    assert result.loc["EMPTY", "NULL_RATIO"] == 1
    assert result.loc["CATEGORY", "INFERRED_TYPE"] == "text"
    assert result.loc["CATEGORY", "NULL_COUNT"] == 1

    repeated = profile_dataframe(pd.DataFrame({"CATEGORY": ["A", "A", "B", "B", None]}))
    assert repeated.column_profile.iloc[0]["INFERRED_TYPE"] == "categorical"


def test_numeric_boolean_date_datetime_and_mixed_inference():
    frame = pd.DataFrame(
        {
            "INTEGER": [1, 2],
            "DECIMAL": [1.5, 2.25],
            "BOOLEAN": [True, False],
            "DATE": [date(2026, 1, 2), date(2026, 2, 3)],
            "DATETIME": ["2026-01-02 10:30", "2026-02-03 12:45"],
            "MIXED": ["A", 2],
        }
    )
    result = profile_dataframe(frame).column_profile.set_index("COLUMN_NAME")
    assert result["INFERRED_TYPE"].to_dict() == {
        "INTEGER": "integer",
        "DECIMAL": "decimal",
        "BOOLEAN": "boolean",
        "DATE": "date",
        "DATETIME": "datetime",
        "MIXED": "text",
    }
    assert result.loc["DATE", "DATE_MIN"] == date(2026, 1, 2)
    assert str(result.loc["DATETIME", "DATE_MAX"]).startswith("2026-02-03 12:45")


def test_duplicates_ratios_and_deterministic_samples():
    frame = pd.DataFrame({"ID": ["001", "001", "002", None], "VALUE": [1, 1, 2, 3]})
    result = profile_dataframe(frame)
    row = result.column_profile.set_index("COLUMN_NAME").loc["ID"]
    assert result.duplicate_row_count == 1
    assert row["NULL_COUNT"] == 1
    assert row["NULL_RATIO"] == 0.25
    assert row["UNIQUE_COUNT"] == 2
    assert row["UNIQUE_RATIO"] == pytest.approx(2 / 3)
    assert row["SAMPLE_VALUES"] == "001 | 002"

    duplicate = profile_dataframe(pd.DataFrame({"A": [1, 1, 1]}))
    assert duplicate.duplicate_row_count == 2


def test_primary_key_and_relationship_suggestions_are_heuristic():
    frame = pd.DataFrame({"record_id": [1, 2, 3], "NAME": ["A", "B", "C"]})
    assert candidate_primary_keys(frame) == ["record_id", "NAME"]
    assert candidate_relationship_columns(frame) == ["record_id"]
    assert candidate_primary_keys(pd.DataFrame(columns=["ID"])) == []


def test_high_cardinality_relationship_heuristic_avoids_tiny_frames():
    tiny = pd.DataFrame({"DESCRIPTION": ["A", "B", "A"]})
    assert candidate_relationship_columns(tiny) == []
    large = pd.DataFrame({"REFERENCE": [*map(str, range(19)), "0"]})
    assert candidate_relationship_columns(large) == ["REFERENCE"]


def test_profile_exports_are_formula_safe_and_exclude_raw_rows():
    profile = profile_dataframe(pd.DataFrame({"=DANGEROUS": ["+formula", "ordinary"]}))
    csv_bytes = profile_csv(profile)
    decoded = csv_bytes.decode("utf-8-sig")
    assert "'=DANGEROUS" in decoded
    assert "'+formula" in decoded

    workbook = profiles_excel(
        {"Bad/Name": profile},
        {"Bad/Name": ["=KEY"]},
        {"Bad/Name": ["+REL"]},
    )
    with pd.ExcelFile(BytesIO(workbook), engine="openpyxl") as excel:
        assert excel.sheet_names == ["Workbook Summary", "Bad_Name"]
        exported = pd.read_excel(excel, "Bad_Name")
        summary = pd.read_excel(excel, "Workbook Summary")
    assert exported.loc[0, "COLUMN_NAME"] == "'=DANGEROUS"
    assert summary.loc[0, "PRIMARY_KEY_SUGGESTIONS"] == "'=KEY"
    assert len(exported) == 1  # one profile row; the two raw source rows were not exported


def test_safe_worksheet_names_resolve_invalid_names_and_collisions():
    names = safe_worksheet_names(["A/B", "A:B", "x" * 40])
    assert list(names.values()) == ["A_B", "A_B_2", "x" * 31]
    reserved = safe_worksheet_names(["Workbook Summary"], reserved=["Workbook Summary"])
    assert reserved["Workbook Summary"] == "Workbook Summary_2"


def test_profiler_page_smoke_without_upload_or_repository(tmp_path, monkeypatch):
    entrypoint = Path(__file__).parents[1] / "app" / "pages" / "14_Source_Data_Profiler.py"
    source = entrypoint.read_text(encoding="utf-8")
    assert "data.repositories" not in source
    assert "Snowflake" not in source.replace("sent to Snowflake", "")
    app = authenticated_app(entrypoint, tmp_path, monkeypatch, Role.DEVELOPER)
    assert list(app.exception) == []
    assert len(app.get("file_uploader")) == 1
    assert any("No source selected" in block.value for block in app.markdown)
