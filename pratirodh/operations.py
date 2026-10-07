"""Opt-in operator controls; no automatic key replacement or network activation."""
from contextlib import closing, contextmanager
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from .evidence import Store, canonical, digest
from .execution import Budget
from .projects.leases import Lease

MAX_BACKUP_BYTES = 64 * 1024 * 1024
MAX_BACKUP_MEMBERS = 20000
MAGIC = b'PRATIRODH-BACKUP-1\x00'


@contextmanager
def locked_store(store):
    lease = Lease('evidence-' + digest(str(store.root))[:24])
    if not lease.acquire(Budget(30)):
        raise TimeoutError('evidence writer busy')
    try:
        yield
    finally:
        lease.release()


def private_write(path, body):
    """Exclusive creation; never overwrite an existing key, backup or source."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())


def key_for(password, salt):
    if not isinstance(password, bytes) or len(password) < 16:
        raise ValueError('backup passphrase must contain at least 16 UTF-8 bytes')
    return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(password)


def allowed_member(name):
    if not isinstance(name, str) or not re.fullmatch(
            r'(?:trust\.pub|signing\.key|index\.sqlite|runs/[a-f0-9]{32}/[^/\\\x00-\x1f]+)', name):
        return False
    # Portable archives must not become Windows streams, device aliases or
    # path aliases when restored on another OS.
    return all(len(part) <= 255 and part not in {'.', '..'}
               and not re.search(r'[<>:"|?*\x00-\x1f\x7f]', part)
               and not part.endswith((' ', '.'))
               and not re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?', part, re.I)
               for part in name.split('/'))


def read_only_database(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError('duplicate backup object key')
        result[name] = value
    return result


def fresh_destination(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise ValueError('destination links are not accepted')
    if path.exists():
        raise ValueError('operation requires a nonexistent destination')
    return path.resolve()


def verified_records(store):
    with closing(read_only_database(store.root / 'index.sqlite')) as database:
        rows = list(database.execute('SELECT id, created, decision, scenario FROM runs ORDER BY id'))
        ids = [row[0] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate evidence index records')
    disk_ids = sorted(path.name for path in (store.root / 'runs').iterdir())
    if disk_ids != ids:
        raise ValueError('evidence index and record inventory disagree')
    for run_id, created, decision, scenario in rows:
        report = store.load(run_id)
        if (report.get('id'), report.get('created'), report.get('decision'),
                report.get('scenario', 'unknown')) != (run_id, created, decision, scenario):
            raise ValueError('evidence index metadata differs from signed record')
    return ids


def encrypted_backup(store, output, password, include_signer=False):
    """Capture signed records plus a SQLite snapshot under the writer lease."""
    if Path(output).exists():
        raise ValueError('backup requires a fresh destination outside evidence store')
    output = fresh_destination(output)
    if output.is_relative_to(store.root):
        raise ValueError('backup requires a fresh destination outside evidence store')
    with locked_store(store):
        paths, source_bytes = [], 0
        for path in store.root.rglob('*'):
            paths.append(path)
            if len(paths) > MAX_BACKUP_MEMBERS:
                raise ValueError('evidence backup exceeds local inventory limit')
            if path.is_file():
                source_bytes += path.stat().st_size
                if source_bytes > MAX_BACKUP_BYTES:
                    raise ValueError('evidence backup exceeds local size limit')
        if any(path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()) for path in paths):
            raise ValueError('evidence links are not accepted')
        ids = verified_records(store)
        bodies, total = {}, 0
        for path in paths:
            if not path.is_file():
                continue
            name = path.relative_to(store.root).as_posix()
            if name in {'index.sqlite', 'index.sqlite-wal', 'index.sqlite-shm'}:
                continue
            if name == 'signing.key' and not include_signer:
                continue
            if not allowed_member(name):
                raise ValueError('unexpected evidence file; backup refused')
            size = path.stat().st_size
            if size + total > MAX_BACKUP_BYTES:
                raise ValueError('evidence backup exceeds local size limit')
            with path.open('rb') as stream:
                body = stream.read(MAX_BACKUP_BYTES - total + 1)
            total += len(body)
            if total > MAX_BACKUP_BYTES:
                raise ValueError('evidence backup exceeds local size limit')
            bodies[name] = base64.b64encode(body).decode('ascii')
        with tempfile.TemporaryDirectory(prefix='pratirodh-backup-') as temporary:
            snapshot = Path(temporary) / 'index.sqlite'
            with closing(read_only_database(store.root / 'index.sqlite')) as source:
                with closing(sqlite3.connect(snapshot)) as target:
                    source.backup(target)
            if snapshot.stat().st_size + total > MAX_BACKUP_BYTES:
                raise ValueError('evidence backup exceeds local size limit')
            bodies['index.sqlite'] = base64.b64encode(snapshot.read_bytes()).decode('ascii')
        public = base64.b64decode(bodies['trust.pub'])
        Ed25519PublicKey.from_public_bytes(public)
        if include_signer:
            signer = Ed25519PrivateKey.from_private_bytes(base64.b64decode(bodies['signing.key']))
            if signer.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw) != public:
                raise ValueError('backup signer does not match trust anchor')
        document = {'version': 1, 'records': ids, 'trust_sha256': digest(public), 'files': bodies}
        salt, nonce = os.urandom(16), os.urandom(12)
        sealed = AESGCM(key_for(password, salt)).encrypt(nonce, canonical(document).encode(), MAGIC)
        blob = MAGIC + salt + nonce + sealed
        if len(blob) > 2 * MAX_BACKUP_BYTES:
            raise ValueError('encrypted backup exceeds local size limit')
        private_write(output, blob)
    return {'records': len(ids), 'trust_sha256': digest(public), 'sha256': digest(blob),
            'encrypted': True, 'includes_signer': include_signer,
            'scope': 'Local encrypted snapshot; off-host placement and retention unverified'}


def restore_backup(backup, output, password, trusted_public):
    """Authenticate and validate everything before exclusive directory creation."""
    if not isinstance(trusted_public, bytes) or len(trusted_public) != 32:
        raise ValueError('independent trust anchor must be a 32-byte Ed25519 public key')
    Ed25519PublicKey.from_public_bytes(trusted_public)
    output = fresh_destination(output)
    backup = Path(backup)
    if backup.stat().st_size > 2 * MAX_BACKUP_BYTES:
        raise ValueError('backup exceeds local size limit')
    with backup.open('rb') as stream:
        blob = stream.read(2 * MAX_BACKUP_BYTES + 1)
    if len(blob) > 2 * MAX_BACKUP_BYTES:
        raise ValueError('backup exceeds local size limit')
    start = len(MAGIC)
    if not blob.startswith(MAGIC) or len(blob) < start + 44:
        raise ValueError('unsupported encrypted backup')
    plain = AESGCM(key_for(password, blob[start:start+16])).decrypt(
        blob[start+16:start+28], blob[start+28:], MAGIC)
    document = json.loads(plain, object_pairs_hook=unique_object)
    if (not isinstance(document, dict) or type(document.get('version')) is not int
            or document['version'] != 1 or not isinstance(document.get('files'), dict)
            or not isinstance(document.get('records'), list)):
        raise ValueError('invalid backup format')
    files = document['files']
    if len(files) > MAX_BACKUP_MEMBERS or not {'trust.pub', 'index.sqlite'} <= files.keys():
        raise ValueError('invalid backup inventory')
    decoded, total = {}, 0
    for name, value in files.items():
        if not allowed_member(name) or not isinstance(value, str):
            raise ValueError('unsafe backup member')
        if len(value) > 4 * ((MAX_BACKUP_BYTES - total + 2) // 3):
            raise ValueError('expanded backup exceeds local size limit')
        body = base64.b64decode(value, validate=True)
        total += len(body)
        if total > MAX_BACKUP_BYTES:
            raise ValueError('expanded backup exceeds local size limit')
        decoded[name] = body
    if decoded['trust.pub'] != trusted_public or digest(trusted_public) != document.get('trust_sha256'):
        raise ValueError('restore trust anchor differs from independently supplied key')
    if 'signing.key' in decoded:
        key = Ed25519PrivateKey.from_private_bytes(decoded['signing.key'])
        if key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw) != trusted_public:
            raise ValueError('restore signer differs from trust anchor')
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='pratirodh-restore-check-') as temporary:
        staging = Path(temporary)
        for name, body in decoded.items():
            destination = staging / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            private_write(destination, body)
        ids = verified_records(Store(staging))
        if ids != document.get('records'):
            raise ValueError('restored record inventory mismatch')
        output.mkdir(mode=0o700)
        for name, body in decoded.items():
            destination = output / name
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            private_write(destination, body)
    return {'records': len(ids), 'trust_sha256': digest(trusted_public),
            'seconds': time.monotonic() - started, 'signatures_verified': True,
            'scope': 'Local recovery drill; off-host retention and production RPO unverified'}


def create_signing_epoch(output):
    """New empty store with a new key; old evidence and anchors remain untouched."""
    if Path(output).exists():
        raise ValueError('new signing epoch requires a nonexistent directory')
    output = fresh_destination(output)
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    output.mkdir(mode=0o700)
    private_write(output / 'signing.key', key.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()))
    private_write(output / 'trust.pub', public)
    return {'trust_sha256': digest(public), 'old_store_modified': False,
            'scope': 'Separate signing epoch; operator activation and revocation policy required'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class HTTPSAlertDelivery:
    """Explicit operator adapter; single bounded attempt, observable failure."""
    def __init__(self, endpoint, token, opener=None, timeout=5):
        if not isinstance(endpoint, str) or re.search(r'[\s\x00-\x1f\x7f]', endpoint):
            raise ValueError('alert endpoint contains invalid characters')
        url = urllib.parse.urlsplit(endpoint)
        # Validate malformed/out-of-range ports before a request can expose
        # its authorization header through an unsanitized transport error.
        try:
            url.port
        except ValueError:
            raise ValueError('alert endpoint has invalid port') from None
        if (url.scheme != 'https' or not url.hostname or url.username or url.password
                or url.query or url.fragment):
            raise ValueError('alert endpoint requires HTTPS without URL credentials or query')
        if (not isinstance(token, str) or not 16 <= len(token) <= 4096
                or not re.fullmatch(r'[A-Za-z0-9._~+/-]+=*', token)):
            raise ValueError('alert bearer token is missing or invalid')
        if (type(timeout) not in (int, float) or not math.isfinite(timeout)
                or not 0 < timeout <= 10):
            raise ValueError('alert timeout must be between zero and ten seconds')
        self.endpoint, self.token, self.timeout = endpoint, token, timeout
        self.opener = opener or urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect())

    def deliver(self, event):
        if (not isinstance(event, dict) or event.get('type') != 'security_alert'
                or not isinstance(event.get('code'), str)
                or not re.fullmatch(r'[a-z_]{1,64}', event['code'])
                or not isinstance(event.get('request_id'), str)
                or not re.fullmatch(r'[a-f0-9]{32}', event['request_id'])
                or type(event.get('count')) is not int or not 1 <= event['count'] <= 1000):
            raise ValueError('invalid security alert')
        # Never transmit arbitrary logs, source, key material or error text.
        body = json.dumps({name: event[name] for name in
                           ('type', 'code', 'request_id', 'count')}).encode()
        request = urllib.request.Request(self.endpoint, data=body,
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.token})
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                if not 200 <= response.status < 300:
                    raise RuntimeError('alert delivery not acknowledged')
        except (OSError, urllib.error.URLError):
            raise RuntimeError('alert delivery failed; operator action required') from None
        return {'delivered': True, 'request_id': event['request_id'],
                'recipient_acknowledgement': 'NOT_VERIFIED'}
