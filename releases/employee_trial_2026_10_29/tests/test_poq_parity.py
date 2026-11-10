import csv,io
from pathlib import Path
import pandas as pd
from app.services.producers_over_quota_report import build_producers_over_quota_report
from tests.test_flock_age_report import QUOTAS
from decimal import Decimal,InvalidOperation
ROOT=Path(__file__).parent/'fixtures'
def number(value):
 try:return Decimal(str(value).replace(',',''))
 except InvalidOperation:return None
def inputs():
 rows=list(csv.DictReader((ROOT/'producers_over_quota/DEV_FlockCurrent.csv').read_text(encoding='utf-8-sig').splitlines()))
 fields=list(csv.DictReader((ROOT/'flock_disposals/Untitled 2_2026-11-09-0841.csv').read_text(encoding='utf-8-sig').splitlines()))
 actual={r['PERMIT_NUMBER']:r for r in fields};f=[];tx=[];owners={}
 for r in rows:
  permit=r['Permit No']
  if not permit.isdecimal():continue
  reg=r['Reg No'];owners[reg]=dict(ACCOUNT_ID=reg,REGISTRATION_NUMBER=reg,ORGANIZATION_NAME=r['Account'],PRODUCER_ROLE=True)
  raw=actual.get(permit,{})
  f.append(dict(FLOCK_ID=permit,PERMIT_NUMBER=permit,ACCOUNT_ID=reg,STATUS='Active',FLOCK_QUOTA_TYPE=r['Quota Type'],HATCH_DATE=r['Hatch Date'],PLACEMENT_DATE=r['Placement Date'],EST_DISPOSAL=raw.get('EST_DISPOSAL',r['Disp. Date']),DISPOSAL_DATE=raw.get('DISPOSAL_DATE')))
  qty=number(r['Counted'])
  if qty is not None:
   tx.append(dict(FLOCK_TRANSACTION_ID=permit,FLOCK_ID=permit,TRANSACTION_TYPE='Delivery' if 'Initial Delivery' in r['Notes'] else 'Count',TRANSACTION_DATE=r['Count Date'],QUANTITY=qty,COUNT_SOURCE_LABEL='DEV report observation'))
 return pd.DataFrame(f),pd.DataFrame(tx),pd.DataFrame(list(owners.values())),pd.DataFrame(),dict(QUOTAS)

from datetime import date
from io import BytesIO
import pytest
from pypdf import PdfReader
from app.services import producers_over_quota_report as report
from app.services.flock_current_report import build_flock_current_report, effective_disposal_date, day
from app.services.flock_reports import build_flock_status_report
from app.services.report_pdf import render_report_pdf
from tests.test_producers_over_quota import account_totals
from tests.test_report_smoke import smoke_repository
from tests.auth_support import authenticated_app


def legacy():
    lines=(ROOT/'legacy_reports/EIMSProducersOverQuota.csv').read_text(encoding='utf-8-sig').splitlines()
    start=next(i for i,line in enumerate(lines) if line.startswith('Registration_Number1,'))
    rows=[r for r in csv.DictReader(io.StringIO('\n'.join(lines[start:]))) if r.get('PermitNo')]
    return {(r['Registration_Number1'],r['PermitNo']):(int(number(r['Inventory'])),r['UtilizationPerFarm']) for r in rows}, rows


def observed(frame):
    result={};reg=None
    for r in frame.to_dict('records'):
        reg=r['Reg No'] or reg
        if r['Permit No']:result[(reg,r['Permit No'])]=(r['Inventory'],r['% Quota'])
    return result


