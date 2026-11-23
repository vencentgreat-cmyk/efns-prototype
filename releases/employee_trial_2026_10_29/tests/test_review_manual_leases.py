"""Synthetic manual-entry restriction with historical bulk compatibility."""
import pandas as pd
import pytest
from app.security import Role, SQLiteAuthStore
from app.services.authorized_repository import AuthorizedRepository
from data.manual_quota import allocation_types
from data.constants import QUOTA_TRANSACTION_TYPES
from data.repositories.base import RepositoryError
from data.repositories.snowflake import SnowflakeRepository
from tests.test_quota_leases import repository, lease
from tests.test_report_center import user
from tests.test_daily_quota_entry import quota_app


@pytest.mark.parametrize('kind',['Lease (In)','Lease (Out)','Lease In','Lease Out'])
def test_manual_form_service_and_authorized_direct_creation_reject_legacy(kind,tmp_path):
    repo=repository();record=dict(lease(),TRANSACTION_METHOD='Allocation',TRANSACTION_TYPE=kind,QUOTA_COUNT=500)
    record.pop('QUOTA_TRANSACTION_ID')
    before=repo.get_quota_transactions()
    with pytest.raises(RepositoryError,match='Method = Lease'):
        repo.create_record_once('QUOTA_TRANSACTION',record,'manual-rejected',actor='synthetic-user')
    proxy=AuthorizedRepository(repo,SQLiteAuthStore(tmp_path/'auth.db'),user(Role.ADMIN))
    with pytest.raises(RepositoryError,match='Method = Lease'):proxy.upsert_quota_transaction(record)
    pd.testing.assert_frame_equal(before,repo.get_quota_transactions())


def test_new_options_exclude_legacy_and_existing_note_edit_is_preserved(tmp_path,monkeypatch):
    repo=repository();app=quota_app(repo,tmp_path,monkeypatch)
    assert app.selectbox(key='quota_tx_form_type').options==allocation_types(QUOTA_TRANSACTION_TYPES)
    assert not any(value.startswith('Lease') for value in app.selectbox(key='quota_tx_form_type').options)
    # Low-level persistence is intentionally retained for historical/bulk data.
    legacy=dict(lease(),TRANSACTION_METHOD=None,QUOTA_TRANSACTION_ID='synthetic-legacy')
    identity=repo.upsert_quota_transaction(legacy)
    app=quota_app(repo,tmp_path,monkeypatch,'edit',identity)
    assert app.selectbox(key='quota_tx_form_type').value=='Lease (Out)'
    app.text_area(key='quota_tx_form_comments').input('Synthetic note')
    app.text_input(key='quota_tx_form_revision_reason').input('Synthetic correction')
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    saved=repo.get_quota_transaction(identity)
    assert saved['TRANSACTION_TYPE']=='Lease (Out)' and saved['QUOTA_COUNT']==20 and saved['COMMENTS']=='Synthetic note'


@pytest.mark.parametrize('kind',['Lease (In)','Lease (Out)','Lease In','Lease Out'])
def test_daily_bulk_and_migration_insert_accept_historical_types(kind):
    repo=repository();record=dict(lease(),TRANSACTION_METHOD=None,TRANSACTION_TYPE=kind,QUOTA_COUNT=500,
        QUOTA_TRANSACTION_ID='synthetic-bulk',ACTION='CREATE')
    repo.import_operational_flock_quota_batch({}, {'QUOTA_TRANSACTION':[record]}, [])
    assert repo.get_quota_transaction('synthetic-bulk')['TRANSACTION_TYPE']==kind
    class Executor:
        def query(self,*args):return pd.DataFrame()
        def executemany(self,sql,params):
            self.params=params;return len(params)
    executor=Executor();record.pop('ACTION')
    assert SnowflakeRepository()._insert_migration_core(executor,'QUOTA_TRANSACTION',[record])==1
    assert kind in executor.params[0]
