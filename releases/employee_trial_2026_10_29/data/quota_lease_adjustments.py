"""Append-only lease changes in existing revision storage and atomic boundary."""
import datetime as dt
import json
from zoneinfo import ZoneInfo
import pandas as pd
from data.position_evidence import day, guid, number
from data.producer_identity import text
from data.quota_leases import is_lease, is_voided, effective_lease_amount, effective_lease_end
from data.record_safety import read_record, history_audit
from data.source_evidence import evidence_json
from data.business_time import version_bind
from data.repositories.base import RepositoryError, ConcurrencyError

ADJUSTMENT_KINDS = ('Ended early', 'Partial return')
LEASE_WRITER_ROLES = frozenset({'Admin', 'Data Editor', 'Developer'})


def get_adjustments(repo, transaction_ids, tx=None):
    """One bounded history read, not one query per lease; no new table/DDL."""
    ids = sorted({guid(value) for value in transaction_ids if guid(value)})
    result = {value: [] for value in ids}
    if not ids: return result
    if repo._is_memory:
        rows = [row for row in repo._continuity_rows['RECORD_REVISION']
                if row.get('ENTITY_TYPE') == 'QUOTA_TRANSACTION'
                and row.get('CHANGE_KIND') in ADJUSTMENT_KINDS and guid(row.get('ENTITY_ID')) in result]
    else:
        try:
            frame = (tx or repo._executor()).query(
                f"SELECT REVISION_ID, ENTITY_ID, AFTER_DATA FROM {repo._continuity_table('RECORD_REVISION')} "
                "WHERE ENTITY_TYPE=%s AND CHANGE_KIND IN (%s,%s) AND LOWER(ENTITY_ID) IN "
                "(SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))))",
                ('QUOTA_TRANSACTION', *ADJUSTMENT_KINDS, json.dumps(ids)))
            rows = frame.to_dict('records')
        except Exception as exc:
            raise RepositoryError('Lease adjustment history could not be verified; unadjusted quota was not assumed.') from exc
    seen = set()
    for row in rows:
        key = guid(row.get('ENTITY_ID')); revision = guid(row.get('REVISION_ID'))
        value = row.get('AFTER_DATA')
        try:
            value = json.loads(value) if isinstance(value,str) else value
            change = value['_LEASE_ADJUSTMENT']
            if key not in result or not revision or revision in seen or not isinstance(change,dict): raise ValueError()
            result[key].append(dict(change, ADJUSTMENT_ID=revision))
            seen.add(revision)
        except (ValueError,TypeError,KeyError) as exc:
            raise RepositoryError('Stored lease adjustment history is invalid; review the lease before calculating quota.') from exc
    return result


def attach_adjustments(repo, frame, tx=None):
    leases = [row for row in frame.to_dict('records') if is_lease(row)]
    if not leases: return frame
    found = get_adjustments(repo, [row['QUOTA_TRANSACTION_ID'] for row in leases], tx)
    result = frame.copy()
    result['_LEASE_ADJUSTMENTS'] = [found.get(guid(row.get('QUOTA_TRANSACTION_ID')), [])
                                    for row in frame.to_dict('records')]
    return result


