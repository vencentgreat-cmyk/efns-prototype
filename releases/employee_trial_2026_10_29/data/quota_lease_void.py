"""One-way, audited lease correction inside the existing continuity boundary."""
import datetime as dt
import json
import pandas as pd

from data.business_time import version_bind
from data.confirmed_quota_position import confirmed_quota_position
from data.position_evidence import day, guid, records
from data.producer_identity import text
from data.quota_leases import is_lease, is_voided, validate_lease_period
from data.quota_position import load_rules
from data.quota_types import quota_type_filter
from data.record_safety import read_record, history_audit
from data.repositories.base import RepositoryError, ConcurrencyError
from data.source_evidence import evidence_json


def void_errors(target, registrations, transactions, inactive_ids, rules):
    """Reject newly negative balances or dependent commitments, past or future.

    Voiding is a correction for the whole original period, not early termination.
    Only the two parties' balances can change; other records remain untouched.
    """
    rows=records(transactions);identity=guid(target['QUOTA_TRANSACTION_ID'])
    after=[dict(row,LEASE_STATUS='Voided') if guid(row.get('QUOTA_TRANSACTION_ID'))==identity else row for row in rows]
    source=next((r for r in records(registrations) if guid(r.get('QUOTA_ID'))==guid(target.get('QUOTA_ID'))),None)
    start,end=day(target.get('EFFECTIVE_DATE')),day(target.get('END_DATE'))
    if source is None or start is None or end is None or start>end or inactive_ids is None:
        return ['The original lease and quota evidence could not be verified; it was not voided.']
    events={start,end}
    for row in rows:
        effective,expiry=day(row.get('EFFECTIVE_DATE')),day(row.get('END_DATE'))
        if effective and start<=effective<=end:events.add(effective)
        if expiry and start<=expiry<end:events.add(expiry+dt.timedelta(days=1))
    for owner in (target['OWNER_ACCOUNT_ID'],target['RELATED_ACCOUNT_ID']):
        for when in sorted(events):
            before=confirmed_quota_position(registrations,rows,owner,source['QUOTA_TYPE'],when,inactive_ids,rules)['net_position']
            updated=confirmed_quota_position(registrations,after,owner,source['QUOTA_TYPE'],when,inactive_ids,rules)['net_position']
            if before is None or updated is None:
                return ['Quota evidence is unavailable for the original lease period; the lease was not voided.']
            if updated<0 and updated<before:
                return ['This lease cannot be voided: another saved lease or transaction depends on its quota, leaving a negative quota position.']
    for row in rows:
        if (not is_lease(row) or is_voided(row) or guid(row.get('QUOTA_TRANSACTION_ID')) in {identity,*inactive_ids}
                or guid(row.get('OWNER_ACCOUNT_ID'))!=guid(target['RELATED_ACCOUNT_ID'])):
            continue
        first,last=day(row.get('EFFECTIVE_DATE')),day(row.get('END_DATE'))
        if first is None or last is None:
            return ['An onward lease has incomplete dates; review it before voiding this lease.']
        if first>end or last<start:continue
        remaining=[r for r in after if guid(r.get('QUOTA_TRANSACTION_ID'))!=guid(row['QUOTA_TRANSACTION_ID'])]
        if validate_lease_period(row,registrations,remaining,inactive_ids,rules):
            return ['This lease cannot be voided because a saved onward lease would no longer have verified available quota.']
    return []


