"""Pure Flock Age projection; quotas must come from existing Quota Summary.

No quota formula or repository access is implemented here. Missing quotas stay
unknown, including provincial totals when any supplied quota is unknown.
"""
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd

from app.services.flock_current_report import build_flock_current_report, quantity, text

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
                           report_date, mortality='0.4', quota_type='Egg Production',
                           *, producer_count=None):
    """Return (result, summary); quotas maps Account IDs to summary-derived values.

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
            row['Notes'] = '; '.join(filter(None, [row['Notes'], 'Quota unavailable from Quota Summary']))
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
        total.update({'Reg No': rows[0]['Reg No'], 'Account': 'Total',
            'Inventory': inventory, 'Quota': quota,
            'Up. Flocks': known_total([r['Up. Flocks'] if r['Up. Flocks'] != '—' else None for r in rows]),
            'Util.': utilization(inventory, quota),
            'Notes': f'Excludes {values.count(None)} flock(s) without known Inventory'
                     + ('; Quota unavailable from Quota Summary' if quota is None else '')})
        output.append(total)
    quota_scope = {**{owner_id: None for owner_id in groups}, **quotas}
    quota_values = [quantity(v) for v in quota_scope.values()]
    allocation = sum(quota_values) if quota_values and all(v is not None for v in quota_values) else None
    inventory = known_total(inventories)
    summary = {'Inventory Birds': inventory, 'NFPMC Allocation': allocation,
        'Provincial Utilization': utilization(inventory, allocation),
        'Issuance for Province': allocation,
        'Producers with Quota': len(quotas) if producer_count is None else producer_count,
        'Notes': f'{quota_values.count(None)} Account quota(s) unavailable; {inventories.count(None)} flock Inventory value(s) excluded'}
    result = pd.DataFrame(output, columns=COLUMNS, dtype=object)
    return result.where(result.notna(), '—'), summary
