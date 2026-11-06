"""Confirmed 2026-11-05 owner quota rule; pure and independent of stock rules."""
import pandas as pd

from data.position_evidence import day, guid, number, records
from data.producer_identity import text
from data.quota_types import quota_type_key

SIGNS = {'Base': 1, 'Adjustment': 1, 'Global Adjustment': 1, 'Purchase': 1,
         'Lease (In)': 1, 'Sale': -1, 'Lease (Out)': -1, 'Terminate Quota': 0}
EXCLUDED = {'National Allocation', 'Provincial Allocation'}
INCREASING_TYPES = ('Base', 'Adjustment', 'Purchase', 'Global Adjustment', 'Lease (In)')


def confirmed_quota_position(registrations, transactions, account_id, quota_type,
                             as_of, inactive_transaction_ids, rules):
    """None evidence means unavailable; a verified empty set means all Active.

    Without an Active Base, sum all eligible Active activity. Invalid required
    dates/quantities or an unresolved Base tie still produce unknown.
    """
    reasons = []
    if rules.get('status') != 'CONFIRMED':
        reasons.append('Quota rules UNCONFIRMED')
    if inactive_transaction_ids is None:
        reasons.append('Transaction state evidence unavailable')
    when, owner = day(as_of), guid(account_id)
    if when is None or owner is None:
        reasons.append('Account and as-of date required')
    regs = [r for r in records(registrations) if guid(r.get('ACCOUNT_ID')) == owner
            and quota_type_key(r.get('QUOTA_TYPE')) == quota_type_key(quota_type)
            and (text(r.get('STATUS')) or '').casefold() == 'active']
    ids = [guid(r.get('QUOTA_ID')) for r in regs]
    if None in ids or len(ids) != len(set(ids)):
        reasons.append('Registration identity missing or duplicate')
    inactive = {guid(value) for value in inactive_transaction_ids or set()}
    rows = [r for r in records(transactions) if guid(r.get('QUOTA_ID')) in ids
            and guid(r.get('OWNER_ACCOUNT_ID')) == owner
            and guid(r.get('QUOTA_TRANSACTION_ID')) not in inactive]
    tx_ids = [guid(r.get('QUOTA_TRANSACTION_ID')) for r in rows]
    if None in tx_ids or len(tx_ids) != len(set(tx_ids)):
        reasons.append('Transaction identity missing or duplicate')
    eligible = []
    for row in rows:
        kind = text(row.get('TRANSACTION_TYPE'))
        kind = {'Lease In': 'Lease (In)', 'Lease Out': 'Lease (Out)'}.get(kind, kind)
        if kind in EXCLUDED:
            continue
        effective = day(row.get('EFFECTIVE_DATE'))
        if effective is None:
            reasons.append('Invalid transaction Effective Date')
        elif when is not None and effective <= when:
            eligible.append((row, kind, effective))
    totals, selected_bases, per_type_sums = {}, {}, {}
    for registration in ids:
        scoped = [(r, k, d) for r, k, d in eligible if guid(r.get('QUOTA_ID')) == registration]
        bases = [(r, d) for r, k, d in scoped if k == 'Base']
        latest_day, selected = None, None
        if bases:
            latest_day = max(d for _, d in bases)
            latest = [r for r, d in bases if d == latest_day]
            if len(latest) > 1:
                stamps = pd.to_datetime([r.get('CREATED_AT') for r in latest], utc=True, errors='coerce')
                if stamps.isna().any():
                    reasons.append('Base tie has missing/invalid Created At')
                    continue
                latest = [r for r, stamp in zip(latest, stamps) if stamp == stamps.max()]
            if len(latest) != 1:
                reasons.append('Base ordering tie unresolved')
                continue
            selected = guid(latest[0]['QUOTA_TRANSACTION_ID'])
            selected_bases[registration] = selected
        total = number(0)
        for row, kind, effective in scoped:
            if latest_day is not None and (effective < latest_day or (kind == 'Base' and guid(row['QUOTA_TRANSACTION_ID']) != selected)):
                continue
            if kind not in SIGNS:
                reasons.append('Unknown quota transaction type: ' + str(kind))
                continue
            if kind in {'Lease (In)', 'Lease (Out)'}:
                end = day(row.get('END_DATE'))
                if text(row.get('END_DATE')) and end is None:
                    reasons.append('Invalid lease End Date')
                    continue
                if end is not None and end < when:
                    continue
            if kind == 'Terminate Quota':
                continue  # Confirmed zero effect, without inventing a balancing quantity.
            value = number(row.get('QUOTA_COUNT'))
            if value is None:
                reasons.append('Missing/invalid Quota Count')
                continue
            total += value * SIGNS[kind]
            if kind in INCREASING_TYPES:
                per_type_sums[kind] = per_type_sums.get(kind, number(0)) + value
        totals[registration] = total
    return {'net_position': None if reasons else sum(totals.values(), number(0)),
            'per_type_sums': None if reasons else per_type_sums,
            'registration_totals': totals, 'selected_bases': selected_bases,
            'reasons': list(dict.fromkeys(reasons))}
