"""Synthetic legacy examples; pure report calculations and safe exports."""
from io import BytesIO

import pandas as pd
import pytest

from app.services.flock_current_report import build_flock_current_report, flock_is_in_current_report
from app.services.report_center import report_csv, report_xlsx, report_definition
from tests.test_report_center import user

DAY = pd.Timestamp('2026-11-04').date()
FIXTURES = [
    ('40390','2026-05-04','2026-09-14','2026-10-02',12439,26,12385,0),
    ('40382','2026-02-10','2026-06-23','2026-07-08',6840,38,6732,0),
    ('40368','2025-08-26','2026-01-06','2026-07-08',9988,62,9831,0),
    ('40407','2026-09-08','2027-01-19','2026-09-08',11000,8,0,11000),
    ('40396','2026-06-22','2026-11-02','2026-06-22',39772,19,39065,0),
    # Placement missing in supplied fixture: use hatch date to exercise placed case.
    ('30369','2025-07-21','2025-07-21','2025-07-21',1979,67,1856,0),
]


def sources(fixtures=FIXTURES):
    flocks, transactions = [], []
    for number, hatch, placement, count_day, qty, *_ in fixtures:
        flocks.append(dict(FLOCK_ID=number,FLOCK_NUMBER=number,ACCOUNT_ID='bayview',
            STATUS='Active',FLOCK_QUOTA_TYPE='Egg Production',PERMIT_NUMBER=number,
            HATCH_DATE=hatch,PLACEMENT_DATE=placement,EST_DISPOSAL='2027-09-13',DISPOSAL_DATE=None))
        transactions.append(dict(FLOCK_ID=number,TRANSACTION_TYPE='Count',TRANSACTION_DATE=count_day,
                                 QUANTITY=qty,COUNT_SOURCE_LABEL='Legacy'))
    return pd.DataFrame(flocks), pd.DataFrame(transactions), pd.DataFrame([
        dict(ACCOUNT_ID='bayview',ORGANIZATION_NAME='Bayview',REGISTRATION_NUMBER='123')])


@pytest.mark.parametrize('fixture',FIXTURES)
def test_legacy_example(fixture):
    result=build_flock_current_report(*sources([fixture]),DAY)
    row=result.iloc[0]
    assert (row['Flock Age'],row['Inventory'],row['Up. Flocks']) == fixture[5:]
    assert row['Counted']==fixture[4]
    assert row['Disp. Date']=='2027-09-13'


def test_bayview_subtotals():
    selected=[r for r in FIXTURES if r[0] in {'40368','40382','40407'}]
    result=build_flock_current_report(*sources(selected),DAY)
    for label in ('Account Total','Quota Total'):
        total=result.loc[result.Account==label].iloc[0]
        assert tuple(total[c] for c in ('Counted','Inventory','Up. Flocks'))==(27828,16563,11000)


def test_all_types_groups_by_distinct_account_then_type_without_mutating_sources():
    f,t,a=sources(FIXTURES[:3])
    f.loc[1,'FLOCK_QUOTA_TYPE']='Special Permit'
    f.loc[2,'ACCOUNT_ID']='other'
    a=pd.concat([a,pd.DataFrame([dict(ACCOUNT_ID='other',ORGANIZATION_NAME='Another',REGISTRATION_NUMBER='456')])])
    snapshots=[frame.copy(deep=True) for frame in (f,t,a)]
    result=build_flock_current_report(f,t,a,DAY,quota_type='All')
    assert result.Account.tolist()==['Another','Account Total','Bayview','Bayview','Account Total','Quota Total','Quota Total']
    assert result.iloc[-2]['Counted']==22427
    assert result.iloc[-1]['Counted']==6840
    for frame,before in zip((f,t,a),snapshots):
        pd.testing.assert_frame_equal(frame,before)


def test_zero_mortality_and_report_day_count_ignore_future_counts():
    f,t,a=sources([FIXTURES[0]])
    assert build_flock_current_report(f,t,a,DAY,0).iloc[0]['Inventory']==12439
    t.loc[0,'TRANSACTION_DATE']='2026-11-04'
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[0],TRANSACTION_DATE='2026-11-05',QUANTITY=999)])])
    assert build_flock_current_report(f,t,a,DAY).iloc[0]['Inventory']==12439


@pytest.mark.parametrize('change',[{'QUANTITY':1},{'COUNT_SOURCE_LABEL':'Other'}])
def test_latest_count_conflict_does_not_select_an_observation(change):
    f,t,a=sources([FIXTURES[0]])
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[0],**change)])])
    result=build_flock_current_report(f,t,a,DAY)
    assert result.iloc[0]['Notes']=='Count conflict'
    assert result.iloc[0]['Counted']==result.iloc[0]['Inventory']=='—'
    assert result.iloc[-1]['Inventory']=='—'
    assert result.iloc[-1]['Notes']=='Excludes 1 flock(s) without usable Count'


