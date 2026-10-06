"""Opt-in pinned-source verification; target code runs only in Docker."""
import os
import subprocess

import pytest
from pratirodh.evidence import Store
from pratirodh.projects.requests_demo import IMAGE_TAG, run_demo


@pytest.mark.skipif(os.getenv('PRATIRODH_DOCKER_TESTS') != '1', reason='opt-in real Linux worker tests')
def test_reference_fix_and_unsafe_mutation_with_real_requests(tmp_path):
    image = subprocess.check_output(['docker', '--context', 'default', 'image', 'inspect',
        IMAGE_TAG, '--format', '{{.Id}}'], text=True, timeout=15).strip()
    store = Store(tmp_path / 'evidence')
    rows = run_demo(tmp_path / 'requests-demo', store, image)
    assert [row['decision'] for row in rows] == ['REJECT', 'READY_FOR_REVIEW']
    assert all(row['matched_expectation'] for row in rows)
    reports = [store.load(row['id']) for row in rows]
    assert all(report['model_calls'] == 0 and report['assurance'] == 'DEMO_ONLY' for report in reports)
    fixed = reports[1]['candidates'][0]
    assert all(check['status'] == 'PASS' for check in fixed['checks'])
    assert len(fixed['mutations']) == 1
    assert fixed['mutations'][0]['status'] == 'CONFIRMED_UNSAFE'
    assert fixed['mutations'][0]['caught'] is True
