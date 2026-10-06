"""Run a trusted sandbox probe through the production worker protocol."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pratirodh.projects.budget import WorkflowBudget
from pratirodh.projects.worker import DockerProjectWorker

PROBE = '''import errno,json,os
from pathlib import Path
assert os.geteuid()==65534, 'target must be unprivileged'
assert not Path('/var/run/docker.sock').exists(), 'Docker socket exposed'
try:
    Path('/sandbox-probe').write_text('unexpected')
except OSError as error:
    assert error.errno in (errno.EROFS,errno.EACCES), str(error)
else:
    raise AssertionError('root filesystem writable')
assert set(os.listdir('/sys/class/net'))=={'lo'}, 'external network interface exposed'
status=Path('/proc/self/status').read_text()
assert int(next(line.split()[1] for line in status.splitlines() if line.startswith('CapEff:')),16)==0
assert next(line.split()[1] for line in status.splitlines() if line.startswith('NoNewPrivs:'))=='1'
print(json.dumps({'unprivileged':True,'root_read_only':True,'network_none':True,'no_docker_socket':True,'no_capabilities':True,'no_new_privileges':True}))
'''


def main():
    preflight = json.loads(Path('run_output/upstream-validation/worker-preflight.json').read_text())
    if preflight['status'] != 'PASS':
        raise SystemExit('worker identity preflight must pass before probing')
    rows = []
    for identity in preflight['workers']:
        manifest = {'worker': {'mode': 'dedicated', 'context': identity['context']}, 'image': identity['image'],
            'commands': {'startup': []}, 'limits': {'command_seconds': 15, 'pids': 64, 'cpus': 1,
                'memory_mb': 256, 'disk_mb': 32, 'output_bytes': 8192}}
        try:
            worker = DockerProjectWorker(manifest)
            observations = worker.execute({'probe.py': PROBE}, [['python3', 'probe.py']],
                WorkflowBudget({'seconds': 60, 'reserve_seconds': 0, 'model_calls': 0, 'candidates': 0}))
            passed = all(o['status'] == 'COMPLETE' and o['exit'] == 0 for o in observations)
            rows.append({'role': identity['role'], 'status': 'PASS' if passed else 'FAIL',
                'image': identity['image'], 'observations': observations})
        except Exception as error:
            rows.append({'role': identity['role'], 'status': 'BLOCKED', 'error': type(error).__name__, 'detail': str(error)[:1000]})
    result = {'status': 'PASS' if all(r['status'] == 'PASS' for r in rows) else 'BLOCKED',
        'observed_at': datetime.now(timezone.utc).isoformat(), 'workers': rows,
        'scope': 'Trusted probe only; no upstream vulnerability qualification'}
    Path('run_output/upstream-validation/worker-sandbox-probe.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
