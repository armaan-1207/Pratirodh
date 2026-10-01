"""Pinned native historical baseline gate in disposable containers; never imports it on host."""
import json
import hashlib
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'pratirodh-historical:edffe24'


def baseline_record():
    record = json.loads((ROOT/'docs/HISTORICAL_BASELINE.json').read_text())
    rebuilt = ROOT/'run_output/HISTORICAL_BASELINE_REBUILD.json'
    if rebuilt.exists():
        replacement = json.loads(rebuilt.read_text())
        for field in ('revision', 'archive_sha256', 'source_hashes', 'dependencies'):
            if replacement[field] != record[field]:
                raise ValueError('rebuilt historical baseline differs from the pinned record: '+field)
        record['image'] = replacement['image']
    return record


def validate():
    record = baseline_record()
    if hashlib.sha256((ROOT/'tools/historical_worker.py').read_bytes()).hexdigest() != record['wrapper_sha256']:
        raise ValueError('historical wrapper differs from recorded revision')
    paths = subprocess.check_output(['git','ls-tree','-r','--name-only',record['revision']],cwd=ROOT,text=True).splitlines()
    script = "import json,sys,hashlib;from pathlib import Path;p=json.load(sys.stdin);print(json.dumps({hashlib.sha256(n.encode()).hexdigest():hashlib.sha256((Path('/baseline')/n).read_bytes()).hexdigest() for n in p}))"
    result = subprocess.run(['docker','run','--rm','--network','none','--read-only','--entrypoint','python','-i',record['image'],'-c',script],
        input=json.dumps(paths),text=True,capture_output=True,timeout=30,check=True)
    if json.loads(result.stdout) != record['source_hashes']:
        raise ValueError('historical image source hashes do not match')
    dependencies = subprocess.check_output(['docker','run','--rm','--network','none','--entrypoint','python',record['image'],'-m','pip','freeze'],text=True,timeout=30).splitlines()
    if sorted(dependencies) != sorted(record['dependencies']):
        raise ValueError('historical image dependencies do not match')
    return record


def execute(payload, seconds=300):
    started = time.monotonic()
    name = 'historical-baseline-' + uuid.uuid4().hex
    wrapper = (ROOT / 'tools/historical_worker.py').resolve()
    image = baseline_record()['image']
    # This is a private container tmpfs, not a shared host temporary path.
    tmpfs_mount = '/tmp:rw,noexec,nosuid,size=128m,mode=1777'  # nosec B108
    command = ['docker', 'run', '--rm', '--name', name, '--network', 'none', '--read-only',
               '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '64',
               '--memory', '2g', '--cpus', '2', '--user', '65534:65534',
               '--tmpfs', tmpfs_mount,
               '--mount', f'type=bind,source={wrapper},target=/harness.py,readonly',
               '--entrypoint', 'python', '-i', image, '-B', '/harness.py']
    try:
        process = subprocess.run(command, input=json.dumps(payload), text=True, encoding='utf-8',
                                 capture_output=True, timeout=seconds)
        if process.returncode:
            raise RuntimeError('historical container unavailable: ' + process.stderr[-300:])
        result = json.loads(process.stdout)
    except subprocess.TimeoutExpired:
        result = {'decision': 'ABSTENTION', 'gap': 'historical execution ceiling exhausted'}
    except (ValueError, RuntimeError, OSError) as exc:
        result = {'decision': 'UNADAPTABLE', 'gap': str(exc)[:400]}
    finally:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=10)
    result.update(elapsed_seconds=round(time.monotonic()-started,3), promotion_applied=False)
    return result


def payload(source, contract, candidate='', patch='', origin='supplied', action='verify'):
    return dict(source=source, candidate=candidate, patch=patch, origin=origin, action=action,
                cwe=contract['cwe'], fixtures=contract['fixtures'], symlinks=contract.get('symlinks', {}))
