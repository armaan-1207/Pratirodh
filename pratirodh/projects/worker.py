"""Disposable containers inside an explicitly selected Linux worker/VM."""
import json
import re
import subprocess
import sys
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
        self.execution_diagnostics = []
        self.cleanup_failed = False
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
        if self.cleanup_failed:
            raise RuntimeError('worker cleanup requires operator confirmation before reuse')
        self.identity()
        limits = self.manifest['limits']
        diagnostic = {'sequence': len(self.execution_diagnostics) + 1,
                      'command_count': len(commands), 'phase': 'SLOT_WAIT',
                      'outcome': 'SLOT_ACQUISITION_FAILURE'}
        self.execution_diagnostics.append(diagnostic)
        entered = time.monotonic()
        lease = Lease('worker', slots=2)
        try:
            if not lease.acquire(budget):
                diagnostic['outcome'] = 'WORKER_SLOT_UNAVAILABLE'
                raise TimeoutError('worker slots unavailable')
        except InterruptedError:
            diagnostic['outcome'] = 'CANCELLED'
            raise
        except TimeoutError:
            if time.monotonic() >= budget.deadline:
                diagnostic['outcome'] = 'WORKFLOW_BUDGET_EXHAUSTED'
            raise
        finally:
            diagnostic['slot_wait_seconds'] = round(time.monotonic() - entered, 3)
            diagnostic['elapsed_seconds'] = diagnostic['slot_wait_seconds']
        name = 'pratirodh-project-' + uuid.uuid4().hex
        self.names.append(name)
        process = None
        dispatched = time.monotonic()
        diagnostic.update(phase='CONTAINER_LAUNCH', outcome='TRANSPORT_FAILURE')
        try:
            try:
                remaining = budget.remaining()
            except TimeoutError:
                diagnostic['outcome'] = 'WORKFLOW_BUDGET_EXHAUSTED'
                raise
            command_window = limits['command_seconds'] * len(commands) + 10
            timeout = min(remaining, command_window)
            diagnostic.update(workflow_remaining_seconds=round(remaining, 3),
                              applied_timeout_seconds=round(timeout, 3),
                              command_limit_seconds=limits['command_seconds'],
                              deadline_source='WORKFLOW_BUDGET' if remaining <= command_window else 'COMMAND_WINDOW')
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
            diagnostic['phase'] = 'CONTAINER_WAIT'
            first = True
            while True:
                try:
                    budget.remaining()
                except TimeoutError:
                    diagnostic['outcome'] = 'WORKFLOW_BUDGET_EXHAUSTED'
                    raise
                if time.monotonic() >= end:
                    diagnostic['outcome'] = 'CONTAINER_DEADLINE_EXPIRED'
                    raise TimeoutError('worker container timeout')
                try:
                    stdout, stderr = process.communicate(payload if first else None, timeout=min(.25, end - time.monotonic()))
                    break
                except subprocess.TimeoutExpired:
                    first = False
            diagnostic['phase'] = 'PROTOCOL_VALIDATION'
            diagnostic['outcome'] = 'INVALID_WORKER_PROTOCOL'
            # Protocol outputs are bounded by the baked worker and Docker limits.
            if len(stdout.encode()) > 2 * 1024 * 1024:
                raise ValueError('worker artifact output exceeds limit')
            if process.returncode:
                diagnostic.update(outcome='CONTAINER_EXIT_NONZERO', container_exit=process.returncode)
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
            diagnostic['outcome'] = 'COMPLETE'
            diagnostic['observation_status_counts'] = {
                status: sum(row['status'] == status for row in observations)
                for status in sorted({row['status'] for row in observations})}
            return observations
        except InterruptedError:
            diagnostic['outcome'] = 'CANCELLED'
            raise
        except subprocess.TimeoutExpired:
            diagnostic['outcome'] = 'TRANSPORT_TIMEOUT'
            raise
        finally:
            diagnostic['container_seconds'] = round(time.monotonic() - dispatched, 3)
            diagnostic['elapsed_seconds'] = round(time.monotonic() - entered, 3)
            original_failure = sys.exc_info()[0] is not None
            cleanup_error = None
            cleanup_failures = []
            try:
                try:
                    removed = subprocess.run(self.prefix + ['rm', '-f', name], capture_output=True, timeout=10)
                    if type(getattr(removed, 'returncode', None)) is not int:
                        raise RuntimeError('invalid worker cleanup result')
                    if removed.returncode:
                        # --rm may already have removed a completed container.
                        # One read-only listing proves absence; this is not a retry.
                        remaining_containers = subprocess.run(self.prefix + ['container', 'ls', '--all',
                            '--filter', 'name=^/' + name + '$', '--format', '{{.ID}}'],
                            capture_output=True, text=True, timeout=10)
                        if (type(getattr(remaining_containers, 'returncode', None)) is not int
                                or remaining_containers.returncode
                                or not isinstance(getattr(remaining_containers, 'stdout', None), str)
                                or remaining_containers.stdout.strip()):
                            raise RuntimeError('worker container absence unverified')
                except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
                    cleanup_error = exc
                    cleanup_failures.append('CONTAINER_REMOVAL_FAILED')
                try:
                    if process is not None:
                        if process.poll() is None:
                            process.kill()
                        process.communicate(timeout=10)
                except (OSError, subprocess.SubprocessError) as exc:
                    cleanup_error = cleanup_error or exc
                    cleanup_failures.append('CLIENT_CLEANUP_FAILED')
            finally:
                lease.release()
                if cleanup_failures:
                    self.cleanup_failed = True
                    diagnostic['cleanup_failures'] = cleanup_failures
            # Preserve the execution failure, but a cleanup failure after success
            # still refuses successful verification. Never retry Docker removal.
            if cleanup_error is not None and not original_failure:
                raise cleanup_error
