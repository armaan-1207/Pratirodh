"""Export verified evidence without keys or applying code to the source."""
from pathlib import Path
import zipfile
import hashlib
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def export_bundle(store, run_id, output):
    report = store.load(run_id)
    referenced = list(dict.fromkeys([run_id] + [r['run_id'] for r in report.get('rows', []) if r.get('run_id')]))
    for item in referenced:
        store.load(item)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('export destination already exists')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(store.run_path(run_id).iterdir()):
            archive.write(path, 'evidence/' + path.name)
        for item in referenced[1:]:
            for path in sorted(store.run_path(item).iterdir()):
                archive.write(path, 'runs/' + item + '/' + path.name)
        archive.write(store.root / 'trust.pub', 'trust.pub')
    return str(output)


def verify_bundle(path, trusted_public=None):
    """Verify an exported bundle in place, without trusting or extracting paths."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('duplicate bundle entries')
        public_bytes = archive.read('trust.pub')
        if trusted_public is not None and trusted_public != public_bytes:
            raise ValueError('bundle trust anchor differs from trusted public key')
        public = Ed25519PublicKey.from_public_bytes(public_bytes)
        seals = [name for name in names if name.endswith('/inventory.json')]
        if not seals:
            raise ValueError('no signed evidence in bundle')
        expected_names = {'trust.pub'}
        for seal_path in seals:
            prefix = seal_path.rsplit('/', 1)[0] + '/'
            seal = archive.read(seal_path)
            public.verify(bytes.fromhex(archive.read(prefix + 'signature.hex').decode()), seal)
            inventory = json.loads(seal)
            if 'report.json' not in inventory:
                raise ValueError('signed report missing from bundle')
            expected_names.update({seal_path, prefix + 'signature.hex'})
            for name, expected in inventory.items():
                if '/' in name or '\\' in name or name in {'.', '..'} or hashlib.sha256(archive.read(prefix + name)).hexdigest() != expected:
                    raise ValueError('bundle artifact integrity failure')
                expected_names.add(prefix + name)
        if set(names) != expected_names:
            raise ValueError('unsigned entries in evidence bundle')
        return {'integrity': 'VALID', 'signed_records': len(seals),
                'trust_verified': trusted_public is not None,
                'trust_fingerprint': hashlib.sha256(archive.read('trust.pub')).hexdigest()}
