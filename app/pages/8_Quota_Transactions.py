"""Quota transaction workspace without balance automation."""

from __future__ import annotations

import datetime as dt
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import pandas as pd
import streamlit as st

from app.ui import apply_theme, clear_widget_prefix, page_header
from data.constants import (
    QUOTA_LEASE_TYPES,
    QUOTA_TRANSACTION_TYPES,
    QUOTA_TYPES,
)
from data.repositories import get_repository
from data.validation import validate_quota_transaction


apply_theme()

if "repo" not in st.session_state:
    st.session_state.repo = get_repository()

repo = st.session_state.repo


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def as_date(value, default=None):
    """Convert pandas or datetime values into a date."""
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
    """Format an audit timestamp for display."""
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
    """Return a safe selectbox index."""
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
    """Clear transaction filters and URL parameters."""
    for key in (
        "quota_tx_filter_account",
        "quota_tx_filter_quota_type",
        "quota_tx_filter_type",
        "quota_tx_filter_date_from",
        "quota_tx_filter_date_to",
    ):
        st.session_state.pop(key, None)

    st.query_params.clear()


# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------

page_header(
    "Quota Transactions",
    (
        "Record quota activity while keeping counterpart and "
        "allocation relationships explicit."
    ),
    "QUOTA MANAGEMENT",
)

st.warning(
    "Transaction totals are provisional activity totals, "
    "not an available quota balance."
)

flash_message = st.session_state.pop(
    "quota_transaction_flash",
    None,
)

if flash_message:
    st.success(flash_message)


# ---------------------------------------------------------------------
# Source data
# ---------------------------------------------------------------------

accounts = repo.get_accounts()
quotas = repo.get_quota_registrations()

if accounts.empty:
    st.warning(
        "No accounts are available. Create an account before "
        "recording a quota transaction."
    )
    st.stop()

if quotas.empty:
    st.warning(
        "No quota registrations are available. Create a quota "
        "registration before recording a transaction."
    )
    st.stop()


def account_display_name(row) -> str:
    registration = row.REGISTRATION_NUMBER or row.ACCOUNT_ID[:8]
    return f"{row.ORGANIZATION_NAME} · {registration}"


def quota_display_name(row) -> str:
    name = row.QUOTA_NAME or row.REGISTRATION_NUMBER
    return f"{name} · {row.QUOTA_TYPE}"


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

quota_labels = {
    quota_display_name(row): row.QUOTA_ID
    for row in quotas.itertuples()
}

quota_names = {
    row.QUOTA_ID: (
        row.QUOTA_NAME
        or row.REGISTRATION_NUMBER
        or row.QUOTA_ID
    )
    for row in quotas.itertuples()
}

quota_label_by_id = {
    quota_id: label
    for label, quota_id in quota_labels.items()
}

quota_account_ids = {
    row.QUOTA_ID: row.ACCOUNT_ID
    for row in quotas.itertuples()
}


# ---------------------------------------------------------------------
# Record details from URL
# ---------------------------------------------------------------------

selected_transaction_id = st.query_params.get("id") or st.query_params.get("transaction_id")

