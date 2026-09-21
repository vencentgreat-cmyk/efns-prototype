"""EFNS application entry point and grouped navigation."""

from __future__ import annotations

import streamlit as st
import os

from app.auth import ensure_authorized_repository, render_user_sidebar, require_authenticated
from app.security import Permission, has_permission
from app.ui import apply_theme, page_header, section_intro, show_data_error
from data.connection import LazySqlExecutor


st.set_page_config(
    page_title="EFNS Internal Data System",
    page_icon="🥚",
    layout="wide",
    initial_sidebar_state="expanded",
)


def page_file(filename: str) -> str:
    prefix = os.getenv("EFNS_PAGE_PREFIX", "pages").strip("/")
    return f"{prefix}/{filename}"


apply_theme()
user = require_authenticated()
repo = ensure_authorized_repository(user)


def dashboard() -> None:
    apply_theme()
    repo = st.session_state.repo
    page_header(
        "Operations Dashboard",
        "A structured view of accounts, flocks, production activity, and recent imports.",
        "OVERVIEW",
    )

    repository_name = getattr(repo, "repository_name", type(repo).__name__.replace("Repository", ""))
    st.markdown(
        f'<div class="efns-repository">Active repository: <strong>{repository_name}</strong></div>',
        unsafe_allow_html=True,
    )

    executor = getattr(repo, "executor", None)
    snowflake_not_connected = (
        repository_name == "Snowflake"
        and isinstance(executor, LazySqlExecutor)
        and not executor.is_resolved
    )
    if snowflake_not_connected and not st.button(
        "Load Snowflake dashboard",
        icon=":material/cloud_sync:",
        type="primary",
    ):
        st.info("Snowflake has not been contacted. Open System Status to check the connection, or load dashboard data explicitly.")
        return
    try:
        operations = repo.get_dashboard_metrics()
    except Exception as exc:
        show_data_error(exc)
        return

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
    next_actions = []
    if has_permission(user, Permission.IMPORT_DATA):
        next_actions.append((
            "Validate a workbook",
            "Review the source, validation results, and normalized records before import.",
            "1_Production_Import.py",
            "Open Production Import",
        ))
    elif has_permission(user, Permission.USE_PROFILER):
        next_actions.append((
            "Profile source data",
            "Inspect CSV and Excel structure without saving or connecting to Snowflake.",
            "14_Source_Data_Profiler.py",
            "Open Source Data Profiler",
        ))
    next_actions.extend((
        (
            "Review production data",
            "Filter the current production records and export the visible result.",
            "2_Production_Data.py",
            "Open Production Data",
        ),
        (
            "Build a report",
            "Choose fields from the provisional account, flock, facility, and production model.",
            "4_Reports.py",
            "Open Custom Reports",
        ),
    ))
    next_columns = st.columns(len(next_actions))
    for column, (title, copy, page, label) in zip(next_columns, next_actions):
        with column:
            st.markdown(
                f'<div class="efns-next-step"><strong>{title}</strong><span>{copy}</span></div>',
                unsafe_allow_html=True,
            )
            st.page_link(page_file(page), label=label)

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

pages = {
        "Overview": [
            st.Page(dashboard, title="Dashboard", icon=":material/dashboard:"),
        ],
        "Production": [
            st.Page(
                page_file("17_Flock_Quota_Import.py"),
                title="Flock & Quota Import",
                icon=":material/upload_file:",
            ),
            st.Page(
                page_file("2_Production_Data.py"),
                title="Production Data",
                icon=":material/table_view:",
            ),
        ],
        "Account & Facility": [
            st.Page(
                page_file("3_Accounts_Facilities_Flocks.py"),
                title="Accounts & Facilities",
                icon=":material/account_tree:",
            ),
            st.Page(
                page_file("11_Facilities.py"),
                title="Facilities",
                icon=":material/domain:",
            ),
            st.Page(
                page_file("13_Facility_Details.py"),
                title="Facility Details",
                icon=":material/home_work:",
            ),
        ],
        "Flock Management": [
            st.Page(page_file("5_Flocks.py"), title="Flocks", icon=":material/egg:"),
            st.Page(page_file("6_Flock_Transactions.py"), title="Flock Transactions", icon=":material/swap_horiz:"),
            st.Page(page_file("9_Salmonella_Tests.py"), title="Salmonella Tests", icon=":material/science:"),
        ],
        "Quota Management": [
            st.Page(page_file("7_Quota_Registrations.py"), title="Quota Registrations", icon=":material/assignment:"),
            st.Page(page_file("8_Quota_Transactions.py"), title="Quota Transactions", icon=":material/compare_arrows:"),
        ],
        "Reporting": [
            st.Page(
                page_file("4_Reports.py"),
                title="Custom Reports",
                icon=":material/analytics:",
            ),
            st.Page(page_file("10_Salmonella_Report.py"), title="Salmonella Test Report", icon=":material/lab_profile:"),
        ],
    }

if has_permission(user, Permission.IMPORT_DATA):
    pages["Production"].insert(0, st.Page(page_file("1_Production_Import.py"), title="Production Import", icon=":material/upload_file:"))

administration = []
if has_permission(user, Permission.VIEW_DIAGNOSTICS):
    administration.append(st.Page(page_file("12_System_Status.py"), title="System Status", icon=":material/settings:"))
if has_permission(user, Permission.USE_PROFILER):
    administration.append(st.Page(page_file("14_Source_Data_Profiler.py"), title="Source Data Profiler", icon=":material/find_in_page:"))
if has_permission(user, Permission.VIEW_AUDIT):
    administration.append(st.Page(page_file("16_Audit_Log.py"), title="Audit Log", icon=":material/history:"))
if has_permission(user, Permission.MANAGE_USERS):
    administration.append(st.Page(page_file("15_User_Management.py"), title="User Management", icon=":material/manage_accounts:"))
if administration:
    pages["Administration"] = administration

navigation = st.navigation(pages)

with st.sidebar:
    render_user_sidebar(user)
    st.divider()
    repository_name = getattr(st.session_state.repo, "repository_name", type(st.session_state.repo).__name__.replace("Repository", ""))
    st.markdown(
        f'<div class="efns-repository">Repository: <strong>{repository_name}</strong></div>',
        unsafe_allow_html=True,
    )

    if repository_name == "Mock":
        st.caption("Runtime: Local Streamlit")
        st.warning("Mock data is stored only in this browser session.")
    else:
        runtime_name = getattr(st.session_state.repo, "runtime_name", "Auto-detect")
        st.caption(f"Runtime: {runtime_name}")
    st.markdown('<span class="efns-status">PROVISIONAL MODEL</span>', unsafe_allow_html=True)

navigation.run()
