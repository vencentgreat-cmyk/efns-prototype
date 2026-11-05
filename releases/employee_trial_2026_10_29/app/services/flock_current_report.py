"""Pure legacy Flock Current projection; independent of PENDING stock drafts."""
from datetime import date
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from math import floor

import pandas as pd

COLUMNS = ['Reg No', 'Account', 'Quota Type', 'Permit No', 'Count Date',
           'Placement Date', 'Flock Age', 'Counted', 'Inventory', 'Hatch Date',
           'Disp. Date', 'Up. Flocks', 'Notes']
MEASURES = ('Counted', 'Inventory', 'Up. Flocks')


def text(value):
    return '' if value is None or pd.isna(value) else str(value).strip()


def day(value):
    if not text(value):
        return None
    return pd.Timestamp(value).date()


def quantity(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() and result >= 0 and result == result.to_integral_value() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def effective_disposal_date(flock):
    """Actual disposal takes precedence over the estimate when supplied."""
    return day(flock.get('DISPOSAL_DATE')) or day(flock.get('EST_DISPOSAL'))


def flock_is_in_current_report(flock, report_date, quota_type):
    """PROVISIONAL inclusion policy; isolate pending lifecycle/type decisions here."""
    kind = text(flock.get('FLOCK_QUOTA_TYPE'))
    matches = (quota_type == 'All' or kind == quota_type
               or (quota_type == 'Egg Production' and kind == 'Special Permit'))
    disposal = effective_disposal_date(flock)
    return (text(flock.get('STATUS')) == 'Active' and matches
            and (disposal is None or disposal > report_date))


def build_flock_current_report(flocks, transactions, accounts, report_date,
                               mortality='0.4', quota_type='Egg Production'):
    """Return only report rows. Subtotals sum known measures and disclose gaps."""
    report_date = day(report_date)
    if report_date is None:
        raise ValueError('Report date is required.')
    try:
        rate = Decimal(str(mortality))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError('Mortality must be finite and non-negative.') from None
    if not rate.is_finite() or rate < 0:
        raise ValueError('Mortality must be finite and non-negative.')
    for frame, key in ((flocks, 'FLOCK_ID'), (accounts, 'ACCOUNT_ID')):
        if not frame.empty and (frame[key].isna().any() or frame[key].duplicated().any()):
            raise ValueError('Missing or duplicate report parent identity: ' + key)
    owners = {str(row['ACCOUNT_ID']): row for row in accounts.to_dict('records')}
    counts = {}
    for row in transactions.to_dict('records'):
        when = day(row.get('TRANSACTION_DATE'))
        if text(row.get('TRANSACTION_TYPE')) == 'Count' and when and when <= report_date:
            counts.setdefault(str(row.get('FLOCK_ID')), []).append(row)
    groups = {}
    for flock in flocks.to_dict('records'):
        if not flock_is_in_current_report(flock, report_date, quota_type):
            continue
        owner_id = str(flock.get('ACCOUNT_ID'))
        owner = owners.get(owner_id, {})
        kind = text(flock.get('FLOCK_QUOTA_TYPE')) or 'Unknown'
        observations = counts.get(str(flock['FLOCK_ID']), [])
        latest_day = max((day(r['TRANSACTION_DATE']) for r in observations), default=None)
        latest = [r for r in observations if day(r['TRANSACTION_DATE']) == latest_day]
        notes = []
        counted = None
        if not latest:
            notes.append('No Count on or before report date')
        elif (len({quantity(r.get('QUANTITY')) for r in latest}) > 1
              or len({text(r.get('COUNT_SOURCE_LABEL')) or 'Unknown' for r in latest}) > 1):
            notes.append('Count conflict')
        else:
            counted = quantity(latest[0].get('QUANTITY'))
            if counted is None:
                notes.append('Invalid Count quantity')
        placement, hatch = day(flock.get('PLACEMENT_DATE')), day(flock.get('HATCH_DATE'))
        inventory = upcoming = None
        if placement is None:
            notes.append('Placement date unavailable')
        elif counted is not None:
            if placement > report_date:
                inventory, upcoming = 0, int(counted)
            else:
                inventory = floor(Fraction(counted) * (1 - Fraction(rate) * 12
                                  * (report_date - latest_day).days / 36500))
                upcoming = 0
        row = dict(zip(COLUMNS, [text(owner.get('REGISTRATION_NUMBER')) or '—',
            text(owner.get('ORGANIZATION_NAME')) or owner_id, kind,
            text(flock.get('PERMIT_NUMBER')) or '—', latest_day, placement,
            (report_date - hatch).days // 7 if hatch else None,
            int(counted) if counted is not None else None, inventory, hatch,
            effective_disposal_date(flock), upcoming, '; '.join(notes)]))
        groups.setdefault((owner_id, kind), []).append((text(flock.get('FLOCK_NUMBER')), row))

    def subtotal(rows, label, kind=''):
        result = {column: None for column in COLUMNS}
        result.update({'Account': label, 'Quota Type': kind, 'Notes': ''})
        for column in MEASURES:
            values = [row[column] for row in rows if row[column] is not None]
            result[column] = sum(values) if values else None
        missing_count = sum(row['Counted'] is None for row in rows)
        result['Notes'] = f'Excludes {missing_count} flock(s) without usable Count'
        missing_placement = sum(row['Counted'] is not None and row['Inventory'] is None for row in rows)
        if missing_placement:
            result['Notes'] += f'; Inventory/Up. Flocks exclude {missing_placement} flock(s) without placement date'
        return result

    output, quota_rows = [], {}
    owner_ids = sorted({key[0] for key in groups}, key=lambda key: (
        text(owners.get(key, {}).get('ORGANIZATION_NAME')), key))
    for owner_id in owner_ids:
        account_rows = []
        for _, kind in sorted(key for key in groups if key[0] == owner_id):
            rows = [row for _, row in sorted(groups[(owner_id, kind)], key=lambda item: item[0])]
            output.extend(rows)
            account_rows.extend(rows)
            quota_rows.setdefault(kind, []).extend(rows)
        output.append(subtotal(account_rows, 'Account Total'))
    for kind, rows in sorted(quota_rows.items()):
        output.append(subtotal(rows, 'Quota Total', kind))
    # Object dtype preserves exact integers and missing values for display/exports.
    result = pd.DataFrame(output, columns=COLUMNS, dtype=object)
    for column in ('Count Date', 'Placement Date', 'Hatch Date', 'Disp. Date'):
        result[column] = result[column].map(lambda value: value.isoformat() if isinstance(value, date) else '—')
    return result.where(result.notna(), '—')
