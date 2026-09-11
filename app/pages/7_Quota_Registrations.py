"""Quota registration and account allocation workspace."""

from __future__ import annotations

import datetime as dt
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import pandas as pd
import streamlit as st

from app.ui import apply_theme, clear_widget_prefix, page_header
from data.constants import QUOTA_STATUSES, QUOTA_TYPES
from data.repositories import get_repository
from data.validation import validate_quota_registration


apply_theme()

if "repo" not in st.session_state:
    st.session_state.repo = get_repository()

repo = st.session_state.repo


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def as_date(value, default=None):
    """Convert pandas/datetime values into a date accepted by Streamlit."""
    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    converted = pd.to_datetime(value, errors="coerce")
    if pd.isna(converted):
        return default

    return converted.date()


def format_datetime(value) -> str:
    """Format a datetime value for read-only display."""
    if value is None:
        return "Not available"

    try:
        if pd.isna(value):
            return "Not available"
    except (TypeError, ValueError):
        pass

    converted = pd.to_datetime(value, errors="coerce")
    if pd.isna(converted):
        return "Not available"

    return converted.strftime("%Y-%m-%d %H:%M")


def option_index(options: list[str], value, default: int = 0) -> int:
    """Return a safe Streamlit selectbox index."""
    try:
        return options.index(value)
    except (ValueError, TypeError):
        return default


def current_page_link(
    parameter: str,
    record_id: str,
    label: str,
) -> str:
    """Create a safe absolute record link for browser and AppTest."""

    raw_url = getattr(st.context, "url", "")
    current_url = str(raw_url or "")

    base_url = current_url.split("?", 1)[0].split("#", 1)[0]

    # AppTest may not provide a normal browser URL.
    if not base_url or base_url.lower() == "none":
        base_url = "http://localhost:8501"

    query = urlencode(
        {
            str(parameter): str(record_id),
        }
    )

    fragment = quote(
        str(label or record_id),
        safe="",
    )

    return f"{base_url}?{query}#{fragment}"


def reset_filters() -> None:
    """Clear quota filters and URL selection."""
    for key in (
        "quota_reg_filter_account",
        "quota_reg_filter_status",
        "quota_reg_filter_type",
    ):
        st.session_state.pop(key, None)

    st.query_params.clear()


# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------

page_header(
    "Quota Registrations",
    (
        "Maintain provisional account quota allocations using stable "
        "account relationships."
    ),
    "QUOTA MANAGEMENT",
)

st.info(
    "Quota types and allocation rules remain provisional. "
    "This module does not calculate available quota balance."
)

flash_message = st.session_state.pop("quota_registration_flash", None)
if flash_message:
    st.success(flash_message)


# ---------------------------------------------------------------------
# Source data
# ---------------------------------------------------------------------

accounts = repo.get_accounts()
all_quotas = repo.get_quota_registrations()

if accounts.empty:
    st.warning(
        "No accounts are available. Create an account before creating "
        "a quota registration."
    )
    st.stop()


def account_display_name(row) -> str:
    registration = row.REGISTRATION_NUMBER or row.ACCOUNT_ID[:8]
    return f"{row.ORGANIZATION_NAME} · {registration}"


account_labels = {
    account_display_name(row): row.ACCOUNT_ID
    for row in accounts.itertuples()
}

account_names = {
    row.ACCOUNT_ID: row.ORGANIZATION_NAME
    for row in accounts.itertuples()
}

account_label_by_id = {
    account_id: label
    for label, account_id in account_labels.items()
}


# ---------------------------------------------------------------------
# Record detail from URL
# ---------------------------------------------------------------------

selected_quota_id = st.query_params.get("quota_id")

