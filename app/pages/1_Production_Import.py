# ============================================================
# EFNS Prototype v0.2 — EIMS Production Workbook Import
# ============================================================
"""Upload, read, preview, and validate an EIMS production workbook."""

from __future__ import annotations

import uuid

import pandas as pd
import streamlit as st

from data.repositories import get_repository


st.set_page_config(
    page_title="EIMS Production Import",
    page_icon="🥚",
    layout="wide",
)

if "repo" not in st.session_state:
    st.session_state.repo = get_repository()

repo = st.session_state.repo

st.title("EIMS Production Import")
st.caption(
    "Upload an EIMS Production Upload workbook. "
    "The system reads production data from the 'EIMS 3' worksheet."
)

# ============================================================
# Workbook requirements
# ============================================================

st.markdown("### Workbook Requirements")

st.write(
    """
The uploaded file must:

- Be an Excel `.xlsm` or `.xlsx` workbook
- Contain a worksheet named **EIMS 3**
- Use the standard EIMS production upload format
- Be recalculated and saved in Excel before uploading
"""
)

st.info(
    "This prototype reads saved Excel values. It does not run Excel macros "
    "or recalculate formulas."
)

st.divider()

# ============================================================
# File upload
# ============================================================

st.markdown("### Upload Production Workbook")

uploaded = st.file_uploader(
    "Choose an EIMS Production Upload file",
    type=["xlsm", "xlsx"],
    help="Upload the completed EIMS Production Upload workbook.",
)

if uploaded is None:
    st.info("Upload an EIMS Production Upload workbook to begin.")
    st.stop()

# ============================================================
# Read EIMS 3 worksheet
# ============================================================

try:
    raw_df = pd.read_excel(
        uploaded,
        sheet_name="EIMS 3",
        header=9,           # Excel row 10 contains readable column names
        usecols="A:AI",     # Read columns A through AI
        engine="openpyxl",
    )

except ValueError:
    st.error(
        "The workbook could not be processed because it does not contain "
        "a worksheet named 'EIMS 3'."
    )
    st.stop()

except ImportError:
    st.error(
        "The openpyxl package is required to read Excel workbooks. "
        "Run: pip install openpyxl"
    )
    st.stop()

except Exception as exc:
    st.error(f"Unable to read the uploaded workbook: {exc}")
    st.stop()

# Clean column names
raw_df.columns = [
    str(column).strip()
    for column in raw_df.columns
]

# Remove completely empty rows
raw_df = raw_df.dropna(how="all")

# Only retain rows that contain a producer number
if "Producer #" in raw_df.columns:
    raw_df = raw_df[
        raw_df["Producer #"].notna()
    ].copy()

raw_df = raw_df.reset_index(drop=True)

# ============================================================
# File summary
# ============================================================

st.success(f"Workbook loaded successfully: {uploaded.name}")

summary_col1, summary_col2, summary_col3 = st.columns(3)

summary_col1.metric("Production Records", len(raw_df))
summary_col2.metric("Columns Detected", len(raw_df.columns))
summary_col3.metric("Worksheet", "EIMS 3")

# ============================================================
# Raw preview
# ============================================================

st.markdown("### Production Data Preview")

if raw_df.empty:
    st.warning(
        "The EIMS 3 worksheet was found, but no production records "
        "were detected."
    )
    st.stop()

st.dataframe(
    raw_df.head(50),
    use_container_width=True,
    hide_index=True,
)

# ============================================================
# Column validation
# ============================================================

st.markdown("### Column Validation")

required_columns = {
    "Grader",
    "Producer #",
    "Grader#",
    "Week",
    "MarketingType",
    "Housing system",
    "Egg Type",
    "Colour",
    "J",
    "XL",
    "L",
    "M",
    "S",
    "PW",
    "B",
    "C",
    "CR",
    "NestRun",
    "RJ",
    "LK",
    "Total",
}

found_columns = set(raw_df.columns)
missing_columns = required_columns - found_columns

if missing_columns:
    st.error(
        "The workbook is missing required columns: "
        + ", ".join(sorted(missing_columns))
    )
    st.stop()
else:
    st.success("All required EIMS production columns were detected.")

# ============================================================
# Prepare normalized data
# ============================================================

normalized_df = raw_df.copy()

# Clean Week, Producer #, and Grader# values
normalized_df["Week"] = (
    normalized_df["Week"]
    .astype(str)
    .str.replace(r"\.0$", "", regex=True)
    .str.strip()
)

normalized_df["Producer #"] = (
    normalized_df["Producer #"]
    .astype(str)
    .str.replace(r"\.0$", "", regex=True)
    .str.strip()
)

normalized_df["Grader#"] = (
    normalized_df["Grader#"]
    .astype(str)
    .str.strip()
)

# Split values such as 202635 into year 2026 and week 35
normalized_df["REPORTING_YEAR"] = pd.to_numeric(
    normalized_df["Week"].str[:4],
    errors="coerce",
)

