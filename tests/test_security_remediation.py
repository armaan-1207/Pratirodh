"""Bounded regression cases for the six dated assessment findings."""
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import re
import threading
from unittest.mock import Mock
import zipfile

import pytest

from pratirodh.evidence import Store
from pratirodh.projects import export
from pratirodh.projects.manifest import inventory, IntakeRejected
from pratirodh.projects.model import LocalModel
from pratirodh.projects.worker import DockerProjectWorker
from pratirodh.security_events import SecurityEvents
from pratirodh.web import create_app


@pytest.mark.parametrize('name', ['id_rsa', 'nested/ID_ED25519', '.env.local', '.ENV.production',
                                   'credentials.json', 'nested/secrets.yaml', 'key.PEM', '.aws/config', '.npmrc'])
def test_secret_locations_do_not_enter_inventory(tmp_path, name):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('ASSESSMENT_ONLY_NOT_A_SECRET')
    with pytest.raises(IntakeRejected, match='remove credentials'):
        inventory(tmp_path)


@pytest.mark.parametrize('body', ['-----BEGIN OPENSSH PRIVATE KEY-----\nSYNTHETIC',
                                   '-----BEGIN RSA PRIVATE KEY-----\nSYNTHETIC',
                                   '-----BEGIN PGP PRIVATE KEY BLOCK-----\nSYNTHETIC'])
def test_renamed_private_material_is_rejected(tmp_path, body):
    (tmp_path / 'notes.txt').write_text(body)
    with pytest.raises(IntakeRejected, match='private key or token'):
        inventory(tmp_path)


def test_legitimate_source_and_fixture_inventory_is_retained(tmp_path):
    (tmp_path / 'app.py').write_text('print("normal")\n')
    (tmp_path / 'fixture.json').write_text('{"case":"normal"}')
    files, hashes, _ = inventory(tmp_path)
    assert set(files) == set(hashes) == {'app.py', 'fixture.json'}


def test_worker_rejects_secret_payload_before_docker(monkeypatch):
    worker = DockerProjectWorker.__new__(DockerProjectWorker)
    identity = Mock(side_effect=AssertionError('Docker must not be contacted'))
    monkeypatch.setattr(worker, 'identity', identity)
    with pytest.raises(IntakeRejected):
        worker.execute({'id_rsa': 'SYNTHETIC'}, [], None)
    identity.assert_not_called()