if selected_quota_id:
    selected_quota = repo.get_quota_registration(str(selected_quota_id))

    if selected_quota is None:
        st.warning("The selected quota registration could not be found.")
    else:
        st.markdown("### Quota Registration Details")

        title = (
            selected_quota.get("QUOTA_NAME")
            or selected_quota.get("REGISTRATION_NUMBER")
            or "Quota Registration"
        )

        st.markdown(f"#### {title}")

        detail_left, detail_middle, detail_right = st.columns(3)

        with detail_left:
            st.caption("Account")
            st.write(
                account_names.get(
                    selected_quota.get("ACCOUNT_ID"),
                    "Unassigned",
                )
            )

            st.caption("Registration Number")
            st.write(selected_quota.get("REGISTRATION_NUMBER") or "—")

            st.caption("Quota Name")
            st.write(selected_quota.get("QUOTA_NAME") or "—")

        with detail_middle:
            st.caption("Quota Type")
            st.write(selected_quota.get("QUOTA_TYPE") or "—")

            st.caption("Status")
            st.write(selected_quota.get("STATUS") or "—")

            st.caption("Effective Date")
            st.write(
                as_date(selected_quota.get("EFFECTIVE_DATE"), "—")
            )

        with detail_right:
            st.caption("End Date")
            st.write(as_date(selected_quota.get("END_DATE"), "—"))

            st.caption("Created On")
            st.write(format_datetime(selected_quota.get("CREATED_AT")))

            st.caption("Last Updated")
            st.write(format_datetime(selected_quota.get("UPDATED_AT")))

        st.caption("Comments")
        st.write(selected_quota.get("COMMENTS") or "No comments.")

        related_transactions = repo.get_quota_transactions(
            quota_id=str(selected_quota_id)
        )

        st.markdown("#### Related Quota Transactions")

        if related_transactions.empty:
            st.info("No quota transactions are connected to this registration.")
        else:
            related_display = related_transactions.copy()

            for column in (
                "QUOTA_TRANSACTION_ID",
                "TRANSACTION_TYPE",
                "EFFECTIVE_DATE",
                "END_DATE",
                "QUOTA_COUNT",
                "PRICE",
                "QUOTA_LEASE_TYPE",
                "COMMENTS",
                "CREATED_AT",
            ):
                if column not in related_display.columns:
                    related_display[column] = None

            st.dataframe(
                related_display[
                    [
                        "QUOTA_TRANSACTION_ID",
                        "TRANSACTION_TYPE",
                        "EFFECTIVE_DATE",
                        "END_DATE",
                        "QUOTA_COUNT",
                        "PRICE",
                        "QUOTA_LEASE_TYPE",
                        "COMMENTS",
                        "CREATED_AT",
                    ]
                ],
                width="stretch",
                height=300,
                hide_index=True,
                column_config={
                    "QUOTA_TRANSACTION_ID": "Transaction ID",
                    "TRANSACTION_TYPE": "Transaction Type",
                    "EFFECTIVE_DATE": st.column_config.DateColumn(
                        "Effective Date",
                        format="YYYY-MM-DD",
                    ),
                    "END_DATE": st.column_config.DateColumn(
                        "End Date",
                        format="YYYY-MM-DD",
                    ),
                    "QUOTA_COUNT": st.column_config.NumberColumn(
                        "Quota Count",
                        format="%.0f",
                    ),
                    "PRICE": st.column_config.NumberColumn(
                        "Price",
                        format="$%.2f",
                    ),
                    "QUOTA_LEASE_TYPE": "Lease Type",
                    "COMMENTS": "Comments",
                    "CREATED_AT": st.column_config.DatetimeColumn(
                        "Created On",
                        format="YYYY-MM-DD HH:mm",
                    ),
                },
            )

        if st.button(
            "Back to all quota registrations",
            key="quota_reg_back",
        ):
            st.query_params.clear()
            st.rerun()

        st.divider()


# ---------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------

requested_account_id = st.query_params.get("account_id")

account_filter_options = ["All", *account_labels.keys()]

if requested_account_id in account_label_by_id:
    requested_label = account_label_by_id[requested_account_id]
    st.session_state["quota_reg_filter_account"] = requested_label

