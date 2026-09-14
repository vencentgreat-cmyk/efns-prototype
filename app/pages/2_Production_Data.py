"""Searchable and filterable production records."""

import streamlit as st

from app.auth import require_page_permission
from app.security import Permission
from app.services.export import spreadsheet_safe
from app.ui import apply_theme, page_header, section_intro
from data.repositories import get_repository


require_page_permission(Permission.VIEW_DATA)
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo

page_header(
    "Production Data",
    "Review production records using a consistent row-level reporting period.",
    "PRODUCTION",
)

all_records = repo.get_production_records()

filter_keys = (
    "production_year_filter",
    "production_week_filter",
    "production_grader_filter",
    "production_barn_filter",
    "production_colour_filter",
)


def reset_filters() -> None:
    for key in filter_keys:
        st.session_state.pop(key, None)


with st.container(border=True):
    section_intro("Filters", "Narrow the table by reporting period and operational attributes.")
    reset_col, _ = st.columns([1, 5])
    reset_col.button("Reset filters", on_click=reset_filters, width="stretch")
    filter_columns = st.columns(5)
    years = (
        sorted(all_records["REPORTING_YEAR"].dropna().astype(int).unique().tolist())
        if "REPORTING_YEAR" in all_records
        else []
    )
    year_value = filter_columns[0].selectbox(
        "Reporting Year", ["All", *years], key="production_year_filter"
    )
    reporting_year = None if year_value == "All" else int(year_value)

    period_records = repo.get_production_records(reporting_year=reporting_year)
    weeks = (
        sorted(period_records["REPORTING_WEEK"].dropna().astype(int).unique().tolist())
        if "REPORTING_WEEK" in period_records
        else []
    )
    week_value = filter_columns[1].selectbox(
        "Reporting Week", ["All", *weeks], key="production_week_filter"
    )
    reporting_week = None if week_value == "All" else int(week_value)

    graders = (
        sorted(period_records["GRADER_NUMBER"].dropna().astype(str).unique().tolist())
        if "GRADER_NUMBER" in period_records
        else []
    )
    grader_value = filter_columns[2].selectbox(
        "Grader Number", ["All", *graders], key="production_grader_filter"
    )
    grader = None if grader_value == "All" else grader_value

    barns = (
        sorted(period_records["BARN_IDENTITY"].dropna().astype(str).unique().tolist())
        if "BARN_IDENTITY" in period_records
        else []
    )
    barn_value = filter_columns[3].selectbox(
        "Barn Identity", ["All", *barns], key="production_barn_filter"
    )
    barn = None if barn_value == "All" else barn_value

    colours = (
        sorted(period_records["EGG_COLOUR"].dropna().astype(str).unique().tolist())
        if "EGG_COLOUR" in period_records
        else []
    )
    colour_value = filter_columns[4].selectbox(
        "Egg Colour", ["All", *colours], key="production_colour_filter"
    )
    colour = None if colour_value == "All" else colour_value

records = repo.get_production_records(
    reporting_year=reporting_year,
    reporting_week=reporting_week,
    grader_number=grader,
    barn_identity=barn,
    egg_colour=colour,
)

metrics = st.columns(4)
for column, label, field in zip(
    metrics,
    ("Total Received", "Total Accepted", "Total Rejected", "Total Loss"),
    ("TOTAL_RECEIVED", "TOTAL_ACCEPTED", "REJECTED", "LOSS"),
):
    value = records[field].sum() if field in records else None
    column.metric(label, "N/A" if value is None else f"{value:,.1f}")

with st.container(border=True):
    section_intro(
        f"Production records · {len(records):,} rows",
        "Filtered operational and source-traceability fields.",
    )
    display_columns = [
        column
        for column in (
            "PRODUCTION_ID",
            "REPORTING_YEAR",
            "REPORTING_WEEK",
            "PRODUCER_NUMBER",
            "GRADER_NUMBER",
            "BARN_IDENTITY",
            "EGG_COLOUR",
            "TOTAL_RECEIVED",
            "REJECTED",
            "LOSS",
            "TOTAL_ACCEPTED",
            "TOTAL",
            "SOURCE_TYPE",
            "MATCH_STATUS",
            "SOURCE_ROW_NUMBER",
            "IMPORT_ID",
        )
        if column in records.columns
    ]
    st.caption(f"Showing {len(records):,} of {len(all_records):,} production records.")
    st.dataframe(
        records[display_columns],
        width="stretch",
        height=470,
        hide_index=True,
        column_config={
            "PRODUCTION_ID": "Production ID",
            "REPORTING_YEAR": "Year",
            "REPORTING_WEEK": "Week",
            "PRODUCER_NUMBER": "Producer",
            "GRADER_NUMBER": "Grader",
            "BARN_IDENTITY": "Barn",
            "EGG_COLOUR": "Egg Colour",
            "TOTAL_RECEIVED": st.column_config.NumberColumn("Received", format="%.1f"),
            "REJECTED": st.column_config.NumberColumn("Rejected", format="%.1f"),
            "LOSS": st.column_config.NumberColumn("Loss", format="%.1f"),
            "TOTAL_ACCEPTED": st.column_config.NumberColumn("Accepted", format="%.1f"),
            "SOURCE_TYPE": "Source",
            "MATCH_STATUS": "Match Status",
        },
    )
    if not records.empty:
        st.download_button(
            "Export filtered CSV",
            spreadsheet_safe(records[display_columns]).to_csv(index=False),
            "production_export.csv",
            "text/csv",
        )
