"""Count observations and candidate changes; no inferred lifecycle/priority.

Count is never an addition. NEW_NETBIRDCOUNT is only an old-system reference.
Same-day counts from different sources are a conflict, even if quantities match.
"""
from data.position_evidence import day, guid, inactive, known_sum, number, records
from data.producer_identity import text


def flock_stock(flock, transactions, as_of, rules, *, source_verified=False,
                missing_source_rows=None, inactive_source_rows=None, live_scope=None):
    rules = rules.get('flock_stock', rules)
    date = day(as_of)
    reasons = []
    if rules.get('status') != 'CONFIRMED':
        reasons.append('Flock stock rules UNCONFIRMED')
    if rules.get('type_sign') != {'Delivery': 1, 'Removal': -1, 'Sale': -1}:
        reasons.append('Unsupported activity direction rule; Count is observation only')
    if not source_verified or missing_source_rows is None or inactive_source_rows is None:
        reasons.append('RAW completeness and record state not verified')
    if missing_source_rows:
        reasons.append(f'{missing_source_rows} source rows not in CORE')
    if inactive_source_rows:
        reasons.append(f'{inactive_source_rows} Inactive source transactions excluded; business meaning unconfirmed')
    if rules.get('lifecycle_rule') != 'EXPLICIT_SCOPE' or live_scope is not True:
        reasons.append('Current/live flock scope not confirmed')
    if date is None or not guid(flock.get('FLOCK_ID')):
        reasons.append('Flock identity and as-of date required')
    rows = [r for r in records(transactions) if guid(r.get('FLOCK_ID')) == guid(flock.get('FLOCK_ID'))]
    ids = [guid(r.get('FLOCK_TRANSACTION_ID')) for r in rows]
    if None in ids or len(ids) != len(set(ids)):
        reasons.append('Transaction identity missing or duplicate')
    active = []
    for row in rows:
        if inactive(row):
            reasons.append('Inactive source transaction excluded; business meaning unconfirmed')
            continue
        when = day(row.get('TRANSACTION_DATE'))
        if when is None:
            reasons.append('Transaction date missing/invalid')
        elif date is not None and when <= date:
            active.append(row)
    counts = [r for r in active if text(r.get('TRANSACTION_TYPE')) == 'Count']
    count_date = max((day(r['TRANSACTION_DATE']) for r in counts), default=None)
    latest = [r for r in counts if day(r['TRANSACTION_DATE']) == count_date]
    by_day = {}
    for row in counts:
        by_day.setdefault(day(row['TRANSACTION_DATE']), []).append(row)
    conflicts = [d for d, group in by_day.items()
                 if len({text(r.get('COUNT_SOURCE_LABEL')) or 'Unknown' for r in group}) > 1
                 or len({number(r.get('QUANTITY')) for r in group}) > 1]
    if conflicts:
        reasons.append('Same-day Count source/quantity conflict; no automatic priority')
    latest_qty = number(latest[0].get('QUANTITY')) if latest and count_date not in conflicts else None
    if latest_qty is None or latest_qty < 0 or latest_qty != latest_qty.to_integral_value():
        reasons.append('No usable latest Count observation')
        latest_qty = None
    deltas = {kind: [] for kind in ('Delivery', 'Removal', 'Sale')}
    for row in active:
        kind = text(row.get('TRANSACTION_TYPE'))
        when = day(row['TRANSACTION_DATE'])
        if kind == 'Count':
            continue
        if kind not in deltas:
            reasons.append('Unknown flock transaction type')
            continue
        if count_date and when == count_date:
            reasons.append('Count and activity share a date; ordering unconfirmed')
        if count_date and when > count_date:
            qty = number(row.get('QUANTITY'))
            deltas[kind].append(qty)
            if qty is None or qty < 0 or qty != qty.to_integral_value():
                reasons.append('Activity quantity missing/invalid')
    sums = {k: known_sum(v) if v else number(0) for k, v in deltas.items()}
    candidate = None
    if latest_qty is not None and all(v is not None for v in sums.values()):
        candidate = latest_qty + sums['Delivery'] - sums['Removal'] - sums['Sale']
        if candidate < 0:
            reasons.append('Candidate stock negative')
    reasons = list(dict.fromkeys(reasons))
    return {'flock_id': flock.get('FLOCK_ID'), 'bird_count': number(flock.get('BIRD_COUNT')),
            'old_system_reference': number(flock.get('NEW_NETBIRDCOUNT')),
            'status': text(flock.get('STATUS')), 'latest_count_date': count_date,
            'latest_count_quantity': latest_qty, 'latest_counts': latest,
            'count_conflict_dates': sorted(conflicts), 'changes_after_count': sums,
            'candidate_current_stock': candidate if not reasons else None, 'reasons': reasons}
