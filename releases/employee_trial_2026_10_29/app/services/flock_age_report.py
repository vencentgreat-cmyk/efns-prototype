"""Pure Flock Age projection and confirmed owner quota calculation.

No repository access is implemented here. Missing state evidence keeps quotas
unknown, including provincial totals when any supplied quota is unknown.
"""
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd

from app.services.flock_current_report import build_flock_current_report, quantity, text
from data.confirmed_quota_position import confirmed_quota_position
from data.quota_types import quota_type_key


def producers_with_positive_quota(accounts, quotas):
    producer_ids = {str(r['ACCOUNT_ID']) for r in accounts.to_dict('records')
                    if r.get('PRODUCER_ROLE') is True or str(r.get('PRODUCER_ROLE')).lower() == 'true'}
    return sum(value is not None and value > 0
               for identity, value in quotas.items() if str(identity) in producer_ids)


def build_flock_age_quotas(registrations, transactions, accounts, report_date,
                          inactive_transaction_ids, rules):
    """Use confirmed Egg Production positions once per active owning Account."""
    active = registrations.loc[
        registrations.get('STATUS', pd.Series(index=registrations.index, dtype=object)).map(text).str.casefold().eq('active')
        & registrations.get('QUOTA_TYPE', pd.Series(index=registrations.index, dtype=object)).map(quota_type_key).eq('Egg Production')]
    quotas, reasons = {}, {}
    for account_id in active.get('ACCOUNT_ID', pd.Series(dtype=object)).dropna().unique():
        position = confirmed_quota_position(registrations, transactions, account_id,
            'Egg Production', report_date, inactive_transaction_ids, rules)
        quotas[str(account_id)] = position['net_position']
        reasons[str(account_id)] = position['reasons']
    return quotas, producers_with_positive_quota(accounts, quotas), reasons

COLUMNS = ['Reg No', 'Account', 'Permit No', 'Facility name', 'Placement Date',
           'Flock Age', 'Inventory', 'Quota', 'Hatch Date', 'Disp. Date',
           'Up. Flocks', 'Util.', 'Notes']


def utilization(inventory, quota):
    if inventory is None or quota is None or quota == 0:
        return '—'
    percent = (Decimal(inventory) * 100 / Decimal(quota)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f'{percent:.2f}%'


def known_total(values):
    known = [v for v in values if v is not None]
    return sum(known) if known else None


def quota_from_summary(frame, metrics):
    """Use existing summary total only when all its issuance values are known."""
    if frame.empty or 'ISSUANCE' not in frame:
        return None
    if any(quantity(value) is None for value in frame.ISSUANCE):
        return None
    return quantity(metrics.get('total_issuance'))


def build_flock_age_report(flocks, transactions, accounts, facilities, quotas,
                           report_date, mortality='0.4', quota_type='Egg Production'):
    """Return (result, summary); quotas maps Account IDs to confirmed positions.

    Special Permit is excluded even for All. Inventory/upcoming subtotals sum
    known measures, with missing detail values disclosed in Notes.
    """
    eligible = flocks.loc[flocks.get('FLOCK_QUOTA_TYPE', pd.Series(index=flocks.index, dtype=object)).map(text) != 'Special Permit']
    # Validate report parameters and parent identities even for an empty result.
    build_flock_current_report(eligible.iloc[:0], transactions.iloc[:0], accounts,
                               report_date, mortality, quota_type)
    if not flocks.empty and (flocks.FLOCK_ID.isna().any() or flocks.FLOCK_ID.duplicated().any()):
        raise ValueError('Missing or duplicate report parent identity: FLOCK_ID')
    if not facilities.empty and facilities.FACILITY_ID.duplicated().any():
        raise ValueError('Duplicate Facility identity')
    names = {str(r['FACILITY_ID']): text(r.get('FACILITY_NAME')) for r in facilities.to_dict('records')}
    grouped_transactions = {str(key): group for key, group in transactions.groupby('FLOCK_ID')} if not transactions.empty else {}
    owners = {str(r['ACCOUNT_ID']): r for r in accounts.to_dict('records')}
    groups = {}
    for flock in eligible.to_dict('records'):
        current = build_flock_current_report(pd.DataFrame([flock]),
            grouped_transactions.get(str(flock['FLOCK_ID']), transactions.iloc[:0]),
            accounts, report_date, mortality, quota_type)
        if current.empty:
            continue
        row = current.iloc[0].to_dict()
        owner_id = str(flock.get('ACCOUNT_ID'))
        quota = quantity(quotas.get(owner_id))
        row.update({'Facility name': names.get(str(flock.get('FACILITY_ID'))) or '—',
                    'Quota': quota, 'Util.': utilization(row['Inventory'] if row['Inventory'] != '—' else None, quota)})
        if quota is None:
            row['Notes'] = '; '.join(filter(None, [row['Notes'], 'Quota position unavailable']))
        groups.setdefault(owner_id, []).append(row)
    output, inventories = [], []
    for owner_id in sorted(groups, key=lambda key: (text(owners.get(key, {}).get('ORGANIZATION_NAME')), key)):
        rows = groups[owner_id]
        rows.sort(key=lambda r: text(r['Permit No']))
        output.extend(rows)
        values = [r['Inventory'] if r['Inventory'] != '—' else None for r in rows]
        inventories.extend(values)
        total = {column: None for column in COLUMNS}
        quota = quantity(quotas.get(owner_id))
        inventory = known_total(values)
        notes = []
        if values.count(None):
            notes.append(f'Excludes {values.count(None)} flock(s) without known Inventory')
        if quota is None:
            notes.append('Quota position unavailable')
        total.update({'Reg No': rows[0]['Reg No'], 'Account': 'Total',
            'Inventory': inventory, 'Quota': quota,
            'Up. Flocks': known_total([r['Up. Flocks'] if r['Up. Flocks'] != '—' else None for r in rows]),
            'Util.': utilization(inventory, quota),
            'Notes': '; '.join(notes)})
        output.append(total)
    quota_scope = {**{owner_id: None for owner_id in groups}, **quotas}
    quota_values = [quantity(v) for v in quota_scope.values()]
    allocation = sum(quota_values) if quota_values and all(v is not None for v in quota_values) else None
    inventory = known_total(inventories)
    summary = {'Inventory Birds': inventory, 'NFPMC Allocation': allocation,
        'Provincial Utilization': utilization(inventory, allocation),
        'Issuance for Province': allocation,
        'Producers with Quota': producers_with_positive_quota(accounts, quotas),
        'Notes': f'{quota_values.count(None)} Account quota(s) unavailable; {inventories.count(None)} flock Inventory value(s) excluded'}
    result = pd.DataFrame(output, columns=COLUMNS, dtype=object)
    return result.where(result.notna(), '—'), summary
