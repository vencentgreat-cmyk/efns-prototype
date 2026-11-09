"""Pure read-only quota report projections. No repository or Streamlit access."""
from decimal import Decimal

import pandas as pd

from data.confirmed_quota_position import confirmed_quota_position, EXCLUDED
from data.position_evidence import day, guid, known_sum, number
from data.producer_identity import text
from data.quota_types import quota_type_key

TRANSACTION_COLUMNS = ['Reg No', 'Account Name', 'Transaction Date', 'Quota End Date',
    'Related Reg No', 'Related Account Name', 'Quota Transaction Type', 'Bird Count']
LEASE_COLUMNS = ['Reg No', 'Account Name', 'Related Reg No', 'Related Account Name',
    'Comments', 'Transaction Date', 'Quota End Date', 'Price', 'Bird Count']
HISTORY_COLUMNS = ['Reg No', 'Account Name', 'Transaction Date', 'Quota End Date',
    'Quota Transaction Type', 'Related Reg No', 'Related Account Name', 'Comments',
    'Bird Count', 'Quota Count Adjust', 'Running Balance', 'Current Quota']
LEASE_TYPES = {'Lease (In)', 'Lease (Out)'}
TRADING_TYPES = {*LEASE_TYPES, 'Sale', 'Purchase'}


def _text(value):
    return text(value) or ''


def _date(value):
    value = day(value)
    return value.strftime('%d/%m/%Y') if value else ''


def _required_date(value):
    value = day(value)
    if value is None:
        raise ValueError('A valid report date is required.')
    return value


def _kind(row):
    value = _text(row.get('TRANSACTION_TYPE'))
    return {'Lease In':'Lease (In)', 'Lease Out':'Lease (Out)'}.get(value, value)


def _order(value):
    value = _text(value)
    return (0, Decimal(value)) if value.isdecimal() else (1, value.casefold()) if value else (2, '')


def _test(row, fields):
    return any(_text(row.get(field)).upper().startswith('DEV_TEST') for field in fields)


def _index(frame, field):
    rows = frame.to_dict('records')
    ids = [guid(row.get(field)) for row in rows]
    if None in ids or len(set(ids)) != len(ids):
        raise ValueError('Missing or duplicate report identity: ' + field)
    return dict(zip(ids, rows))


def _sources(accounts, registrations, transactions, inactive_ids, quota_type, *, active_registrations=True):
    """No date restriction on registrations. Preserve each stored transaction.

    Explicit DEV_TEST prefixes on identities, names, numbers or Comments mark
    test data. Related test Accounts are excluded too. Missing state evidence
    cannot establish Active rows: no report rows are produced in that case.
    """
    owners = _index(accounts, 'ACCOUNT_ID')
    all_owner_ids = set(owners)
    regs = _index(registrations, 'QUOTA_ID')
    _index(transactions, 'QUOTA_TRANSACTION_ID')
    owners = {key:row for key,row in owners.items() if not _test(row,
        ('ACCOUNT_ID','ORGANIZATION_NAME','REGISTRATION_NUMBER'))}
    regs = {key:row for key,row in regs.items()
        if quota_type_key(row.get('QUOTA_TYPE')) == quota_type_key(quota_type)
        and guid(row.get('ACCOUNT_ID')) in owners
        and not _test(row, ('QUOTA_ID','QUOTA_NAME','REGISTRATION_NUMBER','COMMENTS'))
        and (not active_registrations or _text(row.get('STATUS')).casefold() == 'active')}
    if inactive_ids is None:
        return owners, regs, [], ['Transaction state evidence unavailable; Active transactions cannot be established.']
    inactive = {guid(identity) for identity in inactive_ids}
    rows, notes = [], []
    for row in transactions.to_dict('records'):
        registration = regs.get(guid(row.get('QUOTA_ID')))
        owner = guid(row.get('OWNER_ACCOUNT_ID'))
        related = guid(row.get('RELATED_ACCOUNT_ID'))
        if (registration is None or owner != guid(registration.get('ACCOUNT_ID')) or owner not in owners
                or guid(row.get('QUOTA_TRANSACTION_ID')) in inactive
                or _test(row, ('QUOTA_TRANSACTION_ID','COMMENTS'))):
            continue
        if related is not None and related not in owners and related in all_owner_ids:
            continue  # Explicitly marked test counterparty.
        if day(row.get('EFFECTIVE_DATE')) is None:
            notes.append('Invalid Transaction Date: ' + _text(row.get('QUOTA_TRANSACTION_ID')))
        if _text(row.get('END_DATE')) and day(row.get('END_DATE')) is None:
            notes.append('Invalid Quota End Date: ' + _text(row.get('QUOTA_TRANSACTION_ID')))
        if number(row.get('QUOTA_COUNT')) is None:
            notes.append('Unknown Bird Count: ' + _text(row.get('QUOTA_TRANSACTION_ID')))
        rows.append(row)
    return owners, regs, rows, list(dict.fromkeys(notes))


def _row(transaction, owners):
    owner = owners.get(guid(transaction.get('OWNER_ACCOUNT_ID')), {})
    related = owners.get(guid(transaction.get('RELATED_ACCOUNT_ID')), {})
    return {'Reg No':_text(owner.get('REGISTRATION_NUMBER')), 'Account Name':_text(owner.get('ORGANIZATION_NAME')),
        'Transaction Date':_date(transaction.get('EFFECTIVE_DATE')), 'Quota End Date':_date(transaction.get('END_DATE')),
        'Related Reg No':_text(related.get('REGISTRATION_NUMBER')), 'Related Account Name':_text(related.get('ORGANIZATION_NAME')),
        'Quota Transaction Type':_kind(transaction), 'Bird Count':number(transaction.get('QUOTA_COUNT')),
        'Price':number(transaction.get('PRICE')), 'Comments':_text(transaction.get('COMMENTS'))}


