"""Pure legacy over-quota projection over the existing flock/quota builders."""
from decimal import Decimal

import pandas as pd

from app.services.flock_age_report import known_total, utilization
from app.services.flock_current_report import build_flock_current_report, day, quantity, text
from app.services.flock_reports import build_flock_status_report

COLUMNS = ['Reg No', 'Account Name', 'Permit No', 'Flock Age', 'Placement Date',
           'Disposal Date', 'Quota Type', 'Last Count', 'Inventory', '% Quota']


def _order(value):
    value = text(value)
    return (0, int(value)) if value.isdecimal() else (1, value.casefold()) if value else (2, '')


def _date(value):
    return day(value).strftime('%d/%m/%Y') if text(value) not in {'', '—'} else ''


def build_producers_over_quota_report(flocks, transactions, accounts, facilities, quotas,
                                     report_date, mortality='0.4', quota_type='Egg Production'):
    """Filter known Account totals strictly above quota, retaining unknown details.

    Province-wide metrics are exactly Flock Status's metrics, not the sum of the
    filtered output. Account quotas have the same confirmed Egg Production basis.
    The legacy-only zero/Last Count presentation rules do not alter shared builders.
    """
    _, summary = build_flock_status_report(flocks, transactions, accounts, facilities,
                                          quotas, report_date, mortality, quota_type)
    report_date = day(report_date)  # Validated by the shared builder, even if empty.
    owners = {str(row['ACCOUNT_ID']): row for row in accounts.to_dict('records')}
    activity = {str(key): group for key, group in transactions.groupby('FLOCK_ID')} if not transactions.empty else {}
    groups, notes = {}, []
    if quota_type != 'Egg Production':
        notes.append('Only Egg Production has been validated against the legacy report; '
                     'the quota basis remains confirmed Egg Production, as in Flock Status.')
    for flock in flocks.to_dict('records'):
        if text(flock.get('FLOCK_QUOTA_TYPE')) == 'Special Permit':
            continue  # Same exclusion as Flock Age / Flock Status, including All.
        tx = activity.get(str(flock['FLOCK_ID']), transactions.iloc[:0])
        current = build_flock_current_report(pd.DataFrame([flock]), tx, accounts,
                                             report_date, mortality, quota_type)
        if current.empty:
            continue
        source = current.iloc[0].to_dict()
        owner_id = str(flock.get('ACCOUNT_ID'))
        placement = day(flock.get('PLACEMENT_DATE'))
        inventory = None if source['Inventory'] == '—' else source['Inventory']
        reason = source['Notes']
        not_counted = 'No Count or Delivery on or before report date' in reason
        if placement and (placement > report_date or not_counted):
            inventory = 0  # User-confirmed legacy not-yet-placed/not-yet-counted display.
            if not_counted:
                reason = 'Not yet counted; Inventory shown as 0 for this legacy report'
        observation_date = None if source['Count Date'] == '—' else day(source['Count Date'])
        true_count = observation_date and any(
            text(row.get('TRANSACTION_TYPE')) == 'Count' and day(row.get('TRANSACTION_DATE')) == observation_date
            for row in tx.to_dict('records'))
        last_count = _date(observation_date) if placement and placement <= report_date and true_count else ''
        row = dict(zip(COLUMNS, ['', '', source['Permit No'] if source['Permit No'] != '—' else '',
            source['Flock Age'] if source['Flock Age'] != '—' else '', _date(placement),
            _date(source['Disp. Date']), source['Quota Type'], last_count, inventory, '']))
        groups.setdefault(owner_id, []).append((row, reason))
    output = []
    for owner_id in sorted(groups, key=lambda key: (_order(owners.get(key, {}).get('REGISTRATION_NUMBER')), key)):
        owner = owners.get(owner_id, {})
        registration, name = text(owner.get('REGISTRATION_NUMBER')), text(owner.get('ORGANIZATION_NAME'))
        account_label = registration or name or 'Account without a registration number/name'
        rows = sorted(groups[owner_id], key=lambda item: _order(item[0]['Permit No']))
        quota = quantity(quotas.get(owner_id))
        if quota is None or quota == 0:
            notes.append(f'{account_label}: excluded; confirmed quota is '
                         + ('zero' if quota == 0 else 'unavailable') + ', so % Quota is undefined.')
            continue
        inventory = known_total([row['Inventory'] for row, _ in rows])
        unknown = sum(row['Inventory'] is None for row, _ in rows)
        if unknown:
            notes.append(f'{account_label}: total excludes {unknown} flock(s) with genuinely unknown Inventory.')
        if inventory is None:
            notes.append(f'{account_label}: excluded; no known Inventory is available to classify the Account.')
            continue
        if inventory <= quota:  # Exact integer/Decimal comparison, before percent rounding.
            continue
        for index, (row, reason) in enumerate(rows):
            row.update({'Reg No': registration if index == 0 else '',
                        'Account Name': name if index == 0 else '',
                        '% Quota': utilization(row['Inventory'], quota) if row['Inventory'] is not None else ''})
            if row['Inventory'] is None:
                row['Inventory'] = ''
            output.append(row)
            if reason:
                notes.append(f'{account_label}, permit {row["Permit No"] or "unavailable"}: {reason}')
        total = dict.fromkeys(COLUMNS, '')
        total.update({'Account Name': 'Total', 'Inventory': inventory, '% Quota': utilization(inventory, quota)})
        output.append(total)
    result = pd.DataFrame(output, columns=COLUMNS, dtype=object)
    result.attrs['notes'] = list(dict.fromkeys(notes))
    whole, _, fraction = format(Decimal(str(mortality)), 'f').partition('.')
    rate_text = whole + '.' + fraction.ljust(3, '0')
    result.attrs['header'] = (f'For {quota_type} as of {report_date:%d/%m/%Y} '
                              f'at {rate_text} Mortality')
    return result, summary
