"""Presentation-only light theme and deployment coverage."""
from pathlib import Path
import tomllib

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def luminance(hex_color):
    values = [int(hex_color[i:i+2], 16)/255 for i in (1,3,5)]
    linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in values]
    return sum(a*b for a,b in zip(linear, (.2126,.7152,.0722)))


def contrast(a, b):
    high, low = sorted((luminance(a),luminance(b)), reverse=True)
    return (high+.05)/(low+.05)


def test_native_light_config_and_sleep_setting_are_deployed_exactly_once():
    config = tomllib.loads((ROOT/'.streamlit/config.toml').read_text())
    assert set(config) == {'theme', 'snowflake'}
    assert config['snowflake'] == {'sleep': {'streamlitSleepTimeoutMinutes': 10}}
    theme = config['theme']
    assert theme['base'] == 'light'
    assert theme['primaryColor'] == '#225C80'
    assert theme['showWidgetBorder'] is True
    project = yaml.safe_load((ROOT/'snowflake.yml').read_text())['entities']['efns_dev']
    artifacts = project['artifacts']
    assert sum(isinstance(a, dict) and a.get('src') == '.streamlit/config.toml' and a.get('dest') == '.streamlit/config.toml' for a in artifacts) == 1
    assert project['main_file'] == 'streamlit_app.py' and project['pages_dir'] == 'app/pages/'
    assert all('secrets' not in str(a) for a in artifacts)


@pytest.mark.parametrize('foreground,background', [
    ('#202C32','#FFFFFF'), ('#202C32','#F7F6F2'), ('#202C32','#EEF2F1'),
    ('#55636B','#FFFFFF'), ('#55636B','#F7F6F2'), ('#FFFFFF','#225C80'),
    ('#225C80','#FFFFFF'), ('#225C80','#F7F6F2'),
    ('#9D3640','#F5EBEC'), ('#2E6B4E','#EAF0ED'),
    ('#7A5417','#F2EEE8'), ('#375E7A','#EBEFF2'),
])
def test_theme_text_contrast(foreground, background):
    assert contrast(foreground, background) >= 4.5


@pytest.mark.parametrize('foreground,background', [
    ('#FFFFFF', '#123144'),  # observed native focused primary button, 1.52.2
    ('#202C32', '#FBFBF9'),  # native secondary button surface
    ('#202C32', '#F0F0EB'),  # native selected dropdown option surface
    ('#225C80', '#FFFFFF'),  # focused input border against its white surface
])
def test_enabled_native_focus_and_selection_contrast(foreground, background):
    assert contrast(foreground, background) >= 4.5


def test_custom_styles_do_not_repaint_native_states():
    from unittest.mock import patch
    from app.ui import apply_theme
    with patch('app.ui.st.markdown') as output:
        apply_theme()
    css = output.call_args.args[0]
    assert '.efns-page-header h1.efns-page-title' in css and 'color: #202C32' in css
    assert 'background: #EBEFF2' in css
    assert 'font-family: "Source Serif", serif, sans-serif' in css
    assert 'box-shadow' not in css and 'gradient' not in css
    for forbidden in ('stButton', 'stDataFrame', 'data-baseweb', 'data-testid', 'button {', 'input {', 'html {'):
        assert forbidden not in css
