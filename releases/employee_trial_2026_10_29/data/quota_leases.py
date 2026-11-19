"""Pure, opt-in quota leases; legacy/null methods remain allocations."""
import datetime as dt
from decimal import Decimal
import pandas as pd

from data.position_evidence import day, guid, number, records
from data.producer_identity import text
from data.quota_types import quota_type_key

LEASE_END_DATE_INCLUSIVE = True
METHOD_FIELD = 'TRANSACTION_METHOD'


def is_lease(row):
    return (text(row.get(METHOD_FIELD)) or '').casefold() == 'lease'


def is_voided(row):
    return is_lease(row) and (text(row.get('LEASE_STATUS')) or '').casefold() == 'voided'


def lease_active(row, as_of):
    if is_voided(row):
        return False
    start,end,when = day(row.get('EFFECTIVE_DATE')),day(row.get('END_DATE')),day(as_of)
    if start is None or end is None or when is None:
        return False
    return start <= when and (when <= end if LEASE_END_DATE_INCLUSIVE else when < end)


def lease_effects(registrations, transactions, account_id, quota_type, as_of, inactive_ids):
    """New leases overlay snapshots; existing historical Lease types are untouched."""
    owner=guid(account_id);regs={guid(r.get('QUOTA_ID')):r for r in records(registrations)}
    inactive={guid(v) for v in inactive_ids or set()}
    total=Decimal(0);incoming=Decimal(0);adjustments={};reasons=[]
    for row in records(transactions):
        if not is_lease(row):continue
        identity=guid(row.get('_LEASE_SOURCE_ID')) or guid(row.get('QUOTA_TRANSACTION_ID'))
        if identity in inactive:continue
        lessor,lessee=guid(row.get('_LESSOR_ID')) or guid(row.get('OWNER_ACCOUNT_ID')),guid(row.get('_LESSEE_ID')) or guid(row.get('RELATED_ACCOUNT_ID'))
        if owner not in {lessor,lessee}:continue
        source=regs.get(guid(row.get('_LEASE_QUOTA_ID')) or guid(row.get('QUOTA_ID')), {})
        kind=quota_type_key(text(row.get('_LEASE_QUOTA_TYPE')) or source.get('QUOTA_TYPE'))
        if kind != quota_type_key(quota_type):continue
        if not lease_active(row,as_of):continue
        side=text(row.get('_LEASE_SIDE'))
        if side and guid(row.get('OWNER_ACCOUNT_ID')) != owner:continue
        value=number(row.get('QUOTA_COUNT'))
        if value is None or value<=0 or value!=value.to_integral_value() or lessor==lessee:
            reasons.append('Invalid stored lease parties or amount');continue
        own=[r for r in regs.values() if guid(r.get('ACCOUNT_ID'))==owner
             and quota_type_key(r.get('QUOTA_TYPE'))==kind and (text(r.get('STATUS')) or '').casefold()=='active']
        if not own:
            reasons.append('Lease account has no Active Registration for this Quota Type');continue
        signed=value if owner==lessee else -value
        total+=signed
        if signed>0:incoming+=signed
        adjustments[guid(row.get('QUOTA_TRANSACTION_ID'))]=signed
    return total,incoming,adjustments,reasons


def lease_input_errors(record, registrations):
    errors=[];regs={guid(r.get('QUOTA_ID')):r for r in records(registrations)}
    source=regs.get(guid(record.get('QUOTA_ID')), {})
    lessor,lessee=guid(record.get('OWNER_ACCOUNT_ID')),guid(record.get('RELATED_ACCOUNT_ID'))
    value=number(record.get('QUOTA_COUNT'));start,end=day(record.get('EFFECTIVE_DATE')),day(record.get('END_DATE'))
    if not lessor or not lessee or lessor==lessee:errors.append('Lessor and lessee must be different Accounts.')
    if value is None or value<=0 or value!=value.to_integral_value():errors.append('Lease amount must be a finite positive whole number of birds.')
    if start is None or end is None:errors.append('Lease Start Date and Quota End Date are required.')
    elif end<start:errors.append('Quota End Date must be on or after Start Date.')
    kind=quota_type_key(source.get('QUOTA_TYPE'))
    if guid(source.get('ACCOUNT_ID'))!=lessor or (text(source.get('STATUS')) or '').casefold()!='active':errors.append('Select an Active Quota Registration owned by the lessor.')
    if not any(guid(r.get('ACCOUNT_ID'))==lessee and quota_type_key(r.get('QUOTA_TYPE'))==kind
               and (text(r.get('STATUS')) or '').casefold()=='active' for r in regs.values()):
        errors.append('Lessee must have an Active Quota Registration of the same Quota Type.')
    return errors


def validate_lease_period(record, registrations, transactions, inactive_ids, rules):
    """Check every position-change boundary, not just the start/end snapshots."""
    errors=lease_input_errors(record,registrations)
    if errors:return errors
    from data.confirmed_quota_position import confirmed_quota_position
    start,end=day(record['EFFECTIVE_DATE']),day(record['END_DATE'])
    source=next(r for r in records(registrations) if guid(r.get('QUOTA_ID'))==guid(record['QUOTA_ID']))
    events={start,end}
    for row in records(transactions):
        effective=day(row.get('EFFECTIVE_DATE'));expires=day(row.get('END_DATE'))
        if effective and start<=effective<=end:events.add(effective)
        if expires and expires<end and expires>=start:events.add(expires+dt.timedelta(days=1))
    values=[]
    for when in sorted(events):
        position=confirmed_quota_position(registrations,transactions,record['OWNER_ACCOUNT_ID'],source['QUOTA_TYPE'],when,inactive_ids,rules)
        if position['net_position'] is None:return ['Available quota could not be verified for the whole lease period. Review quota evidence before saving.']
        values.append(position['net_position'])
    if number(record['QUOTA_COUNT'])>min(values):return ['Lease amount exceeds the lessor available quota during the lease period.']
    return []


def projected_lease_rows(registrations, transactions, as_of, range_start=None):
    """Read-only directions for reports. Expired/future new leases add no rows."""
    regs={guid(r.get('QUOTA_ID')):r for r in records(registrations)};output=[]
    for row in records(transactions):
        if not is_lease(row):output.append(row);continue
        observation = day(as_of)
        if range_start is not None:
            start = day(row.get('EFFECTIVE_DATE'))
            observation = max(day(range_start), start) if start is not None else None
            if observation is None or observation > day(as_of):continue
        if not lease_active(row,observation):continue
        source=regs.get(guid(row.get('QUOTA_ID')), {});kind=source.get('QUOTA_TYPE')
        base=dict(row,_LEASE_SOURCE_ID=row['QUOTA_TRANSACTION_ID'],_LEASE_QUOTA_ID=row['QUOTA_ID'],
                  _LESSOR_ID=row['OWNER_ACCOUNT_ID'],_LESSEE_ID=row['RELATED_ACCOUNT_ID'],_LEASE_QUOTA_TYPE=kind)
        output.append(dict(base,_LEASE_SIDE='out',TRANSACTION_TYPE='Lease (Out)'))
        output.append(dict(base,_LEASE_SIDE='in',QUOTA_TRANSACTION_ID=str(row['QUOTA_TRANSACTION_ID'])+':in',
            QUOTA_ID=None,OWNER_ACCOUNT_ID=row['RELATED_ACCOUNT_ID'],RELATED_ACCOUNT_ID=row['OWNER_ACCOUNT_ID'],TRANSACTION_TYPE='Lease (In)'))
    return pd.DataFrame(output) if output else transactions.iloc[:0].copy()
