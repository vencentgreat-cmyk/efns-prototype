"""Signed new leases conserve Details totals without changing legacy activity."""
import datetime as dt
from io import BytesIO
import pandas as pd
import pytest
from pypdf import PdfReader
from tests.test_quota_leases import repository
from tests.test_quota_lease_void import saved,void
from tests.test_quota_lease_adjustments import adjust
from tests.test_report_center import user
from app.services.report_center import build_quota_summary_details, build_quota_summary, report_csv, report_xlsx
from app.services.report_pdf import render_report_pdf


def details(repo,when):
    return build_quota_summary_details(repo,user=user(),as_of_date=dt.date.fromisoformat(when),quota_type='Egg Production')


def test_signed_both_sides_and_all_formats_conserve_total():
    r,identity=saved();frame,meta=details(r,'2026-12-21')
    before,old=details(repository(),'2026-12-21')
    outgoing=frame.loc[frame['Quota Transaction Type'].eq('Lease (Out)')]
    incoming=frame.loc[frame['Quota Transaction Type'].eq('Lease (In)')]
    assert outgoing['Reg No'].tolist()==['001'] and outgoing['Quota Bird Count'].tolist()==[-20]
    assert incoming['Reg No'].tolist()==['002'] and incoming['Quota Bird Count'].tolist()==[20]
    assert outgoing['Account Total'].tolist()==[80] and incoming['Account Total'].tolist()==[70]
    assert frame.iloc[0]['Account Total']==meta['total_issuance']==old['total_issuance']==150
    net,net_meta=build_quota_summary(r,user=user(),as_of_date=dt.date(2026,12,21),quota_type='Egg Production')
    assert net_meta['total_issuance']==150
    exported=pd.read_csv(BytesIO(report_csv(user(),frame)),keep_default_na=False)
    assert exported.loc[exported['Quota Transaction Type'].eq('Lease (Out)'),'Quota Bird Count'].astype(int).tolist()==[-20]
    xlsx=pd.read_excel(BytesIO(report_xlsx(user(),frame)),keep_default_na=False)
    assert xlsx.loc[xlsx['Quota Transaction Type'].eq('Lease (In)'),'Quota Bird Count'].astype(int).tolist()==[20]
    pdf=render_report_pdf('Synthetic quota details',['Synthetic date'],frame,report_id='quota-summary-details')
    text=' '.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert 'Lease (Out)' in text and 'Lease (In)' in text and '-20' in text


@pytest.mark.parametrize('when',['2026-12-19','2027-01-11'])
def test_before_and_after_period_byte_identical_without_new_lease(when):
    r,_=saved();actual,meta=details(r,when);expected,old=details(repository(),when)
    pd.testing.assert_frame_equal(actual,expected);assert meta==old
    assert report_csv(user(),actual)==report_csv(user(),expected)
    pd.testing.assert_frame_equal(pd.read_excel(BytesIO(report_xlsx(user(),actual))),pd.read_excel(BytesIO(report_xlsx(user(),expected))))


def test_adjusted_early_end_partial_return_and_void_display():
    r,identity=saved();adjust(r,identity,amount=7)
    frame,meta=details(r,'2026-12-22')
    assert frame.loc[frame['Quota Transaction Type'].eq('Lease (Out)'),'Quota Bird Count'].tolist()==[-13]
    assert frame.loc[frame['Quota Transaction Type'].eq('Lease (In)'),'Quota Bird Count'].tolist()==[13]
    assert meta['total_issuance']==150
    adjust(r,identity,'Ended early','2026-12-23',None,request='end')
    actual,_=details(r,'2026-12-24');baseline,_=details(repository(),'2026-12-24')
    pd.testing.assert_frame_equal(actual,baseline)
    void(r,identity)
    actual,_=details(r,'2026-12-21');baseline,_=details(repository(),'2026-12-21')
    pd.testing.assert_frame_equal(actual,baseline)


def test_legacy_lease_types_are_still_gross_and_no_new_lease_is_unchanged():
    r=repository()
    records=[dict(QUOTA_TRANSACTION_ID='legacy-in',QUOTA_ID='qa',OWNER_ACCOUNT_ID='a',
        TRANSACTION_TYPE='Lease (In)',QUOTA_COUNT=4,EFFECTIVE_DATE='2026-12-20',END_DATE='2027-01-10'),
        dict(QUOTA_TRANSACTION_ID='legacy-out',QUOTA_ID='qa',OWNER_ACCOUNT_ID='a',
        TRANSACTION_TYPE='Lease (Out)',QUOTA_COUNT=3,EFFECTIVE_DATE='2026-12-20',END_DATE='2027-01-10')]
    r._quota_transactions=pd.concat([r._quota_transactions,pd.DataFrame(records)],ignore_index=True)
    frame,meta=details(r,'2026-12-21')
    assert 'Lease (Out)' not in frame['Quota Transaction Type'].tolist()
    assert frame.loc[frame['Quota Transaction Type'].eq('Lease (In)'),'Quota Bird Count'].tolist()==[4]
    assert meta['total_issuance']==154
    r._quota_transactions['TRANSACTION_METHOD']=None
    repeated,new=details(r,'2026-12-21')
    assert report_csv(user(),repeated)==report_csv(user(),frame) and new==meta
