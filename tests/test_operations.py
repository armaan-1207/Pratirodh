"""Synthetic operator drills; no production keys, destinations or source changes."""
import copy
import base64
import json
import sqlite3
from types import SimpleNamespace
import urllib.error
import urllib.request
import ssl
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from cryptography.exceptions import InvalidTag
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from pratirodh.evidence import Store
from pratirodh.operations import (encrypted_backup, restore_backup,
    create_signing_epoch, HTTPSAlertDelivery, NoRedirect, MAGIC, key_for)

PASSWORD = b'synthetic-backup-passphrase-only'


@pytest.fixture
def evidence(tmp_path):
    store = Store(tmp_path / 'original')
    for number in range(3):
        store.save({'id': format(number, '032x'), 'created': '2026-10-07',
                    'decision': 'REJECT', 'scenario': 'SYNTHETIC_PRIVATE_MARKER'}, {})
    return store


@pytest.mark.parametrize('signer', [False, True])
def test_encrypted_recovery_preserves_all_signed_records(tmp_path, evidence, signer):
    backup = tmp_path / 'encrypted.backup'
    saved = encrypted_backup(evidence, backup, PASSWORD, include_signer=signer)
    assert saved['records'] == 3 and saved['encrypted']
    assert b'SYNTHETIC_PRIVATE_MARKER' not in backup.read_bytes()
    assert (evidence.root / 'signing.key').read_bytes() not in backup.read_bytes()
    restored = tmp_path / 'restored'
    receipt = restore_backup(backup, restored, PASSWORD, (evidence.root / 'trust.pub').read_bytes())
    assert receipt['records'] == 3 and receipt['signatures_verified']
    assert (restored / 'signing.key').exists() == signer
    for run_id in evidence.list():
        assert Store(restored).load(run_id) == evidence.load(run_id)
    with pytest.raises(ValueError, match='fresh destination'):
        encrypted_backup(evidence, backup, PASSWORD)
    with pytest.raises(ValueError, match='nonexistent destination'):
        restore_backup(backup, restored, PASSWORD, (evidence.root / 'trust.pub').read_bytes())


@pytest.mark.parametrize('failure', ['wrong-password', 'tamper', 'wrong-trust'])
def test_failed_restore_creates_no_destination(tmp_path, evidence, failure):
    backup = tmp_path / 'encrypted.backup'
    encrypted_backup(evidence, backup, PASSWORD)
    password = PASSWORD
    trust = (evidence.root / 'trust.pub').read_bytes()
    if failure == 'wrong-password':
        password = b'incorrect-synthetic-password'
    elif failure == 'tamper':
        blob = bytearray(backup.read_bytes())
        blob[-1] ^= 1
        backup.write_bytes(blob)
    else:
        trust = b'x' * 32
    destination = tmp_path / 'refused'
    with pytest.raises((ValueError, InvalidTag)):
        restore_backup(backup, destination, password, trust)
    assert not destination.exists()


@pytest.mark.parametrize('problem', ['unexpected-file', 'index-mismatch', 'tampered-record', 'wrong-signer'])
def test_inconsistent_source_cannot_create_backup(tmp_path, evidence, problem):
    if problem == 'unexpected-file':
        (evidence.root / 'unexpected.txt').write_text('not evidence')
    elif problem == 'index-mismatch':
        with sqlite3.connect(evidence.root / 'index.sqlite') as database:
            database.execute('DELETE FROM runs WHERE id = ?', ('0' * 32,))
    elif problem == 'tampered-record':
        path = evidence.run_path('0' * 32) / 'report.json'
        path.chmod(0o600)
        path.write_text('{}')
    else:
        other = tmp_path / 'epoch'
        create_signing_epoch(other)
        (evidence.root / 'signing.key').write_bytes((other / 'signing.key').read_bytes())
    backup = tmp_path / 'refused.backup'
    with pytest.raises(ValueError):
        encrypted_backup(evidence, backup, PASSWORD, include_signer=True)
    assert not backup.exists()