def test_no_count_and_missing_placement_remain_visible():
    f,t,a=sources([FIXTURES[0]])
    result=build_flock_current_report(f,t.iloc[:0],a,DAY)
    assert len(result)==3
    assert all(result.iloc[0][c]=='—' for c in ('Count Date','Counted','Inventory'))
    assert 'No Count' in result.iloc[0]['Notes']
    f.loc[0,'PLACEMENT_DATE']=None
    result=build_flock_current_report(f,t,a,DAY)
    assert result.iloc[0]['Inventory']=='—'
    assert 'Placement date unavailable' in result.iloc[0]['Notes']


def test_mixed_subtotals_sum_known_values_and_count_exclusions_per_group():
    f,t,a=sources(FIXTURES[:3])
    f.loc[2,'ACCOUNT_ID']='other'
    a=pd.concat([a,pd.DataFrame([dict(ACCOUNT_ID='other',ORGANIZATION_NAME='Other',REGISTRATION_NUMBER='456')])])
    t=t.iloc[:1]  # Only 40390 has a usable Count.
    result=build_flock_current_report(f,t,a,DAY)
    totals=result.loc[result.Account=='Account Total']
    assert totals.iloc[0]['Counted']==12439
    assert totals.iloc[0]['Inventory']==12385
    assert totals.iloc[0]['Up. Flocks']==0
    assert totals.iloc[0]['Notes']=='Excludes 1 flock(s) without usable Count'
    assert all(totals.iloc[1][c]=='—' for c in ('Counted','Inventory','Up. Flocks'))
    assert totals.iloc[1]['Notes']=='Excludes 1 flock(s) without usable Count'
    quota=result.loc[result.Account=='Quota Total'].iloc[0]
    assert (quota['Counted'],quota['Inventory'],quota['Up. Flocks'])==(12439,12385,0)
    assert quota['Notes']=='Excludes 2 flock(s) without usable Count'
    # Detail projection is identical whether rendered alone or in the mixed group.
    expected=build_flock_current_report(*sources([FIXTURES[0]]),DAY).iloc[0]
    actual=result.loc[result['Permit No']=='40390'].iloc[0].rename(expected.name)
    pd.testing.assert_series_equal(actual,expected)


def test_known_count_with_missing_placement_contributes_only_known_measures():
    f,t,a=sources(FIXTURES[:2])
    f.loc[1,'PLACEMENT_DATE']=None
    result=build_flock_current_report(f,t,a,DAY)
    for label in ('Account Total','Quota Total'):
        total=result.loc[result.Account==label].iloc[0]
        assert (total['Counted'],total['Inventory'],total['Up. Flocks'])==(19279,12385,0)
        assert total['Notes'].startswith('Excludes 0 flock(s) without usable Count')
        assert 'without placement date' in total['Notes']


@pytest.mark.parametrize('mortality',['NaN','Infinity','-1','abc'])
def test_invalid_mortality(mortality):
    with pytest.raises(ValueError,match='Mortality'):
        build_flock_current_report(*sources([]),DAY,mortality)


def test_provisional_inclusion_boundaries():
    f,_,_=sources([FIXTURES[0]])
    row=f.iloc[0].to_dict()
    assert flock_is_in_current_report(dict(row,FLOCK_QUOTA_TYPE='Special Permit'),DAY,'Egg Production')
    assert flock_is_in_current_report(dict(row,EST_DISPOSAL=None),DAY,'All')
    for changes in ({'STATUS':''},{'STATUS':'Planned'},{'EST_DISPOSAL':DAY},
                    {'DISPOSAL_DATE':DAY},{'FLOCK_QUOTA_TYPE':'Other'}):
        assert not flock_is_in_current_report(dict(row,**changes),DAY,'Egg Production')


def test_exports_escape_formulas_and_catalog_is_available():
    f,t,a=sources([FIXTURES[0]])
    a.loc[0,'ORGANIZATION_NAME']='=1+1'
    result=build_flock_current_report(f,t,a,DAY)
    csv=pd.read_csv(BytesIO(report_csv(user(),result)))
    xlsx=pd.read_excel(BytesIO(report_xlsx(user(),result)))
    assert csv.iloc[0].Account==xlsx.iloc[0].Account=="'=1+1"
    definition=report_definition('flock-current')
    assert definition.status=='Available'
    assert definition.export_formats==('CSV','XLSX','PDF')


