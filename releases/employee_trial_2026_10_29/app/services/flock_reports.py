"""Pure legacy flock report projections; no repository or Streamlit access."""
from app.services.flock_age_report import build_flock_age_report, known_total
from app.services.flock_current_report import day, effective_disposal_date, flock_is_in_current_report, quantity, text
from data.quota_types import quota_type_key
from decimal import Decimal, InvalidOperation

import pandas as pd

STATUS_COLUMNS = ['Reg No', 'Account', 'Permit No', 'Sold', 'Facility Name', 'Placement Date',
                  'Flock Age', 'Inventory', 'Quota', 'Hatch Date', 'Disp. Date', 'Up. Flocks', 'Util.']
COUNTED_COLUMNS = ['Reg No', 'Account Name', 'Quota', 'Flock Age', 'Permit No',
                   'Transaction Date', 'Inspector', 'Count Type', 'Birds Counted']
NEEDING_COLUMNS = ['Registration Number', 'Account Name', 'Permit No', 'Flock Age',
                  'Bird Count', 'Hatch Date', 'Placement Date', 'Disposal Date']
DISPOSAL_COLUMNS = ['Reg No', 'Account Name', 'Placement Date', 'Quota', 'Permit No',
                    'Disposal Age', 'Disposal Plant', 'Disposal Date', 'Placed', 'Disposed']
SALMONELLA_SCHEDULE_COLUMNS = ['Reg No', 'Account Name', 'Permit No', 'Flock Age',
                               'Inventory', 'Hatch Date']
PLACEMENT_COLUMNS = ['Reg No', 'Account Name', 'Start Date Age', 'End Date Age',
                     'Permit No', 'Facility', 'Placement', 'Hatch Date', 'Hatchery',
                     'Pullet Grower', 'Inventory', 'Quota', 'Total Producers',
                     'Total Flocks', 'Total Birds']


def _order(value):
    value = text(value)
    return (0, int(value)) if value.isdecimal() else (1, value.casefold())


def _display_date(value):
    value = day(value)
    return value.isoformat() if value else '—'


def _frame(rows, columns):
    result = pd.DataFrame(rows, columns=columns, dtype=object)
    return result.where(result.notna(), '—')


def _index(frame, key):
    if not frame.empty and (frame[key].isna().any() or frame[key].duplicated().any()):
        raise ValueError('Missing or duplicate report parent identity: ' + key)
    return {str(row[key]): row for row in frame.to_dict('records')}


def _matches_type(flock, quota_type):
    return quota_type == 'All' or quota_type_key(flock.get('FLOCK_QUOTA_TYPE')) == quota_type_key(quota_type)


def _range(start, end):
    start, end = day(start), day(end)
    if start is None or end is None:
        raise ValueError('Start and end dates are required.')
    if start > end:
        raise ValueError('Start date must be on or before end date.')
    return start, end


def _weeks(hatch, date):
    hatch, date = day(hatch), day(date)
    return (date - hatch).days // 7 if hatch and date else None


def _owner(flock, owners):
    identity = str(flock.get('ACCOUNT_ID'))
    owner = owners.get(identity, {})
    return identity, text(owner.get('REGISTRATION_NUMBER')) or '—', text(owner.get('ORGANIZATION_NAME')) or identity


def build_flock_status_report(flocks, transactions, accounts, facilities, quotas,
                              report_date, mortality='0.4', quota_type='Egg Production'):
    """Re-layout the shared Flock Age result; identical calculations/summary."""
    age, summary = build_flock_age_report(flocks, transactions, accounts, facilities,
                                         quotas, report_date, mortality, quota_type)
    groups, details = [], []
    for row in age.to_dict('records'):
        if row['Account'] == 'Total' and row['Permit No'] == '—':
            total = dict(row, **{'Permit No': 'Total', 'Account': details[0]['Account']})
            groups.append((row['Reg No'], [total, *sorted(details, key=lambda r: _order(r['Permit No']))]))
            details = []
        else:
            details.append(row)
    output = []
    for _, rows in sorted(groups, key=lambda group: _order(group[0])):
        output.extend(dict(row, Sold='', **{'Facility Name': row.get('Facility name', '—')}) for row in rows)
    return _frame(output, STATUS_COLUMNS), summary


def build_flock_salmonella_schedule(flocks, transactions, accounts, facilities,
                                    report_date, mortality='0.4', quota_type='Egg Production',
                                    minimum_age=19, maximum_age=255):
    """Flat Age-report rows with known Inventory; DEV_TEST is not special-cased."""
    _age_bounds(minimum_age, maximum_age)
    age, _summary = build_flock_age_report(flocks, transactions, accounts, facilities,
                                           {}, report_date, mortality, quota_type)
    output = []
    for row in age.to_dict('records'):
        if row['Account'] == 'Total' and row['Permit No'] == '—':
            continue
        age_value = row['Flock Age']
        if age_value == '—' or not minimum_age <= age_value <= maximum_age or row['Inventory'] == '—':
            continue
        output.append(dict(row, **{'Account Name': row['Account']}))
    output.sort(key=lambda row: (-row['Flock Age'], _order(row['Reg No']), _order(row['Permit No'])))
    return _frame(output, SALMONELLA_SCHEDULE_COLUMNS)


