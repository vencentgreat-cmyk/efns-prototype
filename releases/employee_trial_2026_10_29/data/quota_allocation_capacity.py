"""Manual Allocation changes protect existing outgoing leases under their owning tx."""
import datetime as dt
import json
import uuid
import pandas as pd
from data.business_time import same_value
from data.position_evidence import day, guid, records
from data.producer_identity import text
from data.quota_types import quota_type_key, quota_type_filter
from data.quota_leases import (is_lease, is_voided, lease_adjustments,
    effective_lease_end, own_quota_capacity_rows)
from data.confirmed_quota_position import confirmed_quota_position
from data.quota_position import load_rules
from data.repositories.base import RepositoryError

CAPACITY_FIELDS = ('QUOTA_ID','OWNER_ACCOUNT_ID','TRANSACTION_TYPE','QUOTA_COUNT',
                   'EFFECTIVE_DATE','END_DATE','TRANSACTION_METHOD')


def _evidence(repo, tx, reference):
    """Read only this owner's type, using the already-owned continuity executor.

    Legacy-only installations need no RAW state/history read. Missing RAW rows
    mean Active, as in existing lease creation; contradictory evidence fails closed.
    """
    if repo._is_memory:
        registrations=repo.get_quota_registrations()
        source=[row for row in records(registrations) if guid(row.get('QUOTA_ID'))==guid(reference.get('QUOTA_ID'))]
    else:
        source=records(tx.query(f"SELECT * FROM {repo._table('QUOTA_REGISTRATION')} WHERE QUOTA_ID=%s",(reference.get('QUOTA_ID'),)))
    if len(source)!=1:raise RepositoryError('Allocation capacity requires an unambiguous Quota Registration.')
    owner=source[0]['ACCOUNT_ID'];kind=quota_type_key(source[0].get('QUOTA_TYPE'))
    if repo._is_memory:
        activity=repo._quota_transactions.copy()
    else:
        aliases=quota_type_filter(kind);aliases=aliases if isinstance(aliases,tuple) else (aliases,)
        slots=','.join(['%s']*len(aliases))
        registrations=tx.query(f"SELECT * FROM {repo._table('QUOTA_REGISTRATION')} WHERE QUOTA_TYPE IN ({slots})",aliases)
        activity=tx.query(f"SELECT qt.* FROM {repo._table('QUOTA_TRANSACTION')} qt JOIN {repo._table('QUOTA_REGISTRATION')} qr ON qr.QUOTA_ID=qt.QUOTA_ID "
            f"WHERE qt.OWNER_ACCOUNT_ID=%s AND qr.QUOTA_TYPE IN ({slots})",(owner,*aliases))
    registry={guid(row.get('QUOTA_ID')):row for row in records(registrations)}
    rows=[row for row in records(activity) if guid(row.get('OWNER_ACCOUNT_ID'))==guid(owner)
        and quota_type_key(registry.get(guid(row.get('QUOTA_ID')),{}).get('QUOTA_TYPE'))==kind]
    if not any(is_lease(row) and not is_voided(row) for row in rows):return None
    rows=own_quota_capacity_rows(rows,owner)
    inactive=set()
    if not repo._is_memory:
        ids=sorted({guid(row.get('QUOTA_TRANSACTION_ID')).upper() for row in rows if guid(row.get('QUOTA_TRANSACTION_ID'))})
        states=tx.query('SELECT UPPER(TARGET_ID) AS TRANSACTION_ID, LOWER(TRIM(RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) AS TRANSACTION_STATE '
            f"FROM {repo._table('MIGRATION_RAW_ROW',repo.schema_raw)} WHERE SOURCE_ENTITY=%s AND UPPER(TARGET_ID) IN "
            '(SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))))',('QUOTA_TRANSACTION',json.dumps(ids)))
        found={}
        for row in records(states):
            key,state=guid(row.get('TRANSACTION_ID')),guid(row.get('TRANSACTION_STATE'))
            if not key or key.upper() not in ids or state not in {'active','inactive'}:
                raise RepositoryError('Quota state evidence could not be verified; the Allocation was not saved.')
            found.setdefault(key,set()).add(state)
        if any(len(values)!=1 for values in found.values()):
            raise RepositoryError('Quota state evidence is contradictory; the Allocation was not saved.')
        inactive={key for key,values in found.items() if values=={'inactive'}}
    from data.quota_lease_adjustments import attach_adjustments
    activity=attach_adjustments(repo,pd.DataFrame(rows),tx)
    return registrations,activity,inactive,owner,kind


