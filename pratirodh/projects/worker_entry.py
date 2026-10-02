"""Trusted worker entrypoint, baked into an operator-prepared image.

No signing keys, controller mounts, or model credentials enter this process.
"""
import json
import os
from pathlib import Path, PurePosixPath
import selectors
import signal
import subprocess
import sys
import threading
import time
import urllib.request


def execute(job):
    files = job['files']
    if not isinstance(files, dict) or len(files) > 1000:
        raise ValueError('invalid source inventory')
    total = 0
    root = Path('/work/source')
    root.mkdir()
    for name, body in files.items():
        path = PurePosixPath(name)
        if not name or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or not isinstance(body, str):
            raise ValueError('invalid worker source path')
        total += len(body.encode())
        if total > 10 * 1024 * 1024:
            raise ValueError('source budget exceeded')
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(body, encoding='utf-8')
    # Node dependencies are prepared separately and immutable in the image.
    if Path('/opt/dependencies/node_modules').exists():
        (root / 'node_modules').symlink_to('/opt/dependencies/node_modules')
    # The root supervisor creates the snapshot, then permanently drops identity.
    # Target code cannot chmod, replace, or rewrite source/tests between commands.
    for path in root.rglob('*'):
        if not path.is_symlink():
            path.chmod(0o555 if path.is_dir() else 0o444)
    root.chmod(0o555)
    os.setgroups([])
    os.setgid(65534)
    os.setuid(65534)
    outputs = []
    services = []
    service_error = threading.Event()
    def drain(pipe):
        amount = 0
        while True:
            data = pipe.read(4096)
            if not data:
                return
            amount += len(data)
            if amount > job['output_bytes']:
                service_error.set()
                return
    deadline = time.monotonic() + job['seconds']
    for index, command in enumerate(job['commands']):
        if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
            raise ValueError('invalid argument array')
        started = time.monotonic()
        env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/work', 'TMPDIR': '/work',
               'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(root),
               'ASAN_OPTIONS': 'detect_leaks=1:abort_on_error=1',
               'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1',
               'CTEST_OUTPUT_ON_FAILURE': '1', 'CI': 'true'}
        if index == len(job['commands']) - 1 and job.get('startup'):
            for startup in job['startup']:
                server = subprocess.Popen(startup, cwd=root, env=env, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, start_new_session=True)
                services.append(server)
                for pipe in (server.stdout, server.stderr):
                    threading.Thread(target=drain, args=(pipe,), daemon=True).start()
            ready = False
            service_deadline = min(deadline, time.monotonic() + 10)
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            while time.monotonic() < service_deadline and not service_error.is_set():
                if any(s.poll() is not None for s in services):
                    break
                try:
                    with opener.open(job['service_ready_url'], timeout=.3) as response:
                        ready = response.status == 200
                    if ready:
                        break
                except Exception:
                    time.sleep(.05)
            if not ready:
                outputs.append({'exit': None, 'stdout': '', 'stderr': '', 'status': 'STARTUP_FAILURE', 'seconds': 0})
                break
        try:
            process = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, start_new_session=True)
        except OSError as exc:
            outputs.append({'exit': None, 'stdout': '', 'stderr': '', 'status': 'MISSING_DEPENDENCY',
                            'error': type(exc).__name__, 'seconds': 0})
            break
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
        selector.register(process.stderr, selectors.EVENT_READ, 'stderr')
        chunks = {'stdout': bytearray(), 'stderr': bytearray()}
        status = 'COMPLETE'
        ceiling = min(deadline, started + job['command_seconds'])
        while selector.get_map():
            if service_error.is_set():
                status = 'OUTPUT_LIMIT'
                break
            if time.monotonic() >= ceiling:
                status = 'TIMEOUT'
                break
            for key, _ in selector.select(min(.1, max(0, ceiling - time.monotonic()))):
                data = os.read(key.fileobj.fileno(), 8192)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                chunks[key.data].extend(data)
                if sum(len(x) for x in chunks.values()) > job['output_bytes']:
                    status = 'OUTPUT_LIMIT'
                    break
            if status != 'COMPLETE':
                break
        # Kill descendants too, including children which outlive the command.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
        selector.close()
        process.stdout.close()
        process.stderr.close()
        outputs.append({'exit': process.returncode,
                        'stdout': bytes(chunks['stdout'][:job['output_bytes']]).decode('utf-8', errors='replace'),
                        'stderr': bytes(chunks['stderr'][:job['output_bytes']]).decode('utf-8', errors='replace'),
                        'status': status, 'seconds': round(time.monotonic() - started, 3)})
        if status != 'COMPLETE' or process.returncode:
            break
    for server in services:
        try:
            os.killpg(server.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        server.wait(timeout=5)
    return outputs


if __name__ == '__main__':
    try:
        raw = sys.stdin.buffer.read(12 * 1024 * 1024 + 1)
        if len(raw) > 12 * 1024 * 1024:
            raise ValueError('request exceeds limit')
        print(json.dumps({'version': 1, 'observations': execute(json.loads(raw))}))
    except Exception as exc:
        print(json.dumps({'version': 1, 'error': type(exc).__name__}))
        sys.exit(2)