filter_header, reset_column = st.columns([5, 1])

with filter_header:
    st.markdown("### Active Quotas")

with reset_column:
    st.button(
        "Reset Filters",
        key="quota_reg_reset",
        on_click=reset_filters,
        width="stretch",
    )

filter_cols = st.columns(3)

account_label = filter_cols[0].selectbox(
    "Account",
    account_filter_options,
    key="quota_reg_filter_account",
)

status = filter_cols[1].selectbox(
    "Status",
    ["All", *QUOTA_STATUSES],
    key="quota_reg_filter_status",
)

quota_type = filter_cols[2].selectbox(
    "Quota Type",
    ["All", *QUOTA_TYPES],
    key="quota_reg_filter_type",
)

quotas = repo.get_quota_registrations(
    account_id=account_labels.get(account_label),
    status=None if status == "All" else status,
    quota_type=None if quota_type == "All" else quota_type,
)


# ---------------------------------------------------------------------
# Quota list
# ---------------------------------------------------------------------

if quotas.empty:
    st.info("No quota registrations match the current filters.")
else:
    display = quotas.copy()

    for column in (
        "QUOTA_ID",
        "REGISTRATION_NUMBER",
        "ACCOUNT_ID",
        "QUOTA_NAME",
        "QUOTA_TYPE",
        "STATUS",
        "EFFECTIVE_DATE",
        "END_DATE",
        "COMMENTS",
        "CREATED_AT",
        "UPDATED_AT",
    ):
        if column not in display.columns:
            display[column] = None

    display["ACCOUNT_NAME"] = display["ACCOUNT_ID"].map(account_names)

    display["ACCOUNT_LINK"] = display.apply(
        lambda row: current_page_link(
            "account_id",
            row["ACCOUNT_ID"],
            row["ACCOUNT_NAME"] or "Unassigned",
        ),
        axis=1,
    )

    display["QUOTA_LINK"] = display.apply(
        lambda row: current_page_link(
            "quota_id",
            row["QUOTA_ID"],
            row["QUOTA_NAME"]
            or row["REGISTRATION_NUMBER"]
            or row["QUOTA_ID"],
        ),
        axis=1,
    )

    st.caption(f"{len(display):,} quota registration(s)")

    st.dataframe(
        display[
            [
                "REGISTRATION_NUMBER",
                "ACCOUNT_LINK",
                "STATUS",
                "QUOTA_LINK",
                "QUOTA_TYPE",
                "EFFECTIVE_DATE",
                "END_DATE",
                "COMMENTS",
                "CREATED_AT",
            ]
        ],
        width="stretch",
        height=430,
        hide_index=True,
        column_config={
            "REGISTRATION_NUMBER": "Registration",
            "ACCOUNT_LINK": st.column_config.LinkColumn(
                "Account",
                display_text=r".*#(.*)$",
                width="medium",
            ),
            "STATUS": "Status",
            "QUOTA_LINK": st.column_config.LinkColumn(
                "Name",
                display_text=r".*#(.*)$",
                width="large",
            ),
            "QUOTA_TYPE": "Quota Type",
            "EFFECTIVE_DATE": st.column_config.DateColumn(
                "Effective Date",
                format="YYYY-MM-DD",
            ),
            "END_DATE": st.column_config.DateColumn(
                "End Date",
                format="YYYY-MM-DD",
            ),
            "COMMENTS": st.column_config.TextColumn(
                "Comments",
                width="large",
            ),
            "CREATED_AT": st.column_config.DatetimeColumn(
                "Created On",
                format="YYYY-MM-DD HH:mm",
            ),
        },
    )


# ---------------------------------------------------------------------
# Create / edit
# ---------------------------------------------------------------------

