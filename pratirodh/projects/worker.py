"""Disposable containers inside an explicitly selected Linux worker/VM."""
import json
import re
import subprocess
import threading
import time
import uuid
from ..evidence import digest
from .leases import Lease

SLOTS = threading.BoundedSemaphore(2)


class DockerProjectWorker:
    def __init__(self, manifest, allow_demo=False):
        self.manifest = manifest
        config = manifest['worker']
        if config['mode'] == 'demo' and not allow_demo:
            raise ValueError('local demo worker requires explicit --demo-worker; unfamiliar projects require a dedicated worker')
        if config['mode'] == 'dedicated' and config['context'] in {'default', 'desktop-linux'}:
            raise ValueError('dedicated worker cannot use the shared local Docker context')
        self.prefix = ['docker', '--context', config['context']]
        self.observations = []
        self.names = []
        self.identity_value = None

    def identity(self):
        if self.identity_value is None:
            result = subprocess.run(self.prefix + ['image', 'inspect', self.manifest['image'], '--format', '{{.Id}}'],
                                    capture_output=True, text=True, timeout=10, check=True)
            value = result.stdout.strip()
            if not re.fullmatch(r'sha256:[a-f0-9]{64}', value) or value != self.manifest['image']:
                raise ValueError('worker image identity mismatch')
            self.identity_value = value
        return self.identity_value

    def execute(self, files, commands, budget):
        from .manifest import validate_intake
        validate_intake(files)
        self.identity()
        limits = self.manifest['limits']
        lease = Lease('worker', slots=2)
        if not lease.acquire(budget):
            raise TimeoutError('worker slots unavailable')
        name = 'pratirodh-project-' + uuid.uuid4().hex
        self.names.append(name)
        process = None
        try:
            timeout = min(budget.remaining(), limits['command_seconds'] * len(commands) + 10)
            command = self.prefix + ['run', '--rm', '--pull=never', '--name', name, '--network', 'none',
                '--read-only', '--cap-drop', 'ALL', '--cap-add', 'SETUID', '--cap-add', 'SETGID',
                '--security-opt', 'no-new-privileges',
                '--pids-limit', str(limits['pids']), '--cpus', str(limits['cpus']),
                '--memory', str(limits['memory_mb']) + 'm', '--memory-swap', str(limits['memory_mb']) + 'm',
                '--ulimit', 'nofile=256:256', '--user', '0:0',
                '--tmpfs', '/work:rw,exec,nosuid,nodev,size=' + str(limits['disk_mb']) + 'm,mode=1777',
                # This is an intentional in-container tmpfs mount. It keeps
                # temporary worker data memory-backed and non-executable.
                '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777',  # nosec B108
                '-i', self.manifest['image']]
            payload = json.dumps({'files': files, 'commands': commands, 'seconds': timeout - 2,
                                  'startup': self.manifest['commands']['startup'],
                                  'service_ready_url': self.manifest.get('service_ready_url'),
                                  'command_seconds': limits['command_seconds'], 'output_bytes': limits['output_bytes']})
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, encoding='utf-8')
            end = time.monotonic() + timeout
            first = True
            while True:
                budget.remaining()
                if time.monotonic() >= end:
                    raise TimeoutError('worker container timeout')
                try:
                    stdout, stderr = process.communicate(payload if first else None, timeout=min(.25, end - time.monotonic()))
                    break
                except subprocess.TimeoutExpired:
                    first = False
            # Protocol outputs are bounded by the baked worker and Docker limits.
            if len(stdout.encode()) > 2 * 1024 * 1024:
                raise ValueError('worker artifact output exceeds limit')
            if process.returncode:
                raise RuntimeError('worker execution failed (exit ' + str(process.returncode) + ')')
            result = json.loads(stdout)
            observations = result.get('observations')
            if result.get('version') != 1 or not isinstance(observations, list) or not 0 < len(observations) <= len(commands):
                raise ValueError('invalid worker protocol/artifacts')
            for observation in observations:
                if observation.get('status') not in {'COMPLETE', 'TIMEOUT', 'OUTPUT_LIMIT', 'MISSING_DEPENDENCY', 'STARTUP_FAILURE'}:
                    raise ValueError('invalid observation status')
                if not isinstance(observation.get('stdout'), str) or not isinstance(observation.get('stderr'), str):
                    raise ValueError('invalid worker output')
                if len((observation['stdout'] + observation['stderr']).encode()) > 2 * limits['output_bytes']:
                    raise ValueError('invalid worker output size')
                if observation['status'] == 'COMPLETE' and type(observation.get('exit')) is not int:
                    raise ValueError('invalid worker exit status')
            self.observations.append({'commands': commands, 'observations': observations,
                                      'source_revision': digest(json.dumps(files, sort_keys=True))})
            return observations
        finally:
            subprocess.run(self.prefix + ['rm', '-f', name], capture_output=True, timeout=10)
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.communicate()
            lease.release()
