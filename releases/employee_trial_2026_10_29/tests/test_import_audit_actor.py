"""Scalar import actors resolve in the owning transaction; synthetic records only."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
import pandas as pd
import pytest

from data.repositories.base import RepositoryError
from data.repositories.snowflake import SnowflakeRepository
from tests.test_production_replacement import repo as memory_repo, raw, stage, existing


@pytest.mark.parametrize('known', [True, False])
def test_memory_reimport_actor_email_or_complete_rollback(known):
    repo = memory_repo()
    repo._production = pd.DataFrame([existing('old')])
    batch, _, _ = stage(repo, raw([{'Producer #':'001','Week':202601,'Total':3}]))
    if known:
        assert repo.commit_staged_production(batch, 'staff') == (batch, 1)
        assert repo.commit_staged_production(batch, 'staff') == (batch, 1)
        assert len(repo._migration_review_audit) == 1
        assert repo._migration_review_audit[0]['ACTOR_EMAIL'] == 'staff@example.invalid'
        assert repo._migration_review_audit[0]['ACTOR_USER_ID'] == 'staff'
    else:
        before = repo._production.copy(deep=True)
        with pytest.raises(RepositoryError, match='email'):
            repo.commit_staged_production(batch, 'UNKNOWN_USER')
        pd.testing.assert_frame_equal(repo._production, before)
        assert repo.get_production_replacement_backups(batch).empty
        assert not getattr(repo, '_migration_review_audit', [])
        assert repo.find_import_by_hash(repo._import_batches[-1]['FILE_HASH'])['STATUS'] == 'Staged'


class FakeSnowflake:
    def __init__(self, batch, old, known):
        self.state = dict(batch=deepcopy(batch), production=[old], audit=[], backups=[], history=[])
        self.known = known
        self.active = False
        self.calls = []
        self.commits = 0
        self.rollbacks = 0

    @contextmanager
    def transaction(self):
        before = deepcopy(self.state)
        self.active = True
        try:
            yield self
            self.commits += 1
        except Exception:
            self.state = before
            self.rollbacks += 1
            raise
        finally:
            self.active = False

    intake_transaction = transaction

    def query(self, sql, params=None):
        assert self.active
        self.calls.append(('query', sql, params))
        if 'APP_USER' in sql:
            assert 'EFNS_DEV.SYNTHETIC_SECURITY.APP_USER' in sql
            assert params == ('USER_A',) and 'LIMIT 2' in sql
            return pd.DataFrame([{'EMAIL':'user-a@example.invalid'}]) if self.known else pd.DataFrame()
        if 'IMPORT_BATCH' in sql:
            return pd.DataFrame([deepcopy(self.state['batch'])])
        if 'COUNT(*)' in sql:
            return pd.DataFrame([{'N':len(self.state['production'])}])
        if 'PRODUCTION_REPLACEMENT_BACKUP' in sql or 'PRODUCTION_SIZE_BREAKDOWN' in sql:
            return pd.DataFrame()
        if 'PRODUCTION_RECORD' in sql:
            return pd.DataFrame(deepcopy(self.state['production']))
        raise AssertionError(sql)

    def execute(self, sql, params=None):
        assert self.active
        self.calls.append(('execute', sql, params))
        if 'INTAKE_LOCK' in sql: return 1
        if 'IMPORT_BATCH' in sql and "STATUS='Staged'" in sql and "STATUS='Committed'" not in sql:
            return 1
        if sql.startswith('DELETE'):
            if 'SIZE_BREAKDOWN' in sql: return 0
            count = len(self.state['production']); self.state['production'] = []; return count
        if 'INSERT INTO' in sql:
            columns = sql.split('(',1)[1].split(')',1)[0].replace(' ','').split(',')
            row = dict(zip(columns, params))
            target = 'audit' if 'AUDIT_EVENT' in sql else 'backups' if 'PRODUCTION_REPLACEMENT_BACKUP' in sql else 'history'
            if target == 'audit': assert row['ACTOR_EMAIL']
            self.state[target].append(row)
            return 1
        if 'IMPORT_BATCH' in sql and "STATUS='Committed'" in sql:
            self.state['batch'].update(STATUS='Committed', ROW_COUNT=params[0], NOTES=params[1])
            return 1
        raise AssertionError(sql)


@pytest.mark.parametrize('known', [True, False])
def test_fake_snowflake_reimport_lookup_is_inside_transaction_and_rollback(known, monkeypatch):
    monkeypatch.setenv('SNOWFLAKE_SCHEMA_SECURITY','SYNTHETIC_SECURITY')
    memory = memory_repo()
    batch_id, _, _ = stage(memory, raw([{'Producer #':'001','Week':202601,'Total':3}]))
    batch = deepcopy(memory._import_batches[-1])
    executor = FakeSnowflake(batch, existing('old'), known)
    repo = SnowflakeRepository(executor)
    repo.get_raw_rows = memory.get_raw_rows
    repo.get_accounts = memory.get_accounts
    repo._append_match = lambda *args: None
    def insert(tx, records, import_id):
        assert tx is executor and tx.active
        tx.state['production'] = records.to_dict('records')
        return len(records)
    repo._insert_production = insert
    if known:
        assert repo.commit_staged_production(batch_id, 'USER_A') == (batch_id, 1)
        assert repo.commit_staged_production(batch_id, 'USER_A') == (batch_id, 1)
        assert len(executor.state['audit']) == 1
        assert executor.state['audit'][0]['ACTOR_EMAIL'] == 'user-a@example.invalid'
        assert len(executor.state['backups']) == 1
    else:
        before = deepcopy(executor.state)
        with pytest.raises(RepositoryError, match='email'):
            repo.commit_staged_production(batch_id, 'USER_A')
        assert executor.state == before
        assert executor.commits == 0 and executor.rollbacks == 1
    assert any(kind=='query' and 'APP_USER' in sql for kind,sql,_ in executor.calls)


def test_authorized_memory_repository_binds_existing_user_store():
    from app.services.authorized_repository import AuthorizedRepository
    from app.security import Role
    from tests.test_report_center import user
    from tests.history_actor_support import MemoryUsers
    actor = user(Role.ADMIN)
    store = MemoryUsers(actor.user_id)
    store.record_action = lambda *args, **kwargs: None
    repo = memory_repo()
    repo._production = pd.DataFrame([existing('old')])
    batch, _, _ = stage(repo, raw([{'Producer #':'001','Week':202601,'Total':3}]))
    proxy = AuthorizedRepository(repo, store, actor)
    proxy.commit_staged_production(batch)
    assert repo._migration_review_audit[0]['ACTOR_EMAIL'] == actor.user_id+'@example.invalid'
