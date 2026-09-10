# ============================================================
# EFNS Prototype v0.1 — Production Data Page
# ============================================================
"""Searchable, filterable production records table."""

import pandas as pd
import streamlit as st

from data.repositories import get_repository


st.set_page_config(page_title="Production Data", page_icon="🥚")

if "repo" not in st.session_state:
    st.session_state.repo = get_repository()

repo = st.session_state.repo

st.title("Production Data")
st.caption("Filterable production records — PROVISIONAL schema")

# --- Filters ---
st.markdown("### Filters")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    all_years = [None] + sorted(
        repo.get_production_records()["REPORTING_YEAR"].dropna().unique().tolist()
    ) if "REPORTING_YEAR" in repo.get_production_records().columns else [None]
    reporting_year = st.selectbox(
        "Reporting Year",
        ["All"] + [str(int(y)) for y in all_years[1:]],
    )
    reporting_year = int(reporting_year) if reporting_year != "All" else None

with col2:
    all_weeks = [None]
    df_temp = repo.get_production_records(reporting_year=reporting_year)
    if "REPORTING_WEEK" in df_temp.columns:
        all_weeks += sorted(df_temp["REPORTING_WEEK"].dropna().unique().tolist())
    reporting_week = st.selectbox(
        "Reporting Week",
        ["All"] + [str(int(w)) for w in all_weeks[1:]],
    )
    reporting_week = int(reporting_week) if reporting_week != "All" else None

with col3:
    all_graders = sorted(df_temp["GRADER_NUMBER"].dropna().unique().tolist()) if "GRADER_NUMBER" in df_temp.columns else []
    grader = st.selectbox("Grader Number", ["All"] + all_graders)
    grader = grader if grader != "All" else None

with col4:
    all_barns = sorted(df_temp["BARN_IDENTITY"].dropna().unique().tolist()) if "BARN_IDENTITY" in df_temp.columns else []
    barn = st.selectbox("Barn Identity", ["All"] + all_barns)
    barn = barn if barn != "All" else None

with col5:
    all_colours = sorted(df_temp["EGG_COLOUR"].dropna().unique().tolist()) if "EGG_COLOUR" in df_temp.columns else []
    colour = st.selectbox("Egg Colour", ["All"] + all_colours)
    colour = colour if colour != "All" else None

# --- Query ---
df = repo.get_production_records(
    reporting_year=reporting_year,
    reporting_week=reporting_week,
    grader_number=grader,
    barn_identity=barn,
    egg_colour=colour,
)

# --- Summary ---
st.divider()
col_a, col_b, col_c, col_d, col_e = st.columns(5)
with col_a:
    st.metric("Rows", len(df))
with col_b:
    st.metric("Total Received", f"{df['TOTAL_RECEIVED'].sum():,.1f}" if "TOTAL_RECEIVED" in df.columns else "N/A")
with col_c:
    st.metric("Total Accepted", f"{df['TOTAL_ACCEPTED'].sum():,.1f}" if "TOTAL_ACCEPTED" in df.columns else "N/A")
with col_d:
    st.metric("Total Rejected", f"{df['REJECTED'].sum():,.1f}" if "REJECTED" in df.columns and df["REJECTED"].notna().any() else "N/A")
with col_e:
    st.metric("Total Loss", f"{df['LOSS'].sum():,.1f}" if "LOSS" in df.columns and df["LOSS"].notna().any() else "N/A")

# --- Data table ---
st.divider()
st.subheader("Production Records")

display_cols = [
    c for c in [
        "PRODUCTION_ID", "REPORTING_YEAR", "REPORTING_WEEK", "GRADER_NUMBER",
        "BARN_IDENTITY", "FLOCK_AGE", "EGG_COLOUR", "NET_WEIGHT", "NET_BOXES",
        "NET_PER_BOX", "TOTAL_RECEIVED", "REJECTED", "LOSS",
        "LEGACY_REJECT_LOSS_TOTAL", "TOTAL_ACCEPTED", "IMPORT_ID", "CREATED_AT",
    ] if c in df.columns
]
st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

# --- CSV Export ---
if not df.empty:
    csv_data = df[display_cols].to_csv(index=False)
    st.download_button(
        "Export Filtered Results to CSV",
        csv_data,
        "production_export.csv",
        "text/csv",
    )