if selected_transaction_id:
    transaction_matches = repo.get_quota_transactions()
    transaction_matches = transaction_matches[
        transaction_matches["QUOTA_TRANSACTION_ID"]
        == str(selected_transaction_id)
    ]

    if transaction_matches.empty:
        st.warning("The selected quota transaction could not be found.")
    else:
        selected_transaction = (
            transaction_matches.iloc[0].to_dict()
        )

        selected_quota = repo.get_quota_registration(
            selected_transaction.get("QUOTA_ID")
        )

        st.markdown("### Quota Transaction Details")

        transaction_type = (
            selected_transaction.get("TRANSACTION_TYPE")
            or "Quota Transaction"
        )

        st.markdown(f"#### {transaction_type}")

        detail_left, detail_middle, detail_right = st.columns(3)

        with detail_left:
            st.caption("Quota Registration")
            st.write(
                quota_names.get(
                    selected_transaction.get("QUOTA_ID"),
                    "Unassigned",
                )
            )

            st.caption("Owner Account")
            st.write(
                account_names.get(
                    selected_transaction.get("OWNER_ACCOUNT_ID"),
                    "Unassigned",
                )
            )

            st.caption("Related Account")
            st.write(
                account_names.get(
                    selected_transaction.get("RELATED_ACCOUNT_ID"),
                    "Unassigned",
                )
            )

        with detail_middle:
            st.caption("Transaction Type")
            st.write(transaction_type)

            st.caption("Effective Date")
            st.write(
                as_date(
                    selected_transaction.get("EFFECTIVE_DATE"),
                    "—",
                )
            )

            st.caption("End Date")
            st.write(
                as_date(
                    selected_transaction.get("END_DATE"),
                    "—",
                )
            )

        with detail_right:
            st.caption("Quota Count")
            quota_count = selected_transaction.get("QUOTA_COUNT")
            st.write(
                f"{float(quota_count):,.0f}"
                if quota_count is not None
                else "—"
            )

            st.caption("Price")
            price = selected_transaction.get("PRICE")
            st.write(
                f"${float(price):,.2f}"
                if price is not None
                else "—"
            )

            st.caption("Lease Type")
            st.write(
                selected_transaction.get("QUOTA_LEASE_TYPE")
                or "Not applicable"
            )

        audit_left, audit_right = st.columns(2)

        with audit_left:
            st.caption("Created On")
            st.write(
                format_datetime(
                    selected_transaction.get("CREATED_AT")
                )
            )

        with audit_right:
            st.caption("Last Updated")
            st.write(
                format_datetime(
                    selected_transaction.get("UPDATED_AT")
                )
            )

        st.caption("Related Quota")
        related_quota_id = selected_transaction.get(
            "RELATED_QUOTA_ID"
        )
        st.write(
            quota_names.get(
                related_quota_id,
                related_quota_id or "Unassigned",
            )
        )

        st.caption("Related Transaction")
        related_transaction_id = selected_transaction.get(
            "RELATED_TRANSACTION_ID"
        )

        if related_transaction_id:
            related_url = current_page_link(
                "transaction_id",
                related_transaction_id,
                related_transaction_id,
            )

            st.markdown(
                f"[{related_transaction_id}]({related_url})"
            )
        else:
            st.write("Unassigned")

        st.caption("Comments")
        st.write(
            selected_transaction.get("COMMENTS")
            or "No comments."
        )

        if selected_quota:
            st.caption("Quota Registration Number")
            st.write(
                selected_quota.get("REGISTRATION_NUMBER") or "—"
            )

        if st.button(
            "Back to all quota transactions",
            key="quota_tx_back",
        ):
            st.query_params.clear()
            st.rerun()

        st.divider()


# ---------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------

requested_account_id = st.query_params.get("account_id")
requested_quota_id = st.query_params.get("quota_id")

account_filter_options = ["All", *account_labels.keys()]

if requested_account_id in account_label_by_id:
    st.session_state["quota_tx_filter_account"] = (
        account_label_by_id[requested_account_id]
    )

filter_title, reset_column = st.columns([5, 1])

with filter_title:
    st.markdown("### Active Quota Transactions")

with reset_column:
    st.button(
        "Reset Filters",
        key="quota_tx_reset",
        on_click=reset_filters,
        width="stretch",
    )

first_filter_row = st.columns(3)

account_filter = first_filter_row[0].selectbox(
    "Account",
    account_filter_options,
    key="quota_tx_filter_account",
)

type_filter = first_filter_row[1].selectbox(
    "Quota Type",
    ["All", *QUOTA_TYPES],
    key="quota_tx_filter_quota_type",
)

transaction_type_filter = first_filter_row[2].selectbox(
    "Transaction Type",
    ["All", *QUOTA_TRANSACTION_TYPES],
    key="quota_tx_filter_type",
)