def adjust_lease(repo, transaction_id, kind, adjustment_date, returned_amount, reason,
                 request_id, expected_updated_at, expected_adjustment_ids, actor,*,reports_confirmed=False):
    """Append history + audit together; original lease and lock code stay unchanged."""
    from data.repositories.continuity import stable_id
    if not isinstance(actor,dict) or actor.get('role') not in LEASE_WRITER_ROLES or not text(actor.get('user_id')):
        raise RepositoryError('Only Admin, Data Editor or Developer may adjust a lease.')
    reason=text(reason); when=day(adjustment_date)
    if kind not in ADJUSTMENT_KINDS or when is None or not reason or len(reason)>2000 or not text(request_id):
        raise RepositoryError('Choose a lease adjustment, valid date and reason of 1 to 2,000 characters.')
    amount=number(returned_amount) if kind=='Partial return' else None
    fingerprint=evidence_json(dict(id=transaction_id,kind=kind,date=when,amount=amount,reason=reason,actor=actor['user_id'],
        **({'reports_confirmed':True} if reports_confirmed is True else {})))
    revision=stable_id('lease-adjustment',transaction_id,request_id)
    with repo._continuity_transaction() as tx:
        before=read_record(repo,'QUOTA_TRANSACTION',transaction_id,tx)
        if before is None or not is_lease(before) or is_voided(before):
            raise RepositoryError('Only a saved, non-voided new-method lease can be adjusted.')
        receipt=repo._history_rows('RECORD_REVISION','REVISION_ID',revision,tx)
        if not receipt.empty:
            saved=receipt.iloc[0]['AFTER_DATA']; saved=json.loads(saved) if isinstance(saved,str) else saved
            if len(receipt)!=1 or saved.get('_LEASE_ADJUSTMENT_REQUEST')!=fingerprint:
                raise RepositoryError('This adjustment request was already used with different values. Reload the lease.')
            return transaction_id
        if expected_updated_at is None or version_bind(before.get('UPDATED_AT'))!=version_bind(expected_updated_at):
            raise ConcurrencyError('The lease changed after review; reload before adjusting it.')
        prior=get_adjustments(repo,[transaction_id],tx)[guid(transaction_id)]
        if expected_adjustment_ids is None or sorted(map(guid,expected_adjustment_ids))!=sorted(guid(v['ADJUSTMENT_ID']) for v in prior):
            raise ConcurrencyError('Lease adjustments changed after review; reload before saving.')
        target=dict(before,_LEASE_ADJUSTMENTS=prior)
        start=day(before.get('EFFECTIVE_DATE'))
        try: end=effective_lease_end(target)
        except ValueError as exc: raise RepositoryError('Lease adjustment evidence is invalid.') from exc
        if start is None or end is None: raise RepositoryError('The saved lease period is incomplete.')
        from data.lease_confirmation import report_change_confirmation
        confirmation=report_change_confirmation(when,reports_confirmed,actor)
        change=dict(KIND=kind)
        if kind=='Ended early':
            if not start<=when<end: raise RepositoryError('New Quota End Date must be on or after Start Date and before the current end date.')
            if any(day(item['EFFECTIVE_DATE'])>when for item in prior if item['KIND']=='Partial return'):
                raise RepositoryError('The end date cannot precede a previously recorded partial return.')
            change.update(EFFECTIVE_DATE=when+dt.timedelta(days=1),NEW_END_DATE=when)
        else:
            remaining=effective_lease_amount(target,when)
            if not start<when<=end or amount is None or amount!=amount.to_integral_value() or amount<1 or remaining is None or amount>remaining:
                raise RepositoryError('Return Date must be after Start Date within the lease period; return a positive whole amount no larger than the amount still leased.')
            if sum((number(item.get('RETURNED_AMOUNT')) or 0) for item in prior)+amount>number(before['QUOTA_COUNT']):
                raise RepositoryError('Total returned amount cannot exceed the original lease amount.')
            change.update(EFFECTIVE_DATE=when,RETURNED_AMOUNT=amount)
        before_view=dict(before,**{'Quota End Date':end,'Returned Amount':None,'Return Date':None})
        after_view=dict(before,**{'Quota End Date':when if kind=='Ended early' else end,
            'Returned Amount':amount,'Return Date':when if kind=='Partial return' else None},
            _LEASE_ADJUSTMENT=change,_LEASE_ADJUSTMENT_REQUEST=fingerprint)
        repo._append_history(tx,'RECORD_REVISION',dict(REVISION_ID=revision,ENTITY_TYPE='QUOTA_TRANSACTION',ENTITY_ID=transaction_id,
            CHANGE_KIND=kind,BUSINESS_AT=dt.datetime.combine(change['EFFECTIVE_DATE'],dt.time(),tzinfo=ZoneInfo('America/Halifax')).astimezone(dt.timezone.utc).replace(tzinfo=None),
            RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),RECORDED_BY=actor['user_id'],
            REASON=reason,BEFORE_DATA=before_view,AFTER_DATA=after_view))
        persisted=repo._history_rows('RECORD_REVISION','REVISION_ID',revision,tx)
        if len(persisted)!=1:
            raise RepositoryError('Mandatory lease adjustment history was not saved exactly once.')
        history_audit(repo,tx,'QUOTA_TRANSACTION',transaction_id,request_id,actor,reason,kind,before_view,after_view,
            report_change_confirmation=confirmation)
    return transaction_id
