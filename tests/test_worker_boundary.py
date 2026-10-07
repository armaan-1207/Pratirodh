"""Trusted boundary fault injection; no upstream harnesses or exploit inputs."""
import json
import os
import subprocess
from types import SimpleNamespace

import pytest

from pratirodh.projects.budget import WorkflowBudget
from pratirodh.projects.examples import create_example
from pratirodh.projects.engine import run_project
from pratirodh.evidence import Store
from pratirodh.projects.worker import DockerProjectWorker
from tools.probe_campaign_workers import PROBE


def manifest():
    return {'image': 'sha256:' + 'a' * 64,
            'worker': {'mode': 'demo', 'context': 'default'},
            'commands': {'startup': []},
            'limits': {'seconds': 60, 'reserve_seconds': 0, 'model_calls': 0,
                       'candidates': 0, 'command_seconds': 2, 'pids': 64,
                       'cpus': 1, 'memory_mb': 256, 'disk_mb': 32,
                       'output_bytes': 8192}}


@pytest.mark.parametrize('payload', [
    'not-json',
    {'version': 2, 'observations': []},
    {'version': 1, 'observations': [{'status': 'READY_FOR_REVIEW', 'stdout': '', 'stderr': ''}]},
    {'version': 1, 'observations': [{'status': 'COMPLETE', 'exit': True, 'stdout': '', 'stderr': ''}]},
    {'version': 1, 'observations': [{'status': 'COMPLETE', 'exit': 0, 'stdout': {}, 'stderr': ''}]},
    {'version': 1, 'observations': [{'status': 'COMPLETE', 'exit': 0, 'stdout': 'x' * 16385, 'stderr': ''}]},
])
def test_invalid_worker_response_rejected_and_cleaned(monkeypatch, payload):
    config = manifest()
    worker = DockerProjectWorker(config, allow_demo=True)
    monkeypatch.setattr(worker, 'identity', lambda: config['image'])
    calls = []
    process = SimpleNamespace(returncode=0, communicate=lambda *a, **k:
                              (payload if isinstance(payload, str) else json.dumps(payload), ''),
                              poll=lambda: 0)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: process)
    monkeypatch.setattr(subprocess, 'run', lambda args, **k: (calls.append(args) or SimpleNamespace(returncode=0)))
    with pytest.raises(ValueError):
        worker.execute({'probe.py': 'print(1)'}, [['python', 'probe.py']],
                       WorkflowBudget(config['limits']))
    assert worker.observations == []
    assert calls == [worker.prefix + ['rm', '-f', worker.names[0]]]


@pytest.mark.parametrize('exit_code', [1, -6])
def test_failed_container_cannot_return_success_observations(monkeypatch, exit_code):
    config = manifest()
    worker = DockerProjectWorker(config, allow_demo=True)
    monkeypatch.setattr(worker, 'identity', lambda: config['image'])
    calls = []
    success = json.dumps({'version': 1, 'observations': [
        {'status': 'COMPLETE', 'exit': 0, 'stdout': 'untrusted success', 'stderr': ''}]})
    process = SimpleNamespace(returncode=exit_code, communicate=lambda *a, **k: (success, ''),
                              poll=lambda: exit_code)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: process)
    monkeypatch.setattr(subprocess, 'run', lambda args, **k: (calls.append(args) or SimpleNamespace(returncode=0)))
    with pytest.raises(RuntimeError, match='worker execution failed'):
        worker.execute({'probe.py': 'print(1)'}, [['python', 'probe.py']],
                       WorkflowBudget(config['limits']))
    assert worker.observations == []
    assert calls == [worker.prefix + ['rm', '-f', worker.names[0]]]


@pytest.mark.parametrize('status,exit_code', [
    ('COMPLETE', -6), ('TIMEOUT', None), ('OUTPUT_LIMIT', None),
    ('MISSING_DEPENDENCY', None), ('STARTUP_FAILURE', None),
])
def test_worker_failure_cannot_be_signed_as_ready(tmp_path, status, exit_code):
    config = manifest()
    path, patch = create_example(tmp_path / 'source', 'python', config['image'])
    store = Store(tmp_path / 'synthetic-evidence')
    worker = SimpleNamespace(identity=lambda: config['image'], observations=[],
        execute=lambda files, commands, budget: [
            {'status': status, 'exit': exit_code, 'stdout': '', 'stderr': ''}
            for command in commands])
    result = run_project(tmp_path / 'source', path, patch=patch, worker=worker, store=store)
    assert result['decision'] == 'INSUFFICIENT_EVIDENCE'
    assert result['candidates'] == []
    assert store.load(result['id'])['decision'] == 'INSUFFICIENT_EVIDENCE'


@pytest.mark.skipif(os.getenv('PRATIRODH_DOCKER_TESTS') != '1',
                    reason='opt-in real Linux worker boundary proof')
def test_pinned_native_worker_faults_isolation_and_recovery(tmp_path, monkeypatch):
    image = subprocess.check_output(
        ['docker', 'image', 'inspect', 'pratirodh-project-worker:0.2', '--format', '{{.Id}}'],
        text=True).strip()
    path, _ = create_example(tmp_path / 'synthetic', 'python', image)
    config = json.loads(path.read_text())
    config['limits']['command_seconds'] = 2
    worker = DockerProjectWorker(config, allow_demo=True)
    monkeypatch.setenv('PRATIRODH_BOUNDARY_CANARY', 'host-only-synthetic-marker')

    def execute(files, commands):
        return worker.execute(files, commands, WorkflowBudget(config['limits']))

    probe = execute({'probe.py': PROBE + '\nassert "PRATIRODH_BOUNDARY_CANARY" not in os.environ\n'},
                    [['python', 'probe.py']])[0]
    assert probe['status'] == 'COMPLETE' and probe['exit'] == 0
    assert all(json.loads(probe['stdout']).values())

    # abort() is intentional fault injection, not a vulnerability reproducer.
    files = {'native.c': '#include <stdlib.h>\n#include <stdio.h>\n'
             'int main(int argc,char **argv) { if(argc != 1) abort(); puts("NATIVE_OK"); return 0; }\n'}
    commands = [['clang', 'native.c', '-o', '/work/native'], ['/work/native']]
    good = execute(files, commands)
    assert all(o['status'] == 'COMPLETE' and o['exit'] == 0 for o in good)
    assert good[-1]['stdout'] == 'NATIVE_OK\n'
    crashed = execute(files, [commands[0], ['/work/native', 'abort']])[-1]
    assert crashed['status'] == 'COMPLETE' and crashed['exit'] != 0

    timeout = execute({'probe.py': 'import time\ntime.sleep(20)\n'},
                      [['python', 'probe.py']])[0]
    assert timeout['status'] == 'TIMEOUT'
    output = execute({'probe.py': 'print("x" * 1000000)\n'},
                     [['python', 'probe.py']])[0]
    assert output['status'] == 'OUTPUT_LIMIT'

    with pytest.raises(ValueError):
        execute({'../outside.py': 'print(1)'}, [['python', 'outside.py']])
    with pytest.raises(RuntimeError, match='worker execution failed'):
        execute({'oversized.txt': 'x' * (10 * 1024 * 1024 + 1)}, [['python', '-c', 'print(1)']])

    recovered = execute(files, commands)
    assert recovered[-1]['status'] == 'COMPLETE' and recovered[-1]['exit'] == 0
    assert recovered[-1]['stdout'] == 'NATIVE_OK\n'
    names = subprocess.check_output(['docker', 'ps', '-a', '--format', '{{.Names}}'], text=True)
    assert not set(worker.names).intersection(names.splitlines())
