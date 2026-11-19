"""Overall Producers Over Quota row: synthetic identities/quantities only."""
from io import BytesIO

import pandas as pd
import pytest
from pypdf import PdfReader

from app.services.producers_over_quota_report import build_producers_over_quota_report,style_producers_over_quota
from app.services.flock_reports import build_flock_status_report
from app.services.report_center import report_csv,report_xlsx
from app.services.report_pdf import render_report_pdf
from tests.test_report_center import user


def synthetic_sources(extra=False):
    keys=['a','b']+(['c'] if extra else [])
    accounts=pd.DataFrame([dict(ACCOUNT_ID=key,REGISTRATION_NUMBER='S-'+key,
        ORGANIZATION_NAME='Synthetic '+key,PRODUCER_ROLE=True) for key in keys])
    facilities=pd.DataFrame([dict(FACILITY_ID='facility-'+key,FACILITY_NAME='Synthetic facility '+key,ACCOUNT_ID=key) for key in keys])
    flocks=pd.DataFrame([dict(FLOCK_ID='flock-'+key,FLOCK_NUMBER='permit-'+key,PERMIT_NUMBER='permit-'+key,
        ACCOUNT_ID=key,FACILITY_ID='facility-'+key,FLOCK_QUOTA_TYPE='Egg Production',STATUS='Active',
        HATCH_DATE='2025-01-01',PLACEMENT_DATE='2025-06-01',EST_DISPOSAL='2027-01-01',DISPOSAL_DATE=None,BIRD_COUNT=quantity)
        for key,quantity in zip(keys,[10,20,5])])
    tx=pd.DataFrame([dict(FLOCK_TRANSACTION_ID='count-'+key,FLOCK_ID='flock-'+key,TRANSACTION_TYPE='Count',
        TRANSACTION_DATE='2026-01-01',QUANTITY=quantity,COUNT_SOURCE_LABEL='Synthetic') for key,quantity in zip(keys,[10,20,5])])
    return flocks,tx,accounts,facilities


@pytest.mark.parametrize('quotas,red',[({'a':5,'b':25},False),({'a':5,'b':10},True),({'a':20,'b':40},False)])
def test_final_total_sums_producer_totals_uses_each_quota_once_and_highlights(quotas,red):
    f,t,a,b=synthetic_sources()
    frame,summary=build_producers_over_quota_report(f,t,a,b,quotas,'2026-01-01',mortality='0')
    position=frame.attrs['overall_total_row']
    existing=frame.iloc[:position]
    producer_totals=existing.loc[existing['Account Name'].eq('Total')]
    assert len(producer_totals)==2 and position==len(frame)-1
    total=frame.iloc[position]
    assert total['Account Name']=='Total' and total['Inventory']==producer_totals.Inventory.sum()==30
    assert frame.attrs['overall_total']['Quota']==sum(quotas.values())
    assert (position in frame.attrs['over_quota_total_rows']) is red
    styles=style_producers_over_quota(frame)._compute().ctx
    assert ('color','#c00000') in styles.get((position,frame.columns.get_loc('% Quota')),[]) if red else not styles.get((position,frame.columns.get_loc('% Quota')),[])
    for exported in [pd.read_csv(BytesIO(report_csv(user(),frame)),keep_default_na=False),
                     pd.read_excel(BytesIO(report_xlsx(user(),frame)),keep_default_na=False)]:
        assert exported.iloc[-1]['Inventory']==30 and exported.iloc[-1]['% Quota']==total['% Quota']
    pdf=render_report_pdf('Synthetic quota',[],frame,report_id='producers-over-quota')
    assert total['% Quota'] in ' '.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert summary['Inventory Birds']==30


def test_province_summary_difference_is_disclosed_not_forced():
    f,t,a,b=synthetic_sources(extra=True);q={'a':5,'b':25,'c':0}
    _,expected=build_flock_status_report(f,t,a,b,q,'2026-01-01',mortality='0')
    frame,summary=build_producers_over_quota_report(f,t,a,b,q,'2026-01-01',mortality='0')
    assert summary=={**expected,'Producers with Quota':2}
    assert summary['Inventory Birds']==35 and frame.iloc[-1]['Inventory']==30
    assert any('Overall Total uses only listed producers' in note and 'difference' in note for note in frame.attrs['notes'])


def test_no_listed_accounts_means_no_artificial_zero_total():
    f,t,a,b=synthetic_sources()
    frame,_=build_producers_over_quota_report(f,t,a,b,{'a':0,'b':None},'2026-01-01')
    assert frame.empty and frame.attrs['overall_total_row'] is None