def test_new_epoch_preserves_old_store_and_refuses_overwrite(tmp_path, evidence):
    old_key = (evidence.root / 'signing.key').read_bytes()
    new = tmp_path / 'next-epoch'
    receipt = create_signing_epoch(new)
    assert receipt['old_store_modified'] is False
    assert old_key == (evidence.root / 'signing.key').read_bytes()
    assert (new / 'trust.pub').read_bytes() != (evidence.root / 'trust.pub').read_bytes()
    Store(new).save({'id': 'f' * 32, 'created': '2026-10-07', 'decision': 'REJECT'}, {})
    assert Store(new).load('f' * 32)['decision'] == 'REJECT'
    assert evidence.load('0' * 32)['decision'] == 'REJECT'
    with pytest.raises(ValueError, match='nonexistent directory'):
        create_signing_epoch(new)


@pytest.mark.parametrize('endpoint', ['http://receiver.invalid/alerts',
    'https://user:password@receiver.invalid/alerts', 'https://receiver.invalid/?token=x',
    'https://receiver.invalid/#secret', 'file:///private'])
def test_alert_endpoint_requires_safe_https(endpoint):
    with pytest.raises(ValueError):
        HTTPSAlertDelivery(endpoint, 'synthetic-token-only')


def test_alert_sanitizes_and_requires_acknowledgement():
    captured = []
    class Response:
        status = 204
        def __enter__(self): return self
        def __exit__(self, *args): pass
    def open_request(request, timeout):
        captured.append((request, timeout))
        return Response()
    delivery = HTTPSAlertDelivery('https://receiver.invalid/alerts', 'synthetic-token-only',
                                 opener=SimpleNamespace(open=open_request))
    event = {'type': 'security_alert', 'code': 'evidence_integrity_denied',
             'request_id': 'a' * 32, 'count': 5, 'source': 'private-source',
             'key': 'private-key', 'exception': 'private-message'}
    original = copy.deepcopy(event)
    assert delivery.deliver(event)['delivered']
    assert event == original
    transmitted = json.loads(captured[0][0].data)
    assert set(transmitted) == {'type', 'code', 'request_id', 'count'}
    assert b'private' not in captured[0][0].data
    assert captured[0][1] == 5


@pytest.mark.parametrize('failure', ['outage', 'redirect'])
def test_alert_failure_is_observable_without_retry_or_secret(failure):
    calls = []
    def refuse(request, timeout):
        calls.append(1)
        if failure == 'redirect':
            raise urllib.error.HTTPError(request.full_url, 302, 'private-token-message', {}, None)
        raise urllib.error.URLError('private-token-message')
    delivery = HTTPSAlertDelivery('https://receiver.invalid/alerts', 'synthetic-token-only',
                                 opener=SimpleNamespace(open=refuse))
    with pytest.raises(RuntimeError, match='operator action required') as result:
        delivery.deliver({'type': 'security_alert', 'code': 'evidence_integrity_denied',
                         'request_id': 'a' * 32, 'count': 5})
    assert 'private-token' not in str(result.value)
    assert calls == [1]
    assert NoRedirect().redirect_request(None, None, None, None, None, None) is None


@pytest.mark.parametrize('count', [True, 0, -1, 1001])
def test_invalid_alert_is_rejected_before_network(count):
    delivery = HTTPSAlertDelivery('https://receiver.invalid/alerts', 'synthetic-token-only',
        opener=SimpleNamespace(open=lambda *a, **k: pytest.fail('network must not be used')))
    with pytest.raises(ValueError):
        delivery.deliver({'type': 'security_alert', 'code': 'denied', 'request_id': 'a' * 32, 'count': count})


