"""Safe controller telemetry distinguishes deadlines without changing decisions."""
import json
import subprocess
from types import SimpleNamespace

import pytest

from pratirodh.evidence import Store
from pratirodh.projects import worker as worker_module
from pratirodh.projects.budget import WorkflowBudget
from pratirodh.projects.engine import run_project
from pratirodh.projects.examples import create_example
from pratirodh.projects.worker import DockerProjectWorker
from tools.requests_diagnostics import summarize, worker_diagnostics


def config():
    return {'image': 'sha256:' + 'a' * 64,
            'worker': {'mode': 'demo', 'context': 'default'},
            'commands': {'startup': []},
            'limits': {'command_seconds': 2, 'pids': 64, 'cpus': 1,
                       'memory_mb': 256, 'disk_mb': 32, 'output_bytes': 8192}}


def setup_worker(monkeypatch, mode='success', acquired=True):
    clock = [0.0]
    monkeypatch.setattr(worker_module.time, 'monotonic', lambda: clock[0])
    released = []
    monkeypatch.setattr(worker_module, 'Lease', lambda *a, **k: SimpleNamespace(
        acquire=lambda budget: acquired, release=lambda: released.append(True)))
    worker = DockerProjectWorker(config(), allow_demo=True)
    monkeypatch.setattr(worker, 'identity', lambda: worker.manifest['image'])
    budget_calls = []
    def remaining():
        budget_calls.append(True)
        if mode == 'budget' and len(budget_calls) > 1:
            raise TimeoutError('private workflow information')
        if mode == 'cancelled':
            raise InterruptedError('private cancellation information')
        return 100
    budget = SimpleNamespace(remaining=remaining, deadline=1000)
    def communicate(*a, **k):
        if k and mode == 'container':
            clock[0] += 20
            raise subprocess.TimeoutExpired('secret-command', 0.25)
        clock[0] += 0.5
        output = 'secret malformed output' if mode == 'protocol' else json.dumps(
            {'version': 1, 'observations': [{'status': 'COMPLETE', 'exit': 0,
                                           'stdout': 'private target output', 'stderr': ''}]})
        return output, 'private Docker error'
    process = SimpleNamespace(returncode=1 if mode == 'exit' else 0,
                              communicate=communicate, poll=lambda: 0)
    calls = []
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: process)
    monkeypatch.setattr(subprocess, 'run', lambda args, **k: (calls.append(args) or SimpleNamespace(returncode=0)))
    return worker, budget, calls, released


@pytest.mark.parametrize('mode,outcome,exception', [
    ('success', 'COMPLETE', None),
    ('container', 'CONTAINER_DEADLINE_EXPIRED', TimeoutError),
    ('budget', 'WORKFLOW_BUDGET_EXHAUSTED', TimeoutError),
    ('cancelled', 'CANCELLED', InterruptedError),
    ('protocol', 'INVALID_WORKER_PROTOCOL', ValueError),
    ('exit', 'CONTAINER_EXIT_NONZERO', RuntimeError),
])
def test_worker_records_failure_category_without_output(monkeypatch, mode, outcome, exception):
    worker, budget, calls, released = setup_worker(monkeypatch, mode)
    if exception:
        with pytest.raises(exception):
            worker.execute({'probe.py': 'private source'}, [['python', 'secret-command']], budget)
    else:
        worker.execute({'probe.py': 'private source'}, [['python', 'secret-command']], budget)
    diagnostic = worker.execution_diagnostics[0]
    assert diagnostic['outcome'] == outcome
    assert diagnostic['sequence'] == 1 and diagnostic['command_count'] == 1
    assert diagnostic['elapsed_seconds'] >= 0
    assert 'private' not in json.dumps(diagnostic)
    assert 'secret-command' not in json.dumps(diagnostic)
    assert released == [True]
    assert calls == [worker.prefix + ['rm', '-f', worker.names[0]]]
    if mode == 'success':
        assert diagnostic['deadline_source'] == 'COMMAND_WINDOW'
        assert diagnostic['applied_timeout_seconds'] == 12
        assert diagnostic['observation_status_counts'] == {'COMPLETE': 1}


def test_slot_timeout_has_no_container_attempt(monkeypatch):
    worker, budget, calls, released = setup_worker(monkeypatch, acquired=False)
    with pytest.raises(TimeoutError, match='worker slots unavailable'):
        worker.execute({'probe.py': 'print(1)'}, [['python', 'probe.py']], budget)
    assert worker.execution_diagnostics[0]['outcome'] == 'WORKER_SLOT_UNAVAILABLE'
    assert worker.execution_diagnostics[0]['phase'] == 'SLOT_WAIT'
    assert calls == released == worker.names == []


def test_sanitizer_drops_arbitrary_fields_and_bad_numbers():
    values = [{'phase': 'CONTAINER_WAIT', 'outcome': 'CONTAINER_DEADLINE_EXPIRED',
               'sequence': True, 'command_count': 4, 'slot_wait_seconds': float('nan'),
               'elapsed_seconds': float('inf'), 'container_seconds': -1,
               'applied_timeout_seconds': 12.5, 'deadline_source': 'COMMAND_WINDOW',
               'observation_status_counts': {'TIMEOUT': 1, 'private': 2, 'COMPLETE': True},
               'stderr': 'private', 'command': 'private', 'source': 'private'},
              {'phase': 'private', 'outcome': 'COMPLETE'}]
    assert worker_diagnostics(values) == [{'phase': 'CONTAINER_WAIT',
        'outcome': 'CONTAINER_DEADLINE_EXPIRED', 'command_count': 4,
        'applied_timeout_seconds': 12.5, 'deadline_source': 'COMMAND_WINDOW',
        'observation_status_counts': {'TIMEOUT': 1}}]
    assert worker_diagnostics({'private': 'secret'}) == []
    assert 'private' not in json.dumps(summarize([{'worker_execution_diagnostics': values}]))


