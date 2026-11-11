"""Legacy PDF projections and separately identified source-observation parity."""
from datetime import date
from io import BytesIO
from pathlib import Path
import hashlib
import json
import re

import pandas as pd
import pytest
from pypdf import PdfReader

from app.services import producers_over_quota_report as report
from app.services.flock_reports import build_flock_status_report
from app.services.report_center import report_csv, report_xlsx, report_definition
from app.services.report_pdf import (render_report_pdf, pdf_display_rows, pdf_summary_lines,
    QUANTITY_COLUMNS_BY_REPORT, SUMMARY_QUANTITY_COLUMNS_BY_REPORT)
from tests.test_flock_age_report import QUOTAS
from tests.test_flock_reports import flock, transaction
from tests.test_flock_status_producer import bayview
from tests.test_report_center import user

DAY = date(2026, 11, 10)
LEGACY = Path(__file__).parent/'fixtures/legacy_reports/EIMSProducersOverQuota.pdf'


def legacy_rows():
    pattern = re.compile(r'^\s*(?:(\d{4})\b)?\s*.*?\b(40\d{3})\s+(\d+)\s+'
        r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+Egg\s+'
        r'(?:(\d{2}/\d{2}/\d{4})\s+)?([\d,]+)\s+([\d.]+%)\s*$')
    registration, rows, totals = None, [], {}
    for page in PdfReader(LEGACY).pages:
        for line in page.extract_text(extraction_mode='layout').splitlines():
            match = pattern.match(line)
            if match:
                reg, permit, age, placed, disposed, counted, inventory, percent = match.groups()
                registration = reg or registration
                rows.append(dict(registration=registration, permit=permit, age=int(age), placed=placed,
                    disposed=disposed, counted=counted or '', inventory=int(inventory.replace(',','')), percent=percent))
            total = re.match(r'^\s*Total\s+([\d,]+)\s+([\d.]+%)\s*$', line)
            if total:
                totals[registration] = (int(total[1].replace(',','')), total[2])
    assert len(rows) == 32 and len(totals) == 16
    return rows, totals


def account_totals(frame):
    totals={};registration=None
    for row in frame.to_dict('records'):
        registration=row['Reg No'] or registration
        if row['Account Name']=='Total':totals[registration]=(row['Inventory'],row['% Quota'])
    return totals


def sources():
    f, t, _, barns, _ = bayview()
    f = f.loc[f.ACCOUNT_ID.eq('a')].copy()
    f['ACCOUNT_ID'] = '7038'
    t = t.loc[t.FLOCK_ID.isin(f.FLOCK_ID)].copy()
    # Reuse supplied source observations. 40402's effective disposal date is
    # taken from the legacy PDF; no claim is made about its current DEV fields.
    f = pd.concat([f, pd.DataFrame([
        flock('40394', owner='7159', HATCH_DATE='2026-06-01', PLACEMENT_DATE='2026-10-12', EST_DISPOSAL='2027-10-11'),
        flock('40402', owner='7402', HATCH_DATE='2026-06-18', PLACEMENT_DATE='2026-10-29', EST_DISPOSAL='2027-10-28'),
        flock('40390', owner='7106', HATCH_DATE='2026-05-04', PLACEMENT_DATE='2026-09-14')])], ignore_index=True)
    t = pd.concat([t, pd.DataFrame([
        transaction('7159-count','40394','2026-10-20',QUANTITY=45773),
        transaction('7402-delivery','40402','2026-06-18',TRANSACTION_TYPE='Delivery',QUANTITY=1979),
        transaction('7106-count','40390','2026-10-02',QUANTITY=12439)])], ignore_index=True)
    names = {'7038':'Bayview Poultry Farm Ltd.', '7159':'2405272 Nova Scotia Ltd.', '7402':'Six Maples Farm'}
    a = pd.DataFrame([dict(ACCOUNT_ID=reg,REGISTRATION_NUMBER=reg,
        ORGANIZATION_NAME=names.get(reg,'Quota-only fixture '+reg),PRODUCER_ROLE=True) for reg in QUOTAS])
    return f,t,a,barns,dict(QUOTAS)


