"""Read-only lease activity, separate from stored transactions and report inputs."""
import pandas as pd

from data.position_evidence import day, guid, records
from data.producer_identity import text
from data.quota_types import quota_type_key
from data.quota_leases import (is_lease, is_voided, lease_adjustments,
    effective_lease_end, effective_lease_amount)


def lease_activity(transactions, accounts, as_of, *, incoming):
    """Current daily quantity uses the calculation resolver, including zero off-period."""
    names = {guid(row.get('ACCOUNT_ID')): text(row.get('ORGANIZATION_NAME'))
             for row in records(accounts)}
    output = []
    for row in records(transactions):
        if not is_lease(row):
            continue
        start, when = day(row.get('EFFECTIVE_DATE')), day(as_of)
        note = ''
        try:
            changes = lease_adjustments(row)
            end = effective_lease_end(row)
            if start is None or end is None or when is None:
                raise ValueError('Incomplete lease period')
            quantity = effective_lease_amount(row, when)
            if quantity is None:
                raise ValueError('Unusable lease quantity')
            if is_voided(row):
                status, note = 'Voided', 'No longer affects quota.'
            else:
                status = 'Scheduled' if when < start else 'Ended' if when > end else 'Active'
                if changes:
                    early = any(change['KIND'] == 'Ended early' for change in changes)
                    status += ' · early-ended' if early else ' · adjusted'
                if when < start or when > end:
                    note = 'Does not affect quota on the displayed date.'
        except ValueError:
            end, quantity, status = None, None, 'Needs review'
            note = 'Effective lease values could not be verified; open the original lease.'
            if is_voided(row):
                quantity, status = 0, 'Voided'
                note = 'No longer affects quota. Effective dates could not be verified.'
        party = row.get('OWNER_ACCOUNT_ID' if incoming else 'RELATED_ACCOUNT_ID')
        output.append({'_LEASE_ID': text(row.get('QUOTA_TRANSACTION_ID')),
            'Transaction Type': 'Lease (In)' if incoming else 'Lease (Out)',
            'Start Date': start.isoformat() if start else '—',
            'Effective End Date': end.isoformat() if end else '—',
            'Current Quantity': str(quantity) if quantity is not None else '—',
            'Lessor Account' if incoming else 'Lessee Account': names.get(guid(party)) or text(party) or '—',
            'Status': status, 'Note': note})
    return pd.DataFrame(output)


def incoming_lease_activity(registration, registrations, transactions, accounts, as_of):
    """Match by recipient Account and source Registration Quota Type, never fabricate a row."""
    if not registration or not guid(registration.get('QUOTA_ID')):
        return pd.DataFrame()
    owner, kind = guid(registration.get('ACCOUNT_ID')), quota_type_key(registration.get('QUOTA_TYPE'))
    if not owner or not kind:
        return pd.DataFrame()
    quotas = {guid(row.get('QUOTA_ID')): row for row in records(registrations)}
    found, seen = [], set()
    for row in records(transactions):
        source = quotas.get(guid(row.get('QUOTA_ID')), {})
        identity = guid(row.get('QUOTA_TRANSACTION_ID'))
        if (is_lease(row) and identity and identity not in seen
                and guid(row.get('RELATED_ACCOUNT_ID')) == owner
                and guid(row.get('OWNER_ACCOUNT_ID')) != owner
                and quota_type_key(source.get('QUOTA_TYPE')) == kind):
            found.append(row)
            seen.add(identity)
    return lease_activity(found, accounts, as_of, incoming=True)


def render_lease_activity(title, frame, *, key, as_of):
    """View-only navigation to the original stored record, never a derived editor."""
    import streamlit as st
    from app.navigation import selected_row_index, open_module

    st.markdown(f'**{title} ({len(frame)})**')
    st.caption(f'Read-only lease information as of {as_of}. Current Quantity is the effective lease amount on this date; stored transactions are unchanged.')
    if frame.empty:
        st.info('No matching lease records.')
        return
    st.dataframe(frame.drop(columns=['_LEASE_ID']), hide_index=True, width='stretch',
        on_select='rerun', selection_mode='single-row', key=key)
    selected = selected_row_index(key)
    if selected is not None and selected < len(frame):
        if st.button('Open original lease record', key=key+'_open', icon=':material/visibility:'):
            open_module('Quota_Transactions', 'detail', frame.iloc[selected]['_LEASE_ID'])