def allocation_capacity_error(registrations, activity, inactive_ids, owner, kind, before, after):
    """Sweep exact change boundaries, equivalent to checking every covered day."""
    registry={guid(row.get('QUOTA_ID')):row for row in records(registrations)}
    identity=guid((before or after or {}).get('QUOTA_TRANSACTION_ID'))
    prospective=[row for row in records(activity) if identity is None or guid(row.get('QUOTA_TRANSACTION_ID'))!=identity]
    if after is not None:
        proposal=dict(before or {},**after)
        if not guid(proposal.get('QUOTA_TRANSACTION_ID')):proposal['QUOTA_TRANSACTION_ID']=str(uuid.uuid4())
        parent=registry.get(guid(proposal.get('QUOTA_ID')))
        if parent:proposal['OWNER_ACCOUNT_ID']=parent.get('ACCOUNT_ID')
        if before is None:proposal['CREATED_AT']=dt.datetime.now(dt.timezone.utc)
        prospective.append(proposal)
    periods=[]
    for row in prospective:
        if (not is_lease(row) or is_voided(row) or guid(row.get('QUOTA_TRANSACTION_ID')) in inactive_ids
                or guid(row.get('OWNER_ACCOUNT_ID'))!=guid(owner)
                or quota_type_key(registry.get(guid(row.get('QUOTA_ID')),{}).get('QUOTA_TYPE'))!=kind):continue
        start=day(row.get('EFFECTIVE_DATE'))
        try:end=effective_lease_end(row)
        except ValueError:raise RepositoryError('Outgoing lease adjustment evidence is invalid; review the lease before changing its Allocation.')
        if start is None or end is None or start>end:
            raise RepositoryError('Outgoing lease dates are incomplete; review the lease before changing its Allocation.')
        periods.append((start,end,text(row.get('QUOTA_TRANSACTION_ID')) or 'unknown lease'))
    if not periods:return None
    last=max(end for _,end,_ in periods)
    events={value for start,end,_ in periods for value in (start,end)}
    capacity_rows=own_quota_capacity_rows(prospective,owner)
    for row in capacity_rows:
        effective,expiry=day(row.get('EFFECTIVE_DATE')),day(row.get('END_DATE'))
        if effective:events.add(effective)
        if expiry and expiry<last:events.add(expiry+dt.timedelta(days=1))
        if is_lease(row):
            try:events.update(change['EFFECTIVE_DATE'] for change in lease_adjustments(row))
            except ValueError:raise RepositoryError('Outgoing lease adjustment evidence is invalid; Allocation capacity is unavailable.')
    for when in sorted(events):
        leases=[identity for start,end,identity in periods if start<=when<=end]
        if not leases:continue
        position=confirmed_quota_position(registrations,capacity_rows,owner,kind,when,inactive_ids,load_rules())['net_position']
        if position is None:
            return f'Available own quota could not be verified on {when} for lease(s) {", ".join(leases)}. Review the evidence or end, reduce or void the lease first.'
        if position<0:
            return f'Cannot save Allocation: {when} has a shortfall of {-position} birds for lease(s) {", ".join(leases)}. End, reduce or void the lease first.'
    return None


def guard_allocation_change(repo, tx, before, after):
    if is_lease(before or {}) or is_lease(after or {}):return
    if before is not None and after is not None and all(same_value(before.get(key),after.get(key)) for key in CAPACITY_FIELDS):return
    checked=set()
    for reference in (before,after):
        if reference is None:continue
        evidence=_evidence(repo,tx,reference)
        if evidence is None:continue
        registrations,activity,inactive,owner,kind=evidence
        key=(guid(owner),kind)
        if key in checked:continue
        checked.add(key)
        error=allocation_capacity_error(registrations,activity,inactive,owner,kind,before,after)
        if error:raise RepositoryError(error)
