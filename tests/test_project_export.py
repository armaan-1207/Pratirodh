import json
import zipfile
import pytest
from pratirodh.evidence import Store, new_id
from pratirodh.projects.export import export_bundle, verify_bundle


def bundle(tmp_path):
    store = Store(tmp_path / 'store')
    child = new_id()
    store.save({'id': child, 'created': '2026-10-02', 'decision': 'REJECTED'}, {'candidate.json': '{}'})
    parent = new_id()
    store.save({'id': parent, 'created': '2026-10-02', 'decision': 'PARTIAL',
                'rows': [{'run_id': child}]}, {'campaign.json': '{}'})
    path = tmp_path / 'bundle.zip'
    export_bundle(store, parent, path)
    return path, (store.root / 'trust.pub').read_bytes()


def test_campaign_export_includes_verified_referenced_runs(tmp_path):
    path, trusted = bundle(tmp_path)
    result = verify_bundle(path, trusted)
    assert result['signed_records'] == 2
    assert result['trust_verified']
    with pytest.raises(ValueError, match='trust anchor'):
        verify_bundle(path, b'0' * 32)


def test_export_rejects_unsigned_extra_artifacts(tmp_path):
    path, trusted = bundle(tmp_path)
    with zipfile.ZipFile(path, 'a') as archive:
        archive.writestr('evidence/unsigned.json', '{}')
    with pytest.raises(ValueError, match='unsigned entries'):
        verify_bundle(path, trusted)


def test_export_detects_modified_artifact(tmp_path):
    path, trusted = bundle(tmp_path)
    altered = tmp_path / 'altered.zip'
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(altered, 'w') as output:
        for name in source.namelist():
            payload = source.read(name)
            output.writestr(name, b'{}' if name == 'evidence/report.json' else payload)
    with pytest.raises(ValueError, match='integrity'):
        verify_bundle(altered, trusted)
