import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid
import sys
import importlib.metadata
from contextlib import closing
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


def digest(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def tree_hash(root):
    root = Path(root)
    values = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in {".git", ".venv", "__pycache__", ".pytest_cache", "run_output", "runs"} for part in relative.parts):
            continue
        if path.is_symlink():
            values[relative.as_posix()] = digest("symlink:" + os.readlink(path))
        elif path.is_file() and path.suffix in {".py", ".txt", ".json", ".toml", ".lock", ".yaml", ".yml"}:
            values[relative.as_posix()] = digest(path.read_bytes())
    return digest(canonical(values))


def bindings(target, manifest, image_id):
    return {"target": tree_hash(target), "contract": digest(Path(manifest).read_bytes()),
            "runner": tree_hash(Path(__file__).parent), "image": image_id,
            'python': sys.version, 'tools': {name: importlib.metadata.version(name)
                                            for name in ('Flask', 'bandit', 'cryptography', 'waitress')}}


class Store:
    def __init__(self, root="run_output/pratirodh"):
        self.root = Path(root).resolve()

    def run_path(self, run_id):
        if not re.fullmatch(r"[a-f0-9]{32}", run_id):
            raise ValueError("invalid run id")
        return self.root / "runs" / run_id

    def save(self, report, artifacts):
        from .projects.leases import Lease
        from .execution import Budget
        for name, value in artifacts.items():
            if ('/' in name or '\\' in name or name in {'.', '..', 'inventory.json', 'signature.hex', 'report.json'}
                    or not isinstance(value, str)):
                raise ValueError('artifact names/content violate evidence policy')
        lease = Lease('evidence-' + digest(str(self.root))[:24])
        if not lease.acquire(Budget(30)):
            raise TimeoutError('evidence writer busy')
        try:
            return self._save(report, artifacts)
        finally:
            lease.release()

    def _save(self, report, artifacts):
        self.root.mkdir(parents=True, exist_ok=True)
        private_path = self.root / "signing.key"
        public_path = self.root / "trust.pub"
        if private_path.exists():
            key = Ed25519PrivateKey.from_private_bytes(private_path.read_bytes())
            public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            if not public_path.exists() or public_path.read_bytes() != public:
                raise ValueError("evidence trust anchor does not match signing key")
        else:
            if public_path.exists():
                raise ValueError("missing signing key for existing trust anchor")
            key = Ed25519PrivateKey.generate()
            private_path.write_bytes(key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                                      serialization.NoEncryption()))
            os.chmod(private_path, 0o600)
            public_path.write_bytes(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
        run_id = report["id"]
        path = self.run_path(run_id)
        path.mkdir(parents=True, exist_ok=False)
        artifacts = dict(artifacts, **{"report.json": json.dumps(report, indent=2, ensure_ascii=False)})
        inventory = {}
        for name, value in artifacts.items():
            if Path(name).name != name:
                raise ValueError("artifact names must be simple filenames")
            payload = value.encode("utf-8")
            (path / name).write_bytes(payload)
            inventory[name] = digest(payload)
        seal = canonical(inventory).encode()
        (path / "inventory.json").write_bytes(seal)
        (path / "signature.hex").write_text(key.sign(seal).hex())
        for item in path.iterdir():
            os.chmod(item, 0o444)
        with closing(sqlite3.connect(self.root / "index.sqlite")) as database, database:
            database.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created TEXT, decision TEXT, scenario TEXT)")
            database.execute("INSERT INTO runs VALUES (?, ?, ?, ?)",
                             (run_id, report["created"], report["decision"], report.get("scenario", "unknown")))
        return run_id

    def load(self, run_id):
        path = self.run_path(run_id)
        seal = (path / "inventory.json").read_bytes()
        Ed25519PublicKey.from_public_bytes((self.root / "trust.pub").read_bytes()).verify(
            bytes.fromhex((path / "signature.hex").read_text()), seal)
        inventory = json.loads(seal)
        if set(p.name for p in path.iterdir()) != set(inventory) | {"inventory.json", "signature.hex"}:
            raise ValueError("artifact inventory changed")
        for name, expected in inventory.items():
            if Path(name).name != name or digest((path / name).read_bytes()) != expected:
                raise ValueError("artifact integrity check failed")
        return json.loads((path / "report.json").read_text(encoding="utf-8"))

    def list(self):
        if not (self.root / "index.sqlite").exists():
            return []
        with closing(sqlite3.connect(self.root / "index.sqlite")) as database:
            return [row[0] for row in database.execute("SELECT id FROM runs ORDER BY created DESC LIMIT 100")]


def fresh(report, executor):
    try:
        return bindings(report["target_path"], report["contract_path"], executor.identity()) == report["bindings"]
    except Exception:
        return False


def new_id():
    return uuid.uuid4().hex


def freshness_changes(report, executor):
    try:
        current = bindings(report['target_path'], report['contract_path'], executor.identity())
        return [key for key in current if current[key] != report.get('bindings', {}).get(key)]
    except Exception:
        return ['execution environment or source unavailable']

