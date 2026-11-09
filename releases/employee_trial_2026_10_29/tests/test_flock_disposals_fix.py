"""Legacy + DEV export reconciliation; no live database or stored-data changes."""
import csv
import io
from io import BytesIO
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from app.services.flock_reports import build_flock_disposals_report,legacy_disposal_age
from app.services.report_center import report_csv,report_xlsx
from tests.test_report_center import user
from tests.test_flock_reports import flock,accounts,transaction

ROOT=Path(__file__).parent/'fixtures'/'flock_disposals'
EXCEPTIONS={'40350','40348','40357','40358','40366','40369','40346'}
PLACED={'40323':33000,'40326':4400,'40328':10000,'40337':502,'40344':1751,'40348':30573,'40357':44808}


def number(value):
    return Decimal(value.replace(',','')) if value and value.strip() else None


def fixture():
    lines=(ROOT/'EIMSFlockDisposals.csv').read_text(encoding='utf-8-sig').splitlines()
    start=next(i for i,line in enumerate(lines) if line.startswith('Registration_Number1,'))
    legacy=[row for row in csv.DictReader(io.StringIO('\n'.join(lines[start:]))) if row.get('PermitNo')]
    dev=list(csv.DictReader(io.StringIO((ROOT/'Untitled 2_2026-11-09-0841.csv').read_text(encoding='utf-8-sig'))))
    tx=list(csv.DictReader(io.StringIO((ROOT/'Untitled 2_2026-11-09-0853.csv').read_text(encoding='utf-8-sig'))))
    by_permit={row['PermitNo']:row for row in legacy}
    rows=[];owners={};quotas={}
    for raw in dev:
        expected=by_permit[raw['PERMIT_NUMBER']]
        owner=expected['Registration_Number1']
        owners[owner]=dict(ACCOUNT_ID=owner,REGISTRATION_NUMBER=owner,ORGANIZATION_NAME=expected['Account_Name'].strip())
        quotas[owner]=number(expected['Quota_Bird_Count'])
        # DEV extract omits parent IDs/type. Synthetic IDs and legacy parent
        # metadata are fixture-only; runtime uses actual FLOCK_ID joins.
        rows.append(dict(raw,FLOCK_ID=raw['PERMIT_NUMBER'],ACCOUNT_ID=owner,FLOCK_QUOTA_TYPE='Egg Production'))
    transactions=pd.DataFrame([dict(row,FLOCK_ID=row['PERMIT_NUMBER'],FLOCK_TRANSACTION_ID=str(i)) for i,row in enumerate(tx)])
    return pd.DataFrame(rows),pd.DataFrame(list(owners.values())),quotas,transactions,by_permit


def test_all_30_fixture_ages_and_23_unchanged_flocks_every_column():
    flocks,owners,quotas,tx,legacy=fixture()
    assert len(flocks)==len(legacy)==30
    before=flocks.copy(deep=True)
    result=build_flock_disposals_report(flocks,owners,quotas,'2026-01-01','2026-11-09',transactions=tx)
    broad=build_flock_disposals_report(flocks,owners,quotas,'2026-01-01','2026-12-31',transactions=tx)
    indexed=broad.set_index('Permit No')
    seen_exceptions=set()
    other_differences=[]
    for dev in flocks.to_dict('records'):
        permit=dev['PERMIT_NUMBER'];expected=legacy[permit]
        legacy_date=pd.to_datetime(expected['Disposal_Date'],format='%d/%m/%Y').date()
        assert legacy_disposal_age(dev['HATCH_DATE'],legacy_date)==int(expected['FlockAgeDisposal'])
        actual_date=pd.Timestamp(dev['DISPOSAL_DATE']).date()
        if actual_date != legacy_date: seen_exceptions.add(permit)
        if permit in EXCEPTIONS:
            # Only DEV-derived Disposal Age is compared for edited legacy flocks.
            assert indexed.loc[permit,'Disposal Age']==(actual_date-pd.Timestamp(dev['HATCH_DATE']).date()).days//7+19
            if actual_date>date(2026,11,9): assert permit not in result['Permit No'].tolist()
            continue
        row=result.loc[result['Permit No'].eq(permit)].iloc[0]
        expected_row={
            'Reg No':expected['Registration_Number1'],'Account Name':expected['Account_Name'].strip(),
            'Placement Date':pd.to_datetime(expected['Placement_Date'],format='%d/%m/%Y').date().isoformat(),
            'Quota':number(expected['Quota_Bird_Count']),'Permit No':permit,
            'Disposal Age':int(expected['FlockAgeDisposal']),'Disposal Plant':expected['Disposal_Plant'].strip(),
            'Disposal Date':legacy_date.isoformat(),'Placed':number(expected['BirdsPlaced1']),
            'Disposed':number(expected['Birds_Disposed']) if expected['Birds_Disposed'] else ''}
        for column,value in expected_row.items():
            if row[column]!=value:
                other_differences.append((permit,column,row[column],value))
        if permit=='40351':
            # User-confirmed additional snapshot exceptions: preserve DEV blanks.
            expected_row.update({'Disposed':'','Disposal Plant':''})
        assert row.to_dict()==expected_row
    assert seen_exceptions==EXCEPTIONS
    assert other_differences==[('40351','Disposal Plant','','In-Barn CO2'),
        ('40351','Disposed','',Decimal(11229))]
    pd.testing.assert_frame_equal(flocks,before)
    # Account totals add visible rows, including blank quantities, without caps.
    for registration,group in result.groupby('Reg No'):
        detail=group.loc[group['Permit No'].ne('Total')]
        total=group.loc[group['Permit No'].eq('Total')].iloc[0]
        for column in ('Placed','Disposed'):
            values=[value for value in detail[column] if value not in ('','—')]
            assert total[column]==(sum(values) if values else ('' if column=='Disposed' else '—'))


