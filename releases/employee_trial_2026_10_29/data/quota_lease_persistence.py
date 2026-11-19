"""New quota-lease writes only; reuse the existing continuity transaction unchanged."""
import json
from data.position_evidence import guid
from data.quota_position import load_rules
from data.quota_types import quota_type_filter
from data.repositories.base import RepositoryError
from data.quota_leases import is_lease, validate_lease_period

IMMUTABLE_LEASE = 'Saved leases cannot be edited or deleted until early termination and correction rules are approved.'


def reject_saved_lease(repo, record_id):
    if record_id:
        stored=repo.get_quota_transaction(record_id)
        if stored and is_lease(stored):raise RepositoryError(IMMUTABLE_LEASE)


def save_new_lease(repo, record):
    """Check capacity and persist one audited deal under the existing global lock.

    Employee create_record_once owns history/idempotency. Nested calls join its
    continuity transaction; direct new-lease writes acquire the same boundary.
    Every Snowflake validation read explicitly uses the owning tx executor.
    """
    with repo._continuity_transaction() as tx:
        identity=record.get('QUOTA_TRANSACTION_ID')
        if repo._is_memory:
            if identity and repo.get_quota_transaction(identity):raise RepositoryError(IMMUTABLE_LEASE)
            regs=repo.get_quota_registrations();activity=repo.get_quota_transactions();inactive=set()
            if repo.get_account(record.get('OWNER_ACCOUNT_ID')) is None or repo.get_account(record.get('RELATED_ACCOUNT_ID')) is None:
                raise RepositoryError('Lessor and lessee must refer to existing Accounts.')
        else:
            if identity and not tx.query(f"SELECT QUOTA_TRANSACTION_ID FROM {repo._table('QUOTA_TRANSACTION')} WHERE QUOTA_TRANSACTION_ID=%s",(identity,)).empty:
                raise RepositoryError('A lease must be a new transaction.')
            source=tx.query(f"SELECT * FROM {repo._table('QUOTA_REGISTRATION')} WHERE QUOTA_ID=%s",(record.get('QUOTA_ID'),))
            if len(source)!=1:raise RepositoryError('Select an unambiguous Quota Registration.')
            aliases=quota_type_filter(source.iloc[0]['QUOTA_TYPE']);aliases=aliases if isinstance(aliases,tuple) else (aliases,)
            placeholders=', '.join(['%s']*len(aliases))
            regs=tx.query(f"SELECT * FROM {repo._table('QUOTA_REGISTRATION')} WHERE QUOTA_TYPE IN ({placeholders})",aliases)
            activity=tx.query(f"SELECT * FROM {repo._table('QUOTA_TRANSACTION')} WHERE OWNER_ACCOUNT_ID=%s OR RELATED_ACCOUNT_ID=%s",(record.get('OWNER_ACCOUNT_ID'),record.get('OWNER_ACCOUNT_ID')))
            if 'TRANSACTION_METHOD' not in activity.columns:
                raise RepositoryError('Lease entry requires the reviewed quota-method schema update. No lease was saved.')
            parents=tx.query(f"SELECT ACCOUNT_ID FROM {repo._table('ACCOUNT')} WHERE ACCOUNT_ID IN (%s,%s)",(record.get('OWNER_ACCOUNT_ID'),record.get('RELATED_ACCOUNT_ID')))
            if {guid(value) for value in parents.get('ACCOUNT_ID',[])}!={guid(record.get('OWNER_ACCOUNT_ID')),guid(record.get('RELATED_ACCOUNT_ID'))}:
                raise RepositoryError('Lessor and lessee must refer to existing Accounts.')
            ids=sorted({guid(v).upper() for v in activity.get('QUOTA_TRANSACTION_ID',[]) if guid(v)})
            states=tx.query('SELECT UPPER(TARGET_ID) AS TRANSACTION_ID, LOWER(TRIM(RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) AS TRANSACTION_STATE '
                f"FROM {repo._table('MIGRATION_RAW_ROW',repo.schema_raw)} WHERE SOURCE_ENTITY=%s AND UPPER(TARGET_ID) IN "
                '(SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))))',('QUOTA_TRANSACTION',json.dumps(ids)))
            evidence={};inactive=set()
            for row in states.to_dict('records'):
                key,state=guid(row.get('TRANSACTION_ID')),guid(row.get('TRANSACTION_STATE'))
                if key is None or key.upper() not in ids or state not in {'active','inactive'}:
                    raise RepositoryError('Quota state evidence is unavailable; no lease was saved.')
                evidence.setdefault(key,set()).add(state)
            if any(len(v)!=1 for v in evidence.values()):raise RepositoryError('Quota state evidence is contradictory; no lease was saved.')
            inactive={key for key,values in evidence.items() if values=={'inactive'}}
        if record.get('TRANSACTION_TYPE')!='Lease (Out)':raise RepositoryError('A new lease must be recorded from the lessor as Leased out.')
        errors=validate_lease_period(record,regs,activity,inactive,load_rules())
        if errors:raise RepositoryError(' '.join(errors))
        stored={**record,'TRANSACTION_METHOD':'Lease'}
        if repo._is_memory:return repo._upsert_frame('_quota_transactions','QUOTA_TRANSACTION_ID',stored)
        return repo._upsert_with_executor(tx,'QUOTA_TRANSACTION',stored)
