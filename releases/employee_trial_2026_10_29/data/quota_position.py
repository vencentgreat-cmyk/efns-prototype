"""Owner-only quota components, gated by rules AND source-completeness evidence.

No repository calls or writes. RAW coverage/state evidence must be supplied by
the caller; CORE does not contain it. Related Account is never treated as Owner.
"""
import json
from pathlib import Path

import pandas as pd

from data.position_evidence import day, guid, inactive, known_sum, number, records
from data.producer_identity import text
from data.quota_types import quota_type_key

EXCLUDED_TYPES = frozenset({'National Allocation', 'Provincial Allocation'})


def load_rules():
    return json.loads((Path(__file__).resolve().parents[1] / 'config/quota_rules.json').read_text(encoding='utf-8'))


def component_table(transactions, account_id=None):
    """Recorded owner-row quantities by type; not direction or net entitlement."""
    rows = [row for row in records(transactions) if guid(row.get('OWNER_ACCOUNT_ID'))
            and (account_id is None or guid(row.get('OWNER_ACCOUNT_ID')) == guid(account_id))]
    groups = {}
    for row in rows:
        if text(row.get('TRANSACTION_TYPE')) in EXCLUDED_TYPES:
            continue
        key = (guid(row['OWNER_ACCOUNT_ID']), text(row.get('TRANSACTION_TYPE')) or 'Unknown')
        groups.setdefault(key, []).append(number(row.get('QUOTA_COUNT')))
    return pd.DataFrame([{'Owner Account ID': owner, 'Transaction Type': kind,
                          'Records': len(values), 'Known quantities': sum(v is not None for v in values),
                          'Missing quantities': sum(v is None for v in values),
                          'Recorded quantity': known_sum(values)}
                         for (owner, kind), values in sorted(groups.items())])


