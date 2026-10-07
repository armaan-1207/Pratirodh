import json
import site
import pytest
from tools.audit_container_dependencies import INVENTORY, applicable


def test_bundle_without_metadata_is_inventoried(tmp_path, monkeypatch, capsys):
    root = tmp_path / 'pip/_vendor'
    (root / 'msgpack').mkdir(parents=True)
    (root / 'vendor.txt').write_text('msgpack==1.1.2\n')
    monkeypatch.setattr(site, 'getsitepackages', lambda: [str(tmp_path)])
    exec(INVENTORY, {})
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 1 and rows[0]['name'] == 'msgpack' and rows[0]['version'] == '1.1.2'


def test_missing_bundled_component_cannot_pass_inventory(tmp_path, monkeypatch):
    root = tmp_path / 'pip/_vendor'
    root.mkdir(parents=True)
    (root / 'vendor.txt').write_text('msgpack==1.1.2\n')
    monkeypatch.setattr(site, 'getsitepackages', lambda: [str(tmp_path)])
    with pytest.raises(ValueError, match='no installed module'):
        exec(INVENTORY, {})


def test_partial_pkg_resources_review_is_narrow():
    rows = [{'name': 'setuptools', 'version': '70.3.0', 'pkg_resources_only': True}]
    advisory = {'id': 'PYSEC-2025-49', 'aliases': ['CVE-2025-47273']}
    assert not applicable(rows, 'setuptools', '70.3.0', advisory)
    assert not applicable(rows, 'setuptools', '70.3.0', {'id': 'PYSEC-2026-3447'})
    assert applicable(rows, 'setuptools', '70.3.0', {'id': 'CVE-OTHER'})
    assert applicable(rows, 'urllib3', '2.7.0', advisory)
    rows.append({'name': 'setuptools', 'version': '70.3.0'})
    assert applicable(rows, 'setuptools', '70.3.0', advisory)