def test_source_observations_reproduce_7038_7159_7402_and_shared_summary():
    f,t,a,b,q = sources()
    before = [frame.copy(deep=True) for frame in (f,t,a,b)]
    result, summary = report.build_producers_over_quota_report(f,t,a,b,q,DAY)
    _, expected_summary = build_flock_status_report(f,t,a,b,q,DAY)
    assert summary == expected_summary  # Province scope, including under-quota 7106.
    assert summary['NFPMC Allocation'] == summary['Issuance for Province'] == 1027985
    assert summary['Producers with Quota'] == 24
    assert set(result.loc[result['Reg No'].ne(''),'Reg No']) == set(QUOTAS)
    totals = account_totals(result)
    assert [totals[reg] for reg in ['7038','7159','7402']] == [(16550,'102.46%'),(45646,'106.20%'),(1941,'108.44%')]
    pdf, _ = legacy_rows()
    indexed = result.loc[result['Permit No'].ne('')].set_index('Permit No')
    for expected in pdf:
        if expected['permit'] not in indexed.index: continue
        row = indexed.loc[expected['permit']]
        assert (row['Flock Age'],row['Inventory'],row['% Quota'],row['Placement Date'],row['Disposal Date'],row['Last Count']) == (
            expected['age'],expected['inventory'],expected['percent'],expected['placed'],expected['disposed'],expected['counted'])
    assert indexed.loc['40407','Inventory'] == 0 and indexed.loc['40407','Flock Age'] == 9
    assert indexed.loc['40407','Last Count'] == indexed.loc['40402','Last Count'] == ''
    assert summary['Inventory Birds'] == result.loc[result['Account Name'].eq('Total'),'Inventory'].sum()
    for frame, original in zip((f,t,a,b),before):pd.testing.assert_frame_equal(frame,original)


def test_all_legacy_account_totals_projection_from_pdf_not_reconstructed_counts(monkeypatch):
    rows, expected_totals = legacy_rows()
    by_permit = {r['permit']:r for r in rows}
    accounts = pd.DataFrame([dict(ACCOUNT_ID=reg,REGISTRATION_NUMBER=reg,ORGANIZATION_NAME='Account '+reg)
                             for reg in expected_totals])
    flocks = pd.DataFrame([flock(r['permit'],owner=r['registration'],
        PLACEMENT_DATE=pd.to_datetime(r['placed'],format='%d/%m/%Y').date()) for r in rows])
    tx = pd.DataFrame([transaction(r['permit'],r['permit'],str(pd.to_datetime(r['counted'],format='%d/%m/%Y').date()))
                       for r in rows if r['counted']])
    province = {'Inventory Birds':1052372,'NFPMC Allocation':1027985,'Provincial Utilization':'102.37%',
               'Issuance for Province':1027985,'Producers with Quota':24,'Notes':''}
    monkeypatch.setattr(report,'build_flock_status_report',lambda *a,**k:(pd.DataFrame(),dict(province)))
    def observed(flocks,*args,**kwargs):
        row = by_permit[flocks.iloc[0].PERMIT_NUMBER]
        return pd.DataFrame([{'Permit No':row['permit'],'Flock Age':row['age'],'Inventory':row['inventory'],
            'Disp. Date':pd.to_datetime(row['disposed'],format='%d/%m/%Y').date(),'Quota Type':'Egg Production',
            'Count Date':pd.to_datetime(row['counted'],format='%d/%m/%Y').date() if row['counted'] else '—','Notes':''}])
    monkeypatch.setattr(report,'build_flock_current_report',observed)
    frame, summary = report.build_producers_over_quota_report(flocks,tx,accounts,pd.DataFrame(),{key:QUOTAS[key] for key in expected_totals},DAY)
    actual = {}; reg = None
    for row in frame.to_dict('records'):
        reg = row['Reg No'] or reg
        if row['Account Name']=='Total':actual[reg]=(row['Inventory'],row['% Quota'])
        elif row['Permit No']:
            expected = by_permit[row['Permit No']]
            assert row['Inventory'] == expected['inventory'] and row['% Quota'] == expected['percent']
    assert actual == expected_totals and summary == {**province,'Producers with Quota':16}
    assert actual['7113'] == (33513,'120.97%')  # Projection proof only; raw Counts unavailable.
    assert frame.set_index('Permit No').loc['40406','Inventory'] == 0