def test_report_center_renders_only_result_and_does_not_audit(tmp_path,monkeypatch):
    from pathlib import Path
    from tests.auth_support import authenticated_app
    from data.repositories.mock import MockRepository
    from app.auth import get_auth_store
    root=Path(__file__).resolve().parents[1]
    app=authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    f,t,a=sources([FIXTURES[0]])
    repo=MockRepository()
    repo.get_flocks=lambda: f
    repo.get_flock_transactions=lambda: t
    repo.get_accounts=lambda: a
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/4_Reports.py').run()
    monkeypatch.setattr(get_auth_store(),'record_action',lambda *args,**kwargs: pytest.fail('Read-only report must not audit/write'))
    app.session_state['report_center_open_report']='flock-current'
    app.run()
    app.date_input(key='flock_current_date').set_value(DAY)
    app.button(key='run_flock_current').click().run()
    assert not app.exception and not app.error
    assert len(app.dataframe)==1
    assert app.dataframe[0].value.iloc[0]['Inventory']==12385
    assert 'FLOCK_ID' not in app.dataframe[0].value
    assert app.selectbox(key='flock_current_type').value=='Egg Production'


def test_follow_up_module_integrity():
    import hashlib
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'DELIVERY_RUNTIME_DIFF_20261030.json').read_text())
    for entry in manifest['follow_up_runtime_changes']:
        assert hashlib.sha256((root/entry['path']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==entry['candidate_lf_sha256']


@pytest.mark.parametrize('fixture,report_date',[
    (('40402','2026-06-18','2026-10-29','2026-06-18',1979,20,1942,0),'2026-11-05'),
    # Placement not supplied for 30369; hatch is a synthetic placed-date input.
    (('30369','2025-07-21','2025-07-21','2025-07-21',1979,67,1856,0),'2026-11-03'),
    (('40407','2026-09-08','2027-01-19','2026-09-08',11000,8,0,11000),'2026-11-05'),
])
def test_legacy_delivery_observations_and_age_report_reuse(fixture,report_date):
    from app.services.flock_age_report import build_flock_age_report
    f,t,a=sources([fixture])
    t['TRANSACTION_TYPE']='Delivery'
    result=build_flock_current_report(f,t,a,report_date)
    row=result.iloc[0]
    assert row['Counted']==fixture[4]
    assert row['Count Date']==fixture[3]
    assert (row['Flock Age'],row['Inventory'],row['Up. Flocks'])==fixture[5:]
    assert row['Notes']=='Initial Delivery quantity used (no later Count)'
    assert result.iloc[-1]['Inventory']==fixture[6]
    age,_=build_flock_age_report(f,t,a,pd.DataFrame(),{'bayview':10000},report_date)
    assert age.iloc[0]['Inventory']==row['Inventory']
    assert age.iloc[0]['Up. Flocks']==row['Up. Flocks']
    assert 'Initial Delivery quantity used (no later Count)' in age.iloc[0].Notes


def test_40366_later_count_wins_over_initial_delivery():
    f,t,a=sources([('40366','2025-07-21','2025-10-01','2025-07-21',5100,0,0,0)])
    t['TRANSACTION_TYPE']='Delivery'
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[0],TRANSACTION_TYPE='Count',
        TRANSACTION_DATE='2026-09-04',QUANTITY=5220)])])
    row=build_flock_current_report(f,t,a,'2026-11-05').iloc[0]
    assert row['Counted']==5220 and row['Count Date']=='2026-09-04'
    assert row['Notes']==''


def test_same_day_count_wins_but_conflicting_counts_remain_a_conflict():
    f,t,a=sources([FIXTURES[0]])
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[0],TRANSACTION_TYPE='Delivery',QUANTITY=999)])])
    row=build_flock_current_report(f,t,a,DAY).iloc[0]
    assert row['Counted']==12439 and row['Notes']==''
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[0],QUANTITY=12440)])])
    row=build_flock_current_report(f,t,a,DAY).iloc[0]
    assert row['Counted']==row['Inventory']=='—'
    assert row['Notes']=='Count conflict'


def test_latest_delivery_can_follow_older_count_and_future_delivery_is_ignored():
    f,t,a=sources([FIXTURES[0]])
    t=pd.concat([t,pd.DataFrame([
        dict(t.iloc[0],TRANSACTION_TYPE='Delivery',TRANSACTION_DATE='2026-11-01',QUANTITY=1000),
        dict(t.iloc[0],TRANSACTION_TYPE='Delivery',TRANSACTION_DATE='2026-11-06',QUANTITY=99999)])])
    row=build_flock_current_report(f,t,a,DAY).iloc[0]
    assert row['Counted']==1000 and row['Count Date']=='2026-11-01'
    assert row['Notes']=='Initial Delivery quantity used (no later Count)'


def test_conflicting_deliveries_do_not_select_an_arbitrary_quantity():
    f,t,a=sources([FIXTURES[0]])
    t['TRANSACTION_TYPE']='Delivery'
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[0],QUANTITY=1)])])
    row=build_flock_current_report(f,t,a,DAY).iloc[0]
    assert row['Counted']==row['Inventory']=='—'
    assert row['Notes']=='Delivery conflict'