def _age_bounds(lower, upper):
    if (isinstance(lower, bool) or isinstance(upper, bool)
            or not isinstance(lower, int) or not isinstance(upper, int)
            or lower < 0 or lower > upper):
        raise ValueError('Age bounds must be non-negative integers with From Age <= To Age.')


def build_scheduled_flock_placements(flocks, transactions, accounts, facilities, quotas,
                                      start_date, end_date, mortality='0.4', quota_type='Egg Production'):
    """Initial quantities, without mortality. All recorded dated Deliveries are eligible.

    Conflicting latest Deliveries remain unknown; BIRD_COUNT is used only when
    no dated Delivery exists. Disposal is evaluated at the start date.
    """
    start, end = _range(start_date, end_date)
    try:
        rate = Decimal(str(mortality))
        valid = rate.is_finite() and rate >= 0
    except (InvalidOperation, ValueError):
        valid = False
    if not valid:
        raise ValueError('Mortality must be finite and non-negative.')
    _index(flocks, 'FLOCK_ID')
    owners, barns = _index(accounts, 'ACCOUNT_ID'), _index(facilities, 'FACILITY_ID')
    deliveries = {}
    for transaction in transactions.to_dict('records'):
        when = day(transaction.get('TRANSACTION_DATE'))
        if text(transaction.get('TRANSACTION_TYPE')) == 'Delivery' and when is not None:
            deliveries.setdefault(str(transaction.get('FLOCK_ID')), []).append((when, quantity(transaction.get('QUANTITY'))))
    groups = {}
    for flock in flocks.to_dict('records'):
        placement, disposal = day(flock.get('PLACEMENT_DATE')), effective_disposal_date(flock)
        if (text(flock.get('STATUS')).casefold() != 'active' or not _matches_type(flock, quota_type)
                or placement is None or not start <= placement <= end or (disposal and disposal <= start)):
            continue
        observations = deliveries.get(str(flock['FLOCK_ID']), [])
        inventory = quantity(flock.get('BIRD_COUNT'))
        if observations:
            latest = max(when for when, _ in observations)
            values = {value for when, value in observations if when == latest}
            inventory = next(iter(values)) if len(values) == 1 else None
        identity, registration, name = _owner(flock, owners)
        barn = barns.get(str(flock.get('FACILITY_ID')), {})
        groups.setdefault(identity, []).append({
            'Reg No': registration, 'Account Name': name,
            'Start Date Age': _weeks(flock.get('HATCH_DATE'), start),
            'End Date Age': _weeks(flock.get('HATCH_DATE'), end),
            'Permit No': text(flock.get('PERMIT_NUMBER')) or '—',
            'Facility': text(barn.get('FACILITY_NAME')) or '—',
            'Placement': placement.isoformat(), 'Hatch Date': _display_date(flock.get('HATCH_DATE')),
            'Hatchery': text(flock.get('HATCHERY')), 'Pullet Grower': text(flock.get('PULLET_GROWER')),
            'Inventory': inventory})
    output, birds, flock_count = [], [], 0
    for identity in sorted(groups, key=lambda key: (_order(groups[key][0]['Reg No']), key)):
        rows = sorted(groups[identity], key=lambda row: (row['Placement'], _order(row['Permit No'])))
        output.extend(rows)
        values = [row['Inventory'] for row in rows]
        birds.extend(values)
        flock_count += len(rows)
        output.append({'Reg No': rows[0]['Reg No'], 'Account Name': rows[0]['Account Name'],
                       'Permit No': 'TOTAL', 'Inventory': known_total(values),
                       'Quota': quantity(quotas.get(identity))})
    if output:
        output.append({'Account Name': 'GRAND TOTAL', 'Inventory': known_total(birds),
                       'Total Producers': len(groups), 'Total Flocks': flock_count,
                       'Total Birds': known_total(birds)})
    return _frame(output, PLACEMENT_COLUMNS)


def build_flocks_counted_report(flocks, transactions, accounts, quotas, start_date,
                                end_date, quota_type='Egg Production'):
    """One row per Count transaction; dates inclusive, no quantity deduplication."""
    start, end = _range(start_date, end_date)
    parents, owners = _index(flocks, 'FLOCK_ID'), _index(accounts, 'ACCOUNT_ID')
    output = []
    for transaction in transactions.to_dict('records'):
        flock = parents.get(str(transaction.get('FLOCK_ID')))
        if flock is None or not _matches_type(flock, quota_type):
            continue
        if any(text(flock.get(field)).upper().startswith('DEV_TEST') for field in ('FLOCK_NUMBER', 'PERMIT_NUMBER')):
            continue
        when = day(transaction.get('TRANSACTION_DATE'))
        if text(transaction.get('TRANSACTION_TYPE')) != 'Count' or when is None or not start <= when <= end:
            continue
        identity, registration, name = _owner(flock, owners)
        output.append(dict(zip(COUNTED_COLUMNS, [registration, name, quantity(quotas.get(identity)),
            _weeks(flock.get('HATCH_DATE'), when), text(flock.get('PERMIT_NUMBER')) or '—',
            when.isoformat(), '', text(transaction.get('COUNT_SOURCE_LABEL')),
            quantity(transaction.get('QUANTITY'))])))
    output.sort(key=lambda r: (_order(r['Reg No']), r['Flock Age'] is None,
                               r['Flock Age'] or 0, r['Transaction Date']))
    return _frame(output, COUNTED_COLUMNS)