def test_full_csv_row_parity_with_only_exact_documented_snapshot_gaps():
    f,t,a,b,q=inputs()
    result,summary=build_producers_over_quota_report(f,t,a,b,q,'2026-11-10')
    expected,raw=legacy();actual=observed(result)
    assert len(expected)==47 and len(actual)==48
    assert set(actual)-set(expected)=={('7159','40366'),('7402','40369')}
    assert set(expected)-set(actual)=={('7038','40407')}
    assert actual[('7159','40366')]==(5174,'12.04%')
    assert actual[('7402','40369')]==(1863,'104.08%')
    differences={key:(actual[key],expected[key]) for key in actual.keys()&expected.keys() if actual[key]!=expected[key]}
    assert differences=={
        ('7168','40371'):((40524,'73.45%'),(40558,'73.51%')),
        ('7168','40395'):((19550,'35.44%'),(19659,'35.63%'))}
    assert summary['Inventory Birds']==1059266==1052372+5174+1863-143
    assert summary['Producers with Quota']==24
    totals=account_totals(result)
    assert len(totals)==24
    for r in raw:
        reg=r['Registration_Number1']
        if reg not in {'7159','7402','7168'}:
            assert totals[reg]==(int(number(r['Inventory1'])),r['Textbox24'])
    # Every under-quota producer from the supplied CSV is present.
    assert {'7050','7065','7078','7101','7106','7107','7161','7165'}<=set(totals)


def test_actual_disposal_is_already_honoured_without_inventing_source_values():
    f,t,a,b,q=inputs();original=f.copy(deep=True)
    stored=f.set_index('PERMIT_NUMBER')
    assert stored.loc['40366','DISPOSAL_DATE']==stored.loc['40369','DISPOSAL_DATE']=='2026-11-30'
    assert effective_disposal_date(stored.loc['40369'])==date(2026,11,30)  # Actual precedes estimate Oct 5.
    # Hypothetical corrected inputs use dates explicitly supplied by the user.
    corrected=f.copy(deep=True)
    for permit,actual in [('40366','2026-09-24'),('40369','2026-10-08')]:
        corrected.loc[corrected.PERMIT_NUMBER.eq(permit),'DISPOSAL_DATE']=actual
    result,summary=build_producers_over_quota_report(corrected,t,a,b,q,'2026-11-10')
    assert {'40366','40369'}.isdisjoint(result['Permit No'])
    assert summary['Inventory Birds']==1052229==1052372-143
    for builder in [build_flock_current_report,lambda f,t,a,date:build_flock_status_report(f,t,a,b,q,date)[0]]:
        assert {'40366','40369'}.isdisjoint(builder(corrected,t,a,'2026-11-10')['Permit No'])
    # On-date actual disposals also exclude; date formatting uses actual when future.
    corrected.loc[corrected.PERMIT_NUMBER.eq('40369'),'DISPOSAL_DATE']='2026-11-10'
    assert '40369' not in build_producers_over_quota_report(corrected,t,a,b,q,'2026-11-10')[0]['Permit No'].tolist()
    pd.testing.assert_frame_equal(f,original)


def test_all_future_flocks_presence_and_exact_stored_date_differences():
    f,t,a,b,q=inputs();result,_=build_producers_over_quota_report(f,t,a,b,q,'2026-11-10')
    _,rows=legacy();future={r['PermitNo'] for r in rows if pd.to_datetime(r['Placement_Date'],dayfirst=True).date()>date(2026,11,10)}
    assert future=={'40407','40397','40404','40399','40406','40405','40400','40401','40403','40398'}
    actual=result.set_index('Permit No')
    assert future-set(actual.index)=={'40407'}
    assert all(actual.loc[p,'Inventory']==0 and actual.loc[p,'Last Count']=='' for p in future-{'40407'})
    assert actual.loc['40406','Placement Date']=='02/03/2027'
    assert actual.loc['40398','Placement Date']=='08/12/2026'
    assert actual.loc['40375','Disposal Date']=='22/03/2027'
    core=pd.read_csv(ROOT/'producers_over_quota/DEV_FutureFlocks.csv',dtype=str).set_index('PERMIT_NUMBER')
    assert core.loc['40406','PLACEMENT_DATE']=='2027-03-02'
    # A present 40407 is retained at zero, not removed by quota/placement filtering.
    from tests.test_producers_over_quota import sources
    supplied=sources();present,_=build_producers_over_quota_report(*supplied,'2026-11-10')
    assert present.set_index('Permit No').loc['40407','Inventory']==0