def test_execution_diagnostics_survive_signed_insufficient_report(tmp_path):
    path, patch = create_example(tmp_path / 'source', 'python', 'sha256:' + 'a' * 64)
    store = Store(tmp_path / 'evidence')
    diagnostics = [{'phase': 'CONTAINER_WAIT', 'outcome': 'CONTAINER_DEADLINE_EXPIRED',
                    'applied_timeout_seconds': 12, 'elapsed_seconds': 12.1}]
    def execute(*a):
        raise TimeoutError('worker container timeout')
    worker = SimpleNamespace(identity=lambda: 'sha256:' + 'a' * 64, observations=[],
                             execution_diagnostics=diagnostics, execute=execute)
    report = run_project(tmp_path / 'source', path, patch=patch, worker=worker, store=store)
    assert report['decision'] == 'INSUFFICIENT_EVIDENCE'
    assert report['reason'] == 'BUDGET_EXHAUSTION'
    saved = store.load(report['id'])
    assert saved['worker_execution_diagnostics'] == diagnostics
    assert summarize([saved])['reports'][0]['worker_execution_diagnostics'] == diagnostics

def test_cleanup_timeout_still_kills_client_releases_lease_and_preserves_timeout(monkeypatch):
    worker, budget, _, released = setup_worker(monkeypatch, 'container')
    killed = []
    def communicate(*a, **k):
        if k.get('timeout') != 10:
            raise TimeoutError('original worker timeout')
        return '', ''
    process = SimpleNamespace(returncode=None, communicate=communicate,
                              poll=lambda: None, kill=lambda: killed.append(True))
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: process)
    def remove(*a, **k):
        raise subprocess.TimeoutExpired('private docker command', 10)
    monkeypatch.setattr(subprocess, 'run', remove)
    with pytest.raises(TimeoutError, match='original worker timeout'):
        worker.execute({'probe.py': 'print(1)'}, [['python', 'probe.py']], budget)
    assert killed == released == [True]
    assert worker.execution_diagnostics[0]['cleanup_failures'] == ['CONTAINER_REMOVAL_FAILED']

@pytest.mark.parametrize('listing_exit,listing_stdout,should_fail', [
    (0, '', False), (0, 'existing-id', True), (1, '', True)])
def test_nonzero_removal_requires_independent_container_absence(monkeypatch, listing_exit, listing_stdout, should_fail):
    worker, budget, _, released = setup_worker(monkeypatch)
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        return (SimpleNamespace(returncode=1) if 'rm' in args else
                SimpleNamespace(returncode=listing_exit, stdout=listing_stdout))
    monkeypatch.setattr(subprocess, 'run', run)
    if should_fail:
        with pytest.raises(RuntimeError, match='worker container absence unverified'):
            worker.execute({'probe.py': 'print(1)'}, [['python', 'probe.py']], budget)
        assert worker.execution_diagnostics[0]['cleanup_failures'] == ['CONTAINER_REMOVAL_FAILED']
    else:
        worker.execute({'probe.py': 'print(1)'}, [['python', 'probe.py']], budget)
        assert 'cleanup_failures' not in worker.execution_diagnostics[0]
    assert released == [True]
    assert len(calls) == 2
    assert calls[0] == worker.prefix + ['rm', '-f', worker.names[0]]
    assert calls[1] == worker.prefix + ['container', 'ls', '--all', '--filter',
        'name=^/' + worker.names[0] + '$', '--format', '{{.ID}}']


def test_client_cleanup_timeout_cannot_return_success_and_releases_lease(monkeypatch):
    worker, budget, _, released = setup_worker(monkeypatch)
    calls = []
    def communicate(*args, **kwargs):
        if kwargs.get('timeout') == 10:
            raise subprocess.TimeoutExpired('private client', 10)
        return json.dumps({'version': 1, 'observations': [
            {'status': 'COMPLETE', 'exit': 0, 'stdout': '', 'stderr': ''}]}), ''
    process = SimpleNamespace(returncode=0, communicate=communicate, poll=lambda: 0)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: process)
    with pytest.raises(subprocess.TimeoutExpired):
        worker.execute({'probe.py': 'print(1)'}, [['python', 'probe.py']], budget)
    assert released == [True]
    diagnostic = worker.execution_diagnostics[0]
    assert diagnostic['cleanup_failures'] == ['CLIENT_CLEANUP_FAILED']
    assert 'private' not in json.dumps(worker_diagnostics([diagnostic]))

@pytest.mark.parametrize('result', [None, SimpleNamespace(returncode=True), SimpleNamespace(returncode='0')])
def test_malformed_cleanup_result_quarantines_worker(monkeypatch, result):
    worker, budget, _, released = setup_worker(monkeypatch)
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: result)
    with pytest.raises(RuntimeError, match='invalid worker cleanup result'):
        worker.execute({'probe.py': 'print(1)'}, [['python', 'probe.py']], budget)
    assert released == [True] and worker.cleanup_failed
    with pytest.raises(RuntimeError, match='operator confirmation'):
        worker.execute({'probe.py': 'print(1)'}, [['python', 'probe.py']], budget)
    assert len(worker.execution_diagnostics) == 1