def test_real_loopback_https_alert_and_untrusted_certificate_rejection(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    now = datetime.now(timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(hours=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256()))
    cert_path, key_path = tmp_path / 'local.crt', tmp_path / 'local.key'
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    key_path.chmod(0o600)
    received = []
    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.headers.get('Authorization') != 'Bearer synthetic-token-only':
                self.send_error(401)
                return
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096:
                self.send_error(413)
                return
            received.append(json.loads(self.rfile.read(length)))
            self.send_response(204)
            self.end_headers()
        def log_message(self, *args): pass
    receiver = ThreadingHTTPServer(('127.0.0.1', 0), Receiver)
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(cert_path, key_path)
    receiver.socket = server_context.wrap_socket(receiver.socket, server_side=True)
    thread = threading.Thread(target=receiver.serve_forever, daemon=True)
    thread.start()
    endpoint = 'https://localhost:' + str(receiver.server_port) + '/alerts'
    event = {'type': 'security_alert', 'code': 'integrity_denied',
             'request_id': 'a' * 32, 'count': 5, 'private': 'do not send'}
    try:
        with pytest.raises(RuntimeError, match='delivery failed'):
            HTTPSAlertDelivery(endpoint, 'synthetic-token-only').deliver(event)
        assert received == []
        trusted = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(cert_path))))
        assert HTTPSAlertDelivery(endpoint, 'synthetic-token-only', opener=trusted).deliver(event)['delivered']
        assert len(received) == 1 and 'private' not in received[0]
    finally:
        receiver.shutdown()
        receiver.server_close()
        thread.join(timeout=5)


def sealed_document(path, document):
    salt, nonce = b's' * 16, b'n' * 12
    plain = document.encode() if isinstance(document, str) else json.dumps(document).encode()
    path.write_bytes(MAGIC + salt + nonce + AESGCM(key_for(PASSWORD, salt)).encrypt(nonce, plain, MAGIC))


@pytest.mark.parametrize('name', ['artifact.txt:secret', 'CON', 'nul.json',
    'artifact.', 'artifact ', 'bad?.txt', 'bad|name', 'LPT1.txt'])
def test_restore_rejects_portable_path_aliases_before_creation(tmp_path, evidence, name):
    backup, output = tmp_path / 'hostile.backup', tmp_path / 'refused'
    trust = (evidence.root / 'trust.pub').read_bytes()
    from pratirodh.evidence import digest
    sealed_document(backup, {'version': 1, 'records': [], 'trust_sha256': digest(trust),
        'files': {'trust.pub': base64.b64encode(trust).decode(), 'index.sqlite': '',
                  'runs/' + 'a' * 32 + '/' + name: ''}})
    with pytest.raises(ValueError, match='unsafe backup member'):
        restore_backup(backup, output, PASSWORD, trust)
    assert not output.exists()


@pytest.mark.parametrize('document', ['[]', 'null', '{"version":1,"version":1}',
    '{"version":true,"records":[],"files":{}}'])
def test_restore_rejects_malformed_authenticated_structure(tmp_path, document):
    backup, output = tmp_path / 'bad.backup', tmp_path / 'refused'
    sealed_document(backup, document)
    with pytest.raises(ValueError):
        restore_backup(backup, output, PASSWORD, b'x' * 32)
    assert not output.exists()


def test_source_size_limit_applies_before_evidence_parsing(tmp_path, evidence, monkeypatch):
    import pratirodh.operations as operations
    monkeypatch.setattr(operations, 'MAX_BACKUP_BYTES', 64)
    monkeypatch.setattr(evidence, 'load', lambda *_: pytest.fail('unbounded evidence parsing'))
    output = tmp_path / 'refused.backup'
    with pytest.raises(ValueError, match='size limit'):
        encrypted_backup(evidence, output, PASSWORD)
    assert not output.exists()


def test_inventory_limit_applies_before_evidence_parsing(tmp_path, evidence, monkeypatch):
    import pratirodh.operations as operations
    monkeypatch.setattr(operations, 'MAX_BACKUP_MEMBERS', 2)
    monkeypatch.setattr(evidence, 'load', lambda *_: pytest.fail('unbounded evidence parsing'))
    with pytest.raises(ValueError, match='inventory limit'):
        encrypted_backup(evidence, tmp_path / 'refused.backup', PASSWORD)


