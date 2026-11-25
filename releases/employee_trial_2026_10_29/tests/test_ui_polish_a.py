"""Synthetic presentation regressions; no changes to business expectations."""
import ast
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from app.ui import page_header, section_intro, secondary_text
from tests.auth_support import authenticated_app
from tests.test_production_replacement import raw, repo as production_repo

ROOT = Path(__file__).resolve().parents[1]


class Outline(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.headings.append(int(tag[1]))


def outline(app):
    parser = Outline()
    for item in app.markdown:
        parser.feed(item.value)
    assert parser.headings.count(1) == 1
    assert all(b <= a + 1 for a, b in zip(parser.headings, parser.headings[1:]))
    return parser.headings


def test_shared_headings_escape_content_and_follow_outline():
    with patch('app.ui.st.markdown') as output:
        page_header('<script>title</script>', '<img src=x>', '<b>context</b>')
        section_intro('<img src=x>', '<script>copy</script>')
        section_intro('Supporting detail', level=3)
        secondary_text('<img src=x>')
    html = ''.join(call.args[0] for call in output.call_args_list)
    parser = Outline()
    parser.feed(html)
    assert parser.headings == [1, 2, 3]
    assert 'script' not in parser.tags and 'img' not in parser.tags and 'b' not in parser.tags
    assert '&lt;script&gt;title&lt;/script&gt;' in html and '&lt;b&gt;context&lt;/b&gt;' in html
    assert '&lt;img src=x&gt;' in html


@pytest.mark.parametrize('entrypoint', ['streamlit_app.py', 'app/Home.py'])
def test_every_page_has_one_title_and_no_skipped_heading_levels(entrypoint, tmp_path, monkeypatch):
    app = authenticated_app(ROOT / entrypoint, tmp_path, monkeypatch)
    outline(app)
    for page in sorted((ROOT / 'app/pages').glob('*.py')):
        relative = f'pages/{page.name}' if entrypoint == 'app/Home.py' else f'app/pages/{page.name}'
        app.switch_page(relative).run()
        assert not app.exception, page.name
        outline(app)


@pytest.mark.parametrize('entrypoint', ['streamlit_app.py', 'app/Home.py'])
@pytest.mark.parametrize('case', ['ready', 'errors', 'warnings', 'empty', 'committed'])
def test_import_disclosure_counts_button_state_and_unchanged_rows(entrypoint, case, tmp_path, monkeypatch):
    from data import importing, production_intake
    from data.production_replacement import upload_errors
    repository = production_repo()
    records = [] if case == 'empty' else [
        {'Producer #': '001', 'Week': 202601, 'Total': 3.125},
        {'Producer #': '001', 'Week': 202602, 'Total': 2.75},
    ]
    frame = raw(records)
    before = frame.copy(deep=True)
    errors = [f'Synthetic blocking error {i}' for i in range(35)] if case == 'errors' else []
    warnings = [f'Synthetic warning {i}' for i in range(34)] if case == 'warnings' else []
    original_prepare = production_intake.prepare_workbook
    expected, _, base_errors, base_warnings = original_prepare(frame, 'file', repository.get_accounts())
    expected_errors = upload_errors(frame, expected, base_errors + errors)
    expected_warnings = base_warnings + warnings
    staged = []
    original_stage = repository.stage_production_upload
    def stage(metadata, rows, *args, **kwargs):
        staged.append((metadata.copy(), [row.copy() for row in rows]))
        return original_stage(metadata, rows, *args, **kwargs)
    monkeypatch.setattr(repository, 'stage_production_upload', stage)
    if case == 'committed':
        monkeypatch.setattr(repository, 'find_import_by_hash', lambda *_: {'STATUS': 'Committed', 'IMPORT_ID': 'synthetic-import'})
    def prepare(*args, **kwargs):
        normalized, rows, actual_errors, actual_warnings = original_prepare(*args, **kwargs)
        return normalized, rows, [*actual_errors, *errors], [*actual_warnings, *warnings]
    monkeypatch.setattr(production_intake, 'prepare_workbook', prepare)
    monkeypatch.setattr(importing, 'read_eims_workbook', lambda _: frame.copy(deep=True))
    uploaded = BytesIO(b'synthetic in-memory workbook')
    uploaded.name = 'synthetic.xlsx'
    monkeypatch.setattr(st, 'file_uploader', lambda *args, **kwargs: uploaded)
    downloads = []
    original_download = st.download_button
    def download(label, data, *args, **kwargs):
        downloads.append((label, data))
        return original_download(label, data, *args, **kwargs)
    monkeypatch.setattr(st, 'download_button', download)
    app = authenticated_app(ROOT / entrypoint, tmp_path, monkeypatch)
    app.session_state['_base_repo'] = repository
    app.switch_page(('pages/' if entrypoint == 'app/Home.py' else 'app/pages/') + '1_Production_Import.py').run()
    assert not app.exception
    outline(app)
    assert {item.label: item.value for item in app.metric} == {
        'Production Records': str(len(frame)), 'Blocking Errors': str(len(expected_errors)), 'Warnings': str(len(expected_warnings)),
    }
    button = next(item for item in app.button if item.label == 'Import validated records')
    assert button.disabled is (case in ('errors', 'empty', 'committed'))
    disclosures = [item.value for item in app.markdown if 'efns-section-copy' in item.value]
    assert any('Showing 30 of 35 blocking errors' in text for text in disclosures) is (case == 'errors')
    assert any('Showing 30 of 34 warnings' in text for text in disclosures) is (case == 'warnings')
    for prefix, count in [('Synthetic blocking error ', 30 if errors else 0), ('Synthetic warning ', 30 if warnings else 0)]:
        assert sum(item.value.startswith('• ' + prefix) for item in app.markdown) == count
    issue_download = [data for label, data in downloads if label == 'Download validation issues']
    if expected_errors or expected_warnings:
        assert pd.read_csv(BytesIO(issue_download[-1]))['Validation issue'].tolist() == expected_errors + expected_warnings
    else:
        assert not issue_download
    assert any('replace the complete existing set' in item.value for item in app.markdown)
    assert any('does not execute macros or recalculate formulas' in item.value for item in app.info)
    assert any(item.label == 'Technical details' for item in app.expander)
    pd.testing.assert_frame_equal(frame, before, check_exact=True)
    pd.testing.assert_frame_equal(app.dataframe[-1].value, expected[[c for c in (
        'SOURCE_ROW_NUMBER', 'SOURCE_WEEK_CODE', 'REPORTING_YEAR', 'REPORTING_WEEK',
        'PRODUCER_NUMBER', 'GRADER_NUMBER', 'MARKETING_TYPE', 'HOUSING_SYSTEM',
        'EGG_TYPE', 'EGG_COLOUR', 'TOTAL', 'SOURCE_TYPE', 'MATCH_STATUS') if c in expected]].head(50), check_exact=True)
    assert staged[-1][0]['SOURCE_RECORD_COUNT'] == len(frame)
    assert len(staged[-1][1]) == len(frame)
    assert repository._production.empty  # presentation/rerun must not commit


def test_batch_reference_is_secondary_and_summary_numbers_are_unchanged():
    from app.services.production_import_review import summary_text
    summary = dict(import_id='synthetic-batch', rows_inserted=2, rows_replaced=3,
                   producer_weeks_replaced=1, rows_written=2, rows_unchanged=4,
                   week_start=202601, week_end=202602)
    app = AppTest.from_string('import streamlit as st\nfrom app.services.production_import_review import render_import_summary\nrender_import_summary(st.session_state.summary)')
    app.session_state['summary'] = summary
    app.run()
    assert not app.exception
    assert app.success[0].value == summary_text(summary).removeprefix('Batch synthetic-batch: ')
    assert 'synthetic-batch' not in app.success[0].value
    assert app.expander[0].label == 'Batch reference' and not app.expander[0].proto.expanded
    assert app.code[0].value == 'synthetic-batch'


@pytest.mark.parametrize('entrypoint', ['streamlit_app.py', 'app/Home.py'])
def test_reference_and_filtered_audit_empty_states(entrypoint, tmp_path, monkeypatch):
    repository = production_repo()
    for method in ('get_contacts', 'get_quota_allocations', 'get_efc_dates'):
        monkeypatch.setattr(repository, method, lambda *args, **kwargs: pd.DataFrame())
    app = authenticated_app(ROOT / entrypoint, tmp_path, monkeypatch)
    app.session_state['_base_repo'] = repository
    prefix = 'pages/' if entrypoint == 'app/Home.py' else 'app/pages/'
    app.switch_page(prefix + '20_EIMS_Reference_Data.py').run()
    assert not app.exception
    assert sum(item.value == 'No records match these filters.' for item in app.info) == 3
    from types import SimpleNamespace
    events = [SimpleNamespace(occurred_at='2026-01-01', actor_email='user-a@example.invalid', action='A', entity_type='X', entity_id='1', details={}),
              SimpleNamespace(occurred_at='2026-01-01', actor_email='user-b@example.invalid', action='B', entity_type='Y', entity_id='2', details={})]
    from app.security import SQLiteAuthStore
    monkeypatch.setattr(SQLiteAuthStore, 'list_audit', lambda *args, **kwargs: events)
    app.switch_page(prefix + '16_Audit_Log.py').run()
    app.selectbox[0].select('user-a@example.invalid')
    app.selectbox[1].select('B').run()
    assert not app.exception
    assert any(item.value == 'No records match these filters.' for item in app.info)
    assert any('latest 5,000 audit events' in item.value for item in app.caption)
    assert app.dataframe[0].value.empty


def test_polish_uses_only_supported_presentation_apis():
    source = (ROOT / 'app/ui.py').read_text()
    ast.parse(source)
    assert 'st.dialog' not in source and 'st.fragment' not in source and 'st.cache' not in source
    assert 'data-testid' not in source and 'data-baseweb' not in source