def _evidence(repo,tx,target):
    if repo._is_memory:
        return repo.get_quota_registrations(),repo.get_quota_transactions(),set()
    source=tx.query(f"SELECT * FROM {repo._table('QUOTA_REGISTRATION')} WHERE QUOTA_ID=%s",(target['QUOTA_ID'],))
    if len(source)!=1:raise RepositoryError('The lease registration is missing or ambiguous.')
    aliases=quota_type_filter(source.iloc[0]['QUOTA_TYPE']);aliases=aliases if isinstance(aliases,tuple) else (aliases,)
    placeholders=','.join(['%s']*len(aliases))
    regs=tx.query(f"SELECT * FROM {repo._table('QUOTA_REGISTRATION')} WHERE QUOTA_TYPE IN ({placeholders})",aliases)
    activity=tx.query(f"SELECT qt.* FROM {repo._table('QUOTA_TRANSACTION')} qt JOIN {repo._table('QUOTA_REGISTRATION')} qr ON qr.QUOTA_ID=qt.QUOTA_ID WHERE qr.QUOTA_TYPE IN ({placeholders})",aliases)
    ids=sorted({guid(value).upper() for value in activity.get('QUOTA_TRANSACTION_ID',[]) if guid(value)})
    state_rows=tx.query('SELECT UPPER(TARGET_ID) AS TRANSACTION_ID, LOWER(TRIM(RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) AS TRANSACTION_STATE '
        f"FROM {repo._table('MIGRATION_RAW_ROW',repo.schema_raw)} WHERE SOURCE_ENTITY=%s AND UPPER(TARGET_ID) IN "
        '(SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))))',('QUOTA_TRANSACTION',json.dumps(ids)))
    states={}
    for row in state_rows.to_dict('records'):
        key,state=guid(row.get('TRANSACTION_ID')),guid(row.get('TRANSACTION_STATE'))
        if key is None or key.upper() not in ids or state not in {'active','inactive'}:
            raise RepositoryError('Quota state evidence is unavailable; the lease was not voided.')
        states.setdefault(key,set()).add(state)
    if any(len(value)!=1 for value in states.values()):raise RepositoryError('Quota state evidence is contradictory; the lease was not voided.')
    return regs,activity,{key for key,value in states.items() if value=={'inactive'}}


def void_lease(repo,transaction_id,reason,request_id,expected_updated_at,actor):
    from data.repositories.continuity import stable_id
    if not isinstance(actor,dict) or actor.get('role')!='Admin' or not text(actor.get('user_id')):
        raise RepositoryError('Only an application Admin can void a lease.')
    reason=text(reason)
    if not reason or len(reason)>2000 or not text(request_id):
        raise RepositoryError('A reason of 1 to 2,000 characters and request identity are required.')
    fingerprint=evidence_json(dict(id=transaction_id,reason=reason,actor=actor['user_id']))
    revision_id=stable_id('void-lease',transaction_id,request_id)
    with repo._continuity_transaction() as tx:
        before=read_record(repo,'QUOTA_TRANSACTION',transaction_id,tx)
        if before is None or not is_lease(before):
            raise RepositoryError('Only a saved new-method Lease can be voided; allocations and legacy lease rows are unchanged.')
        if 'LEASE_STATUS' not in before:
            raise RepositoryError('Lease void schema update is required; no changes were saved.')
        receipt=repo._history_rows('RECORD_REVISION','REVISION_ID',revision_id,tx)
        if not receipt.empty:
            saved=receipt.iloc[0]['AFTER_DATA'];saved=json.loads(saved) if isinstance(saved,str) else saved
            if len(receipt)!=1 or saved.get('_VOID_REQUEST')!=fingerprint or not is_voided(before):
                raise RepositoryError('The void receipt differs from this request; reload the saved record.')
            return transaction_id
        if is_voided(before):raise RepositoryError('This lease is already Voided. Create a new lease instead; voiding cannot be undone here.')
        if expected_updated_at is None or version_bind(before.get('UPDATED_AT'))!=version_bind(expected_updated_at):
            raise ConcurrencyError('The lease changed after review; reload before voiding.')
        regs,activity,inactive=_evidence(repo,tx,before)
        errors=void_errors(before,regs,activity,inactive,load_rules())
        if errors:raise RepositoryError(' '.join(errors))
        update=dict(QUOTA_TRANSACTION_ID=transaction_id,LEASE_STATUS='Voided',EXPECTED_UPDATED_AT=before['UPDATED_AT'])
        if repo._is_memory:repo._upsert_frame('_quota_transactions','QUOTA_TRANSACTION_ID',update)
        else:repo._upsert_with_executor(tx,'QUOTA_TRANSACTION',update)
        after=read_record(repo,'QUOTA_TRANSACTION',transaction_id,tx)
        if after is None or not is_voided(after):raise RepositoryError('Lease void could not be verified; the change was rolled back.')
        repo._append_history(tx,'RECORD_REVISION',dict(REVISION_ID=revision_id,ENTITY_TYPE='QUOTA_TRANSACTION',ENTITY_ID=transaction_id,
            CHANGE_KIND='Voided',BUSINESS_AT=None,RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),
            RECORDED_BY=actor['user_id'],REASON=reason,BEFORE_DATA=before,AFTER_DATA=dict(after,_VOID_REQUEST=fingerprint)))
        history_audit(repo,tx,'QUOTA_TRANSACTION',transaction_id,request_id,actor,reason,'Voided',before,after)
    return transaction_id
