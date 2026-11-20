"""Atomic production replacement persistence; owned by the repository layer."""
from contextlib import contextmanager
import copy
import datetime as dt
import json
import uuid
import pandas as pd
from data.producer_identity import text
from data.position_evidence import guid
from data.source_evidence import evidence_json
from data.repositories.base import RepositoryError, ConcurrencyError
from data.production_replacement import BACKUP_TABLE, SUMMARY_KEY, producer_week

def _table(repo):
    return f'{repo.database}.{repo.schema_raw}.{BACKUP_TABLE}'


def get_backups(repo, import_id):
    if not text(import_id):
        raise RepositoryError('Import Batch ID is required.')
    if repo._is_memory:
        return pd.DataFrame([copy.deepcopy(row) for row in repo._continuity_rows.get(BACKUP_TABLE, []) if row['IMPORT_ID']==import_id])
    try:
        return repo._query(f'SELECT * FROM {_table(repo)} WHERE IMPORT_ID=%s ORDER BY SOURCE_WEEK_CODE, PRODUCER_ACCOUNT_ID, PRODUCTION_ID', (import_id,))
    except Exception as exc:
        raise RepositoryError('Replacement backup table is unavailable. Review the production backup schema update and access grants.') from exc


def get_summary(repo, import_id):
    if not text(import_id):
        raise RepositoryError('Import Batch ID is required.')
    if repo._is_memory:
        rows = [r for r in repo._import_batches if r['IMPORT_ID']==import_id]
    else:
        rows = repo._query(f"SELECT NOTES FROM {repo._table('IMPORT_BATCH', repo.schema_raw)} WHERE IMPORT_ID=%s", (import_id,)).to_dict('records')
    if len(rows)!=1:
        raise RepositoryError('Import Batch was not found or is ambiguous.')
    try:
        return json.loads(rows[0].get('NOTES') or '{}').get(SUMMARY_KEY, {})
    except (TypeError, ValueError):
        return {}