normalized_df["REPORTING_WEEK"] = pd.to_numeric(
    normalized_df["Week"].str[-2:],
    errors="coerce",
)

# Production quantity columns
numeric_columns = [
    "J",
    "XL",
    "L",
    "M",
    "S",
    "PW",
    "B",
    "C",
    "CR",
    "NestRun",
    "NR25+",
    "NR24+",
    "NR23+",
    "NR22+",
    "NR21+",
    "NR20+",
    "NR19+",
    "NR18+",
    "NR17+",
    "OL",
    "ON",
    "FG",
    "FC",
    "Subtotal",
    "RJ",
    "LK",
    "Total",
]

# Only process numeric columns that actually exist
existing_numeric_columns = [
    column
    for column in numeric_columns
    if column in normalized_df.columns
]

for column in existing_numeric_columns:
    normalized_df[column] = pd.to_numeric(
        normalized_df[column],
        errors="coerce",
    )

# ============================================================
# Data validation
# ============================================================

st.markdown("### Data Validation")

errors: list[str] = []
warnings: list[str] = []

for index, row in normalized_df.iterrows():
    # Data starts on Excel row 11
    excel_row = index + 11

    producer_number = str(row.get("Producer #", "")).strip()

    if not producer_number or producer_number.lower() == "nan":
        errors.append(
            f"Excel row {excel_row}: Producer # is missing."
        )

    reporting_year = row.get("REPORTING_YEAR")
    reporting_week = row.get("REPORTING_WEEK")

    if pd.isna(reporting_year):
        errors.append(
            f"Excel row {excel_row}: Week does not contain a valid year."
        )

    if pd.isna(reporting_week):
        errors.append(
            f"Excel row {excel_row}: Week is invalid."
        )
    elif not 1 <= int(reporting_week) <= 53:
        errors.append(
            f"Excel row {excel_row}: Reporting week must be between 1 and 53."
        )

    for column in existing_numeric_columns:
        value = row.get(column)

        if pd.notna(value) and value < 0:
            errors.append(
                f"Excel row {excel_row}: {column} cannot be negative."
            )

    total = row.get("Total")

    if pd.isna(total):
        warnings.append(
            f"Excel row {excel_row}: Total is empty or could not be read."
        )

if errors:
    st.error(f"{len(errors)} validation error(s) found:")

    for error in errors[:20]:
        st.write(f"- {error}")

    if len(errors) > 20:
        st.write(f"- ...and {len(errors) - 20} more errors")

else:
    st.success("No blocking validation errors were found.")

if warnings:
    with st.expander(
        f"Show {len(warnings)} validation warning(s)"
    ):
        for warning in warnings[:50]:
            st.write(f"- {warning}")

# ============================================================
# Normalized preview
# ============================================================

st.markdown("### Normalized Preview")

display_mapping = {
    "Grader": "GRADER_NAME",
    "Producer #": "PRODUCER_NUMBER",
    "Grader#": "GRADER_NUMBER",
    "MarketingType": "MARKETING_TYPE",
    "Housing system": "HOUSING_SYSTEM",
    "Egg Type": "EGG_TYPE",
    "Colour": "EGG_COLOUR",
    "Subtotal": "SUBTOTAL",
    "RJ": "REJECTS",
    "LK": "LEAKERS",
    "Total": "TOTAL",
}

normalized_preview = normalized_df.rename(
    columns=display_mapping
)

preview_columns = [
    "REPORTING_YEAR",
    "REPORTING_WEEK",
    "GRADER_NAME",
    "PRODUCER_NUMBER",
    "GRADER_NUMBER",
    "MARKETING_TYPE",
    "HOUSING_SYSTEM",
    "EGG_TYPE",
    "EGG_COLOUR",
    "J",
    "XL",
    "L",
    "M",
    "S",
    "PW",
    "B",
    "C",
    "CR",
    "NestRun",
    "SUBTOTAL",
    "REJECTS",
    "LEAKERS",
    "TOTAL",
]

available_preview_columns = [
    column
    for column in preview_columns
    if column in normalized_preview.columns
]

st.dataframe(
    normalized_preview[available_preview_columns].head(50),
    use_container_width=True,
    hide_index=True,
)

# ============================================================
# Database import
# ============================================================

st.markdown("### Database Import")

st.caption(
    "Import the validated EIMS production records into the current "
    "prototype repository. Mock data remains available until the app restarts."
)

