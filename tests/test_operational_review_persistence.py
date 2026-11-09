import pandas as pd
import pytest

from data.operational_flock_quota_import import analyze_operational_files
from data.repositories.mock import MockRepository
from data.repositories.base import RepositoryError
from tests.test_operational_flock_quota_import import csv_upload,quota_row


def prepare(repo,upload):
    original=repo.archive_source_file(upload.name,upload.getvalue(),'DAILY_FLOCK_QUOTA')
    report=analyze_operational_files([upload],'Auto-detect',repo)
    raw=[dict(row,SOURCE_FILE_ID=original['SOURCE_FILE_ID']) for row in report.raw_rows]
    batch=repo.stage_operational_review(dict(FILE_HASH=report.package_hash,FILENAME=upload.name),raw)
    return batch,report,original


def test_unsupported_and_rejected_rows_survive_review_without_core_write():
    repo=MockRepository();before=len(repo._flocks)
    upload=csv_upload('unsupported.csv',[{'accountid':'synthetic-guid','name':'Synthetic'}])
    batch,report,original=prepare(repo,upload)
    rows=repo.get_raw_rows(batch)
    assert len(rows)==1 and rows.iloc[0].VALIDATION_STATUS=='UNSUPPORTED'
    assert rows.iloc[0].TARGET_ID is None and len(repo._flocks)==before
    assert repo.get_source_file_bytes(original['SOURCE_FILE_ID'])==upload.getvalue()


def test_staged_operational_commit_and_retry_reuse_raw():
    repo=MockRepository()
    batch,report,_=prepare(repo,csv_upload('quota.csv',[quota_row(repo,'STAGED')]))
    before=len(repo._quota_registrations)
    result=repo.commit_staged_operational(batch,report.records_by_entity)
    assert result['total_count']==1 and len(repo._quota_registrations)==before+1
    assert repo.commit_staged_operational(batch,report.records_by_entity)['already_committed']
    assert len(repo.get_raw_rows(batch))==1 and len(repo._quota_registrations)==before+1


def test_changed_prepared_rows_are_not_committed():
    repo=MockRepository()
    batch,report,_=prepare(repo,csv_upload('quota.csv',[quota_row(repo,'TAMPER')]))
    records=report.records_by_entity
    records['QUOTA_REGISTRATION'][0]['REGISTRATION_NUMBER']='DIFFERENT'
    with pytest.raises(RepositoryError):repo.commit_staged_operational(batch,records)
    assert repo.find_import_by_hash(report.package_hash)['STATUS']=='Staged'


def test_failed_operational_commit_preserves_staged_raw(monkeypatch):
    repo=MockRepository()
    batch,report,_=prepare(repo,csv_upload('quota.csv',[quota_row(repo,'FAIL')]))
    before=len(repo._quota_registrations)
    def fail(*args):raise RuntimeError('synthetic write failure')
    monkeypatch.setattr(repo,'upsert_quota_registration',fail)
    with pytest.raises(RuntimeError):repo.commit_staged_operational(batch,report.records_by_entity)
    assert repo.find_import_by_hash(report.package_hash)['STATUS']=='Staged'
    assert len(repo.get_raw_rows(batch))==1 and len(repo._quota_registrations)==before