second_filter_row = st.columns(2)

date_from = second_filter_row[0].date_input(
    "Effective Date From",
    value=None,
    key="quota_tx_filter_date_from",
)

date_to = second_filter_row[1].date_input(
    "Effective Date To",
    value=None,
    key="quota_tx_filter_date_to",
)

transactions = repo.get_quota_transactions(
    account_id=account_labels.get(account_filter),
    quota_id=(
        str(requested_quota_id)
        if requested_quota_id
        else None
    ),
    quota_type=(
        None
        if type_filter == "All"
        else type_filter
    ),
    transaction_type=(
        None
        if transaction_type_filter == "All"
        else transaction_type_filter
    ),
    date_from=date_from,
    date_to=date_to,
)


# ---------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------

if transactions.empty:
    total_quantity = 0
else:
    total_quantity = pd.to_numeric(
        transactions["QUOTA_COUNT"],
        errors="coerce",
    ).fillna(0).sum()

metric_left, metric_right = st.columns(2)

metric_left.metric(
    "Filtered Transactions",
    f"{len(transactions):,}",
)

metric_right.metric(
    "Filtered Transaction Quantity",
    f"{total_quantity:,.0f}",
    help="Activity total only; this is not an available balance.",
)


# ---------------------------------------------------------------------
# Transaction list
# ---------------------------------------------------------------------

if transactions.empty:
    st.info("No quota transactions match the current filters.")
