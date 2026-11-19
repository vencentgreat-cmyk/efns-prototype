"""Staff-facing empty explanations without changing report eligibility or values."""
from pathlib import Path

import pytest

from tests.auth_support import authenticated_app
from tests.test_report_smoke import smoke_repository
from app.services.production_reports import NEST_FIELDS, build_nest_run_report
from data.business_time import halifax_today

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('entrypoint', ['streamlit_app.py', 'app/Home.py'])
@pytest.mark.parametrize('case,source_weeks,included', [
    ('no_weeks', 0, 0), ('excluded', 1, 0), ('included', 1, 1),
])
def test_nest_run_counts_explain_source_vs_inclusion(entrypoint,case,source_weeks,included,tmp_path,monkeypatch):
    repo = smoke_repository('normal')
    records = repo._production.copy(deep=True)
    if case == 'no_weeks':
        records = records.iloc[:0].copy()
    elif case == 'excluded':
        records['MARKETING_TYPE'] = 'RE'
        records.loc[:,list(NEST_FIELDS.values())] = 0
    repo.get_production_report_records = lambda start,end: records.copy(deep=True)
    year = halifax_today().year
    frame,metadata = build_nest_run_report(records,repo.get_accounts(),year,year*100+1,year*100+53)
    assert metadata['source_week_count'] == source_weeks
    assert metadata['included_row_count'] == included
    assert len(frame.loc[frame['Row Type'].eq('Data')]) == included
    app = authenticated_app(ROOT/entrypoint,tmp_path,monkeypatch)
    app.session_state['_base_repo'] = repo
    app.switch_page('pages/4_Reports.py' if entrypoint == 'app/Home.py' else 'app/pages/4_Reports.py').run()
    app.session_state['report_center_open_report'] = 'production-nest-run'
    app.run()
    app.button(key='run_production_nest_run').click().run()
    assert not app.error and not app.exception
    assert any(item.value == f'Source weeks found: {source_weeks}; Included rows: {included} (excluding totals).'
               for item in app.caption)
    messages = [item.value for item in app.info]
    if case == 'no_weeks':
        assert 'No production weeks were found for the requested year and week range.' in messages
        assert not any('no rows pass' in message for message in messages)
    elif case == 'excluded':
        assert 'Production weeks were found, but no rows pass the current provisional Nest Run inclusion rule.' in messages
        assert not any('No production weeks were found' in message for message in messages)
    else:
        assert not any('no rows pass' in message or 'No production weeks were found' in message for message in messages)


@pytest.mark.parametrize('entrypoint', ['streamlit_app.py', 'app/Home.py'])
def test_flock_age_empty_result_has_explicit_explanation(entrypoint,tmp_path,monkeypatch):
    app = authenticated_app(ROOT/entrypoint,tmp_path,monkeypatch)
    app.session_state['_base_repo'] = smoke_repository('empty')
    app.switch_page('pages/4_Reports.py' if entrypoint == 'app/Home.py' else 'app/pages/4_Reports.py').run()
    app.session_state['report_center_open_report'] = 'flock-age'
    app.run()
    app.button(key='run_flock_age').click().run()
    assert not app.error and not app.exception
    assert app.session_state['flock_age_result'].empty
    assert any(item.value == 'No flocks are included for the selected Flock Age report parameters. Review the filters and any evidence notes above.'
               for item in app.info)
