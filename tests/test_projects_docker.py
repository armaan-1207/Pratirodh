"""Real container tests are opt-in; never execute imported projects on host."""
import json
import os
import subprocess
import threading
import time
import pytest
from pratirodh.evidence import Store
from pratirodh.projects.examples import create_example
from pratirodh.projects.engine import run_project
from pratirodh.projects.budget import WorkflowBudget
from pratirodh.projects.worker import DockerProjectWorker

pytestmark = pytest.mark.skipif(os.getenv('PRATIRODH_DOCKER_TESTS') != '1', reason='opt-in real Linux worker tests')


@pytest.fixture(scope='module')
def image():
    return subprocess.check_output(['docker', 'image', 'inspect', 'pratirodh-project-worker:0.2', '--format', '{{.Id}}'], text=True).strip()


@pytest.mark.parametrize('language', ['python', 'node', 'cpp'])
@pytest.mark.parametrize('workflow', ['repair', 'discover'])
def test_real_multi_file_end_to_end(tmp_path, image, language, workflow):
    root = tmp_path / language
    manifest, patch = create_example(root, language, image)
    store = Store(tmp_path / 'evidence')
    report = run_project(root, manifest, workflow, patch=patch, store=store, allow_demo=True)
    assert report['decision'] == 'READY_FOR_REVIEW', json.dumps(report, indent=2)
    assert all(m['status'] == 'CONFIRMED_UNSAFE' and m['caught'] for m in report['candidates'][0]['mutations'])
    assert store.load(report['id']) == report


def test_worker_isolation_limits_and_missing_dependency(tmp_path, image):
    root = tmp_path / 'python'
    manifest_path, _ = create_example(root, 'python', image)
    manifest = json.loads(manifest_path.read_text())
    worker = DockerProjectWorker(manifest, allow_demo=True)
    def execute(script):
        return worker.execute({'probe.py': script}, [['python', 'probe.py']], WorkflowBudget(manifest['limits']))[0]
    observed = execute('import os,pathlib\nprint(os.getuid())\nprint(pathlib.Path("/var/run/docker.sock").exists())\ntry:\n pathlib.Path("probe.py").write_text("changed")\nexcept PermissionError:\n print("IMMUTABLE")\nprint(sorted(os.environ))\n')
    assert observed['stdout'].startswith('65534\nFalse\nIMMUTABLE\n')
    assert 'GEMINI_API_KEY' not in observed['stdout']
    network = execute('import socket\ns=socket.socket();s.settimeout(1)\ntry:\n s.connect(("1.1.1.1",443)); print("CONNECTED")\nexcept OSError:\n print("BLOCKED")\n')
    assert network['stdout'] == 'BLOCKED\n'
    missing = worker.execute({'a.txt': ''}, [['no-such-dependency']], WorkflowBudget(manifest['limits']))[0]
    assert missing['status'] == 'MISSING_DEPENDENCY'
    output = execute('print("x"*100000)')
    assert output['status'] == 'OUTPUT_LIMIT'
    manifest['limits']['command_seconds'] = 1
    timeout = execute('import time\ntime.sleep(5)')
    assert timeout['status'] == 'TIMEOUT'
    manifest['limits']['disk_mb'] = 16
    disk = execute('from pathlib import Path\np=Path("/work/fill")\ntry:\n with p.open("wb") as f:\n  for _ in range(40): f.write(b"x"*1024*1024)\nexcept OSError:\n print("DISK_LIMIT")\n')
    assert disk['stdout'] == 'DISK_LIMIT\n'


def test_worker_cancellation_cleans_container(tmp_path, image):
    path, _ = create_example(tmp_path / 'project', 'python', image)
    manifest = json.loads(path.read_text())
    worker = DockerProjectWorker(manifest, allow_demo=True)
    cancel = threading.Event()
    timer = threading.Timer(1, cancel.set)
    timer.start()
    try:
        with pytest.raises(InterruptedError):
            worker.execute({'a.py': 'import time\ntime.sleep(20)'}, [['python', 'a.py']], WorkflowBudget(manifest['limits'], cancel))
    finally:
        timer.cancel()
    names = subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}'], text=True)
    assert not set(worker.names) & set(names.splitlines())


def test_worker_http_service_lifecycle(tmp_path, image):
    path, _ = create_example(tmp_path / 'project', 'python', image)
    manifest = json.loads(path.read_text())
    manifest['commands']['startup'] = [['python', 'server.py']]
    manifest['service_ready_url'] = 'http://127.0.0.1:8097/health'
    worker = DockerProjectWorker(manifest, allow_demo=True)
    files = {'server.py': 'from flask import Flask\napp=Flask(__name__)\n@app.get("/health")\ndef health():\n return "HEALTHY"\napp.run(host="127.0.0.1",port=8097)\n',
             'check.py': 'import urllib.request\nprint(urllib.request.urlopen("http://127.0.0.1:8097/health").read().decode())\n'}
    result = worker.execute(files, [['python', 'check.py']], WorkflowBudget(manifest['limits']))
    assert result[0]['status'] == 'COMPLETE'
    assert result[0]['stdout'] == 'HEALTHY\n'