@pytest.mark.parametrize('status', [301, 302, 303, 307, 308])
@pytest.mark.parametrize('payload', [None, {'prompt': 'SYNTHETIC_ONLY'}])
def test_project_model_get_and_post_never_follow_redirects(status, payload):
    class Target(BaseHTTPRequestHandler):
        hits = 0
        def do_GET(self):
            Target.hits += 1
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{}')
        do_POST = do_GET
        def log_message(self, *args):
            pass
    target = ThreadingHTTPServer(('127.0.0.1', 0), Target)
    class Redirect(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.command == 'POST':
                self.rfile.read(int(self.headers.get('Content-Length', '0')))
            self.send_response(status)
            self.send_header('Location', f'http://127.0.0.1:{target.server_port}/target')
            self.end_headers()
        do_POST = do_GET
        def log_message(self, *args):
            pass
    origin = ThreadingHTTPServer(('127.0.0.1', 0), Redirect)
    servers = [origin, target]
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        model = LocalModel({'profile': 'laptop', 'runtime': 'ollama', 'name': 'qwen2.5-coder:7b',
            'endpoint': f'http://127.0.0.1:{origin.server_port}', 'weights_digest': 'sha256:' + 'a'*64,
            'runtime_digest': 'sha256:' + 'b'*64, 'quantization': 'Q4_K_M', 'available_memory_gb': 8})
        with pytest.raises(RuntimeError, match='redirects are prohibited'):
            model._request('/api/tags', payload)
        assert Target.hits == 0
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()


@pytest.mark.parametrize('case', ['key', 'member', 'total', 'count', 'ratio', 'archive', 'path'])
def test_bundle_limits_reject_before_any_decompression(tmp_path, monkeypatch, case):
    path = tmp_path / 'bounded.zip'
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('trust.pub', b'x' * (131072 if case == 'key' else 32))
        archive.writestr('evidence/../outside' if case == 'path' else 'evidence/artifact.txt', b'a' * 256)
    limits = {'member': ('MAX_MEMBER_BYTES', 128), 'total': ('MAX_TOTAL_BYTES', 128),
              'count': ('MAX_MEMBERS', 1), 'ratio': ('MAX_COMPRESSION_RATIO', 1),
              'archive': ('MAX_ARCHIVE_BYTES', 10)}
    if case in limits:
        monkeypatch.setattr(export, *limits[case])
    opened = Mock(side_effect=AssertionError('untrusted member must not be decompressed'))
    monkeypatch.setattr(zipfile.ZipFile, 'open', opened)
    with pytest.raises(ValueError, match='limit|size|unsafe'):
        export.verify_bundle(path, b'x' * 32)
    opened.assert_not_called()


def events(caplog):
    return [json.loads(record.message) for record in caplog.records if record.message.startswith('{')]


def test_integrity_denial_is_logged_and_aggregated_without_secret_content(tmp_path, caplog):
    store = Store(tmp_path / 'store')
    run_id = 'a' * 32
    store.save({'id': run_id, 'created': '2026-10-07', 'decision': 'REJECT'}, {})
    report = store.run_path(run_id) / 'report.json'
    report.chmod(0o644)
    report.write_text('{"private":"SYNTHETIC_DO_NOT_LOG"}')
    client = create_app(store).test_client()
    with caplog.at_level(logging.WARNING):
        responses = [client.get('/runs/' + run_id) for _ in range(5)]
    assert all(response.status_code == 409 for response in responses)
    captured = events(caplog)
    denials = [item for item in captured if item['type'] == 'security_event']
    alerts = [item for item in captured if item['type'] == 'security_alert']
    assert len(denials) == 5 and len(alerts) == 1 and alerts[0]['count'] == 5
    assert all(item['code'] == 'evidence_integrity_denied' and item['record_id'] == run_id for item in captured)
    assert all(re.fullmatch('[a-f0-9]{32}', item['request_id']) for item in captured)
    assert denials[-1]['request_id'] == responses[-1].headers['X-Request-ID']
    assert 'SYNTHETIC_DO_NOT_LOG' not in caplog.text


def test_alert_window_and_identifier_sanitization(caplog):
    now = [0]
    sink = SecurityEvents(logging.getLogger('security-regression'), clock=lambda: now[0])
    for _ in range(6):
        sink.emit('evidence_export_denied', 'b'*32, record_id='unsafe\nPRIVATE')
    now[0] = 61
    for _ in range(5):
        sink.emit('evidence_export_denied', 'b'*32, record_id='c'*32)
    assert len([item for item in events(caplog) if item['type'] == 'security_alert']) == 2
    assert 'PRIVATE' not in caplog.text
    assert sink.recent.maxlen == 1000


def test_intake_ui_is_actionable_without_echoing_contents(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    (source / '.env.local').write_text('SYNTHETIC_DO_NOT_DISPLAY')
    client = create_app(Store(tmp_path / 'store')).test_client()
    client.get('/projects')
    with client.session_transaction() as session:
        token = session['csrf']
    response = client.post('/projects/inspect', data={'source': str(source), 'csrf': token})
    assert response.status_code == 400
    assert b'Inspection blocked' in response.data and b'No project code was executed' in response.data
    assert b'SYNTHETIC_DO_NOT_DISPLAY' not in response.data


def test_validation_security_scope_is_dated_and_not_certification(tmp_path):
    response = create_app(Store(tmp_path / 'store')).test_client().get('/validation')
    assert response.status_code == 200
    assert b'Recorded application security checks' in response.data
    assert b'2026-10-07' in response.data
    assert b'do not certify' in response.data
    assert b'Azure qualification' in response.data