with st.expander(
    "Create or edit a quota registration",
    expanded=bool(selected_quota_id),
):
    quota_options = {
        (
            f"{row.REGISTRATION_NUMBER} · "
            f"{row.QUOTA_NAME or row.QUOTA_TYPE}"
        ): row.QUOTA_ID
        for row in all_quotas.itertuples()
    }

    record_options = ["Create new", *quota_options.keys()]

    default_record_label = "Create new"

    if selected_quota_id:
        for label, quota_id in quota_options.items():
            if quota_id == selected_quota_id:
                default_record_label = label
                break

    edit_label = st.selectbox(
        "Record",
        record_options,
        index=option_index(record_options, default_record_label),
        key="quota_reg_record",
        on_change=clear_widget_prefix,
        args=("quota_reg_", ("quota_reg_record",)),
    )

    current = (
        repo.get_quota_registration(quota_options[edit_label])
        if edit_label != "Create new"
        else {}
    ) or {}

    current_account_label = account_label_by_id.get(
        current.get("ACCOUNT_ID"),
        list(account_labels.keys())[0],
    )

    left, right = st.columns(2)

    selected_account = left.selectbox(
        "Account *",
        list(account_labels.keys()),
        index=option_index(
            list(account_labels.keys()),
            current_account_label,
        ),
        key="quota_reg_account",
    )

    registration = left.text_input(
        "Registration Number *",
        value=str(current.get("REGISTRATION_NUMBER") or ""),
        key="quota_reg_number",
    )

    name = left.text_input(
        "Quota Name",
        value=str(current.get("QUOTA_NAME") or ""),
        key="quota_reg_name",
    )

    selected_type = right.selectbox(
        "Quota Type *",
        QUOTA_TYPES,
        index=option_index(
            list(QUOTA_TYPES),
            current.get("QUOTA_TYPE"),
        ),
        key="quota_reg_type",
    )

    selected_status = right.selectbox(
        "Status",
        QUOTA_STATUSES,
        index=option_index(
            list(QUOTA_STATUSES),
            current.get("STATUS"),
        ),
        key="quota_reg_status",
    )

    effective = right.date_input(
        "Effective Date",
        value=as_date(
            current.get("EFFECTIVE_DATE"),
            dt.date.today(),
        ),
        key="quota_reg_effective",
    )

    end_date = right.date_input(
        "End Date",
        value=as_date(current.get("END_DATE")),
        key="quota_reg_end",
    )

    comments = st.text_area(
        "Comments",
        value=str(current.get("COMMENTS") or ""),
        key="quota_reg_comments",
    )

    if current:
        audit_left, audit_right = st.columns(2)

        audit_left.text_input(
            "Created On",
            value=format_datetime(current.get("CREATED_AT")),
            disabled=True,
            key="quota_reg_created_on",
        )

        audit_right.text_input(
            "Last Updated",
            value=format_datetime(current.get("UPDATED_AT")),
            disabled=True,
            key="quota_reg_updated_on",
        )

    if st.button(
        "Save Quota Registration",
        type="primary",
        key="quota_reg_save",
    ):
        record = {
            "QUOTA_ID": current.get("QUOTA_ID"),
            "REGISTRATION_NUMBER": registration.strip(),
            "ACCOUNT_ID": account_labels[selected_account],
            "QUOTA_NAME": name.strip() or registration.strip(),
            "QUOTA_TYPE": selected_type,
            "STATUS": selected_status,
            "EFFECTIVE_DATE": effective,
            "END_DATE": end_date,
            "COMMENTS": comments.strip() or None,
        }

        errors = validate_quota_registration(repo, record)

        if errors:
            for error in errors:
                st.error(error)
        else:
            try:
                quota_id = repo.upsert_quota_registration(record)

                st.session_state["quota_registration_flash"] = (
                    f"Quota registration saved: {quota_id}"
                )

                st.query_params.clear()
                st.query_params["quota_id"] = quota_id
                st.rerun()

            except ValueError as exc:
                st.error(str(exc))
