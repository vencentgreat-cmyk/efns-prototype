"""Synthetic selected-file lineage; no real source exports or credentials."""
import copy
import datetime as dt
import json

import pandas as pd
import pytest

from data.repositories.base import RepositoryError
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository
from data.source_trace import TARGETS, trace_summary


@pytest.fixture
def repo():
    r = MockRepository()
    r._raw_rows = []
    r._continuity_rows['SOURCE_FILE'] = [dict(SOURCE_FILE_ID='archive', ORIGINAL_FILENAME='account.csv', FILE_HASH='a'*64, FILE_SIZE_BYTES=123, IMPORT_ROUTE='HISTORICAL_EIMS')]
    r._migration_files = [dict(MIGRATION_BATCH_ID='b', SOURCE_FILENAME='account.csv', SOURCE_ENTITY='ACCOUNT', FILE_HASH='a'*64, FILE_SIZE_BYTES=123)]
    r._migration_batches = [dict(MIGRATION_BATCH_ID='b', STATUS='COMMITTED')]
    r._migration_raw_rows = [dict(MIGRATION_BATCH_ID='b', MIGRATION_RAW_ROW_ID='shared', SOURCE_FILENAME='account.csv', SOURCE_ENTITY='ACCOUNT', SOURCE_ROW_NUMBER=1, SOURCE_ID='a', TARGET_ID='a', VALIDATION_STATUS='READY')]
    r._migration_id_map = [dict(MIGRATION_BATCH_ID='b', MIGRATION_RAW_ROW_ID='shared', SOURCE_ENTITY='ACCOUNT', SOURCE_ID='a', TARGET_ID='a', STATUS='COMMITTED')]
    r._accounts = pd.DataFrame([dict(ACCOUNT_ID='a')])
    return r


def test_account_98_and_read_only(repo):
    repo._migration_raw_rows = [dict(repo._migration_raw_rows[0], MIGRATION_RAW_ROW_ID=str(i), SOURCE_ID=str(i), TARGET_ID=str(i), SOURCE_ROW_NUMBER=i+1) for i in range(98)]
    repo._migration_id_map = [dict(repo._migration_id_map[0], MIGRATION_RAW_ROW_ID=str(i), SOURCE_ID=str(i), TARGET_ID=str(i)) for i in range(98)]
    repo._accounts = pd.DataFrame({'ACCOUNT_ID': [str(i) for i in range(98)]})
    before = copy.deepcopy((repo._migration_raw_rows, repo._migration_id_map, repo._migration_batches))
    result = repo.get_source_review_rows('archive')
    assert len(result) == 98 and result.CORE_TARGET_COUNT.eq(1).all()
    assert trace_summary(result).iloc[0]['Distinct verified targets'] == 98
    assert before == (repo._migration_raw_rows, repo._migration_id_map, repo._migration_batches)


def test_multiple_imports_same_raw_id_use_full_identity(repo):
    repo._migration_files.append(dict(repo._migration_files[0], MIGRATION_BATCH_ID='second'))
    repo._migration_batches.append(dict(MIGRATION_BATCH_ID='second', STATUS='FAILED'))
    repo._migration_raw_rows.append(dict(repo._migration_raw_rows[0], MIGRATION_BATCH_ID='second', SOURCE_ID='other', TARGET_ID='other', VALIDATION_STATUS='REJECTED'))
    # Same RAW ID in a third, unrelated file/batch must never leak in.
    repo._migration_id_map.append(dict(repo._migration_id_map[0], MIGRATION_BATCH_ID='third', TARGET_ID='wrong'))
    result = repo.get_source_review_rows('archive')
    assert len(result) == 2
    assert result.iloc[0].MAPPED_TARGET_ID == 'a'
    assert result.iloc[1].MAPPING_STATUS == 'Missing mapping'
    assert result.iloc[1].VALIDATION_STATUS == 'REJECTED'
    assert len(trace_summary(result)) == 2


@pytest.mark.parametrize('field,value', [('FILE_HASH','b'*64), ('FILE_SIZE_BYTES',124), ('SOURCE_FILENAME','different.csv')])
def test_filename_alone_never_links(repo, field, value):
    repo._migration_files[0][field] = value
    assert repo.get_source_review_rows('archive').empty


@pytest.mark.parametrize('problem', ['no map','rejected','missing target','duplicate target','duplicate mapping','wrong entity','wrong source','wrong target','duplicate file'])
def test_missing_or_ambiguous_evidence_preserves_one_source_row(repo, problem):
    if problem == 'no map': repo._migration_id_map.clear()
    elif problem == 'rejected':
        repo._migration_raw_rows[0]['VALIDATION_STATUS'] = 'REJECTED'
        repo._migration_id_map[0]['STATUS'] = 'REJECTED'
    elif problem == 'missing target': repo._accounts = repo._accounts.iloc[:0]
    elif problem == 'duplicate target': repo._accounts = pd.concat([repo._accounts]*2)
    elif problem == 'duplicate mapping': repo._migration_id_map *= 2
    elif problem == 'wrong entity': repo._migration_id_map[0]['SOURCE_ENTITY'] = 'FLOCK'
    elif problem == 'wrong source': repo._migration_id_map[0]['SOURCE_ID'] = 'other'
    elif problem == 'wrong target': repo._migration_id_map[0]['TARGET_ID'] = 'other'
    elif problem == 'duplicate file': repo._migration_files *= 2
    result = repo.get_source_review_rows('archive')
    assert len(result) == 1
    assert trace_summary(result).iloc[0]['Distinct verified targets'] == 0