def test_backup_rejects_index_metadata_that_disagrees_with_signed_report(tmp_path, evidence):
    with sqlite3.connect(evidence.root / 'index.sqlite') as database:
        database.execute('UPDATE runs SET decision = ?', ('READY_FOR_REVIEW',))
    backup = tmp_path / 'refused.backup'
    with pytest.raises(ValueError, match='index metadata differs'):
        encrypted_backup(evidence, backup, PASSWORD)
    assert not backup.exists()


def test_cli_refuses_echoing_passphrase_fallback(monkeypatch):
    import getpass
    import warnings
    from tools.manage_operations import secret_prompt
    def fallback(message):
        warnings.warn('echo fallback', getpass.GetPassWarning)
        pytest.fail('echo fallback must not continue')
    monkeypatch.setattr(getpass, 'getpass', fallback)
    with pytest.raises(ValueError, match='non-echoing interactive terminal'):
        secret_prompt('Synthetic passphrase: ')


def test_database_path_with_uri_fragment_round_trips(tmp_path):
    store = Store(tmp_path / 'evidence#snapshot')
    store.save({'id': 'a' * 32, 'created': '2026-10-07', 'decision': 'REJECT'}, {})
    backup = tmp_path / 'snapshot.backup'
    encrypted_backup(store, backup, PASSWORD)
    receipt = restore_backup(backup, tmp_path / 'restored#snapshot', PASSWORD,
                             (store.root / 'trust.pub').read_bytes())
    assert receipt['records'] == 1


@pytest.mark.parametrize('token', ['synthetic\tcontrol-token', 'synthetic\x00control-token',
    'synthetic-token-' + chr(0x100), 'synthetic token space', 'a' * 5000])
def test_alert_token_rejected_before_transport(token):
    with pytest.raises(ValueError, match='bearer token'):
        HTTPSAlertDelivery('https://receiver.invalid/alerts', token)


def test_alert_token_padding_is_included_in_length_bound():
    with pytest.raises(ValueError, match='bearer token'):
        HTTPSAlertDelivery('https://receiver.invalid/alerts', 'synthetic-token-only' + '=' * 4096)


def test_alert_requires_string_identifiers():
    delivery = HTTPSAlertDelivery('https://receiver.invalid/alerts', 'synthetic-token-only',
        opener=SimpleNamespace(open=lambda *a, **k: pytest.fail('network must not be used')))
    with pytest.raises(ValueError, match='invalid security alert'):
        delivery.deliver({'type': 'security_alert', 'code': 'denied',
                         'request_id': int('1' * 32), 'count': 1})


def test_invalid_trust_key_is_rejected_before_any_backup_read(tmp_path):
    with pytest.raises(ValueError, match='32-byte Ed25519'):
        restore_backup(tmp_path / 'not-read.backup', tmp_path / 'not-created', PASSWORD, b'short')
    assert not (tmp_path / 'not-created').exists()


@pytest.mark.parametrize('endpoint', ['https://receiver.invalid:wrong/alerts',
    'https://receiver.invalid:70000/alerts', ' https://receiver.invalid/alerts',
    'https://receiver.invalid/alert\n'])
def test_malformed_alert_endpoint_rejected_before_transport(endpoint):
    with pytest.raises(ValueError):
        HTTPSAlertDelivery(endpoint, 'synthetic-token-only')


@pytest.mark.parametrize('timeout', [True, float('nan'), float('inf'), '5'])
def test_invalid_alert_timeout_rejected(timeout):
    with pytest.raises(ValueError, match='timeout'):
        HTTPSAlertDelivery('https://receiver.invalid/alerts', 'synthetic-token-only', timeout=timeout)


@pytest.mark.parametrize('event', [None, [], 'private-token-message'])
def test_invalid_alert_structure_does_not_reach_transport(event):
    delivery = HTTPSAlertDelivery('https://receiver.invalid/alerts', 'synthetic-token-only',
        opener=SimpleNamespace(open=lambda *a, **k: pytest.fail('network must not be used')))
    with pytest.raises(ValueError, match='invalid security alert'):
        delivery.deliver(event)
