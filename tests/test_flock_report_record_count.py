"""Synthetic Flock record counts, not bird counts or real company fixtures."""
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.security import AuthorizationError
from app.services.report_center import (
    FLOCK_RECORD_COUNT, FLOCK_RECORD_COUNT_LABEL,
    build_custom_report, report_csv, report_xlsx,
)
from data.repositories.mock import MockRepository
from tests.auth_support import authenticated_app
from tests.test_report_center import user


COUNTS = [10, 14, 5, 2, 2, 2]


@pytest.fixture
def repo():
    r = MockRepository()
    r._accounts = pd.DataFrame([
        dict(ACCOUNT_ID='synthetic-host', ORGANIZATION_NAME='Synthetic facility owner'),
        dict(ACCOUNT_ID='synthetic-flock-owner', ORGANIZATION_NAME='Synthetic flock owner'),
        dict(ACCOUNT_ID='synthetic-other', ORGANIZATION_NAME='Synthetic other owner'),
    ])
    r._facilities = pd.DataFrame([
        dict(FACILITY_ID=f'synthetic-facility-{i}', FACILITY_NAME=f'Synthetic facility {i}',
             ACCOUNT_ID='synthetic-host', STATUS='Active') for i in range(6)
    ] + [dict(FACILITY_ID='synthetic-other-facility', FACILITY_NAME='Synthetic other facility',
              ACCOUNT_ID='synthetic-other', STATUS='Active')])
    rows = []
    for i, count in enumerate(COUNTS):
        for n in range(count):
            rows.append(dict(FLOCK_ID=f'synthetic-flock-{i}-{n}', FLOCK_NUMBER=f'SYNTHETIC-{i}-{n}',
                ACCOUNT_ID='synthetic-flock-owner', FACILITY_ID=f'synthetic-facility-{i}',
                STATUS='Active', BIRD_COUNT=[None, 0, -5, 100][n % 4]))
    rows.append(dict(FLOCK_ID='synthetic-excluded', FLOCK_NUMBER='SYNTHETIC-EXCLUDED',
        ACCOUNT_ID='synthetic-other', FACILITY_ID='synthetic-other-facility', STATUS='Active', BIRD_COUNT=999))
    r._flocks = pd.DataFrame(rows)
    return r


def run(repo, **kwargs):
    args = dict(user=user(), dataset='Flocks', selected_fields=['FLOCK_ID', 'FACILITY_ID'],
        filters={'facility_account_id': 'synthetic-host'})
    args.update(kwargs)
    return build_custom_report(repo, **args)


def assert_six_groups(result):
    assert list(result.columns) == ['Facility ID', FLOCK_RECORD_COUNT_LABEL]
    assert len(result) == 6
    assert result.set_index('Facility ID')[FLOCK_RECORD_COUNT_LABEL].to_dict() == {
        f'synthetic-facility-{i}': n for i, n in enumerate(COUNTS)
    }
    assert result[FLOCK_RECORD_COUNT_LABEL].sum() == 35


def assert_exports(result):
    for frame in (pd.read_csv(BytesIO(report_csv(user(), result))),
                  pd.read_excel(BytesIO(report_xlsx(user(), result)))):
        pd.testing.assert_frame_equal(result, frame, check_dtype=False)


@pytest.mark.parametrize('explicit', [False, True])
def test_group_counts_without_any_numeric_output_and_legacy_none(repo, explicit):
    before = repo._flocks.copy(deep=True)
    detail = run(repo)
    assert len(detail) == 35
    grouped = run(repo, group_by=['FACILITY_ID'], count_records=explicit)
    assert_six_groups(grouped)
    assert_exports(grouped)
    pd.testing.assert_frame_equal(repo._flocks, before)


