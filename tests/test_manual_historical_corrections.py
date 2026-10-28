"""Synthetic end-to-end contracts for persisted manual migration decisions."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import datetime as dt
import json
import re
from types import SimpleNamespace
from uuid import UUID

import pandas as pd
import pytest

from app.security import Role
from app.services.authorized_repository import AuthorizedRepository
from data.repositories.base import RepositoryError, ConcurrencyError
from data.migration import load_mapping
from tests.test_historical_corrections import _repository, _raw, BATCH_ID

ACTOR = {'user_id': str(UUID(int=501)), 'email': 'synthetic.operator@nsegg.ca'}
FLOCK = str(UUID(int=601))
FT = str(UUID(int=602))
QT = str(UUID(int=603))


@pytest.fixture
def repo():
    result = _repository()
    result._facilities = pd.DataFrame([
        {'FACILITY_ID': 'facility-a', 'ACCOUNT_ID': 'account-a', 'FACILITY_NAME': 'Synthetic building A'},
        {'FACILITY_ID': 'facility-b', 'ACCOUNT_ID': 'account-b', 'FACILITY_NAME': 'Synthetic building B'},
    ])
    result._migration_raw_rows = [
        _raw('FLOCK', 'r-flock', 2, dict(FLOCK_ID=FLOCK, FLOCK_NUMBER='Synthetic F',
             ACCOUNT_ID='account-b', FACILITY_ID='facility-a', HATCH_DATE='2025-01-01',
             PERMIT_NUMBER='P-SYN', BIRD_COUNT='10')),
        _raw('FLOCK_TRANSACTION', 'r-dependent', 3, dict(FLOCK_TRANSACTION_ID=str(UUID(int=604)),
             FLOCK_ID=FLOCK, TRANSACTION_TYPE='Placement', QUANTITY='10', TRANSACTION_DATE='2025-01-02')),
        _raw('FLOCK_TRANSACTION', 'r-ft', 4, dict(FLOCK_TRANSACTION_ID=FT,
             FLOCK_ID=None, TRANSACTION_TYPE='Placement', QUANTITY='10', TRANSACTION_DATE='2025-01-02')),
        _raw('QUOTA_TRANSACTION', 'r-qt', 5, dict(QUOTA_TRANSACTION_ID=QT,
             QUOTA_ID=None, OWNER_ACCOUNT_ID=None, TRANSACTION_TYPE='Allocation',
             EFFECTIVE_DATE='2025-01-02', QUOTA_COUNT='-5')),
    ]
    return result


def save(repo, raw='r-flock', changes=None, version=0, request='save-1', **kwargs):
    return repo.save_historical_correction_decision(BATCH_ID, raw,
        changes if changes is not None else {'ACCOUNT_ID': 'account-a'},
        kwargs.pop('basis', 'Synthetic verified source relationship'), version, request,
        confirmed=kwargs.pop('confirmed', True), actor=ACTOR, **kwargs)


def preview(repo):
    return repo.preview_historical_correction_review(BATCH_ID)


def item(repo, raw):
    return next(row for row in preview(repo).rows if row['MIGRATION_RAW_ROW_ID'] == raw)


def commit(repo, token=None):
    return repo.commit_historical_correction_review(BATCH_ID, token or preview(repo).review_token, actor=ACTOR)


def test_flock_decision_separate_from_core_and_dependency_revalidation(repo):
    original = deepcopy(repo._migration_raw_rows), deepcopy(repo._migration_batches)
    old_flocks = repo._flocks.copy(deep=True)
    decision = save(repo)
    assert decision['BEFORE_DATA']['ACCOUNT_ID'] == 'account-b'
    assert decision['AFTER_DATA']['ACCOUNT_ID'] == 'account-a'
    assert decision['ACTOR_EMAIL'] == ACTOR['email'] and decision['RECORDED_AT'] is not None
    pd.testing.assert_frame_equal(repo._flocks, old_flocks)
    assert item(repo, 'r-flock')['DISPOSITION'] == 'READY_CORE'
    assert item(repo, 'r-dependent')['DISPOSITION'] == 'PENDING_CONFIRMATION'
    first = commit(repo)
    assert first['counts'] == {'FLOCK': 1}
    assert item(repo, 'r-flock')['DISPOSITION'] == 'ALREADY_COMMITTED'
    assert item(repo, 'r-dependent')['DISPOSITION'] == 'READY_CORE'
    second = commit(repo)
    assert second['counts'] == {'FLOCK_TRANSACTION': 1}
    assert len(repo._flock_transactions) == 1
    assert (repo._migration_raw_rows, repo._migration_batches) == original
    assert repo._migration_correction_rows[0]['DECISION_ID'] == decision['DECISION_ID']
    assert len(repo._migration_review_audit) == 3


def test_wrong_ownership_and_missing_parent_stay_pending(repo):
    save(repo, changes={'ACCOUNT_ID': 'account-b', 'FACILITY_ID': 'facility-a'})
    assert item(repo, 'r-flock')['DISPOSITION'] == 'PENDING_CONFIRMATION'
    assert any('does not belong' in message for message in item(repo, 'r-flock')['CURRENT_VALIDATION_MESSAGES'])
    save(repo, changes={'FACILITY_ID': 'missing-facility'}, version=1, request='save-2')
    assert item(repo, 'r-flock')['DISPOSITION'] == 'PENDING_CONFIRMATION'
    with pytest.raises(RepositoryError, match='no validated eligible'):
        commit(repo)


@pytest.mark.parametrize('basis,confirmed', [('', True), ('  ', True), ('Evidence', False)])
def test_basis_and_confirmation_required(repo, basis, confirmed):
    with pytest.raises(RepositoryError, match='confirmation'):
        save(repo, basis=basis, confirmed=confirmed)
    assert not repo._migration_correction_decisions


def test_transaction_selection_and_quota_owner_are_validated(repo):
    save(repo, 'r-ft', {'FLOCK_ID': 'flock-existing'})
    assert item(repo, 'r-ft')['DISPOSITION'] == 'READY_CORE'
    decision = save(repo, 'r-qt', {'QUOTA_ID': 'quota-existing'})
    assert decision['AFTER_DATA']['OWNER_ACCOUNT_ID'] == 'account-a'
    assert item(repo, 'r-qt')['CORRECTED_DATA']['QUOTA_COUNT'] == -5
    assert item(repo, 'r-qt')['DISPOSITION'] == 'READY_CORE'
    with pytest.raises(ValueError):
        save(repo, 'r-qt', {'QUOTA_ID': 'quota-existing', 'OWNER_ACCOUNT_ID': 'account-b'}, version=1)
    commit(repo)
    assert repo._quota_transactions.iloc[0]['OWNER_ACCOUNT_ID'] == 'account-a'
    assert repo._quota_transactions.iloc[0]['QUOTA_COUNT'] == -5


def test_missing_quota_owner_and_related_transaction_are_not_accepted(repo):
    repo._quota_registrations.loc[0, 'ACCOUNT_ID'] = 'missing-account'
    save(repo, 'r-qt', {'QUOTA_ID': 'quota-existing'})
    assert item(repo, 'r-qt')['DISPOSITION'] == 'PENDING_CONFIRMATION'
    repo._quota_registrations.loc[0, 'ACCOUNT_ID'] = 'account-a'
    mapping = load_mapping()['entities']['QUOTA_TRANSACTION']['field_map']
    repo._migration_raw_rows[-1]['RAW_DATA'][mapping['RELATED_TRANSACTION_ID'].upper()] = str(UUID(int=699))
    assert item(repo, 'r-qt')['DISPOSITION'] == 'PENDING_CONFIRMATION'


def test_dependency_still_requires_dates_and_other_validations(repo):
    spec = load_mapping()['entities']['FLOCK_TRANSACTION']
    repo._migration_raw_rows[1]['RAW_DATA'][spec['field_map']['TRANSACTION_DATE'].upper()] = 'not-a-date'
    save(repo)
    commit(repo)
    assert item(repo, 'r-dependent')['DISPOSITION'] == 'PENDING_CONFIRMATION'
    assert item(repo, 'r-dependent')['CURRENT_VALIDATION_MESSAGES']


def test_version_cas_request_idempotency_and_stale_preview(repo):
    original_token = preview(repo).review_token
    first = save(repo)
    assert save(repo) == first
    assert len(repo._migration_correction_decisions) == 1
    with pytest.raises(ConcurrencyError):
        save(repo, changes={'ACCOUNT_ID': 'account-b'})
    with pytest.raises(ConcurrencyError):
        save(repo, request='other-request')
    with pytest.raises(ConcurrencyError):
        commit(repo, original_token)
    accepted_token = preview(repo).review_token
    save(repo, changes={'ACCOUNT_ID': 'account-b', 'FACILITY_ID': 'facility-b'}, version=1, request='revision-2')
    with pytest.raises(ConcurrencyError):
        commit(repo, accepted_token)
    commit(repo)
    assert repo._flocks.iloc[-1]['FACILITY_ID'] == 'facility-b'


def test_fresh_parent_validation_and_untraced_existing_target(repo):
    save(repo)
    token = preview(repo).review_token
    repo._facilities.loc[0, 'ACCOUNT_ID'] = 'account-b'
    with pytest.raises(ConcurrencyError):
        commit(repo, token)
    repo._facilities.loc[0, 'ACCOUNT_ID'] = 'account-a'
    repo._flocks = pd.concat([repo._flocks, pd.DataFrame([{'FLOCK_ID': FLOCK, 'ACCOUNT_ID': 'account-a'}])], ignore_index=True)
    assert item(repo, 'r-flock')['DISPOSITION'] == 'PENDING_CONFIRMATION'
    assert 'FLOCK' not in commit(repo)['counts']
    assert item(repo, 'r-flock')['DISPOSITION'] == 'PENDING_CONFIRMATION'


def test_duplicate_commit_and_immutable_committed_decision(repo):
    save(repo)
    token = preview(repo).review_token
    result = commit(repo, token)
    assert commit(repo, token)['idempotent']
    assert len(repo._flocks) == 2
    assert len(repo._migration_correction_batches) == 1
    assert result['correction_batch_id'] == repo._migration_correction_batches[0]['MIGRATION_CORRECTION_BATCH_ID']
    with pytest.raises(RepositoryError, match='cannot be overwritten'):
        save(repo, version=1, request='edit-after-commit')
    with pytest.raises(RepositoryError, match='review'):
        repo.commit_historical_corrections(BATCH_ID)


@pytest.mark.parametrize('failure_table', ['MIGRATION_CORRECTION_BATCH', 'MIGRATION_CORRECTION_ROW', 'AUDIT_EVENT'])
def test_commit_rolls_back_core_tracking_and_mandatory_audit(repo, monkeypatch, failure_table):
    save(repo)
    before = deepcopy(repo._migration_raw_rows), deepcopy(repo._migration_batches), deepcopy(repo._migration_review_audit)
    original = repo._review_insert
    def broken(tx, table, record):
        if table == failure_table:
            raise RepositoryError('Synthetic storage failure')
        return original(tx, table, record)
    monkeypatch.setattr(repo, '_review_insert', broken)
    with pytest.raises(RepositoryError, match='Synthetic storage failure'):
        commit(repo)
    assert len(repo._flocks) == 1
    assert not repo._migration_correction_rows and not repo._migration_correction_batches
    assert len(repo._migration_correction_decisions) == 1
    assert (repo._migration_raw_rows, repo._migration_batches, repo._migration_review_audit) == before


def test_save_audit_failure_rolls_back_decision(repo, monkeypatch):
    def fail(*_args):
        raise RepositoryError('Synthetic audit failure')
    monkeypatch.setattr(repo, '_review_audit', fail)
    with pytest.raises(RepositoryError, match='audit failure'):
        save(repo)
    assert not repo._migration_correction_decisions


def test_concurrent_save_is_serialized_and_batch_scoped(repo):
    def attempt(number):
        try:
            save(repo, request=f'request-{number}')
            return 'saved'
        except ConcurrencyError:
            return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(attempt, [1, 2])) == ['conflict', 'saved']
    other = deepcopy(repo._migration_raw_rows[0])
    other['MIGRATION_BATCH_ID'] = 'other-batch'
    other['RAW_DATA'] = {}
    repo._migration_raw_rows.append(other)
    assert len(preview(repo).rows) == 4
    assert repo.get_historical_correction_source(BATCH_ID, 'r-flock')['RAW_DATA']


def test_read_only_users_cannot_save_or_commit_and_actor_is_not_spoofable(repo):
    user = SimpleNamespace(user_id=ACTOR['user_id'], email=ACTOR['email'], role=Role.REPORTING_VIEWER, active=True)
    wrapped = AuthorizedRepository(repo, SimpleNamespace(), user)
    with pytest.raises(RepositoryError, match='permission'):
        wrapped.save_historical_correction_decision(BATCH_ID, 'r-flock', {}, 'Evidence', 0, 'a', confirmed=True)
    with pytest.raises(RepositoryError, match='permission'):
        wrapped.commit_historical_correction_review(BATCH_ID, 'a'*64)
    user.role = Role.ADMIN
    wrapped.save_historical_correction_decision(BATCH_ID, 'r-flock', {'ACCOUNT_ID': 'account-a'}, 'Evidence', 0, 'a',
        confirmed=True, actor={'user_id': 'fake', 'email': 'fake@nsegg.ca'})
    assert repo._migration_correction_decisions[0]['ACTOR_EMAIL'] == ACTOR['email']


def test_snowflake_parameterized_variants_and_server_timestamps():
    from data.repositories.correction_review import CorrectionReviewRepository
    class Boundary(CorrectionReviewRepository):
        _is_memory = False
        database = 'EFNS_DEV'
        schema_raw = 'RAW'
        def _table(self, table, schema=None):
            return f'EFNS_DEV.{schema or "CORE"}.{table}'
    statements = []
    tx = SimpleNamespace(execute=lambda sql, params: statements.append((sql, params)))
    Boundary()._review_insert(tx, 'MIGRATION_CORRECTION_DECISION', dict(
        DECISION_ID='id', CHANGES={'FLOCK_ID': 'id'}, BASIS="Quoted ' evidence", RECORDED_AT='client-time'))
    sql, params = statements[0]
    assert 'PARSE_JSON(%s)' in sql and 'CONVERT_TIMEZONE' in sql
    assert "Quoted ' evidence" not in sql and "Quoted ' evidence" in params
    assert 'client-time' not in params


class TransactionExecutor:
    """Isolated SQL boundary double: no Snowflake connection or live data."""
    def __init__(self, memory):
        from data.repositories.correction_review import CORE, RAW_TABLES
        self.tables = {name: getattr(memory, attr).to_dict('records') for name, (attr, _) in CORE.items()}
        self.tables.update({name: deepcopy(getattr(memory, attr)) for name, attr in RAW_TABLES.items()})
        self.tables['AUDIT_EVENT'] = []
        self.events = []
        self.active = False
        self.fail_audit = False
        self.skip_insert = False

    @contextmanager
    def transaction(self):
        assert not self.active, 'Nested transaction ownership is forbidden'
        before = deepcopy(self.tables)
        self.active = True
        self.events.append('BEGIN')
        try:
            yield self
            self.events.append('COMMIT')
        except Exception:
            self.tables = before
            self.events.append('ROLLBACK')
            raise
        finally:
            self.active = False

    def query(self, sql, params=None):
        self.events.append(('QUERY', self.active, sql, params))
        table = re.search(r'FROM EFNS_DEV\.\w+\.(\w+)', sql)[1]
        rows = deepcopy(self.tables[table])
        if params:
            field = re.search(r'WHERE (\w+)\s*=\s*%s', sql)[1]
            rows = [row for row in rows if row.get(field) == params[0]]
        return pd.DataFrame(rows)

    def execute(self, sql, params=()):
        assert self.active
        self.events.append(('EXECUTE', sql, params))
        if sql.startswith('UPDATE EFNS_DEV.RAW.INTAKE_LOCK'):
            return 1
        table = re.search(r'INSERT INTO EFNS_DEV\.\w+\.(\w+)', sql)[1]
        if table == 'AUDIT_EVENT' and self.fail_audit:
            raise RepositoryError('Synthetic SQL audit failure')
        columns = re.search(r'\(([^)]+)\) SELECT', sql)[1].split(', ')
        from data.repositories.correction_review import VARIANTS
        values = iter(params)
        record = {}
        for field in columns:
            if field in {'CREATED_AT', 'UPDATED_AT', 'COMMITTED_AT', 'RECORDED_AT', 'OCCURRED_AT'}:
                record[field] = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
            else:
                value = next(values)
                record[field] = json.loads(value) if field in VARIANTS else value
        self.tables[table].append(record)
        return 1

    def executemany(self, sql, rows):
        assert self.active
        self.events.append(('BULK', sql, rows))
        if self.skip_insert:
            return 0
        table = re.search(r'INSERT INTO EFNS_DEV\.\w+\.(\w+)', sql)[1]
        columns = re.search(r'\(([^)]+)\) SELECT', sql)[1].split(', ')
        for row in rows:
            self.tables[table].append(dict(zip(columns[:-2], row[:-1])))
        return len(rows)


def test_real_snowflake_repository_uses_one_transaction_for_decision_and_commit(repo):
    from data.repositories.snowflake import SnowflakeRepository
    executor = TransactionExecutor(repo)
    sql_repo = SnowflakeRepository(executor=executor)
    decision = save(sql_repo)
    assert executor.events.count('BEGIN') == executor.events.count('COMMIT') == 1
    assert all(event[1] for event in executor.events if isinstance(event, tuple) and event[0] == 'QUERY')
    assert len(executor.tables['FLOCK']) == 1
    result = commit(sql_repo)
    assert result['counts'] == {'FLOCK': 1}
    assert executor.events.count('BEGIN') == executor.events.count('COMMIT') == 2
    trace = executor.tables['MIGRATION_CORRECTION_ROW'][0]
    assert trace['DECISION_ID'] == decision['DECISION_ID']
    assert len(executor.tables['AUDIT_EVENT']) == 2
    assert executor.tables['MIGRATION_RAW_ROW'] == repo._migration_raw_rows


@pytest.mark.parametrize('failure', ['audit', 'skipped-insert'])
def test_snowflake_commit_failure_rolls_back_the_single_transaction(repo, failure):
    from data.repositories.snowflake import SnowflakeRepository
    executor = TransactionExecutor(repo)
    sql_repo = SnowflakeRepository(executor=executor)
    save(sql_repo)
    executor.fail_audit = failure == 'audit'
    executor.skip_insert = failure == 'skipped-insert'
    with pytest.raises(RepositoryError):
        commit(sql_repo)
    assert executor.events.count('ROLLBACK') == 1
    assert executor.events.count('COMMIT') == 1  # The independent decision save.
    assert len(executor.tables['FLOCK']) == 1
    assert not executor.tables['MIGRATION_CORRECTION_BATCH']
    assert not executor.tables['MIGRATION_CORRECTION_ROW']
    assert len(executor.tables['MIGRATION_CORRECTION_DECISION']) == 1


def test_correction_editor_saves_and_revalidates_without_core_write(repo,tmp_path):
    from streamlit.testing.v1 import AppTest
    user = SimpleNamespace(user_id=ACTOR['user_id'], email=ACTOR['email'], role=Role.ADMIN, active=True)
    wrapped = AuthorizedRepository(repo, SimpleNamespace(), user)
    entrypoint=tmp_path/'review_correction_editor.py'
    entrypoint.write_text('''
import streamlit as st
from app.services.historical_correction_workspace import render_correction_editor
repository=st.session_state.review_repo
preview=repository.preview_historical_correction_review('DEV_MIGRATION_SYNTHETIC_CORRECTION')
render_correction_editor(repository,preview,True)
''',encoding='utf-8')
    app = AppTest.from_file(entrypoint)
    app.session_state['review_repo'] = wrapped
    app.run()
    assert not app.exception
    account = next(control for control in app.selectbox if control.label == 'Account Id')
    account.set_value('account-a')
    app.text_area[0].set_value('Synthetic meeting evidence for the correct Account')
    app.checkbox[0].check()
    next(button for button in app.button if button.label == 'Save correction decision').click().run()
    assert not app.exception
    assert len(repo._migration_correction_decisions) == 1
    assert item(repo, 'r-flock')['DISPOSITION'] == 'READY_CORE'
    assert len(repo._flocks) == 1


def test_upgrade_and_fresh_schema_have_identical_manual_decision_columns():
    from scripts.prepare_company_deployment import deployment_tables, saved_tables, ROOT
    from scripts.company_database_deployment import manual_decision_columns, key_groups
    tables = deployment_tables()
    assert len(saved_tables()) == 32 and len(tables) == 33
    columns = manual_decision_columns()
    assert len(columns) == 15
    assert len({(row['TABLE_NAME'], row['COLUMN_NAME']) for row in columns}) == 15
    assert key_groups(tables['RAW.MIGRATION_CORRECTION_DECISION'])['foreign'] == {
        (('ORIGINAL_MIGRATION_BATCH_ID', 'MIGRATION_RAW_ROW_ID'), 'EFNS_DEV.RAW.MIGRATION_RAW_ROW',
         ('MIGRATION_BATCH_ID', 'MIGRATION_RAW_ROW_ID'))}
    upgrade = (ROOT / 'sql/17_Historical_Manual_Corrections.sql').read_text()
    assert 'UPDATE EFNS_DEV.RAW.MIGRATION_RAW_ROW' not in upgrade
    assert 'GRANT SELECT,INSERT ON TABLE EFNS_DEV.RAW.MIGRATION_CORRECTION_DECISION' in upgrade


def test_multiple_source_rows_claiming_same_guid_remain_pending(repo):
    duplicate = deepcopy(repo._migration_raw_rows[0])
    duplicate['MIGRATION_RAW_ROW_ID'] = 'r-flock-duplicate'
    duplicate['SOURCE_ROW_NUMBER'] = 8
    repo._migration_raw_rows.append(duplicate)
    save(repo)
    assert item(repo, 'r-flock')['DISPOSITION'] == 'PENDING_CONFIRMATION'
    assert any('More than one' in message for message in item(repo, 'r-flock')['CURRENT_VALIDATION_MESSAGES'])


def test_orphan_or_duplicate_decision_versions_fail_closed(repo):
    decision = save(repo)
    repo._migration_correction_decisions.append(deepcopy(decision))
    with pytest.raises(ValueError, match='Duplicate manual decision version'):
        preview(repo)
    repo._migration_correction_decisions[-1]['MIGRATION_RAW_ROW_ID'] = 'not-an-original-row'
    with pytest.raises(ValueError, match='does not resolve'):
        preview(repo)


def test_commit_trace_requires_exact_decision_version_and_success_receipt(repo):
    save(repo)
    token=preview(repo).review_token
    commit(repo,token)
    repo._migration_correction_rows[0]['DECISION_VERSION']=99
    assert item(repo,'r-flock')['DISPOSITION']=='PENDING_CONFIRMATION'
    with pytest.raises(RepositoryError,match='cannot be overwritten'):
        save(repo,version=1,request='edit-inconsistent-committed-trace')
    with pytest.raises(RepositoryError,match='inconsistent decision/source trace'):
        commit(repo,token)
    repo._migration_correction_batches[0]['STATUS']='FAILED'
    with pytest.raises(RepositoryError,match='incomplete correction receipt'):
        commit(repo,token)

