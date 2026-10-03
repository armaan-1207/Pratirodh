"""Live guest and Docker identity checks before imported-source execution."""
import json
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlparse

from .manifest import load
from .model import LocalModel
from ..evidence import digest


def command(arguments):
    return subprocess.run(arguments, check=True, capture_output=True, text=True,
                          encoding='utf-8', timeout=30).stdout.strip()


def attest_worker(context, image, run=command):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', context) or context in {'default', 'desktop-linux'}:
        raise ValueError('campaign requires a dedicated worker context')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', image):
        raise ValueError('worker image must be pinned')
    config = json.loads(run(['docker', 'context', 'inspect', context]))[0]
    endpoint = urlparse(config['Endpoints']['docker']['Host'])
    if endpoint.scheme != 'ssh' or not endpoint.hostname or endpoint.password or endpoint.path not in {'', '/'}:
        raise ValueError('guest identity requires an SSH Docker endpoint')
    if endpoint.username and not re.fullmatch(r'[A-Za-z0-9_.-]+', endpoint.username):
        raise ValueError('invalid worker SSH username')
    if not re.fullmatch(r'[A-Za-z0-9_.:-]+', endpoint.hostname):
        raise ValueError('invalid worker SSH hostname')
    host = ((endpoint.username + '@') if endpoint.username else '') + endpoint.hostname
    identity = run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    '-o', 'StrictHostKeyChecking=yes', '-p', str(endpoint.port or 22), host,
                    'cat /proc/sys/kernel/random/boot_id /etc/machine-id']).splitlines()
    if len(identity) != 2 or not re.fullmatch(r'[a-f0-9-]{36}', identity[0]) or not re.fullmatch(r'[a-f0-9]{32}', identity[1]):
        raise ValueError('guest boot and machine identities unavailable')
    info = json.loads(run(['docker', '--context', context, 'info', '--format', '{{json .}}']))
    if not info.get('ID') or not info.get('KernelVersion') or info.get('OSType') != 'linux':
        raise ValueError('Linux worker daemon identity unavailable')
    actual = run(['docker', '--context', context, 'image', 'inspect', image, '--format', '{{.Id}}'])
    if actual != image:
        raise ValueError('worker image identity mismatch')
    return {'context': context, 'image': image, 'daemon_id': info['ID'],
            'kernel_version': info['KernelVersion'], 'boot_id_digest': digest(identity[0]),
            'machine_id_digest': digest(identity[1]), 'status': 'PASS',
            'observed_at': datetime.now(timezone.utc).isoformat()}


def separate(execution, audit):
    for field in ('context', 'daemon_id', 'boot_id_digest', 'machine_id_digest'):
        if not execution.get(field) or not audit.get(field) or execution[field] == audit[field]:
            raise ValueError('execution and audit workers must have distinct ' + field)


def attest_campaign(path, frozen):
    base = Path(path).resolve().parent
    workers, models = {}, set()
    for case in frozen['cases']:
        manifest, _ = load(base / case['target'], base / case['manifest'])
        audit = json.loads((base / case['audit']).read_text(encoding='utf-8'))
        execution_key = (manifest['worker']['context'], manifest['image'])
        audit_key = (audit['context'], audit.get('image', manifest['image']))
        for key in (execution_key, audit_key):
            if key not in workers:
                workers[key] = attest_worker(*key)
        separate(workers[execution_key], workers[audit_key])
        signature = json.dumps(manifest['model'], sort_keys=True)
        if signature not in models:
            LocalModel(manifest['model']).preflight()
            models.add(signature)
    return {'status': 'PASS', 'workers': list(workers.values()), 'model_configurations': len(models),
            'updated': datetime.now(timezone.utc).isoformat(),
            'scope': 'Distinct guest kernels and Docker daemons on operator-managed hosts; not physical-host isolation'}