def test_filters_and_names_preserve_facility_id_grain(repo):
    repo._facilities.loc[:1, 'FACILITY_NAME'] = 'Synthetic same label'
    result = run(repo, selected_fields=['FACILITY_ID', 'FACILITY_NAME'],
        group_by=['FACILITY_ID', 'FACILITY_NAME'], count_records=True,
        filters={'facility_account_id':'synthetic-host', 'account_id':'synthetic-flock-owner'})
    assert len(result) == 6 and result[FLOCK_RECORD_COUNT_LABEL].sum() == 35
    assert_exports(result)
    filtered = run(repo, group_by=['FACILITY_ID'], filters={
        'facility_account_id':'synthetic-host', 'facility_id':'synthetic-facility-0'})
    assert len(filtered) == 1 and filtered.iloc[0][FLOCK_RECORD_COUNT_LABEL] == 10


def test_missing_facility_count_is_not_dropped_and_birds_are_not_counted(repo):
    repo._flocks = pd.DataFrame([
        dict(FLOCK_ID='synthetic-a', FACILITY_ID=None, BIRD_COUNT=None),
        dict(FLOCK_ID='synthetic-b', FACILITY_ID=None, BIRD_COUNT=0),
        dict(FLOCK_ID='synthetic-c', FACILITY_ID='synthetic-facility-0', BIRD_COUNT=-100),
    ])
    result = run(repo, filters={}, group_by=['FACILITY_ID'])
    assert len(result) == 2 and result[FLOCK_RECORD_COUNT_LABEL].sum() == 3
    assert result.loc[result['Facility ID'].isna(), FLOCK_RECORD_COUNT_LABEL].tolist() == [2]
    assert_exports(result)


def test_empty_count_retains_columns_and_no_phantom_groups(repo):
    result = run(repo, group_by=['FACILITY_ID'], filters={'facility_account_id':'missing'})
    assert result.empty
    assert list(result.columns) == ['Facility ID', FLOCK_RECORD_COUNT_LABEL]
    assert_exports(result)
    repo._flocks['FACILITY_ID'] = pd.Categorical(repo._flocks.FACILITY_ID,
        categories=[*repo._facilities.FACILITY_ID, 'synthetic-unused'])
    result = run(repo, filters={}, group_by=['FACILITY_ID'])
    assert 'synthetic-unused' not in result['Facility ID'].tolist()


def test_numeric_sum_detail_sort_and_permissions_are_preserved(repo):
    result = run(repo, group_by=['FACILITY_ID'], count_records=True,
        sort_by=FLOCK_RECORD_COUNT, ascending=False)
    assert result[FLOCK_RECORD_COUNT_LABEL].tolist() == [14, 10, 5, 2, 2, 2]
    numeric = run(repo, selected_fields=['FACILITY_ID', 'BIRD_COUNT'],
        group_by=['FACILITY_ID'], aggregations={'BIRD_COUNT':'sum'})
    assert FLOCK_RECORD_COUNT_LABEL not in numeric and 'Bird Count' in numeric
    assert len(run(repo)) == 35
    with pytest.raises(AuthorizationError):run(repo, user=user(active=False), group_by=['FACILITY_ID'])


def test_status_and_explicit_date_filters_apply_before_count(repo):
    repo._flocks.loc[0, 'STATUS'] = 'Planned'
    repo._flocks['PLACEMENT_DATE'] = '2026-01-02'
    repo._flocks.loc[0, 'PLACEMENT_DATE'] = '2025-01-02'
    for extra in ({'statuses':('Active',)}, {'date_field':'PLACEMENT_DATE', 'date_from':'2026-01-01'}):
        result = run(repo, group_by=['FACILITY_ID'], filters={'facility_account_id':'synthetic-host', **extra})
        assert len(result) == 6 and result[FLOCK_RECORD_COUNT_LABEL].sum() == 34
        assert result.set_index('Facility ID').loc['synthetic-facility-0', FLOCK_RECORD_COUNT_LABEL] == 9
        assert_exports(result)


