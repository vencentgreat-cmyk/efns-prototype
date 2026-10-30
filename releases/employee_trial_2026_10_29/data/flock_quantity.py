"""Explicit current observations/removals, isolated from historical writers."""
import datetime as dt
from decimal import Decimal
from zoneinfo import ZoneInfo
import pandas as pd
from data.repositories.base import RepositoryError,ConcurrencyError
from data.repositories.continuity import stable_id,NOW
from data.source_evidence import evidence_json
from data.producer_identity import text
from data.validation import validate_flock_transaction
from data.business_time import advance_version_sql


def record_current_quantity(repo, record, request_id, expected_updated_at, reason, *, confirmed=False, actor=None, expected_bird_count=...):
    if not confirmed or not request_id or not str(reason or '').strip() or not actor or not actor.get('user_id') or not actor.get('email'):
        raise RepositoryError('An authenticated recorder, reason, request identity and current-quantity confirmation are required.')
    record=dict(record)
    if record.get('FLOCK_TRANSACTION_ID'):
        raise RepositoryError('Current quantity entry creates a new transaction; existing activity must not be reapplied.')
    errors=validate_flock_transaction(repo,record,current_count=True)
    if errors: raise RepositoryError(' '.join(errors))
    if record['TRANSACTION_TYPE'] not in ('Count','Removal'):
        raise RepositoryError('Only an explicit current Count or quantified Removal can update Bird Count. Delivery/Sale remain activity only.')
    record['QUANTITY']=int(Decimal(str(record['QUANTITY'])))
    business_date=pd.Timestamp(record['TRANSACTION_DATE']).date()
    from data.business_time import halifax_today,same_value,precise_version_sql
    if business_date != halifax_today():
        raise RepositoryError('Current quantity entry is limited to today (Halifax). Save historical activity without applying it to current Bird Count.')
    txid=stable_id('current-flock-quantity',request_id)
    revision_id=stable_id('current-flock-quantity-revision',txid)
    record['FLOCK_TRANSACTION_ID']=txid
    fingerprint=evidence_json(dict(record=record,reason=reason,actor=actor))
    with repo._continuity_transaction() as tx:
        if repo._is_memory:
            existing=repo._flock_transactions[repo._flock_transactions.FLOCK_TRANSACTION_ID==txid]
            current=repo.get_flock(record['FLOCK_ID'])
        else:
            existing=tx.query(precise_version_sql(f"SELECT * FROM {repo._table('FLOCK_TRANSACTION')} WHERE FLOCK_TRANSACTION_ID=%s"),(txid,))
            frames=tx.query(precise_version_sql(f"SELECT * FROM {repo._table('FLOCK')} WHERE FLOCK_ID=%s"),(record['FLOCK_ID'],))
            if len(frames)!=1: raise RepositoryError('Flock identity is missing or duplicated.')
            current=frames.iloc[0].to_dict()
        revisions=repo._history_rows('RECORD_REVISION','REVISION_ID',revision_id,tx)
        if not existing.empty or not revisions.empty:
            if len(existing)!=1 or len(revisions)!=1: raise RepositoryError('Quantity transaction/history is inconsistent; do not reapply.')
            saved=revisions.iloc[0].AFTER_DATA
            if isinstance(saved,str):
                import json
                saved=json.loads(saved)
            if saved.get('_QUANTITY_REQUEST')!=fingerprint: raise RepositoryError('This quantity request was already used with different values.')
            actual=existing.iloc[0]
            if any(text(actual.get(k))!=text(record.get(k)) for k in ('FLOCK_ID','TRANSACTION_TYPE','NOTES')) or Decimal(str(actual.QUANTITY))!=Decimal(str(record['QUANTITY'])) or pd.Timestamp(actual.TRANSACTION_DATE).date()!=business_date:
                raise RepositoryError('The original quantity activity was subsequently edited; inspect history, do not reapply it.')
            return txid
        if current is None: raise RepositoryError('Flock no longer exists.')
        if expected_updated_at is None or pd.Timestamp(current['UPDATED_AT'])!=pd.Timestamp(expected_updated_at):
            raise ConcurrencyError('Flock changed after review; reload current quantity.')
        old=current.get('BIRD_COUNT')
        if expected_bird_count is ...:
            raise RepositoryError('The Bird Count actually reviewed is required; reload and confirm again.')
        if not same_value(old,expected_bird_count):
            raise ConcurrencyError('Bird Count changed after review; reload and explicitly confirm the new value.')
        if old is None or pd.isna(old):
            if record['TRANSACTION_TYPE']=='Removal': raise RepositoryError('Cannot deduct a removal from an unknown Bird Count. Record a confirmed Count first.')
        quantity=int(record['QUANTITY'])
        new=quantity if record['TRANSACTION_TYPE']=='Count' else Decimal(str(old))-quantity
        if new<0: raise RepositoryError('Removal exceeds recorded current Bird Count; nothing was saved.')
        if repo._is_memory:
            repo._upsert_frame('_flock_transactions','FLOCK_TRANSACTION_ID',record)
            repo._upsert_frame('_flocks','FLOCK_ID',dict(FLOCK_ID=current['FLOCK_ID'],BIRD_COUNT=int(new),EXPECTED_UPDATED_AT=expected_updated_at))
            after=repo.get_flock(current['FLOCK_ID'])
            timestamp=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        else:
            repo._upsert_with_executor(tx,'FLOCK_TRANSACTION',record)
            # A string conversion keeps Snowflake NTZ nanoseconds; converting
            # pandas.Timestamp to Python datetime would silently truncate them.
            version=pd.Timestamp(expected_updated_at).tz_localize(None).isoformat()
            affected=tx.execute(f"UPDATE {repo._table('FLOCK')} SET BIRD_COUNT=%s,UPDATED_AT={advance_version_sql(NOW)} WHERE FLOCK_ID=%s AND UPDATED_AT=TO_TIMESTAMP_NTZ(%s) AND BIRD_COUNT IS NOT DISTINCT FROM %s",(int(new),current['FLOCK_ID'],version,old))
            if affected!=1: raise ConcurrencyError('Flock changed during quantity save; nothing may commit.')
            reread=tx.query(precise_version_sql(f"SELECT * FROM {repo._table('FLOCK')} WHERE FLOCK_ID=%s"),(current['FLOCK_ID'],))
            if len(reread)!=1 or reread.iloc[0].BIRD_COUNT!=new: raise RepositoryError('Quantity update could not be verified.')
            after=reread.iloc[0].to_dict()
            timestamp=pd.Timestamp(tx.query(f'SELECT {NOW} RECORDED_AT').iloc[0].RECORDED_AT).to_pydatetime()
        history_after=dict(after,_QUANTITY_REQUEST=fingerprint)
        repo._append_history(tx,'RECORD_REVISION',dict(REVISION_ID=revision_id,ENTITY_TYPE='FLOCK',ENTITY_ID=current['FLOCK_ID'],CHANGE_KIND='QUANTITY_ACTIVITY',BUSINESS_AT=None,RECORDED_AT=timestamp,RECORDED_BY=actor['email'],REASON=f"{record['TRANSACTION_TYPE']} {txid}; source date {business_date}; {reason}",BEFORE_DATA=current,AFTER_DATA=history_after))
        if len(repo._history_rows('RECORD_REVISION','REVISION_ID',revision_id,tx))!=1:
            raise RepositoryError('Quantity revision was not saved exactly once.')
        audit=dict(AUDIT_ID=stable_id('current-flock-quantity-audit',txid),ACTOR_USER_ID=actor['user_id'],ACTOR_EMAIL=actor['email'],ACTION='UPDATE',ENTITY_TYPE='FLOCK',ENTITY_ID=current['FLOCK_ID'],DETAILS={'transaction_id':txid,'revision_id':revision_id,'reason':reason,'old_bird_count':old,'new_bird_count':int(new)},OCCURRED_AT=dt.datetime.now(dt.timezone.utc))
        if repo._is_memory:
            repo._review_insert(tx,'AUDIT_EVENT',audit)
        else:
            params=tuple(evidence_json(v) if k=='DETAILS' else v for k,v in audit.items() if k!='OCCURRED_AT')
            if tx.execute(f"INSERT INTO {repo.database}.APP.AUDIT_EVENT (AUDIT_ID,ACTOR_USER_ID,ACTOR_EMAIL,ACTION,ENTITY_TYPE,ENTITY_ID,DETAILS,OCCURRED_AT) SELECT %s,%s,%s,%s,%s,%s,PARSE_JSON(%s),CONVERT_TIMEZONE('UTC',CURRENT_TIMESTAMP())",params)!=1:
                raise RepositoryError('Quantity audit was not saved exactly once.')
        return txid
