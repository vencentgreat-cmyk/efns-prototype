"""Schema-agnostic, in-memory profiling for tabular source files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
import re

import pandas as pd
from pandas.api import types as ptypes


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm"}
SAMPLE_LIMIT = 3
RELATIONSHIP_SUFFIXES = ("_id", "_number", "_code", "_no")


class ProfilingError(Exception):
    """A credential-safe error suitable for display on the profiler page."""


@dataclass(frozen=True)
class ProfileResult:
    """Advisory statistics for one source sheet or delimited file."""

    row_count: int
    column_count: int
    duplicate_row_count: int
    column_profile: pd.DataFrame


def _file_bytes(file) -> bytes:
    if isinstance(file, (bytes, bytearray)):
        return bytes(file)
    if isinstance(file, (str, Path)):
        try:
            return Path(file).read_bytes()
        except OSError as exc:
            raise ProfilingError("The selected file could not be read.") from exc
    if not hasattr(file, "read"):
        raise ProfilingError("The supplied source is not a readable tabular file.")

    original_position = None
    try:
        if hasattr(file, "tell"):
            original_position = file.tell()
        if hasattr(file, "seek"):
            file.seek(0)
        content = file.read()
        if isinstance(content, str):
            content = content.encode("utf-8")
        return bytes(content)
    except (OSError, TypeError, ValueError) as exc:
        raise ProfilingError("The selected file could not be read.") from exc
    finally:
        if original_position is not None and hasattr(file, "seek"):
            try:
                file.seek(original_position)
            except (OSError, ValueError):
                pass


def _source_filename(file, filename: str | None) -> str:
    source_name = filename or getattr(file, "name", None)
    if not source_name and isinstance(file, (str, Path)):
        source_name = str(file)
    if not source_name:
        raise ProfilingError("A filename with a supported extension is required.")
    return Path(str(source_name)).name


def _safe_labels(labels) -> list[str]:
    """Return stable, non-empty, case-insensitively unique source labels."""
    used: set[str] = set()
    result: list[str] = []
    for index, value in enumerate(labels, start=1):
        base = str(value).strip() or f"Sheet {index}"
        candidate = base
        suffix = 2
        while candidate.casefold() in used:
            candidate = f"{base} ({suffix})"
            suffix += 1
        used.add(candidate.casefold())
        result.append(candidate)
    return result


def read_tabular(file, filename: str | None = None) -> dict[str, pd.DataFrame]:
    """Read a CSV or every Excel worksheet without persisting the source."""
    source_name = _source_filename(file, filename)
    extension = Path(source_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ProfilingError("Unsupported format. Upload a CSV, XLSX, or XLSM file.")
    content = _file_bytes(file)
    if not content:
        raise ProfilingError("The uploaded file is empty.")

    try:
        if extension == ".csv":
            # Keep lexical source representations such as leading-zero IDs.
            frames = {Path(source_name).stem or "CSV": pd.read_csv(BytesIO(content), dtype=object)}
        else:
            # openpyxl reads cell values only; VBA macros are never executed.
            frames = pd.read_excel(BytesIO(content), sheet_name=None, engine="openpyxl")
    except (pd.errors.EmptyDataError, UnicodeError, ValueError, OSError, ImportError) as exc:
        raise ProfilingError("The file could not be parsed as tabular data.") from exc

    if not frames or all(frame.empty and len(frame.columns) == 0 for frame in frames.values()):
        raise ProfilingError("The file does not contain any tabular rows or columns.")
    labels = _safe_labels(frames.keys())
    return {label: frame for label, frame in zip(labels, frames.values())}


def _non_null(series: pd.Series) -> pd.Series:
    return series[~series.isna()]


def _looks_like_integer_text(values: pd.Series) -> bool:
    strings = values.map(str)
    if not strings.map(lambda value: bool(re.fullmatch(r"[+-]?\d+", value.strip()))).all():
        return False
    # Keep leading-zero identifiers as text.
    return not strings.map(lambda value: bool(re.fullmatch(r"[+-]?0\d+", value.strip()))).any()


def _looks_like_decimal_text(values: pd.Series) -> bool:
    strings = values.map(str)
    return strings.map(
        lambda value: bool(re.fullmatch(r"[+-]?(?:\d+\.\d+|\d+\.|\.\d+)", value.strip()))
    ).all()


def _date_kind(values: pd.Series) -> str | None:
    if values.map(lambda value: isinstance(value, datetime)).all():
        return "date" if values.map(lambda value: value.time() == datetime.min.time()).all() else "datetime"
    if values.map(lambda value: isinstance(value, date) and not isinstance(value, datetime)).all():
        return "date"
    strings = values.map(str).str.strip()
    if strings.map(lambda value: bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))).all():
        return "date"
    if strings.map(
        lambda value: bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?", value))
    ).all():
        return "datetime"
    return None


def _inferred_type(series: pd.Series) -> str:
    values = _non_null(series)
    if values.empty:
        return "empty/unknown"
    if ptypes.is_bool_dtype(series.dtype) or values.map(lambda value: isinstance(value, bool)).all():
        return "boolean"
    if ptypes.is_datetime64_any_dtype(series.dtype):
        timestamps = pd.to_datetime(values, errors="coerce")
        return "date" if (timestamps.dt.time == datetime.min.time()).all() else "datetime"
    if ptypes.is_integer_dtype(series.dtype):
        return "integer"
    if ptypes.is_float_dtype(series.dtype) or ptypes.is_numeric_dtype(series.dtype):
        numeric = pd.to_numeric(values, errors="coerce")
        return "integer" if numeric.map(float.is_integer).all() else "decimal"

    date_kind = _date_kind(values)
    if date_kind:
        return date_kind
    if _looks_like_integer_text(values):
        return "integer"
    if _looks_like_decimal_text(values):
        return "decimal"

    unique_count = int(values.nunique(dropna=True))
    unique_ratio = unique_count / len(values)
    # Generic advisory rule: repeated values, at least four observations,
    # no more than 20 distinct values, and at most 50% unique.
    if len(values) >= 4 and unique_count <= 20 and unique_ratio <= 0.5:
        return "categorical"
    return "text"


def _sample_text(series: pd.Series) -> str:
    values = _non_null(series).drop_duplicates().head(SAMPLE_LIMIT)
    return " | ".join(str(value) for value in values.tolist())


def _date_range(series: pd.Series, inferred_type: str):
    if inferred_type not in {"date", "datetime"}:
        return None, None
    converted = pd.to_datetime(_non_null(series), errors="coerce").dropna()
    if converted.empty:
        return None, None
    minimum, maximum = converted.min(), converted.max()
    if inferred_type == "date":
        return minimum.date(), maximum.date()
    return minimum, maximum


def profile_dataframe(df: pd.DataFrame) -> ProfileResult:
    """Profile a frame without modifying or coercing its source columns."""
    row_count = len(df)
    records = []
    for position, column in enumerate(df.columns):
        series = df.iloc[:, position]
        non_null_count = int(series.notna().sum())
        null_count = row_count - non_null_count
        unique_count = int(_non_null(series).nunique(dropna=True))
        inferred_type = _inferred_type(series)
        date_min, date_max = _date_range(series, inferred_type)
        records.append(
            {
                "COLUMN_NAME": str(column),
                "INFERRED_TYPE": inferred_type,
                "NULL_COUNT": null_count,
                "NULL_RATIO": null_count / row_count if row_count else 0.0,
                "NON_NULL_COUNT": non_null_count,
                "UNIQUE_COUNT": unique_count,
                "UNIQUE_RATIO": unique_count / non_null_count if non_null_count else 0.0,
                "SAMPLE_VALUES": _sample_text(series),
                "DATE_MIN": date_min,
                "DATE_MAX": date_max,
            }
        )
    columns = [
        "COLUMN_NAME", "INFERRED_TYPE", "NULL_COUNT", "NULL_RATIO",
        "NON_NULL_COUNT", "UNIQUE_COUNT", "UNIQUE_RATIO", "SAMPLE_VALUES",
        "DATE_MIN", "DATE_MAX",
    ]
    duplicate_count = int(df.duplicated(keep="first").sum()) if row_count else 0
    return ProfileResult(row_count, len(df.columns), duplicate_count, pd.DataFrame(records, columns=columns))


def candidate_primary_keys(df: pd.DataFrame) -> list[str]:
    """Return heuristic single-column key candidates, never confirmed keys."""
    if df.empty:
        return []
    candidates = []
    for position, column in enumerate(df.columns):
        series = df.iloc[:, position]
        if not series.isna().any() and int(series.nunique(dropna=False)) == len(df):
            candidates.append(str(column))
    return candidates


def candidate_relationship_columns(df: pd.DataFrame) -> list[str]:
    """Return deterministic relationship-like column suggestions.

    Besides identifier-shaped names, the generic data heuristic requires at
    least 20 non-null values and 80–99.999% cardinality. This avoids labelling
    every text column in small samples while still surfacing repeated codes.
    """
    candidates = []
    for position, column in enumerate(df.columns):
        name = str(column)
        series = df.iloc[:, position]
        values = _non_null(series)
        shaped = name.casefold().endswith(RELATIONSHIP_SUFFIXES)
        unique_ratio = int(values.nunique(dropna=True)) / len(values) if len(values) else 0.0
        high_cardinality = len(values) >= 20 and 0.8 <= unique_ratio < 1.0
        if shaped or high_cardinality:
            candidates.append(name)
    return candidates
