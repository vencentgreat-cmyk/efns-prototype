"""Read-only views for EIMS entities added by the historical migration."""

from __future__ import annotations

import streamlit as st

from app.auth import require_page_permission
from app.security import Permission
from app.ui import apply_theme, page_header, show_data_error
from data.repositories import get_repository


require_page_permission(Permission.VIEW_DATA)
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo

page_header(
    "EIMS Reference Data",
    "Read-only access to contacts, quota allocations, and the EFC date dimension.",
    "REFERENCE",
)

contacts_tab, allocations_tab, dates_tab = st.tabs(
    ["Contacts", "Quota Allocations", "EFC Date Dimension"]
)

with contacts_tab:
    contact_search = st.text_input("Contact name, email, or phone", key="eims_contact_search")
    try:
        contacts = repo.get_contacts(keyword=contact_search or None)
        st.dataframe(contacts, hide_index=True, width="stretch")
    except Exception as exc:
        show_data_error(exc)

with allocations_tab:
    allocation_filters = st.columns(2)
    quota_type = allocation_filters[0].text_input("Quota type", key="eims_allocation_type")
    province = allocation_filters[1].text_input("Province", key="eims_allocation_province")
    try:
        allocations = repo.get_quota_allocations(
            quota_type=quota_type or None,
            province=province or None,
        )
        st.dataframe(allocations, hide_index=True, width="stretch")
    except Exception as exc:
        show_data_error(exc)

with dates_tab:
    date_filters = st.columns(2)
    date_from = date_filters[0].date_input("From", value=None, key="eims_date_from")
    date_to = date_filters[1].date_input("To", value=None, key="eims_date_to")
    if date_from and date_to and date_from > date_to:
        st.error("From must be on or before To.")
    else:
        try:
            dates = repo.get_efc_dates(date_from=date_from, date_to=date_to)
            st.dataframe(dates, hide_index=True, width="stretch")
        except Exception as exc:
            show_data_error(exc)
