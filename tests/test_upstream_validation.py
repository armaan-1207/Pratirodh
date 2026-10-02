import json
from pathlib import Path

from pratirodh.upstream_status import load_status
from pratirodh.web import create_app


ROOT = Path(__file__).resolve().parents[1]


def test_upstream_manifest_is_balanced_and_explicitly_gated():
    manifest = json.loads((ROOT / 'benchmark/upstream-v1/manifest.json').read_text(encoding='utf-8'))
    assert manifest['target_count'] == 24
    assert len(manifest['cases']) == 24
    assert {x['language'] for x in manifest['cases']} == {'Python', 'JavaScript', 'C/C++'}
    assert all(sum(x['language'] == language for x in manifest['cases']) == 8 for language in manifest['counts'])
    assert all(x['repository_url'].startswith('https://github.com/') for x in manifest['cases'])
    assert all(x['advisory_url'].startswith('https://') for x in manifest['cases'])
    assert all(x['audit']['status'] == 'PENDING' for x in manifest['cases'])


def test_status_projection_never_invents_campaign_completion(tmp_path):
    manifest_dir = tmp_path / 'benchmark/upstream-v1'
    manifest_dir.mkdir(parents=True)
    (manifest_dir / 'manifest.json').write_text(json.dumps({'target_count': 24, 'cases': []}))
    state_dir = tmp_path / 'run_output/upstream-validation'
    state_dir.mkdir(parents=True)
    (state_dir / 'status.json').write_text(json.dumps({'qualified': 24, 'completed': 200, 'audited': 200}))
    status = load_status(tmp_path)
    assert status['target'] == 24
    assert status['qualified'] == 0
    assert status['completed'] == 0
    assert status['audited'] == 0
    assert status['release_complete'] is False


def test_validation_and_walkthrough_routes_are_explicit(tmp_path):
    client = create_app(store=__import__('pratirodh.evidence', fromlist=['Store']).Store(tmp_path)).test_client()
    validation = client.get('/validation')
    assert validation.status_code == 200
    assert b'24 upstream cases' in validation.data
    assert b'0 / 24' in validation.data
    walkthrough = client.get('/walkthrough')
    assert walkthrough.status_code == 200
    assert b'RECORDED RUN' in walkthrough.data
