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


def test_native_light_config_is_theme_only_and_deployed_exactly_once():
    config = tomllib.loads((ROOT/'.streamlit/config.toml').read_text())
    assert set(config) == {'theme'}
    theme = config['theme']
    assert theme['base'] == 'light'
    assert theme['primaryColor'] == '#3F56D9'
    assert theme['showWidgetBorder'] is True
    project = yaml.safe_load((ROOT/'snowflake.yml').read_text())['entities']['efns_dev']
    artifacts = project['artifacts']
    assert sum(isinstance(a, dict) and a.get('src') == '.streamlit/config.toml' and a.get('dest') == '.streamlit/config.toml' for a in artifacts) == 1
    assert project['main_file'] == 'streamlit_app.py' and project['pages_dir'] == 'app/pages/'
    assert all('secrets' not in str(a) for a in artifacts)


@pytest.mark.parametrize('foreground,background', [
    ('#172033','#FFFFFF'), ('#172033','#F6F8FC'), ('#172033','#F1F5F9'),
    ('#475467','#FFFFFF'), ('#475467','#E8EEFB'), ('#FFFFFF','#3F56D9'),
    ('#172554','#E8EEFB'), ('#2453BE','#FFFFFF'),
    ('#FFFFFF','#2236AA'),
])
def test_theme_text_contrast(foreground, background):
    assert contrast(foreground, background) >= 4.5


def test_custom_styles_do_not_repaint_native_states():
    from unittest.mock import patch
    from app.ui import apply_theme
    with patch('app.ui.st.markdown') as output:
        apply_theme()
    css = output.call_args.args[0]
    assert 'h1.efns-page-title' in css and 'color: #172033 !important' in css
    assert 'background: #e8eefb' in css
    for forbidden in ('stButton', 'stDataFrame', 'data-baseweb', 'button {', 'input {', 'html {'):
        assert forbidden not in css
