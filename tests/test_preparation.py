"""Preparation is static and must not imply runtime qualification."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from pratirodh.projects.examples import create_example

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('preparation', ROOT / 'scripts/check_preparation.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def write(path, data):
    path.write_text(json.dumps(data), encoding='utf-8')


@pytest.fixture
def case(tmp_path):
    path = tmp_path / 'recipes/example'
    manifest, _ = create_example(path / 'target', 'python', 'sha256:' + 'a' * 64, 'execution-worker')
    manifest.rename(path / 'manifest.json')
    write(path / 'recipe.json', {'license_review': {'approved': True, 'identifier': 'MIT'},
                               'source_revision': 'a' * 40, 'fix_revision': 'b' * 40})
    write(path / 'audit.json', {'context': 'audit-worker', 'image': 'sha256:' + 'b' * 64,
                              'files': {'audit_check.py': 'assert 1 == 1\n'},
                              'checks': [{'role': role, 'command': ['python', 'audit_check.py'],
                                          'exit': 0, 'stdout': ''} for role in ('control', 'security')]})
    return path


def codes(case):
    return {x['code'] for x in checker.check_case(case)['blockers']}


def edit_audit(case, **changes):
    path = case / 'audit.json'
    data = json.loads(path.read_text())
    data.update(changes)
    write(path, data)


def test_complete_structure_does_not_claim_qualification(case, monkeypatch):
    monkeypatch.setattr(checker, 'probe_worker', lambda *args: pytest.fail('unexpected daemon probe'))
    result = checker.report(case.parent)
    assert result['summary']['structurally_ready'] == 1
    assert result['cases']['example']['qualification'] == 'NOT_CHECKED'
    assert result['cases']['example']['audit_independence'] == 'NOT_VERIFIED'
    assert set(result['workers'].values()) == {'NOT_CHECKED'}


@pytest.mark.parametrize('files,code', [({}, 'EMPTY_AUDIT'),
    ({'audit_check.py': 'a' * 64}, 'INVALID_AUDIT_FILE'),
    ({'audit_check.py': 'placeholder'}, 'INVALID_AUDIT_FILE'),
    ({'audit_check.py': 'def bad(:\n'}, 'INVALID_SOURCE'),
    ({'audit_check.py': '# audit coming soon\n'}, 'EMPTY_SOURCE'),
    ({'audit_check.py': 'def test_fake(): pass\n'}, 'EMPTY_TEST'),
    ({'../audit_check.py': 'assert True\n'}, 'INVALID_AUDIT_FILE'),
    ({'portal.py': 'assert True\n'}, 'AUDIT_SOURCE_COLLISION'),
    ({'readme.txt': 'source is forthcoming'}, 'AUDIT_TARGET_UNRESOLVED')])
def test_nonempty_files_are_insufficient(case, files, code):
    edit_audit(case, files=files)
    assert code in codes(case)


def test_selector_missing_and_indirect_commands_block(case):
    edit_audit(case, checks=[{'role': 'security', 'command': ['pytest', 'audit_check.py::test_missing'],
                             'exit': 0, 'stdout': ''}])
    assert {'MISSING_CHECK_SELECTOR', 'MISSING_AUDIT_ROLES'} <= codes(case)
    edit_audit(case, checks=[{'role': 'control', 'command': ['npm', 'test'], 'exit': 0}])
    assert {'UNRESOLVED_CHECK_TARGET', 'INVALID_AUDIT_ORACLE'} <= codes(case)


def test_stale_inventory_and_digest_block(case):
    (case / 'target/portal.py').write_text('print("changed")\n')
    edit_audit(case, digest='c' * 64)
    assert {'INVALID_MANIFEST', 'AUDIT_DIGEST_MISMATCH'} <= codes(case)


def test_malformed_shapes_report_blockers(case):
    (case / 'recipe.json').write_text('{')
    edit_audit(case, checks=[{'role': [], 'command': None, 'violation': []}], files={'audit.py': '\ud800'})
    assert {'INVALID_JSON', 'INVALID_AUDIT_FILE', 'INVALID_COMMAND', 'INVALID_AUDIT_ORACLE'} <= codes(case)


def test_worker_timeout_is_explicit(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired('docker', kwargs['timeout'])
    monkeypatch.setattr(checker.subprocess, 'run', timeout)
    assert checker.probe_worker('audit-worker', 1) == 'TIMEOUT'


def test_cli_outside_repo_and_preserves_report(case, tmp_path):
    output = tmp_path / 'report.json'
    command = [sys.executable, str(ROOT / 'scripts/check_preparation.py'), '--recipes',
               str(case.parent), '--output', str(output)]
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    before = output.read_bytes()
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert output.read_bytes() == before
    edit_audit(case, files={})
    result = subprocess.run(command[:-2], cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert result.returncode == 2


def test_empty_input_is_not_ready(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/check_preparation.py'), '--recipes', str(tmp_path)],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 2


def test_fate_requires_a_prepared_snapshot_before_readiness(tmp_path):
    import shutil
    original = ROOT / 'benchmark/recipes/python-cve-2020-25459'
    for name in ('recipe.json', 'audit.json'):
        shutil.copyfile(original / name, tmp_path / name)
    result = checker.check_case(tmp_path)
    assert result['status'] == 'BLOCKED'
    assert result['qualification'] == 'NOT_CHECKED'
    assert result['blockers']