else:
    display = transactions.copy()

    required_columns = (
        "QUOTA_TRANSACTION_ID",
        "QUOTA_ID",
        "OWNER_ACCOUNT_ID",
        "RELATED_ACCOUNT_ID",
        "TRANSACTION_TYPE",
        "EFFECTIVE_DATE",
        "END_DATE",
        "QUOTA_COUNT",
        "PRICE",
        "QUOTA_LEASE_TYPE",
        "COMMENTS",
        "CREATED_AT",
        "UPDATED_AT",
    )

    for column in required_columns:
        if column not in display.columns:
            display[column] = None

    display["OWNER_NAME"] = (
        display["OWNER_ACCOUNT_ID"].map(account_names)
    )

    display["RELATED_ACCOUNT_NAME"] = (
        display["RELATED_ACCOUNT_ID"].map(account_names)
    )

    display["QUOTA_NAME"] = (
        display["QUOTA_ID"].map(quota_names)
    )

    display["TRANSACTION_LABEL"] = display.apply(
        lambda row: (
            f"{row['TRANSACTION_TYPE']} · "
            f"{float(row['QUOTA_COUNT'] or 0):,.0f}"
        ),
        axis=1,
    )

    display["TRANSACTION_LINK"] = display.apply(
        lambda row: current_page_link(
            "transaction_id",
            row["QUOTA_TRANSACTION_ID"],
            row["TRANSACTION_LABEL"],
        ),
        axis=1,
    )

    display["QUOTA_LINK"] = display.apply(
        lambda row: current_page_link(
            "quota_id",
            row["QUOTA_ID"],
            row["QUOTA_NAME"] or row["QUOTA_ID"],
        ),
        axis=1,
    )

    display["OWNER_LINK"] = display.apply(
        lambda row: current_page_link(
            "account_id",
            row["OWNER_ACCOUNT_ID"],
            row["OWNER_NAME"] or "Unassigned",
        ),
        axis=1,
    )

    display["RELATED_ACCOUNT_LINK"] = display.apply(
        lambda row: (
            current_page_link(
                "account_id",
                row["RELATED_ACCOUNT_ID"],
                row["RELATED_ACCOUNT_NAME"],
            )
            if pd.notna(row["RELATED_ACCOUNT_ID"])
            else None
        ),
        axis=1,
    )

    st.dataframe(
        display[
            [
                "TRANSACTION_LINK",
                "QUOTA_LINK",
                "OWNER_LINK",
                "RELATED_ACCOUNT_LINK",
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
        height=430,
        hide_index=True,
        column_config={
            "TRANSACTION_LINK": st.column_config.LinkColumn(
                "Transaction",
                display_text=r".*#(.*)$",
                width="medium",
            ),
            "QUOTA_LINK": st.column_config.LinkColumn(
                "Quota Registration",
                display_text=r".*#(.*)$",
                width="large",
            ),
            "OWNER_LINK": st.column_config.LinkColumn(
                "Owner Account",
                display_text=r".*#(.*)$",
                width="medium",
            ),
            "RELATED_ACCOUNT_LINK": st.column_config.LinkColumn(
                "Related Account",
                display_text=r".*#(.*)$",
                width="medium",
            ),
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
# Create / edit form
# ---------------------------------------------------------------------

with st.expander(
    "Create or edit a quota transaction",
    expanded=bool(selected_transaction_id),
):
    all_transactions = repo.get_quota_transactions()

    transaction_options = {}

    for row in all_transactions.itertuples():
        quantity = float(row.QUOTA_COUNT or 0)
        label = (
            f"{row.TRANSACTION_TYPE} · "
            f"{quantity:,.0f} · "
            f"{row.QUOTA_TRANSACTION_ID[:8]}"
        )
        transaction_options[label] = row.QUOTA_TRANSACTION_ID

    record_options = [
        "Create new",
        *transaction_options.keys(),
    ]

    default_record_label = "Create new"

    if selected_transaction_id:
        for label, transaction_id in transaction_options.items():
            if transaction_id == selected_transaction_id:
                default_record_label = label
                break

    edit_label = st.selectbox(
        "Record",
        record_options,
        index=option_index(
            record_options,
            default_record_label,
        ),
        key="quota_tx_record",
        on_change=clear_widget_prefix,
        args=("quota_tx_", ("quota_tx_record",)),
    )

    current = {}

    if edit_label != "Create new":
        transaction_id = transaction_options[edit_label]

        current_matches = all_transactions[
            all_transactions["QUOTA_TRANSACTION_ID"]
            == transaction_id
        ]

        if not current_matches.empty:
            current = current_matches.iloc[0].to_dict()

    current_quota_label = quota_label_by_id.get(
        current.get("QUOTA_ID"),
        list(quota_labels.keys())[0],
    )

    selected_quota = st.selectbox(
        "Quota Registration *",
        list(quota_labels.keys()),
        index=option_index(
            list(quota_labels.keys()),
            current_quota_label,
        ),
        key="quota_tx_quota",
    )

    selected_quota_id = quota_labels[selected_quota]
    owner_account_id = quota_account_ids[selected_quota_id]

    st.info(
        "Owner Account: "
        f"{account_names.get(owner_account_id, 'Unassigned')}"
    )

    left, right = st.columns(2)

    selected_transaction_type = left.selectbox(
        "Transaction Type *",
        QUOTA_TRANSACTION_TYPES,
        index=option_index(
            list(QUOTA_TRANSACTION_TYPES),
            current.get("TRANSACTION_TYPE"),
        ),
        key="quota_tx_type",
    )

    related_account_options = [
        "-- Select --",
        *account_labels.keys(),
    ]

    current_related_account_label = account_label_by_id.get(
        current.get("RELATED_ACCOUNT_ID"),
        "-- Select --",
    )

    related_account = left.selectbox(
        "Related Account",
        related_account_options,
        index=option_index(
            related_account_options,
            current_related_account_label,
        ),
        key="quota_tx_related_account",
    )

    quantity_value = pd.to_numeric(
        current.get("QUOTA_COUNT"),
        errors="coerce",
    )

    if pd.isna(quantity_value):
        quantity_value = 0.0

    quota_count = left.number_input(
        "Quota Count *",
        min_value=0.0,
        value=float(quantity_value),
        step=1.0,
        key="quota_tx_count",
    )

    price_value = pd.to_numeric(
        current.get("PRICE"),
        errors="coerce",
    )

    if pd.isna(price_value):
        price_value = 0.0

    price = left.number_input(
        "Price",
        min_value=0.0,
        value=float(price_value),
        step=1.0,
        key="quota_tx_price",
    )

    effective_date = right.date_input(
        "Effective Date *",
        value=as_date(
            current.get("EFFECTIVE_DATE"),
            dt.date.today(),
        ),
        key="quota_tx_effective",
    )

    end_date = right.date_input(
        "End Date",
        value=as_date(current.get("END_DATE")),
        key="quota_tx_end",
    )

    lease_options = [
        "Not applicable",
        *QUOTA_LEASE_TYPES,
    ]

    current_lease_type = (
        current.get("QUOTA_LEASE_TYPE")
        or "Not applicable"
    )

    selected_lease_type = right.selectbox(
        "Quota Lease Type",
        lease_options,
        index=option_index(
            lease_options,
            current_lease_type,
        ),
        key="quota_tx_lease_type",
    )

    related_quota_options = [
        "-- Select --",
        *quota_labels.keys(),
    ]

    current_related_quota_label = quota_label_by_id.get(
        current.get("RELATED_QUOTA_ID"),
        "-- Select --",
    )

    related_quota = right.selectbox(
        "Related Quota",
        related_quota_options,
        index=option_index(
            related_quota_options,
            current_related_quota_label,
        ),
        key="quota_tx_related_quota",
    )

    related_transaction_id = right.text_input(
        "Related Transaction ID",
        value=str(
            current.get("RELATED_TRANSACTION_ID")
            or ""
        ),
        key="quota_tx_related_transaction",
    )

    comments = st.text_area(
        "Comments",
        value=str(current.get("COMMENTS") or ""),
        key="quota_tx_comments",
    )

    if current:
        audit_left, audit_right = st.columns(2)

        audit_left.text_input(
            "Created On",
            value=format_datetime(
                current.get("CREATED_AT")
            ),
            disabled=True,
            key="quota_tx_created_on",
        )

        audit_right.text_input(
            "Last Updated",
            value=format_datetime(
                current.get("UPDATED_AT")
            ),
            disabled=True,
            key="quota_tx_updated_on",
        )

    if st.button(
        "Save Quota Transaction",
        type="primary",
        key="quota_tx_save",
    ):
        record = {
            "QUOTA_TRANSACTION_ID": current.get(
                "QUOTA_TRANSACTION_ID"
            ),
            "TRANSACTION_TYPE": selected_transaction_type,
            "QUOTA_ID": selected_quota_id,
            "EFFECTIVE_DATE": effective_date,
            "END_DATE": end_date,
            "QUOTA_COUNT": quota_count,
            "RELATED_ACCOUNT_ID": (
                account_labels[related_account]
                if related_account != "-- Select --"
                else None
            ),
            "RELATED_QUOTA_ID": (
                quota_labels[related_quota]
                if related_quota != "-- Select --"
                else None
            ),
            "RELATED_TRANSACTION_ID": (
                related_transaction_id.strip() or None
            ),
            "PRICE": price,
            "QUOTA_LEASE_TYPE": (
                None
                if selected_lease_type == "Not applicable"
                else selected_lease_type
            ),
            "COMMENTS": comments.strip() or None,
        }

        errors = validate_quota_transaction(
            repo,
            record,
        )

        if errors:
            for error in errors:
                st.error(error)
        else:
            try:
                saved_transaction_id = (
                    repo.upsert_quota_transaction(record)
                )

                st.session_state["quota_transaction_flash"] = (
                    "Quota transaction saved: "
                    f"{saved_transaction_id}"
                )

                st.query_params.clear()
                st.query_params["transaction_id"] = (
                    saved_transaction_id
                )
                st.rerun()

            except ValueError as exc:
                st.error(str(exc))
