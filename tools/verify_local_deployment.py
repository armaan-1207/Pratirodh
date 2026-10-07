"""Isolated local TLS, log delivery and synthetic restore verification.

Uses already installed Docker images; it does not provision public resources,
read operator secrets, modify production evidence, or assert public readiness.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from pathlib import Path
import secrets
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid

if not __debug__:
    raise RuntimeError('deployment verification requires assertions; unset PYTHONOPTIMIZE and omit -O')

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pratirodh.evidence import Store
from pratirodh.security_events import SecurityEvents


def docker(*args, check=True):
    result = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=90)
    if check and result.returncode:
        # Environment values and container logs can contain credentials.
        raise RuntimeError('Docker operation failed: ' + args[0])
    return result.stdout.strip()


def alert_delivery():
    received = []
    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096:
                self.send_error(413)
                return
            received.append(json.loads(self.rfile.read(length)))
            self.send_response(204)
            self.end_headers()
        def log_message(self, *args):
            pass
    receiver = ThreadingHTTPServer(('127.0.0.1', 0), Receiver)
    thread = threading.Thread(target=receiver.serve_forever, daemon=True)
    thread.start()
    class LocalCollector(logging.Handler):
        def emit(self, record):
            message = json.loads(record.getMessage())
            if message['type'] == 'security_alert':
                request = urllib.request.Request(
                    f'http://127.0.0.1:{receiver.server_port}/alerts',
                    data=json.dumps(message).encode(),
                    headers={'Content-Type': 'application/json'})
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(request, timeout=5) as response:
                    assert response.status == 204
    logger = logging.Logger('local-deployment-collector')
    logger.addHandler(LocalCollector())
    try:
        events = SecurityEvents(logger)
        for _ in range(5):
            events.emit('evidence_integrity_denied', uuid.uuid4().hex,
                        record_id='invalid\nSYNTHETIC_PRIVATE_MARKER')
        assert len(received) == 1 and received[0]['count'] == 5
        assert 'SYNTHETIC_PRIVATE_MARKER' not in json.dumps(received)
        return {'delivered': 1, 'threshold': 5, 'sanitized': True,
                'scope': 'Temporary local log collector and HTTP receiver; public delivery not configured'}
    finally:
        receiver.shutdown()
        receiver.server_close()
        thread.join(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', default='pratirodh-dashboard:cleanup-candidate')
    parser.add_argument('--output', default='run_output/local-deployment-verification.json')
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('verification receipt already exists; choose a new --output path')
    # Refuse downloads: this check only exercises locally available images.
    image_id = docker('image', 'inspect', args.image, '--format', '{{.Id}}')
    caddy_id = docker('image', 'inspect', 'caddy:2', '--format', '{{.Id}}')
    suffix = uuid.uuid4().hex[:12]
    network, dashboard, proxy = ('pratirodh-' + suffix + part for part in ('-network', '-dashboard', '-tls'))
    receipt = {'checked_at': datetime.now(timezone.utc).isoformat(),
               'dashboard_image': image_id, 'proxy_image': caddy_id,
               'scope': 'Local synthetic verification only', 'public_activation': 'NOT_CONFIGURED'}
    with tempfile.TemporaryDirectory(prefix='pratirodh-deploy-check-') as temporary:
        root = Path(temporary)
        original = Store(root / 'private')
        run_id = uuid.uuid4().hex
        original.save({'id': run_id, 'created': '2026-10-07', 'decision': 'REJECT',
                       'scenario': 'Synthetic deployment restore check'}, {})
        trust = (original.root / 'trust.pub').read_bytes()
        backup = root / 'private-backup'
        shutil.copytree(original.root, backup)
        restore = root / 'restored-private'
        shutil.copytree(backup, restore)
        restored = Store(restore)
        assert (restore / 'trust.pub').read_bytes() == trust
        assert (restore / 'signing.key').read_bytes() == (original.root / 'signing.key').read_bytes()
        assert restored.load(run_id) == original.load(run_id)
        public = root / 'public'
        shutil.copytree(restore, public, ignore=shutil.ignore_patterns('signing.key'))
        assert not (public / 'signing.key').exists()
        assert Store(public).load(run_id) == original.load(run_id)
        altered = root / 'tampered-restore'
        shutil.copytree(public, altered)
        altered_report = Store(altered).run_path(run_id) / 'report.json'
        altered_report.chmod(0o600)
        altered_report.write_text('{}')
        try:
            Store(altered).load(run_id)
        except ValueError:
            pass
        else:
            raise AssertionError('tampered restore was accepted')
        receipt['restore'] = {'signature_verified': True, 'private_key_restored': True,
                              'public_snapshot_excludes_private_key': True,
                              'tampered_restore_rejected': True,
                              'trust_fingerprint': hashlib.sha256(trust).hexdigest(),
                              'scope': 'Synthetic staging restore; operator backup infrastructure not verified'}
        config = root / 'Caddyfile'
        config.write_text('localhost {\n tls internal\n reverse_proxy ' + dashboard +
                          ':8765\n}\n:443 {\n respond 403\n}\n')
        password = secrets.token_urlsafe(32)
        try:
            docker('network', 'create', '--internal', network)
            docker('run', '-d', '--pull', 'never', '--name', dashboard, '--network', network,
                   '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
                   '--pids-limit', '64', '--memory', '512m', '--cpus', '1',
                   # Private container tmpfs; not a host temporary-file path.
                   '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=32m,mode=1777',  # nosec B108
                   '-e', 'PRATIRODH_ENV=production', '-e', 'PRATIRODH_READ_ONLY=1',
                   '-e', 'PRATIRODH_PASSWORD=' + password,
                   '-e', 'PRATIRODH_SESSION_SECRET=' + secrets.token_urlsafe(48),
                   '-v', str(public) + ':/app/run_output/pratirodh:ro', args.image)
            # Docker's internal-only network intentionally does not publish ports.
            # The proxy alone attaches to bridge; the dashboard remains internal.
            docker('run', '-d', '--pull', 'never', '--name', proxy, '--network', 'bridge',
                   '-p', '127.0.0.1::443', '-v', str(config) + ':/etc/caddy/Caddyfile:ro', 'caddy:2')
            docker('network', 'connect', network, proxy)
            backend = json.loads(docker('inspect', dashboard))[0]
            assert not backend['HostConfig']['PortBindings']
            assert not any(backend['NetworkSettings']['Ports'].values())
            assert backend['HostConfig']['ReadonlyRootfs']
            assert not any('docker.sock' in mount['Destination'] for mount in backend['Mounts'])
            container = json.loads(docker('inspect', proxy))[0]
            bindings = container['NetworkSettings']['Ports']['443/tcp']
            assert bindings and bindings[0]['HostIp'] == '127.0.0.1'
            port = bindings[0]['HostPort']
            ca = root / 'local-root.crt'
            for _ in range(30):
                result = docker('cp', proxy + ':/data/caddy/pki/authorities/local/root.crt', str(ca), check=False)
                if ca.exists():
                    break
                time.sleep(1)
            context = ssl.create_default_context(cafile=str(ca))
            base = 'https://localhost:' + port
            # Prohibit machine proxy settings from routing this local check elsewhere.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                                urllib.request.HTTPSHandler(context=context))
            def request(path, auth=False, data=None, extra=None):
                headers = dict(extra or {})
                if auth:
                    headers['Authorization'] = 'Basic ' + base64.b64encode(('reviewer:' + password).encode()).decode()
                try:
                    response = opener.open(urllib.request.Request(base + path, data=data, headers=headers), timeout=10)
                    return response.status, response.headers, response.read()
                except urllib.error.HTTPError as error:
                    return error.code, error.headers, error.read()
            for _ in range(30):
                try:
                    if request('/healthz')[0] == 200:
                        break
                except (OSError, urllib.error.URLError):
                    pass
                time.sleep(1)
            health_status = request('/healthz')[0]
            if health_status != 200:
                # Prior to authentication, proxy diagnostics contain no credentials.
                raise RuntimeError('local TLS health failed: ' + str(health_status) + '\n' +
                                   docker('logs', '--tail', '4', proxy, check=False))
            untrusted = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                urllib.request.HTTPSHandler(context=ssl.create_default_context()))
            try:
                untrusted.open(base + '/healthz', timeout=10)
            except urllib.error.URLError as error:
                assert isinstance(error.reason, ssl.SSLCertVerificationError)
            else:
                raise AssertionError('local certificate accepted without its trust anchor')
            assert request('/validation')[0] == 401
            status, headers, body = request('/validation', auth=True)
            assert status == 200 and b'Recorded local functional verification' in body
            assert request('/projects/inspect', auth=True, data=b'')[0] == 403
            invalid_host_status = request('/validation', auth=True, extra={'Host': 'unexpected.invalid'})[0]
            assert invalid_host_status == 403, 'proxy must reject unexpected hosts'
            backend_denial = docker('exec', dashboard, 'python', '-c',
                "import urllib.request,urllib.error; "
                "r=urllib.request.Request('http://127.0.0.1:8765/validation',headers={'Host':'unexpected.invalid'}); "
                "exec('try:\\n urllib.request.urlopen(r,timeout=5)\\nexcept urllib.error.HTTPError as e:\\n print(e.code)')")
            assert backend_denial == '403'
            assert 'Secure' in headers.get('Set-Cookie', '') and 'HttpOnly' in headers.get('Set-Cookie', '')
            assert headers['Strict-Transport-Security'] == 'max-age=31536000'
            assert "frame-ancestors 'none'" in headers['Content-Security-Policy']
            assert headers['X-Content-Type-Options'] == 'nosniff'
            assert headers['Cache-Control'] == 'no-store'
            receipt['https'] = {'trusted_local_ca_verified': True, 'hostname_verified': True,
                                'untrusted_ca_rejected': True,
                                'anonymous_status': 401, 'authenticated_status': 200,
                                'readonly_post_status': 403, 'proxy_unexpected_host_status': invalid_host_status,
                                'backend_unexpected_host_status': 403,
                                'secure_cookie_and_headers': True, 'loopback_binding': True,
                                'dashboard_has_no_published_ports': True}
            receipt['alert_delivery'] = alert_delivery()
        finally:
            docker('rm', '-f', '-v', proxy, dashboard, check=False)
            docker('network', 'rm', network, check=False)
    receipt['status'] = 'PASS'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
