"""Missing/broken rule files must fail closed, not break a page."""
import logging

import pytest

from data import quota_position as module


@pytest.mark.parametrize('contents',[None,'{ invalid JSON','[]','{"status":"CONFIRMED","flock_stock":null}'])
def test_missing_or_invalid_rule_file_returns_independent_pending_default(tmp_path,monkeypatch,caplog,contents):
    path=tmp_path/'rules.json'
    if contents is not None:path.write_text(contents,encoding='utf-8')
    monkeypatch.setattr(module,'RULES_PATH',path)
    with caplog.at_level(logging.WARNING):
        first=module.load_rules()
    assert first['status']=='PENDING' and first['flock_stock']['status']=='PENDING'
    assert first['units_compatible'] is False
    assert any('PENDING' in record.message for record in caplog.records)
    first['status']='CONFIRMED';first['flock_stock']['status']='CONFIRMED'
    second=module.load_rules()
    assert second['status']=='PENDING' and second['flock_stock']['status']=='PENDING'


def test_valid_rule_file_remains_readable(tmp_path,monkeypatch):
    path=tmp_path/'rules.json'
    path.write_text('{"status":"PENDING","type_sign":{},"flock_stock":{"status":"PENDING","type_sign":{}}}',encoding='utf-8')
    monkeypatch.setattr(module,'RULES_PATH',path)
    assert module.load_rules()['type_sign']=={}