def test_seven_delivery_placed_values_override_recorded_bird_count():
    flocks,owners,quotas,tx,_=fixture()
    result=build_flock_disposals_report(flocks,owners,quotas,'2026-01-01','2026-12-31',transactions=tx)
    for permit,expected in PLACED.items():
        assert result.loc[result['Permit No'].eq(permit),'Placed'].iloc[0]==expected
        assert flocks.loc[flocks.PERMIT_NUMBER.eq(permit),'BIRD_COUNT'].iloc[0]!=str(expected)


def test_earliest_multiple_delivery_fallback_and_null_disposed_notes():
    f=pd.DataFrame([flock('multi',DISPOSAL_DATE='2026-01-01',BIRD_COUNT=999,BIRDS_DISPOSED=150),
        flock('fallback',DISPOSAL_DATE='2026-11-09',BIRD_COUNT=7,BIRDS_DISPOSED=None),
        flock('zero',DISPOSAL_DATE='2026-11-09',BIRD_COUNT=0,BIRDS_DISPOSED=0)])
    tx=pd.DataFrame([transaction('later','multi','2026-01-01',TRANSACTION_TYPE='Delivery',QUANTITY=200),
        transaction('earliest','multi','2024-01-01',TRANSACTION_TYPE='Delivery',QUANTITY=100),
        transaction('count','multi','2023-01-01',QUANTITY=800)])
    result=build_flock_disposals_report(f,accounts(),{},'2026-01-01','2026-11-09',transactions=tx)
    indexed=result.set_index('Permit No')
    assert indexed.loc['multi','Placed']==100
    assert indexed.loc['fallback','Placed']==7 and indexed.loc['fallback','Disposed']==''
    assert indexed.loc['zero','Disposed']==0
    assert indexed.loc['Total','Placed']==107 and indexed.loc['Total','Disposed']==150
    assert any('multiple Deliveries' in note and 'multi' in note for note in result.attrs['notes'])
    assert any('BIRD_COUNT fallback' in note and 'fallback' in note for note in result.attrs['notes'])
    assert legacy_disposal_age(None,'2026-01-01') is None


def test_conflicting_earliest_and_undated_deliveries_do_not_guess():
    f=pd.DataFrame([flock('conflict',DISPOSAL_DATE='2026-01-01'),flock('undated',DISPOSAL_DATE='2026-01-01')])
    tx=pd.DataFrame([transaction('one','conflict','2020-01-01',TRANSACTION_TYPE='Delivery',QUANTITY=10),
        transaction('two','conflict','2020-01-01',TRANSACTION_TYPE='Delivery',QUANTITY=11),
        transaction('missing','undated',None,TRANSACTION_TYPE='Delivery',QUANTITY=12)])
    result=build_flock_disposals_report(f,accounts(),{},'2026-01-01','2026-11-09',transactions=tx)
    assert result.Placed.tolist()==['—','—','—']
    assert any('Placed unknown' in note for note in result.attrs['notes'])


def test_null_disposed_exports_blank_and_values_unchanged():
    flocks,owners,quotas,tx,_=fixture()
    result=build_flock_disposals_report(flocks,owners,quotas,'2026-01-01','2026-11-09',transactions=tx)
    for exported in (pd.read_csv(BytesIO(report_csv(user(),result)),keep_default_na=False),
                     pd.read_excel(BytesIO(report_xlsx(user(),result)),keep_default_na=False)):
        assert exported.loc[exported['Permit No'].astype(str).eq('40340'),'Disposed'].tolist()==['']
        assert exported.loc[exported['Permit No'].astype(str).eq('40323'),'Placed'].tolist()==[33000]


def test_disposals_page_loads_all_delivery_dates_and_shows_notes(tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    from data.repositories.mock import MockRepository
    from app.auth import get_auth_store
    flocks,owners,quotas,tx,_=fixture()
    repo=MockRepository()
    repo._flocks,repo._accounts,repo._flock_transactions=flocks,owners,tx
    repo._quota_registrations=pd.DataFrame([dict(QUOTA_ID=identity,ACCOUNT_ID=identity,
        QUOTA_TYPE='Egg Production',STATUS='Active') for identity in quotas])
    repo._quota_transactions=pd.DataFrame([dict(QUOTA_TRANSACTION_ID=identity,QUOTA_ID=identity,
        OWNER_ACCOUNT_ID=identity,TRANSACTION_TYPE='Base',QUOTA_COUNT=value,EFFECTIVE_DATE='2020-01-01')
        for identity,value in quotas.items()])
    original=repo.get_flock_transactions
    reads=[]
    def read(**kwargs):
        reads.append(kwargs)
        return original(**kwargs)
    repo.get_flock_transactions=read
    app=authenticated_app(Path(__file__).resolve().parents[1]/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/4_Reports.py').run()
    monkeypatch.setattr(get_auth_store(),'record_action',lambda *args,**kwargs:pytest.fail('Report is read-only'))
    app.session_state['report_center_open_report']='flock-disposals'
    app.run()
    app.date_input(key='flock_disposals_start').set_value(date(2026,1,1))
    app.date_input(key='flock_disposals_end').set_value(date(2026,11,9))
    app.button(key='run_flock_disposals').click().run()
    assert not app.exception and not app.error
    assert reads==[{'transaction_type':'Delivery'}]
    frame=app.dataframe[0].value
    assert Decimal(str(frame.loc[frame['Permit No'].eq('40323'),'Placed'].iloc[0]))==33000
    assert any('BIRD_COUNT fallback' in item.value for item in app.caption)
    assert not any('PROVISIONAL Disposal Age' in item.value for item in app.warning)