@pytest.mark.parametrize('quota,expected',[(16550,True),(16549,True),(20000,True),(0,False),(None,False)])
def test_all_positive_quota_accounts_are_listed_and_undefined_quota_noted(quota,expected):
    f,t,a,b,q = sources(); q['7038']=quota
    result,_ = report.build_producers_over_quota_report(f,t,a,b,q,DAY)
    assert ('7038' in result['Reg No'].tolist()) == expected
    if quota in (None,0):
        assert any('7038: excluded' in n for n in result.attrs['notes'])
        assert {'7159','7402'} <= set(result['Reg No'])


def test_rounding_does_not_control_account_inclusion():
    f,t,a,b,q=sources(); q['7038']=16549.9999
    # Confirmed quotas are whole birds: fractional/unusable quota remains unknown.
    result,_=report.build_producers_over_quota_report(f,t,a,b,q,DAY)
    assert '7038' not in result['Reg No'].tolist()
    f=f.loc[f.ACCOUNT_ID.eq('7038')].copy();t=t.loc[t.FLOCK_ID.isin(f.FLOCK_ID)]
    f=f.loc[f.FLOCK_ID.eq('40368')];t=t.loc[t.FLOCK_ID.eq('40368')].copy();t['QUANTITY']=1000001;t['TRANSACTION_DATE']=DAY
    result,_=report.build_producers_over_quota_report(f,t,a,b,{'7038':1000000},DAY)
    assert result.iloc[-1]['% Quota']=='100.00%' and result.iloc[-1]['Inventory']==1000001


def test_unknown_detail_known_subtotal_future_zero_and_mortality():
    f,t,a,b,q=sources()
    extra=pd.DataFrame([flock('unknown',owner='7038',PLACEMENT_DATE=None),
                        flock('not-counted',owner='7038',PLACEMENT_DATE='2027-01-19')])
    f=pd.concat([f,extra],ignore_index=True)
    result,_=report.build_producers_over_quota_report(f,t,a,b,q,DAY)
    indexed=result.loc[result['Permit No'].ne('')].set_index('Permit No')
    assert indexed.loc['unknown','Inventory']==''
    assert indexed.loc['not-counted','Inventory']==0 and indexed.loc['not-counted','Last Count']==''
    assert account_totals(result)['7038'][0]==16550
    assert any('7038: total excludes 1 flock' in n for n in result.attrs['notes'])
    q['7038']=16600
    ordinary,_=report.build_producers_over_quota_report(f,t,a,b,q,DAY)
    zero,_=report.build_producers_over_quota_report(f,t,a,b,q,DAY,mortality=0)
    assert '7038' in ordinary['Reg No'].tolist() and '7038' in zero['Reg No'].tolist()
    assert account_totals(ordinary)['7038'][1]=='99.70%'
    assert account_totals(zero)['7038'][1]=='101.37%'


def test_future_count_is_blank_same_day_count_beats_delivery_and_empty_nulls():
    f,t,a,b,q=sources()
    t=pd.concat([t,pd.DataFrame([transaction('future-count','40407','2026-11-09',QUANTITY=11000),
        transaction('same-day-delivery','40368','2026-07-08',TRANSACTION_TYPE='Delivery',QUANTITY=1)])],ignore_index=True)
    result,_=report.build_producers_over_quota_report(f,t,a,b,q,DAY)
    indexed=result.loc[result['Permit No'].ne('')].set_index('Permit No')
    assert indexed.loc['40407','Last Count']=='' and indexed.loc['40368','Last Count']=='08/07/2026'
    empty,_=report.build_producers_over_quota_report(f.iloc[:0],t.iloc[:0],a.iloc[:0],b.iloc[:0],{},DAY)
    assert empty.empty and list(empty)==report.COLUMNS
    a[['REGISTRATION_NUMBER','ORGANIZATION_NAME']]=None;f[['HATCH_DATE','PLACEMENT_DATE']]=None;t['QUANTITY']=None
    nulls,_=report.build_producers_over_quota_report(f,t,a,b,q,DAY)
    assert not nulls.empty and not re.search(r'\b(None|nan|NaT)\b',' '.join(nulls.attrs['notes']))


