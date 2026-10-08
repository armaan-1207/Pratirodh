"""Exercise failure-artifact plumbing without running project code on the host."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('decision', ['INSUFFICIENT_EVIDENCE', 'READY_FOR_REVIEW'])
def test_project_diagnostic_is_written_before_decision_assertion(tmp_path, monkeypatch, decision):
    path = Path(__file__).with_name('test_projects_docker.py')
    spec = importlib.util.spec_from_file_location('ci_project_test_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = {'id': 'a' * 32, 'decision': decision, 'reason': 'BUDGET_EXHAUSTION',
              'patch': 'private-source', 'gaps': ['private-key'],
              'worker_execution_diagnostics': [{'phase': 'CONTAINER_WAIT',
                  'outcome': 'CONTAINER_DEADLINE_EXPIRED', 'applied_timeout_seconds': 10,
                  'deadline_source': 'WORKFLOW_BUDGET', 'stderr': 'private-token'}],
              'candidates': [{'mutations': [{'status': 'CONFIRMED_UNSAFE', 'caught': True}]}]}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, 'create_example', lambda *args: ('manifest', 'private-patch'))
    monkeypatch.setattr(module, 'Store', lambda *args: SimpleNamespace(load=lambda _: report))
    monkeypatch.setattr(module, 'run_project', lambda *args, **kwargs: report)
    call = lambda: module.test_real_multi_file_end_to_end(tmp_path, 'image', 'cpp', 'repair')
    if decision == 'INSUFFICIENT_EVIDENCE':
        with pytest.raises(AssertionError) as failure:
            call()
        assert 'CONTAINER_DEADLINE_EXPIRED' in str(failure.value)
        assert 'private' not in str(failure.value)
    else:
        call()
    result = json.loads((tmp_path / 'run_output/ci-diagnostics/project-repair-cpp.json').read_text())
    assert result['reports'][0]['decision'] == decision
    assert result['reports'][0]['worker_execution_diagnostics'][0]['applied_timeout_seconds'] == 10
    assert 'private' not in json.dumps(result)