def test_batch_local_duplicate_raw_identity_stops(repo):
    repo._migration_raw_rows *= 2
    with pytest.raises(RepositoryError, match='identity'):
        repo.get_source_review_rows('archive')


def test_date_lineage_is_not_deduplicated(repo):
    day = dt.date(2020, 1, 2)
    repo._migration_files[0]['SOURCE_ENTITY'] = 'DIM_EFC_DATE'
    repo._migration_raw_rows = [dict(repo._migration_raw_rows[0], SOURCE_ENTITY='DIM_EFC_DATE', MIGRATION_RAW_ROW_ID=str(i), SOURCE_ID=day, TARGET_ID=day) for i in range(2)]
    repo._migration_id_map = [dict(repo._migration_id_map[0], SOURCE_ENTITY='DIM_EFC_DATE', MIGRATION_RAW_ROW_ID=str(i), SOURCE_ID='2020-01-02', TARGET_ID='2020-01-02') for i in range(2)]
    repo._efc_dates = pd.DataFrame({'DAY':[day]})
    summary = trace_summary(repo.get_source_review_rows('archive')).iloc[0]
    assert summary['Source rows'] == 2 and summary['Verified committed source rows'] == 2
    assert summary['Distinct verified targets'] == 1


def test_all_entities_have_correct_target_key(repo):
    for entity, (pk, attr) in TARGETS.items():
        repo._migration_files[0]['SOURCE_ENTITY'] = entity
        repo._migration_raw_rows[0]['SOURCE_ENTITY'] = entity
        repo._migration_id_map[0]['SOURCE_ENTITY'] = entity
        setattr(repo, attr, pd.DataFrame({pk:['a']}))
        assert repo.get_source_review_rows('archive').iloc[0].COMMIT_STATUS == 'Committed target verified'


def test_actual_repository_sql_is_selected_file_scoped_and_constant_queries(repo):
    class ReadOnly:
        def __init__(self): self.calls = []
        def query(self, sql, params=None):
            self.calls.append((sql, params))
            assert sql.lstrip().startswith('SELECT')
            if '.SOURCE_FILE ' in sql: return pd.DataFrame(repo._continuity_rows['SOURCE_FILE'])
            if '.IMPORT_RAW_ROW ' in sql: return pd.DataFrame()
            if 'COUNT(*) TARGET_COUNT' in sql:
                assert json.loads(params[0]) == ['A']
                return pd.DataFrame([dict(TARGET_ID='a', TARGET_COUNT=1)])
            if 'SELECT r.*' in sql or 'SELECT m.*' in sql:
                assert 'r.MIGRATION_BATCH_ID' in sql and 'r.MIGRATION_RAW_ROW_ID' in sql if 'SELECT m.*' in sql else 'f.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID' in sql
                assert params == ('account.csv', 'a'*64, 123)
                return pd.DataFrame(repo._migration_raw_rows if 'SELECT r.*' in sql else repo._migration_id_map)
            if 'SELECT b.' in sql: return pd.DataFrame(repo._migration_batches)
            return pd.DataFrame(repo._migration_files)
    ex = ReadOnly()
    result = SnowflakeRepository(ex).get_source_review_rows('archive')
    assert len(result) == 1 and result.iloc[0].CORE_TARGET_COUNT == 1
    assert len(ex.calls) == 7  # direct, metadata, file, RAW, map, batch, target
    assert all(params is not None for _, params in ex.calls)


def test_original_files_page_shows_rejected_and_unmapped_rows(repo, tmp_path, monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from app.auth import SESSION_TOKEN_KEY
    from tests.auth_support import authenticated_app
    monkeypatch.setenv('EFNS_RUNTIME_MODE', 'local')
    monkeypatch.setenv('REPOSITORY_MODE', 'mock')
    root = Path(__file__).resolve().parents[1]
    home = authenticated_app(root/'streamlit_app.py', tmp_path, monkeypatch)
    repo._accounts['ORGANIZATION_NAME'] = 'Synthetic account'
    repo._production = repo._production.iloc[:0]
    repo._flocks = repo._flocks.iloc[:0]
    repo._migration_raw_rows.append(dict(repo._migration_raw_rows[0], MIGRATION_RAW_ROW_ID='rejected', SOURCE_ID='bad', TARGET_ID=None, VALIDATION_STATUS='REJECTED', SOURCE_ROW_NUMBER=2))
    app = AppTest.from_file(root/'app/pages/21_Record_History.py', default_timeout=30)
    app.session_state[SESSION_TOKEN_KEY] = home.session_state[SESSION_TOKEN_KEY]
    app.session_state['_base_repo'] = repo
    app.run()
    assert not app.exception and not app.error
    summaries = [d.value for d in app.dataframe if 'Source rows' in d.value]
    assert summaries[0].iloc[0]['Source rows'] == 2
    assert summaries[0].iloc[0]['Rejected rows'] == 1
    detail = next(d.value for d in app.dataframe if 'MAPPING_STATUS' in d.value and 'RAW_DATA' not in d.value)
    assert len(detail) == 2 and 'Missing mapping' in detail.MAPPING_STATUS.tolist()
    assert any('2 retained source rows' in c.value for c in app.caption)