def test_only_over_quota_total_percentages_are_red_in_ui_and_pdf():
    f,t,a,b,q=inputs();frame,_=build_producers_over_quota_report(f,t,a,b,q,'2026-11-10')
    styles=report.style_producers_over_quota(frame)._compute().ctx
    column=frame.columns.get_loc('% Quota');marked=frame.attrs['over_quota_total_rows']
    assert len(marked)==16
    assert set(styles)=={(position,column) for position in marked}
    assert all(('color','#c00000') in styles[(position,column)] for position in marked)
    assert all(frame.iloc[position]['Account Name']=='Total' for position in marked)
    payload=render_report_pdf('Producers Over Quota Report',['For Egg Production as of 10/11/2026 at 0.400 Mortality'],frame,report_id='producers-over-quota')
    red_text=[];state={'rgb':(0,0,0)}
    def operand(op,args,*unused):
        if op==b'rg':state['rgb']=tuple(float(x) for x in args)
    def text(value,*unused):
        if value.strip() and state['rgb'][0]>.7 and state['rgb'][1:]==(0,0):red_text.append(value.strip())
    for page in PdfReader(BytesIO(payload)).pages:page.extract_text(visitor_operand_before=operand,visitor_text=text)
    assert len(red_text)==16 and all(value.endswith('%') for value in red_text)


def test_page_calculation_notes_are_collapsed_and_table_styled(tmp_path,monkeypatch):
    repo=smoke_repository('normal')
    repo._flock_transactions['TRANSACTION_TYPE']='Delivery'
    repo._flock_transactions['QUANTITY']=200
    app=authenticated_app(Path(__file__).resolve().parents[1]/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/4_Reports.py').run()
    app.session_state['report_center_open_report']='producers-over-quota'
    app.run();app.button(key='run_producers_over_quota').click().run()
    assert not app.exception and not app.error
    notes=next(e for e in app.expander if e.label.startswith('Calculation notes ('))
    assert not notes.proto.expanded
    assert all(c.value not in [v.value for v in app.caption if v not in notes.caption] for c in notes.caption)
    assert any('Initial Delivery quantity used' in c.value for c in notes.caption)
    assert app.dataframe and '#c00000' in app.dataframe[0].proto.styler.styles


@pytest.mark.parametrize('quota,red',[(16550,False),(20000,False),(16549,True)])
def test_exactly_100_and_under_are_listed_but_only_over_is_red(quota,red):
    from tests.test_producers_over_quota import sources
    f,t,a,b,_=sources()
    f=f.loc[f.ACCOUNT_ID.eq('7038')];t=t.loc[t.FLOCK_ID.isin(f.FLOCK_ID)]
    a=a.loc[a.ACCOUNT_ID.eq('7038')]
    result,summary=build_producers_over_quota_report(f,t,a,b,{'7038':quota},'2026-11-10')
    assert summary['Producers with Quota']==1 and len(account_totals(result))==1
    assert bool(result.attrs['over_quota_total_rows']) is red


def test_only_three_stored_date_differences_in_export_fixture():
    f,t,a,b,q=inputs();result,_=build_producers_over_quota_report(f,t,a,b,q,'2026-11-10')
    _,rows=legacy();expected={r['PermitNo']:r for r in rows}
    differences={}
    for row in result.to_dict('records'):
        permit=row['Permit No']
        if permit not in expected:continue
        for key,source in [('Placement Date','Placement_Date'),('Disposal Date','Disposal_Date')]:
            if row[key]!=expected[permit][source]:differences[(permit,key)]=(row[key],expected[permit][source])
    assert differences=={
        ('40406','Placement Date'):('02/03/2027','01/03/2027'),
        ('40398','Placement Date'):('08/12/2026','07/12/2026'),
        ('40375','Disposal Date'):('22/03/2027','27/05/2027')}


def test_positive_quota_producer_without_current_flocks_still_has_name_and_total():
    f,t,a,b,q=inputs();owner=a.loc[a.ACCOUNT_ID.eq('7038')]
    result,summary=build_producers_over_quota_report(f.iloc[:0],t.iloc[:0],owner,b,{'7038':16152},'2026-11-10')
    assert result.iloc[0]['Reg No']=='7038' and result.iloc[0]['Account Name']=='Bayview Poultry Farm Ltd.'
    assert account_totals(result)['7038']==(0,'0.00%') and summary['Producers with Quota']==1
    assert not result['Permit No'].ne('').any()