@contextmanager
def replace_sets(repo, tx, records, accounts, import_id, actor):
    """Backup/delete before yielding to the existing insert and batch finalization.

    The existing memory transaction snapshots production/history. Its size-child
    frame needs this scoped rollback copy; the lock implementation is untouched.
    """
    keys = {producer_week(row,accounts) for row in records.to_dict('records')}
    if any(owner is None or week is None for owner,week in keys):
        raise RepositoryError('Producer and production week must be established for every uploaded row.')
    if repo._is_memory:
        candidates = repo._production.copy(deep=True)
        total_before = len(candidates)
    else:
        owners = sorted({owner for owner,_ in keys})
        tokens = {text(row.get('PRODUCER_NUMBER')) for row in records.to_dict('records')}
        for account in accounts.to_dict('records'):
            if guid(account.get('ACCOUNT_ID')) in owners:
                tokens.update([text(account.get('ACCOUNT_ID')),text(account.get('REGISTRATION_NUMBER'))])
        tokens = sorted({value.casefold() for value in tokens if value})
        weeks = sorted({week for _,week in keys})
        candidates = tx.query(f"SELECT * FROM {repo._table('PRODUCTION_RECORD')} WHERE "
            '(LOWER(TRIM(PRODUCER_ACCOUNT_ID)) IN (SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s)))) '
            'OR (PRODUCER_ACCOUNT_ID IS NULL AND LOWER(TRIM(PRODUCER_NUMBER)) IN '
            '(SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s)))))) AND '
            'COALESCE(TRY_TO_NUMBER(SOURCE_WEEK_CODE),REPORTING_YEAR*100+REPORTING_WEEK) IN '
            '(SELECT VALUE::NUMBER FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))))',
            (json.dumps(owners),json.dumps(tokens),json.dumps(weeks)))
        total_before = int(tx.query(f"SELECT COUNT(*) AS N FROM {repo._table('PRODUCTION_RECORD')}").iloc[0]['N'])
    old_rows = [row for row in candidates.to_dict('records') if producer_week(row,accounts) in keys]
    old_ids = [row['PRODUCTION_ID'] for row in old_rows]
    if len(set(old_ids))!=len(old_ids) or any(not text(value) for value in old_ids):
        raise RepositoryError('Existing production identities are missing or duplicated; replacement was refused.')
    replaced_keys = {producer_week(row,accounts) for row in old_rows}
    summary = dict(import_id=import_id,rows_inserted=sum(producer_week(r,accounts) not in replaced_keys for r in records.to_dict('records')),
        rows_replaced=len(old_rows),rows_written=len(records),rows_unchanged=total_before-len(old_rows),
        producer_weeks_replaced=len(replaced_keys),week_start=min((w for _,w in replaced_keys),default=None),
        week_end=max((w for _,w in replaced_keys),default=None))
    children_before = repo._size_breakdown.copy(deep=True) if repo._is_memory else None
    try:
        if old_rows:
            if not text(actor):
                raise RepositoryError('An authenticated recorder is required to replace existing production.')
            if repo._is_memory:
                if BACKUP_TABLE not in repo._continuity_rows:
                    raise RepositoryError('Production backup schema update is required before overwriting existing rows.')
                children = repo._size_breakdown.loc[repo._size_breakdown.PRODUCTION_ID.isin(old_ids)].to_dict('records')
            else:
                try:
                    tx.query(f'SELECT REPLACEMENT_ID FROM {_table(repo)} WHERE 1=0')
                except Exception as exc:
                    raise RepositoryError('Production backup schema update/access is required before overwriting existing rows.') from exc
                children = tx.query(f'SELECT * FROM {repo.database}.{repo.schema_core}.PRODUCTION_SIZE_BREAKDOWN '
                    'WHERE PRODUCTION_ID IN (SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))))', (json.dumps(old_ids),)).to_dict('records')
            for row in old_rows:
                owner, week = producer_week(row,accounts)
                backup = dict(REPLACEMENT_ID=str(uuid.uuid4()),IMPORT_ID=import_id,PRODUCTION_ID=row['PRODUCTION_ID'],
                    PRODUCER_ACCOUNT_ID=owner,SOURCE_WEEK_CODE=week,REPLACED_BY=actor,
                    REPLACED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),OLD_VALUES=copy.deepcopy(row),
                    SIZE_BREAKDOWN_ROWS=[child for child in children if child['PRODUCTION_ID']==row['PRODUCTION_ID']])
                if repo._is_memory:
                    repo._continuity_rows[BACKUP_TABLE].append(backup)
                else:
                    fields=list(backup);values=tuple(evidence_json(backup[k]) if k in {'OLD_VALUES','SIZE_BREAKDOWN_ROWS'} else backup[k] for k in fields)
                    slots=['PARSE_JSON(%s)' if k in {'OLD_VALUES','SIZE_BREAKDOWN_ROWS'} else '%s' for k in fields]
                    if tx.execute(f"INSERT INTO {_table(repo)} ({','.join(fields)}) SELECT {','.join(slots)}",values)!=1:
                        raise RepositoryError('Replacement backup was not saved exactly once; no rows were replaced.')
            if repo._is_memory:
                repo._size_breakdown=repo._size_breakdown.loc[~repo._size_breakdown.PRODUCTION_ID.isin(old_ids)].copy()
                repo._production=repo._production.loc[~repo._production.PRODUCTION_ID.isin(old_ids)].copy()
            else:
                condition='WHERE PRODUCTION_ID IN (SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))))'
                params=(json.dumps(old_ids),)
                if tx.execute(f'DELETE FROM {repo.database}.{repo.schema_core}.PRODUCTION_SIZE_BREAKDOWN '+condition,params)!=len(children):
                    raise ConcurrencyError('Production size rows changed during replacement.')
                if tx.execute(f"DELETE FROM {repo._table('PRODUCTION_RECORD')} "+condition,params)!=len(old_ids):
                    raise ConcurrencyError('Production rows changed during replacement.')
        yield summary
    except Exception:
        if repo._is_memory:
            repo._size_breakdown=children_before
        raise
