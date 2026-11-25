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
    assert rules['status']=='CONFIRMED' and rules['units_compatible'] is False
    assert rules['confirmed_by']=='Yuxin Yang / validated against legacy Flock Age report 2026-11-05'
    assert rules['flock_stock']['status']=='PENDING'


def test_all_declared_runtime_changes_match_current_bytes():
    root=Path(__file__).resolve().parents[1]
    diff=json.loads((root/'DELIVERY_RUNTIME_DIFF_20261030.json').read_text(encoding='utf-8'))
    baseline=json.loads((root/'RELEASE_SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    assert diff['baseline_files']==len(baseline['runtime_files'])
    assert diff['candidate_artifacts']==len(shipped_paths(root))
    for row in diff_entries(diff):
        assert row['status']!='DELETED'
        actual=hashlib.sha256((root/row['path']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        assert actual==row['candidate_lf_sha256'],row['path']


def diff_entries(value):
    if isinstance(value,dict):
        if 'path' in value and 'candidate_lf_sha256' in value:yield value
        for child in value.values():yield from diff_entries(child)
    elif isinstance(value,list):
        for child in value:yield from diff_entries(child)


def shipped_paths(root):
    config=yaml.safe_load((root/'snowflake.yml').read_text(encoding='utf-8'))
    paths=set()
    for artifact in config['entities']['efns_dev']['artifacts']:
        pattern=artifact if isinstance(artifact,str) else artifact['src']
        matches=[path for path in root.glob(pattern) if path.is_file()]
        assert matches, f'No shipped files match artifact {pattern}'
        paths.update(path.relative_to(root).as_posix() for path in matches)
    return paths


def assert_complete_shipped_diff(root, baseline, diff):
    originals={row['path']:row for row in baseline['runtime_files']}
    declared={row['path']:row for row in diff_entries(diff)}
    for path in shipped_paths(root):
        raw=(root/path).read_bytes()
        binary=Path(path).suffix=='.png'
        actual=hashlib.sha256(raw if binary else raw.replace(b'\r\n',b'\n')).hexdigest()
        before=originals.get(path,{})
        original=before.get('captured_deployed_sha256' if binary else 'repository_lf_sha256')
        if actual==original:continue
        assert path in declared, f'Unregistered modified/new shipped file: {path}'
        field='candidate_sha256' if binary else 'candidate_lf_sha256'
        assert actual==declared[path].get(field), f'Shipped-file hash mismatch: {path}'


def test_every_shipped_file_is_original_or_registered():
    root=Path(__file__).resolve().parents[1]
    baseline=json.loads((root/'RELEASE_SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    diff=json.loads((root/'DELIVERY_RUNTIME_DIFF_20261030.json').read_text(encoding='utf-8'))
    assert_complete_shipped_diff(root,baseline,diff)
    assert 'app/pages/3_Accounts_Facilities_Flocks.py' in {row['path'] for row in diff_entries(diff)}


@pytest.mark.parametrize('change',['modified','new','binary-new','wrong-hash'])
def test_completeness_guard_rejects_unregistered_or_wrong_shipped_bytes(tmp_path,change):
    (tmp_path/'app').mkdir()
    (tmp_path/'snowflake.yml').write_text('entities:\n  efns_dev:\n    artifacts:\n      - app/*\n',encoding='utf-8')
    original=b'original synthetic file\n';path=tmp_path/'app/existing.py';path.write_bytes(original)
    baseline={'runtime_files':[{'path':'app/existing.py','repository_lf_sha256':hashlib.sha256(original).hexdigest()}]}
    diff={}
    assert_complete_shipped_diff(tmp_path,baseline,diff)
    if change in {'modified','wrong-hash'}:path.write_bytes(b'modified synthetic file\n')
    else:(tmp_path/('app/new.png' if change=='binary-new' else 'app/new.py')).write_bytes(b'synthetic new bytes')
    if change=='wrong-hash':diff={'runtime_changes':[{'path':'app/existing.py','candidate_lf_sha256':hashlib.sha256(original).hexdigest()}]}
    with pytest.raises(AssertionError,match='Unregistered|hash mismatch'):
        assert_complete_shipped_diff(tmp_path,baseline,diff)