@pytest.mark.parametrize('kind,expected',[('not-counted',0),('conflict',''),('invalid','')])
def test_not_yet_counted_zero_is_distinct_from_genuinely_unknown(kind,expected):
    f,t,a,b,q=sources();q['7038']=9000
    t=t.loc[t.FLOCK_ID.ne('40382')].copy()
    if kind!='not-counted':
        extra=[transaction('bad','40382','2026-07-08',QUANTITY=None if kind=='invalid' else 6840)]
        if kind=='conflict':extra.append(transaction('other','40382','2026-07-08',QUANTITY=6841))
        t=pd.concat([t,pd.DataFrame(extra)],ignore_index=True)
    result,_=report.build_producers_over_quota_report(f,t,a,b,q,DAY)
    assert result.set_index('Permit No').loc['40382','Inventory']==expected
    assert account_totals(result)['7038'][0]==9823


def test_scope_matches_status_and_non_egg_note():
    f,t,a,b,q=sources()
    f.loc[f.ACCOUNT_ID.eq('7038'),'STATUS']='Inactive'
    result,_=report.build_producers_over_quota_report(f,t,a,b,q,DAY)
    assert account_totals(result)['7038']==(0,'0.00%')
    assert '40368' not in result['Permit No'].tolist()
    f.loc[f.ACCOUNT_ID.eq('7159'),'FLOCK_QUOTA_TYPE']='Special Permit'
    result,_=report.build_producers_over_quota_report(f,t,a,b,q,DAY,quota_type='All')
    assert account_totals(result)['7159']==(0,'0.00%')
    assert any('Only Egg Production' in n for n in result.attrs['notes'])


def test_exports_pdf_summary_quantities_dates_and_catalog():
    f,t,a,b,q=sources();a.loc[a.ACCOUNT_ID.eq('7038'),'ORGANIZATION_NAME']='=Untrusted name'
    frame,summary=report.build_producers_over_quota_report(f,t,a,b,q,DAY)
    csv=pd.read_csv(BytesIO(report_csv(user(),frame)),keep_default_na=False)
    xlsx=pd.read_excel(BytesIO(report_xlsx(user(),frame))).fillna('')
    assert "'=Untrusted name" in csv['Account Name'].tolist() and "'=Untrusted name" in xlsx['Account Name'].tolist()
    assert '06/01/2026' in csv['Placement Date'].tolist() and '05/01/2027' in xlsx['Disposal Date'].tolist()
    definition=report_definition('producers-over-quota')
    assert definition.status=='Available' and definition.category=='Flock' and definition.export_formats==('CSV','XLSX','PDF')
    assert QUANTITY_COLUMNS_BY_REPORT[definition.report_id]==('Inventory',)
    assert SUMMARY_QUANTITY_COLUMNS_BY_REPORT[definition.report_id]==('Inventory Birds','NFPMC Allocation','Issuance for Province','Producers with Quota')
    rows=pdf_display_rows(frame,definition.report_id)
    sample=next(row for row in rows[1:] if row[2]=='40368')
    assert sample[0]=='7038' and sample[8]=='9,823' and sample[9]=='60.82%'
    lines=pdf_summary_lines(summary,definition.report_id)
    assert 'NFPMC Allocation: 1,027,985' in lines
    pdf=render_report_pdf(definition.name,[frame.attrs['header'],*lines],frame,report_id=definition.report_id)
    text='\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert 'For Egg Production as of 10/11/2026 at 0.400 Mortality' in text
    assert '16,550' in text and '1,027,985' in text and '102.46%' in text
    full={'Inventory Birds':1052372,'NFPMC Allocation':1027985,'Provincial Utilization':'102.37%',
          'Issuance for Province':1027985,'Producers with Quota':24}
    assert 'Inventory Birds: 1,052,372' in pdf_summary_lines(full,definition.report_id)


def test_header_retains_extra_mortality_precision_and_manifest_covers_new_files():
    f,t,a,b,q=sources()
    frame,_=report.build_producers_over_quota_report(f,t,a,b,q,DAY,mortality='0.4001')
    assert frame.attrs['header'].endswith('at 0.4001 Mortality')
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'DELIVERY_RUNTIME_DIFF_20261030.json').read_text())
    for item in manifest['producers_over_quota_artifacts']:
        assert hashlib.sha256((root/item['path']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==item['candidate_lf_sha256']