def _frame(rows, columns):
    result = pd.DataFrame(rows, columns=columns, dtype=object)
    return result.where(result.notna(), '')


def _metadata(header, notes, **values):
    return dict(header=header, notes=list(dict.fromkeys(notes)), **values)


def build_quota_transactions_report(accounts, registrations, transactions, inactive_transaction_ids,
                                    start_date, end_date, quota_type='Egg Production'):
    start, end = _required_date(start_date), _required_date(end_date)
    if start > end:
        raise ValueError('Start Date must be on or before End Date.')
    owners, _regs, source, notes = _sources(accounts, registrations, transactions, inactive_transaction_ids, quota_type)
    rows = []
    for transaction in source:
        when, until, kind = day(transaction.get('EFFECTIVE_DATE')), day(transaction.get('END_DATE')), _kind(transaction)
        if kind not in TRADING_TYPES or when is None:
            continue
        overlaps = kind in LEASE_TYPES and when <= end and (not _text(transaction.get('END_DATE')) or (until is not None and until >= start))
        if start <= when <= end or overlaps:
            rows.append((transaction, _row(transaction, owners)))
    rows.sort(key=lambda item: (_order(item[1]['Reg No']), item[1]['Quota Transaction Type'],
        day(item[0].get('EFFECTIVE_DATE')), guid(item[0].get('QUOTA_TRANSACTION_ID'))))
    return _frame([row for _,row in rows], TRANSACTION_COLUMNS), _metadata(
        f'For {quota_type} as of {_date(start)} to {_date(end)}', notes)


def build_quota_leases_report(accounts, registrations, transactions, inactive_transaction_ids,
                              as_of_date, quota_type='Egg Production', *, by_end_date=False):
    as_of = _required_date(as_of_date)
    owners, _regs, source, notes = _sources(accounts, registrations, transactions, inactive_transaction_ids, quota_type)
    rows, missing = [], 0
    for transaction in source:
        if _kind(transaction) != 'Lease (Out)':
            continue
        end = day(transaction.get('END_DATE'))
        if _text(transaction.get('END_DATE')) and end is None:
            notes.append('Invalid Quota End Date: ' + _text(transaction.get('QUOTA_TRANSACTION_ID')))
            continue
        if end is not None and end < as_of:
            continue
        missing += end is None
        rows.append((transaction, _row(transaction, owners)))
    def order(item):
        transaction, row = item
        base = (_order(row['Reg No']), day(transaction.get('EFFECTIVE_DATE')) or as_of,
                guid(transaction.get('QUOTA_TRANSACTION_ID')))
        end = day(transaction.get('END_DATE'))
        return ((end is None, -end.toordinal() if end else 0, *base) if by_end_date else base)
    rows.sort(key=order)
    output = [row for _,row in rows]
    total = known_sum([row['Bird Count'] for row in output])
    if output:
        output.append({'Account Name':'Total Bird Count', 'Bird Count':total})
    notes.append(f'{missing} lease(s) with no Quota End Date included.')
    if any(row['Bird Count'] is None for _,row in rows):
        notes.append('Total Bird Count sums known quantities only.')
    columns = ['Quota End Date', *[column for column in LEASE_COLUMNS if column != 'Quota End Date']] if by_end_date else LEASE_COLUMNS
    return _frame(output, columns), _metadata(f'For {quota_type} as of {_date(as_of)}', notes, total_birds=total)


def build_quota_history_report(accounts, registrations, transactions, inactive_transaction_ids,
                               as_of_date, quota_type='Egg Production', account_id=None, *, rules):
    as_of = _required_date(as_of_date)
    owners, regs, source, notes = _sources(accounts, registrations, transactions, inactive_transaction_ids,
                                          quota_type, active_registrations=True)
    groups = {}
    for transaction in source:
        owner, when = guid(transaction.get('OWNER_ACCOUNT_ID')), day(transaction.get('EFFECTIVE_DATE'))
        if (account_id is not None and owner != guid(account_id)) or _kind(transaction) in EXCLUDED:
            continue
        if when is not None and when <= as_of:
            groups.setdefault(owner, []).append(transaction)
    output = []
    for owner in sorted(groups, key=lambda identity: (_order(owners[identity].get('REGISTRATION_NUMBER')), identity)):
        rows = groups[owner]
        def order(transaction):
            stamp = pd.to_datetime(transaction.get('CREATED_AT'), utc=True, errors='coerce')
            return (day(transaction.get('EFFECTIVE_DATE')), pd.isna(stamp),
                    stamp if pd.notna(stamp) else pd.Timestamp(0, tz='UTC'), guid(transaction.get('QUOTA_TRANSACTION_ID')))
        rows.sort(key=order)
        position = confirmed_quota_position(pd.DataFrame(list(regs.values())), pd.DataFrame(source),
            owner, quota_type, as_of, inactive_transaction_ids, rules)
        if position['reasons']:
            notes.append((_text(owners[owner].get('REGISTRATION_NUMBER')) or owner) + ': ' + '; '.join(position['reasons']))
        running = number(0) if position['net_position'] is not None else None
        for transaction in rows:
            adjustments = position['transaction_adjustments']
            adjust = adjustments.get(guid(transaction.get('QUOTA_TRANSACTION_ID')), number(0)) if adjustments is not None else None
            if running is not None:
                running += adjust
            row = _row(transaction, owners)
            row.update({'Quota Count Adjust':adjust, 'Running Balance':running, 'Current Quota':position['net_position']})
            output.append(row)
    return _frame(output, HISTORY_COLUMNS), _metadata(f'For {quota_type} as of {_date(as_of)}', notes)
