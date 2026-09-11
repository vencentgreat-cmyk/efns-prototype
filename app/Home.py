"""EFNS application entry point and grouped navigation."""

from __future__ import annotations

import streamlit as st

from app.ui import apply_theme, page_header, section_intro
from data.repositories import get_repository


st.set_page_config(
    page_title="EFNS Internal Data System",
    page_icon="🥚",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

if "repo" not in st.session_state:
    st.session_state.repo = get_repository()


def dashboard() -> None:
    apply_theme()
    repo = st.session_state.repo
    operations = repo.get_dashboard_metrics()
    page_header(
        "Operations Dashboard",
        "A structured view of accounts, flocks, production activity, and recent imports.",
        "OVERVIEW",
    )

    repository_name = type(repo).__name__.replace("Repository", "")
    st.markdown(
        f'<div class="efns-repository">Active repository: <strong>{repository_name}</strong></div>',
        unsafe_allow_html=True,
    )

    section_intro("Operational overview", "Current session counts from public repository queries.")
    cols = st.columns(4)
    for column, label, value in zip(
        cols,
        ("Active Accounts", "Active Facilities", "Active Flocks", "Active Quotas"),
        (
            operations.get("active_account_count", 0),
            operations.get("active_facility_count", 0),
            operations.get("active_flock_count", 0),
            operations.get("active_quota_count", 0),
        ),
    ):
        column.metric(label, value)

    section_intro("Recent activity", "Quota, testing, and production workload indicators.")
    totals = st.columns(4)
    for column, label, key in zip(
        totals,
        ("Recent Quota Transactions", "Pending Tests", "Tests Needing Attention", "Production Records"),
        ("recent_quota_transaction_count", "pending_salmonella_count", "attention_salmonella_count", "production_record_count"),
    ):
        column.metric(label, f"{operations.get(key, 0):,}")

    st.info(
        "Prototype status: entity names and relationships remain provisional until "
        "authoritative Dataverse metadata is available."
    )

    section_intro("Next actions", "Continue with the most common operational tasks.")
    next_columns = st.columns(3)
    next_actions = (
        (
            "Validate a workbook",
            "Review the source, validation results, and normalized records before import.",
            "pages/1_Production_Import.py",
            "Open Production Import",
        ),
        (
            "Review production data",
            "Filter the current production records and export the visible result.",
            "pages/2_Production_Data.py",
            "Open Production Data",
        ),
        (
            "Build a report",
            "Choose fields from the provisional account, flock, facility, and production model.",
            "pages/4_Reports.py",
            "Open Custom Reports",
        ),
    )
    for column, (title, copy, page, label) in zip(next_columns, next_actions):
        with column:
            st.markdown(
                f'<div class="efns-next-step"><strong>{title}</strong><span>{copy}</span></div>',
                unsafe_allow_html=True,
            )
            st.page_link(page, label=label)

    with st.container(border=True):
        section_intro("Recent imports", "The ten most recent workbook or synthetic import batches.")
        imports = repo.get_import_batches()
        if imports.empty:
            st.info("No import batches are available in this session.")
        else:
            columns = [
                column
                for column in (
                    "FILENAME",
                    "SOURCE",
                    "REPORTING_YEAR",
                    "REPORTING_WEEK",
                    "ROW_COUNT",
                    "STATUS",
                    "UPLOAD_TIMESTAMP",
                )
                if column in imports.columns
            ]
            st.dataframe(
                imports.sort_values("UPLOAD_TIMESTAMP", ascending=False)[columns].head(10),
                width="stretch",
                hide_index=True,
            )


with st.sidebar:
    st.markdown(
        '<div class="efns-brand">EFNS Data System<small>Internal operations prototype</small></div>',
        unsafe_allow_html=True,
    )

navigation = st.navigation(
    {
        "Overview": [
            st.Page(dashboard, title="Dashboard", icon=":material/dashboard:"),
        ],
        "Production": [
            st.Page(
                "pages/1_Production_Import.py",
                title="Production Import",
                icon=":material/upload_file:",
            ),
            st.Page(
                "pages/2_Production_Data.py",
                title="Production Data",
                icon=":material/table_view:",
            ),
        ],
        "Account & Facility": [
            st.Page(
                "pages/3_Accounts_Facilities_Flocks.py",
                title="Accounts, Facilities & Flocks",
                icon=":material/account_tree:",
            ),
        ],
        "Flock Management": [
            st.Page("pages/5_Flocks.py", title="Flocks", icon=":material/egg:"),
            st.Page("pages/6_Flock_Transactions.py", title="Flock Transactions", icon=":material/swap_horiz:"),
            st.Page("pages/9_Salmonella_Tests.py", title="Salmonella Tests", icon=":material/science:"),
        ],
        "Quota Management": [
            st.Page("pages/7_Quota_Registrations.py", title="Quota Registrations", icon=":material/assignment:"),
            st.Page("pages/8_Quota_Transactions.py", title="Quota Transactions", icon=":material/compare_arrows:"),
        ],
        "Reporting": [
            st.Page(
                "pages/4_Reports.py",
                title="Custom Reports",
                icon=":material/analytics:",
            ),
            st.Page("pages/10_Salmonella_Report.py", title="Salmonella Test Report", icon=":material/lab_profile:"),
        ],
    }
)

with st.sidebar:
    repository_name = type(st.session_state.repo).__name__.replace("Repository", "")
    st.markdown(
        f'<div class="efns-repository">Repository: <strong>{repository_name}</strong></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<span class="efns-status">PROVISIONAL MODEL</span>', unsafe_allow_html=True)

navigation.run()