def build_flocks_needing_counts_report(flocks, transactions, accounts, report_date,
                                       quota_type='Egg Production', from_age=19,
                                       to_age=299, count_type='All'):
    """Use Age inclusion plus placement/age scope; Deliveries never satisfy Count."""
    date = day(report_date)
    if date is None:
        raise ValueError('Report date is required.')
    _age_bounds(from_age, to_age)
    if count_type not in {'All', 'Board', 'Producer', 'EFC/CEMA'}:
        raise ValueError('Unknown Count Type.')
    _index(flocks, 'FLOCK_ID')
    owners = _index(accounts, 'ACCOUNT_ID')
    counted = set()
    for transaction in transactions.to_dict('records'):
        when = day(transaction.get('TRANSACTION_DATE'))
        if text(transaction.get('TRANSACTION_TYPE')) != 'Count' or when is None or when > date:
            continue
        label = text(transaction.get('COUNT_SOURCE_LABEL'))
        matches = (count_type == 'All' or label == count_type
                   or (count_type == 'EFC/CEMA' and label not in {'Producer', 'Board'}))
        if matches:
            counted.add(str(transaction.get('FLOCK_ID')))
    output = []
    for flock in flocks.to_dict('records'):
        if text(flock.get('FLOCK_QUOTA_TYPE')) == 'Special Permit' or not flock_is_in_current_report(flock, date, quota_type):
            continue
        placement, age = day(flock.get('PLACEMENT_DATE')), _weeks(flock.get('HATCH_DATE'), date)
        if placement is None or placement > date or age is None or not from_age <= age <= to_age:
            continue
        if str(flock['FLOCK_ID']) in counted:
            continue
        _, registration, name = _owner(flock, owners)
        output.append(dict(zip(NEEDING_COLUMNS, [registration, name,
            text(flock.get('PERMIT_NUMBER')) or '—', age, quantity(flock.get('BIRD_COUNT')),
            _display_date(flock.get('HATCH_DATE')), placement.isoformat(),
            _display_date(effective_disposal_date(flock))])))
    output.sort(key=lambda r: (_order(r['Registration Number']), _order(r['Permit No'])))
    return _frame(output, NEEDING_COLUMNS)


def provisional_disposal_age(hatch_date, disposal_date):
    """PROVISIONAL: whole elapsed weeks; NOT validated against legacy Disposal Age."""
    return _weeks(hatch_date, disposal_date)


def build_flock_disposals_report(flocks, accounts, quotas, start_date, end_date,
                                  quota_type='Egg Production'):
    """Actual disposal dates only, independent of current flock status/estimates."""
    start, end = _range(start_date, end_date)
    _index(flocks, 'FLOCK_ID')
    owners, groups = _index(accounts, 'ACCOUNT_ID'), {}
    for flock in flocks.to_dict('records'):
        disposal = day(flock.get('DISPOSAL_DATE'))
        if disposal is None or not start <= disposal <= end or not _matches_type(flock, quota_type):
            continue
        identity, registration, name = _owner(flock, owners)
        groups.setdefault(identity, []).append(dict(zip(DISPOSAL_COLUMNS, [
            registration, name, _display_date(flock.get('PLACEMENT_DATE')),
            quantity(quotas.get(identity)), text(flock.get('PERMIT_NUMBER')) or '—',
            provisional_disposal_age(flock.get('HATCH_DATE'), disposal),
            text(flock.get('DISPOSAL_PLANT')), disposal.isoformat(),
            quantity(flock.get('BIRD_COUNT')), quantity(flock.get('BIRDS_DISPOSED'))])))
    output = []
    for identity in sorted(groups, key=lambda key: (_order(groups[key][0]['Reg No']), key)):
        rows = sorted(groups[identity], key=lambda r: (r['Disposal Date'], _order(r['Permit No'])))
        output.extend(rows)
        total = {column: None for column in DISPOSAL_COLUMNS}
        total.update({'Reg No': rows[0]['Reg No'], 'Account Name': rows[0]['Account Name'],
                      'Permit No': 'Total', 'Quota': quantity(quotas.get(identity)),
                      'Placed': known_total([row['Placed'] for row in rows]),
                      'Disposed': known_total([row['Disposed'] for row in rows])})
        output.append(total)
    return _frame(output, DISPOSAL_COLUMNS)