def test_duplicate_flock_ids_are_not_silently_counted(repo):
    duplicated = pd.concat([repo._flocks, repo._flocks.iloc[:1]], ignore_index=True)
    repo.get_flocks = lambda **kwargs: duplicated.copy()
    with pytest.raises(ValueError, match='Duplicate report record identifiers'):
        run(repo, group_by=['FACILITY_ID'])


def test_explicit_count_requires_group_and_cannot_mix_numeric_aggregation(repo):
    with pytest.raises(ValueError, match='grouping field'):run(repo, count_records=True)
    with pytest.raises(ValueError, match='either Flock record count'):
        run(repo, selected_fields=['FACILITY_ID', 'BIRD_COUNT'], group_by=['FACILITY_ID'],
            aggregations={'BIRD_COUNT':'sum'}, count_records=True)


def test_page_group_count_detail_and_saved_configuration(repo, tmp_path, monkeypatch):
    import app.services.report_center as center
    emitted = {}
    def csv_export(actor, frame):
        content = report_csv(actor, frame)
        emitted['csv'] = (frame.copy(), content)
        return content
    def xlsx_export(actor, frame, sheet_name='EFNS Report'):
        content = report_xlsx(actor, frame, sheet_name)
        emitted['xlsx'] = (frame.copy(), content)
        return content
    monkeypatch.setattr(center, 'report_csv', csv_export)
    monkeypatch.setattr(center, 'report_xlsx', xlsx_export)
    app = authenticated_app(Path(__file__).parents[1]/'app/Home.py', tmp_path, monkeypatch)
    app.session_state._base_repo = repo
    app.session_state.repo = repo
    app.switch_page('pages/4_Reports.py').run()
    app.radio(key='report_center_section').set_value('Customize Report').run()
    app.selectbox(key='custom_report_dataset').set_value('Flocks').run()
    app.multiselect(key='custom_report_columns').set_value(['Flock ID', 'Facility ID', 'Facility Name']).run()
    account = next(v for v in app.selectbox(key='custom_filter_facility_account').options if v.startswith('Synthetic facility owner'))
    app.selectbox(key='custom_filter_facility_account').set_value(account).run()
    next(b for b in app.button if b.label == 'Run Report').click().run()
    assert len(app.session_state.custom_report_result) == 35
    app.multiselect(key='custom_report_group').set_value(['Facility ID']).run()
    assert app.selectbox(key='custom_report_aggregate_field').options == [FLOCK_RECORD_COUNT_LABEL]
    next(b for b in app.button if b.label == 'Run Report').click().run()
    assert not app.exception and not app.error
    result = app.session_state.custom_report_result
    assert_six_groups(result)
    assert any(table.value.equals(result) for table in app.dataframe)
    assert_exports(result)
    for kind in ('csv', 'xlsx'):
        pd.testing.assert_frame_equal(emitted[kind][0], result)
        exported = pd.read_csv(BytesIO(emitted[kind][1])) if kind == 'csv' else pd.read_excel(BytesIO(emitted[kind][1]))
        pd.testing.assert_frame_equal(exported, result, check_dtype=False)
    assert app.session_state.custom_report_configuration['count_records'] is True
    assert_six_groups(build_custom_report(repo, user=user(), **app.session_state.custom_report_configuration))
    app.selectbox(key='custom_report_sort').set_value(FLOCK_RECORD_COUNT_LABEL).run()
    app.radio(key='custom_report_direction').set_value('Descending').run()
    next(b for b in app.button if b.label == 'Run Report').click().run()
    assert app.session_state.custom_report_result[FLOCK_RECORD_COUNT_LABEL].tolist() == [14, 10, 5, 2, 2, 2]
    app.multiselect(key='custom_report_group').set_value([]).run()
    next(b for b in app.button if b.label == 'Run Report').click().run()
    assert not app.exception and not app.error
    assert len(app.session_state.custom_report_result) == 35
    assert FLOCK_RECORD_COUNT_LABEL not in app.session_state.custom_report_result