# Rename source columns to database-friendly names. These names avoid spaces
# and symbols such as # and +, which will simplify the later Snowflake import.
database_mapping = {
    "Grader": "GRADER_NAME",
    "Producer #": "PRODUCER_NUMBER",
    "Grader#": "GRADER_NUMBER",
    "Week": "SOURCE_WEEK_CODE",
    "MarketingType": "MARKETING_TYPE",
    "Housing system": "HOUSING_SYSTEM",
    "Egg Type": "EGG_TYPE",
    "Colour": "EGG_COLOUR",
    "J": "JUMBO",
    "XL": "EXTRA_LARGE",
    "L": "LARGE",
    "M": "MEDIUM",
    "S": "SMALL",
    "PW": "PEEWEE",
    "B": "GRADE_B",
    "C": "GRADE_C",
    "CR": "CRACKS",
    "NestRun": "NEST_RUN",
    "NR25+": "NEST_RUN_25_PLUS",
    "NR24+": "NEST_RUN_24_PLUS",
    "NR23+": "NEST_RUN_23_PLUS",
    "NR22+": "NEST_RUN_22_PLUS",
    "NR21+": "NEST_RUN_21_PLUS",
    "NR20+": "NEST_RUN_20_PLUS",
    "NR19+": "NEST_RUN_19_PLUS",
    "NR18+": "NEST_RUN_18_PLUS",
    "NR17+": "NEST_RUN_17_PLUS",
    "OL": "OTHER_LEVIABLE",
    "ON": "OTHER_NON_LEVIABLE",
    "FG": "FARM_GATE_SALES",
    "FC": "ON_FARM_CONSUMPTION",
    "Subtotal": "SUBTOTAL",
    "RJ": "REJECTS",
    "LK": "LEAKERS",
    "Total": "TOTAL",
}

database_df = normalized_df.rename(columns=database_mapping).copy()

# Retain known business fields and remove accidental blank Excel columns.
database_columns = [
    "GRADER_NAME",
    "PRODUCER_NUMBER",
    "GRADER_NUMBER",
    "SOURCE_WEEK_CODE",
    "REPORTING_YEAR",
    "REPORTING_WEEK",
    "MARKETING_TYPE",
    "HOUSING_SYSTEM",
    "EGG_TYPE",
    "EGG_COLOUR",
    "JUMBO",
    "EXTRA_LARGE",
    "LARGE",
    "MEDIUM",
    "SMALL",
    "PEEWEE",
    "GRADE_B",
    "GRADE_C",
    "CRACKS",
    "NEST_RUN",
    "NEST_RUN_25_PLUS",
    "NEST_RUN_24_PLUS",
    "NEST_RUN_23_PLUS",
    "NEST_RUN_22_PLUS",
    "NEST_RUN_21_PLUS",
    "NEST_RUN_20_PLUS",
    "NEST_RUN_19_PLUS",
    "NEST_RUN_18_PLUS",
    "NEST_RUN_17_PLUS",
    "OTHER_LEVIABLE",
    "OTHER_NON_LEVIABLE",
    "FARM_GATE_SALES",
    "ON_FARM_CONSUMPTION",
    "SUBTOTAL",
    "REJECTS",
    "LEAKERS",
    "TOTAL",
]

database_df = database_df[
    [column for column in database_columns if column in database_df.columns]
].copy()

database_df["PRODUCTION_ID"] = [
    str(uuid.uuid4()) for _ in range(len(database_df))
]

reporting_years = (
    database_df["REPORTING_YEAR"].dropna().astype(int).unique()
)
reporting_weeks = (
    database_df["REPORTING_WEEK"].dropna().astype(int).unique()
)

batch_year = int(reporting_years[0]) if len(reporting_years) == 1 else None
batch_week = int(reporting_weeks[0]) if len(reporting_weeks) == 1 else None

filename = st.text_input(
    "Source filename",
    value=uploaded.name,
)

if errors:
    st.error(
        "Import is unavailable until all blocking validation errors are fixed."
    )
else:
    st.success(
        f"{len(database_df)} validated production records are ready to import."
    )


def prepare_legacy_mock_repository(records: pd.DataFrame) -> None:
    """Allow the v0.1 MockRepository to preserve new EIMS columns."""

    if not hasattr(repo, "_production"):
        return

    for column in records.columns:
        if column not in repo._production.columns:
            repo._production[column] = pd.NA


if st.button(
    "Import Data",
    type="primary",
    disabled=bool(errors),
):
    try:
        import_id = repo.create_import_batch(
            {
                "IMPORT_ID": str(uuid.uuid4()),
                "FILENAME": filename,
                "SOURCE": "EIMS Production Workbook - EIMS 3",
                "REPORTING_YEAR": batch_year,
                "REPORTING_WEEK": batch_week,
                "STATUS": "Validated",
                "ROW_COUNT": 0,
                "ERROR_COUNT": len(errors),
                "NOTES": "Imported from the EIMS 3 worksheet.",
            }
        )

        prepare_legacy_mock_repository(database_df)

        imported_count = repo.insert_production_records(
            database_df,
            import_id,
        )

        st.success(
            f"Successfully imported {imported_count} production records."
        )
        st.write(f"**Import ID:** `{import_id}`")

        with st.expander("Show imported records"):
            st.dataframe(
                database_df.head(50),
                use_container_width=True,
                hide_index=True,
            )

    except NotImplementedError:
        st.error(
            "The selected repository does not support production imports yet. "
            "Use MockRepository for the current prototype."
        )

    except Exception as exc:
        st.error(f"Import failed: {exc}")
