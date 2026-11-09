"""Staff trial display gate; no changes to quota contexts or Report Center."""
from pathlib import Path

import pytest

from app.services import quota_usage
from tests.auth_support import authenticated_app
from tests.test_staff_workflows import chain

TITLE='Historical / registered Bird Count — not current inventory'
METRICS={'Current usable quota','Recorded Bird Count total','Current occupancy','Usage percentage'}
COMPONENT='Recorded component quantity (not a balance)'


def test_quota_panel_defaults_to_hidden():
    assert quota_usage.SHOW_QUOTA_USAGE_PANEL is False


@pytest.mark.parametrize('renderer',['account','flock'])
def test_hidden_render_helpers_emit_nothing_and_create_no_containers(renderer,monkeypatch):
    import streamlit as st
    monkeypatch.setattr(quota_usage,'SHOW_QUOTA_USAGE_PANEL',False)
    def forbidden(*args,**kwargs):
        pytest.fail('Hidden panel must not load its context or create any UI elements')
    monkeypatch.setattr(quota_usage,'account_usage_context',forbidden)
    for name in ('subheader','caption','metric','columns','container','expander','dataframe','info','warning','write'):
        monkeypatch.setattr(st,name,forbidden)
    if renderer=='account':
        assert quota_usage.render_account_usage(object(),'account') is None
    else:
        assert quota_usage.render_quota_usage(object(),{'ACCOUNT_ID':'account','FLOCK_QUOTA_TYPE':'Egg Production'}) is None


@pytest.mark.parametrize('enabled',[False,True])
@pytest.mark.parametrize('page,entity',[
    ('5_Flocks','flock'),('3_Accounts_Facilities_Flocks','account'),('7_Quota_Registrations','quota')])
def test_actual_pages_hide_or_restore_complete_panel(page,entity,enabled,chain,tmp_path,monkeypatch):
    repo,account,_other,_facility,quota,flock,_record=chain
    monkeypatch.setattr(quota_usage,'SHOW_QUOTA_USAGE_PANEL',enabled)
    original=quota_usage.account_usage_context
    def context(*args,**kwargs):
        result=original(*args,**kwargs)
        # Deterministic display-only component fixture; business context tests
        # remain unchanged and continue exercising the actual calculation.
        result['summaries'][0]['position']['components']={'Base':123}
        return result
    monkeypatch.setattr(quota_usage,'account_usage_context',context)
    root=Path(__file__).resolve().parents[1]
    app=authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.session_state[f'_efns_record_{page}_view']='detail'
    app.session_state[f'_efns_record_{page}_id']={'flock':flock,'account':account,'quota':quota}[entity]
    app.switch_page('app/pages/'+page+'.py').run()
    assert not app.exception and not app.error
    assert any(item.value==TITLE for item in app.subheader) is enabled
    assert METRICS.issubset({item.label for item in app.metric}) is enabled
    assert any('Calculation basis pending confirmation' in item.value for item in app.caption) is enabled
    assert any(item.label=='Calculation basis and limitations' for item in app.expander) is enabled
    assert any(COMPONENT in item.value.columns for item in app.dataframe) is enabled
    assert any('Account-wide recorded Bird Count' in item.value for item in app.caption) is enabled
    assert any('owner transaction records shown as activity only' in item.value for item in app.caption) is enabled
    # The existing surrounding record layout remains populated in both states.
    expected_tabs=['Summary','Details'] if entity=='flock' else ['Summary','Related Records']
    assert [item.label for item in app.tabs][:2]==expected_tabs
    if entity=='account':
        assert any('Account Information' in item.value for item in app.markdown)
    elif entity=='flock':
        assert any('Latest Count:' in item.value for item in app.caption)
    else:
        assert any('**Registration Number**' in item.value for item in app.markdown)
