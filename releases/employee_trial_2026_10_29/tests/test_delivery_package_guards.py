"""Final candidate completeness and calculation safety; offline only."""
from pathlib import Path
import hashlib
import json

import pytest
import yaml

from data.quota_position import load_rules
from tests.test_delivery_base_snapshots import position, transaction


def test_unknown_type_is_not_hidden_by_a_later_snapshot():
    rows=[transaction('unknown','DEV_TEST unknown activity',5,'2026-01-01'),
          transaction('base','Base',100,'2026-02-01')]
    result=position(rows)
    assert result['net_position'] is None
    assert result['unknown_type_count']==1


def test_runtime_rules_file_is_shipped_and_stays_pending():
    root=Path(__file__).resolve().parents[1]
    cfg=yaml.safe_load((root/'snowflake.yml').read_text(encoding='utf-8'))
    sources=[x if isinstance(x,str) else x['src'] for x in cfg['entities']['efns_dev']['artifacts']]
    assert 'config/quota_rules.json' in sources
    assert 'data/*.py' in sources
    rules=load_rules()
    assert rules['status']=='PENDING' and rules['units_compatible'] is False
    assert rules['flock_stock']['status']=='PENDING'


def test_all_declared_runtime_changes_match_current_bytes():
    root=Path(__file__).resolve().parents[1]
    diff=json.loads((root/'DELIVERY_RUNTIME_DIFF_20261030.json').read_text(encoding='utf-8'))
    assert diff['baseline_files']==89 and diff['candidate_artifacts']==95
    for row in diff['runtime_changes']:
        assert row['status']!='DELETED'
        actual=hashlib.sha256((root/row['path']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        assert actual==row['candidate_lf_sha256'],row['path']
