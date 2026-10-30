"""T4: all app/data source text remains free of Han characters."""
from pathlib import Path
import re


def test_app_and_data_contain_no_cjk_text():
    root = Path(__file__).resolve().parents[1]
    cjk = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f]')
    suffixes = {'.py', '.css', '.html', '.js', '.ts', '.json', '.toml', '.yaml', '.yml'}
    findings = []
    for directory in ('app', 'data'):
        for path in (root/directory).rglob('*'):
            if path.is_file() and path.suffix in suffixes:
                for line, value in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
                    if cjk.search(value):
                        findings.append(f'{path.relative_to(root)}:{line}')
    assert not findings, findings
