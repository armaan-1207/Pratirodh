"""Opt-in pinned-source verification; target code runs only in Docker."""
import os
import subprocess
import json
from pathlib import Path

import pytest
from pratirodh.evidence import Store
from pratirodh.projects.requests_demo import IMAGE_TAG, run_demo
from tools.requests_diagnostics import summarize


@pytest.mark.skipif(os.getenv('PRATIRODH_DOCKER_TESTS') != '1', reason='opt-in real Linux worker tests')
def test_reference_fix_and_unsafe_mutation_with_real_requests(tmp_path):
    image = subprocess.check_output(['docker', '--context', 'default', 'image', 'inspect',
        IMAGE_TAG, '--format', '{{.Id}}'], text=True, timeout=15).strip()
    store = Store(tmp_path / 'evidence')
    partial = []
    try:
        rows = run_demo(tmp_path / 'requests-demo', store, image, result_callback=partial.append)
    finally:
        diagnostic = summarize([store.load(row['id']) for row in partial])
        output = Path('run_output/ci-diagnostics/requests.json')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(diagnostic, indent=2) + '\n', encoding='utf-8')
    assert [row['decision'] for row in rows] == ['REJECT', 'READY_FOR_REVIEW'], json.dumps(diagnostic)
    assert all(row['matched_expectation'] for row in rows)
    reports = [store.load(row['id']) for row in rows]
    assert all(report['model_calls'] == 0 and report['assurance'] == 'DEMO_ONLY' for report in reports)
    fixed = reports[1]['candidates'][0]
    assert all(check['status'] == 'PASS' for check in fixed['checks'])
    assert len(fixed['mutations']) == 1
    assert fixed['mutations'][0]['status'] == 'CONFIRMED_UNSAFE'
    assert fixed['mutations'][0]['caught'] is True


@pytest.mark.skipif(os.getenv('PRATIRODH_DOCKER_TESTS') != '1', reason='opt-in real Linux worker tests')
def test_requests_worker_has_no_unused_native_build_stack():
    import json
    probe = """import ctypes.util,importlib.util,json,pyexpat,shutil
print(json.dumps(dict(tools={n:shutil.which(n) for n in ['clang','clang++','cmake','make','node','npm']},
 libraries={n:ctypes.util.find_library(n) for n in ['xml2','expat','curl']},
 packaging={n:importlib.util.find_spec(n) is not None for n in ['pip','setuptools','wheel']},
 expat=pyexpat.version_info)))"""
    data = json.loads(subprocess.check_output(['docker', '--context', 'default', 'run', '--rm',
        '--network', 'none', '--entrypoint', 'python', IMAGE_TAG, '-c', probe], text=True, timeout=30))
    assert not any(data['tools'].values()), data
    assert not any(data['libraries'].values()), data
    assert not any(data['packaging'].values()), data
    # CPython's bundled parser is distinct from the removed OS libexpat1.
    assert tuple(data['expat']) >= (2, 8, 5), data