def quota_position(registrations, transactions, account_id, quota_type, as_of, rules,
                   *, missing_source_rows=None, pending_rejected_count=0,
                   inactive_source_rows=None, source_verified=False, unresolved_owner_rows=0):
    """An empty *verified* evidence set is different from absent evidence.

    Counts are for this Account/type; callers must also attach unresolved-owner
    gaps conservatively rather than assigning them using labels/counterparties.
    Allocation rows are outside this model, not missing account entitlement.
    """
    reasons = []
    account = guid(account_id)
    date = day(as_of)
    regs = [r for r in records(registrations) if guid(r.get('ACCOUNT_ID')) == account
            and quota_type_key(r.get('QUOTA_TYPE')) == quota_type_key(quota_type)]
    ids = [guid(r.get('QUOTA_ID')) for r in regs]
    all_ids = [guid(r.get('QUOTA_ID')) for r in records(registrations)]
    if not account or not date:
        reasons.append('Account identity and as-of date are required')
    if not regs or None in ids or len(ids) != len(set(ids)):
        reasons.append('Registration identity missing or duplicate')
    signs = rules.get('type_sign', {})
    if rules.get('status') != 'CONFIRMED':
        reasons.append('Quota rules UNCONFIRMED')
    if not source_verified or missing_source_rows is None or inactive_source_rows is None:
        reasons.append('RAW completeness and record state not verified')
    if missing_source_rows:
        reasons.append(f'{missing_source_rows} source rows not in CORE')
    if pending_rejected_count:
        reasons.append(f'{pending_rejected_count} pending/rejected source rows')
    if unresolved_owner_rows:
        reasons.append(f'{unresolved_owner_rows} source rows have unresolved Owner; completeness cannot be certified')
    if inactive_source_rows:
        reasons.append(f'{inactive_source_rows} Inactive source transactions excluded; business meaning unconfirmed')
    if any(guid(r.get('OWNER_ACCOUNT_ID')) == account and guid(r.get('QUOTA_ID')) not in all_ids
           and text(r.get('TRANSACTION_TYPE')) not in EXCLUDED_TYPES for r in records(transactions)):
        reasons.append('Owner transaction references a missing Registration; type cannot be resolved')
    selected = [r for r in records(transactions)
                if guid(r.get('OWNER_ACCOUNT_ID')) == account and guid(r.get('QUOTA_ID')) in ids]
    owned_elsewhere = [r for r in records(transactions) if guid(r.get('QUOTA_ID')) in ids
                       and guid(r.get('OWNER_ACCOUNT_ID')) != account]
    if owned_elsewhere:
        reasons.append('Transaction Owner conflicts with Registration Account')
    tx_ids = [guid(r.get('QUOTA_TRANSACTION_ID')) for r in selected]
    if None in tx_ids or len(tx_ids) != len(set(tx_ids)):
        reasons.append('Transaction identity missing or duplicate')
    buckets = {}
    active_leases = []
    excluded_bases = []
    absorbed_activity = []
    closed = {}
    unknown = inactive_count = excluded = 0
    candidate = number(0)
    eligible = []
    for row in selected:
        kind = text(row.get('TRANSACTION_TYPE'))
        kind = {'Lease In':'Lease (In)', 'Lease Out':'Lease (Out)'}.get(kind, kind)
        if kind in EXCLUDED_TYPES:
            excluded += 1
            continue
        if inactive(row):
            inactive_count += 1
            continue
        effective = day(row.get('EFFECTIVE_DATE'))
        if effective is None:
            reasons.append('Missing/invalid Effective Date')
            continue
        if date is not None and effective <= date:
            eligible.append((row, kind, effective))
    latest = {}
    for registration in ids:
        bases = [(r, d) for r, k, d in eligible if k == 'Base' and guid(r.get('QUOTA_ID')) == registration]
        if not bases:
            continue
        if rules.get('base_policy') != 'LATEST_SNAPSHOT_PER_REGISTRATION':
            reasons.append('Latest Base snapshot policy not specified')
        last_day = max(d for _, d in bases)
        last = [r for r, d in bases if d == last_day]
        if len(last) != 1:
            reasons.append('Multiple latest Base snapshots on the same date; ordering unresolved')
        # A tie has no selected Base; never pick an arbitrary GUID/row order.
        latest[registration] = (last_day, guid(last[0].get('QUOTA_TRANSACTION_ID')) if len(last) == 1 else None)
    totals = {}
    for row, kind, effective in eligible:
        registration = guid(row.get('QUOTA_ID'))
        identity = guid(row.get('QUOTA_TRANSACTION_ID'))
        base = latest.get(registration)
        qty = number(row.get('QUOTA_COUNT'))
        if kind == 'Terminate Quota':
            if rules.get('terminate_policy') != 'ZERO_EFFECT_CLOSE_REGISTRATION' or qty != 0:
                reasons.append('Terminate Quota must be a zero-effect closure with quantity zero')
            else:
                closed[registration] = max(closed.get(registration, effective), effective)
            if base and effective < base[0]:
                reasons.append('Base follows registration closure; reopening is unconfirmed')
        if kind == 'Base' and base and identity != base[1]:
            excluded_bases.append(dict(row))
            continue
        if kind != 'Base' and base and effective < base[0]:
            if kind in {'Lease (In)', 'Lease (Out)'}:
                end = day(row.get('END_DATE'))
                if end is None or (date is not None and end >= date):
                    reasons.append('Active/undated lease predates latest Base; snapshot inclusion unconfirmed')
            absorbed_activity.append(dict(row))
            continue
        if kind != 'Base' and base and effective == base[0]:
            reasons.append('Base and activity share a date; snapshot ordering unconfirmed')
        if kind in {'Lease (In)', 'Lease (Out)'}:
            end = day(row.get('END_DATE'))
            if rules.get('lease_active_rule') != 'EFFECTIVE_DATE<=as_of<=END_DATE':
                reasons.append('Lease active rule unsupported/unconfirmed')
            if end is None or end < effective:
                reasons.append('Lease End Date missing/invalid')
                continue
            if date > end:
                continue
            active_leases.append(row)
        buckets.setdefault(kind or 'Unknown', []).append(qty)
        sign = signs.get(kind)
        if kind not in signs or sign not in {-1, 0, 1}:
            unknown += 1
            continue
        if qty is None:
            reasons.append('Missing/invalid Quota Count')
            continue
        if kind != 'Adjustment' and qty < 0:
            reasons.append('Negative quantity has unconfirmed direction for ' + str(kind))
        effect = qty * sign
        if kind == 'Terminate Quota':
            effect = number(0)  # Closure never manufactures a balancing quantity.
        candidate += effect
        totals[registration] = totals.get(registration, number(0)) + effect
    for registration, closed_day in closed.items():
        if totals.get(registration, number(0)) != 0:
            reasons.append('Closed Registration has non-zero candidate; reconcile sold/transferred quantity')
        if any(guid(r.get('QUOTA_ID')) == registration and k != 'Terminate Quota' and d > closed_day
               for r, k, d in eligible):
            reasons.append('Activity follows registration closure; requires review')
    if unknown:
        reasons.append(f'{unknown} unknown transaction type rows')
    if inactive_count:
        reasons.append(f'{inactive_count} Inactive CORE-linked transactions excluded; business meaning unconfirmed')
    reasons = list(dict.fromkeys(reasons))
    return {'account_id': account_id, 'quota_type': quota_type, 'as_of': date,
            'components': {k: known_sum(v) for k, v in buckets.items()},
            'active_leases': active_leases, 'unknown_type_count': unknown,
            'excluded_base_rows': excluded_bases, 'excluded_base_count': len(excluded_bases),
            'absorbed_activity_rows': absorbed_activity,
            'closed_registrations': sorted(closed),
            'pending_rejected_count': pending_rejected_count,
            'missing_source_count': missing_source_rows,
            'inactive_count': inactive_count, 'excluded_allocation_count': excluded,
            'net_position': None if reasons else candidate, 'reasons': reasons}
