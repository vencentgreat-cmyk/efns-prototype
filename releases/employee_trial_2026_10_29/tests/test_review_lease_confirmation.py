"""Synthetic past-date acknowledgement, persisted in the existing audit transaction."""
import datetime as dt
from copy import deepcopy
import pytest
from data.repositories.base import RepositoryError
from tests.test_quota_lease_void import saved, ADMIN
from tests.test_daily_quota_entry import quota_app


def correct(repo,identity,kind,confirmed=False,request='correction'):
    current=repo.get_quota_transaction(identity)
    if kind=='Voided':
        return repo.void_quota_lease(identity,'Synthetic correction',request,current['UPDATED_AT'],actor=ADMIN,reports_confirmed=confirmed)
    return repo.adjust_quota_lease(identity,kind,dt.date(2026,12,22),7 if kind=='Partial return' else None,
        'Synthetic correction',request,current['UPDATED_AT'],[],actor=ADMIN,reports_confirmed=confirmed)


@pytest.mark.parametrize('kind',['Partial return','Ended early','Voided'])
def test_past_date_requires_confirmation_and_records_it_atomically(kind,monkeypatch):
    monkeypatch.setattr('data.business_time.halifax_today',lambda:dt.date(2026,12,25))
    repo,identity=saved();before=deepcopy(repo._continuity_rows)
    with pytest.raises(RepositoryError,match='Confirm that figures in reports'):
        correct(repo,identity,kind)
    assert repo._continuity_rows==before
    assert correct(repo,identity,kind,True)==identity
    detail=repo._migration_review_audit[-1]['DETAILS']['report_change_confirmation']
    assert detail['required'] is True and detail['confirmed'] is True
    assert detail['confirmed_by']==ADMIN['user_id'] and detail['confirmed_at']
    count=len(repo._migration_review_audit)
    assert correct(repo,identity,kind,True)==identity and len(repo._migration_review_audit)==count


@pytest.mark.parametrize('kind',['Partial return','Ended early','Voided'])
@pytest.mark.parametrize('offset',[0,-1],ids=['today','future'])
def test_today_and_future_corrections_do_not_require_confirmation(kind,offset,monkeypatch):
    selected=dt.date(2026,12,20 if kind=='Voided' else 22)
    monkeypatch.setattr('data.business_time.halifax_today',lambda:selected+dt.timedelta(days=offset))
    repo,identity=saved()
    assert correct(repo,identity,kind)==identity
    detail=repo._migration_review_audit[-1]['DETAILS']['report_change_confirmation']
    assert detail['required'] is False and detail['confirmed'] is False


@pytest.mark.parametrize('kind',['Partial return','Ended early','Voided'])
def test_ui_warns_blocks_until_acknowledged_and_audit_records_it(kind,tmp_path,monkeypatch):
    monkeypatch.setattr('data.business_time.halifax_today',lambda:dt.date(2026,12,25))
    repo,identity=saved();app=quota_app(repo,tmp_path,monkeypatch,'detail',identity)
    scope=('lease_void_' if kind=='Voided' else 'lease_adjust_')+identity
    if kind!='Voided':
        app.selectbox(key=scope+'_kind').select(kind).run()
        app.date_input(key=scope+'_date').set_value(dt.date(2026,12,22)).run()
        if kind=='Partial return':app.text_input(key=scope+'_amount').input('7')
    app.text_input(key=scope+'_reason').input('Synthetic past-date correction').run()
    button_key=scope+('_submit' if kind=='Voided' else '_save')
    assert app.button(key=button_key).disabled
    assert any('reports already produced' in item.value for item in app.warning)
    checkbox=next(item for item in app.checkbox if item.key.startswith(scope+'_reports_confirm_'))
    checkbox.check().run()
    assert not app.button(key=button_key).disabled
    app.button(key=button_key).click().run()
    assert not app.exception and not app.error
    assert repo._migration_review_audit[-1]['DETAILS']['report_change_confirmation']['confirmed'] is True
