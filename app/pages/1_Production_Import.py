# ============================================================
# EFNS Prototype v0.1 — Production Import Page
# ============================================================
"""CSV upload, preview, validation, and normalization."""

from __future__ import annotations

import datetime as dt
import io
import uuid

import pandas as pd
import streamlit as st

from data.repositories import get_repository


st.set_page_config(page_title="Production Import", page_icon="🥚")

if "repo" not in st.session_state:
    st.session_state.repo = get_repository()

repo = st.session_state.repo

st.title("Production Import")
st.caption("Upload external grader/production CSV for ingestion into RAW → CORE")

# --- Download sample template ---
st.markdown("### Sample Template")
st.caption("Download a template CSV to see the expected format.")

# Build a sample template
template = pd.DataFrame(
    {
        "REPORTING_YEAR": [dt.date.today().year],
        "REPORTING_WEEK": [1],
        "GRADER_NUMBER": ["G-101"],
        "BARN_IDENTITY": ["Barn-A1"],
        "FLOCK_AGE": [45],
        "EGG_COLOUR": ["White"],
        "NET_WEIGHT": [1500.0],
        "NET_BOXES": [80.0],
        "NET_PER_BOX": [18.75],
        "TOTAL_RECEIVED": [80.0],
        "REJECTED": [1.5],
        "LOSS": [0.5],
        "LEGACY_REJECT_LOSS_TOTAL": [None],
        "TOTAL_ACCEPTED": [78.0],
    }
)
csv_buffer = io.StringIO()
template.to_csv(csv_buffer, index=False)
st.download_button(
    "Download Template CSV",
    csv_buffer.getvalue(),
    "production_template.csv",
    "text/csv",
)

st.divider()

# --- Upload ---
st.markdown("### Upload CSV")
uploaded = st.file_uploader("Choose a production CSV file", type=["csv"])

if uploaded is not None:
    # Read and preview
    raw_df = pd.read_csv(uploaded)
    st.write(f"**Rows:** {len(raw_df)}  |  **Columns:** {len(raw_df.columns)}")
    st.subheader("Raw Preview")
    st.dataframe(raw_df.head(20), use_container_width=True, hide_index=True)

    # --- Column detection ---
    st.subheader("Column Detection")
    expected = {
        "REPORTING_YEAR", "REPORTING_WEEK", "GRADER_NUMBER", "BARN_IDENTITY",
        "FLOCK_AGE", "EGG_COLOUR", "NET_WEIGHT", "NET_BOXES", "NET_PER_BOX",
        "TOTAL_RECEIVED", "REJECTED", "LOSS", "LEGACY_REJECT_LOSS_TOTAL",
        "TOTAL_ACCEPTED",
    }
    found = set(raw_df.columns)
    missing = expected - found
    extra = found - expected

    if not missing and not extra:
        st.success("All expected columns detected.")
    else:
        if missing:
            st.warning(f"Missing columns (will be NULL): {', '.join(sorted(missing))}")
        if extra:
            st.info(f"Extra/unrecognized columns: {', '.join(sorted(extra))}")

    # --- Validation ---
    st.subheader("Validation")
    errors = []

    for _, row in raw_df.iterrows():
        row_num = getattr(row, "name", "?") + 2  # +2 for 0-index + header
        if pd.notna(row.get("TOTAL_RECEIVED")) and pd.notna(row.get("TOTAL_ACCEPTED")):
            try:
                rcv = float(row["TOTAL_RECEIVED"])
                acc = float(row["TOTAL_ACCEPTED"])
                if acc > rcv:
                    errors.append(f"Row {row_num}: TOTAL_ACCEPTED ({acc}) > TOTAL_RECEIVED ({rcv})")
            except (ValueError, TypeError):
                pass

        rej = row.get("REJECTED")
        loss = row.get("LOSS")
        legacy = row.get("LEGACY_REJECT_LOSS_TOTAL")
        has_separate = pd.notna(rej) or pd.notna(loss)
        has_legacy = pd.notna(legacy)
        if has_separate and has_legacy:
            errors.append(
                f"Row {row_num}: Both separate REJECTED/LOSS and LEGACY_REJECT_LOSS_TOTAL provided."
            )

    if errors:
        st.error(f"{len(errors)} validation issue(s):")
        for e in errors[:20]:
            st.write(f"- {e}")
        if len(errors) > 20:
            st.write(f"... and {len(errors) - 20} more")
    else:
        st.success("No validation issues found.")

    # --- Normalized preview ---
    st.subheader("Normalized Preview (What Would Be Written to CORE)")
    norm_cols = [
        "GRADER_NUMBER", "BARN_IDENTITY", "FLOCK_AGE", "EGG_COLOUR",
        "NET_WEIGHT", "NET_BOXES", "NET_PER_BOX",
        "TOTAL_RECEIVED", "REJECTED", "LOSS", "LEGACY_REJECT_LOSS_TOTAL",
        "TOTAL_ACCEPTED", "REPORTING_YEAR", "REPORTING_WEEK",
    ]
    preview_cols = [c for c in norm_cols if c in raw_df.columns]
    st.dataframe(raw_df[preview_cols].head(20), use_container_width=True, hide_index=True)

    # --- Commit (mock) ---
    st.subheader("Commit to Database")
    st.caption("In v0.1, this writes to the in-memory MockRepository.")
    filename = st.text_input("Source filename for import record", value=getattr(uploaded, "name", "unknown.csv"))

    if st.button("Import Data", type="primary"):
        if errors:
            st.error("Cannot import with validation errors. Fix the issues first.")
        else:
            import_id = repo.create_import_batch({
                "IMPORT_ID": str(uuid.uuid4()),
                "FILENAME": filename,
                "SOURCE": "User Upload",
                "REPORTING_YEAR": int(raw_df["REPORTING_YEAR"].iloc[0]) if "REPORTING_YEAR" in raw_df.columns else None,
                "REPORTING_WEEK": int(raw_df["REPORTING_WEEK"].iloc[0]) if "REPORTING_WEEK" in raw_df.columns else None,
                "STATUS": "Committed",
            })
            # Prepare production records
            recs = raw_df.copy()
            if "PRODUCTION_ID" not in recs.columns:
                recs["PRODUCTION_ID"] = [str(uuid.uuid4()) for _ in range(len(recs))]
            count = repo.insert_production_records(recs, import_id)
            st.success(f"Imported {count} production records. Import ID: {import_id}")
            st.balloons()
else:
    st.info("Upload a CSV file to begin.")