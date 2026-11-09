"""Safe tabular exports for user-controlled text fields."""

from __future__ import annotations

import pandas as pd


FORMULA_PREFIXES = ("=", "+", "-", "@")


def spreadsheet_safe(frame: pd.DataFrame) -> pd.DataFrame:
    """Prevent text values from being interpreted as spreadsheet formulas."""
    safe = frame.copy()
    for column in safe.select_dtypes(include=["object", "string"]).columns:
        safe[column] = safe[column].map(
            lambda value: (
                "'" + value
                if isinstance(value, str) and value.lstrip().startswith(FORMULA_PREFIXES)
                else value
            )
        )
    return safe
