"""Offline validation of the shipped Snowflake sleep configuration."""
from pathlib import Path
import tomllib

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_sleep_timeout_is_valid_integer_in_supported_range():
    with (ROOT / '.streamlit/config.toml').open('rb') as source:
        config = tomllib.load(source)
    value = config['snowflake']['sleep']['streamlitSleepTimeoutMinutes']
    assert type(value) is int
    assert 5 <= value <= 240
    assert value == 10


def test_snowflake_artifacts_ship_streamlit_config_at_original_path():
    manifest = yaml.safe_load((ROOT / 'snowflake.yml').read_text(encoding='utf-8'))
    artifacts = manifest['entities']['efns_dev']['artifacts']
    assert any(isinstance(item, dict)
               and item.get('src') == '.streamlit/config.toml'
               and item.get('dest') == '.streamlit/config.toml'
               for item in artifacts)
