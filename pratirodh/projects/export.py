"""Export verified evidence without keys or applying code to the source."""
from pathlib import Path
import zipfile
import hashlib
import json
import re
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_MEMBERS = 20000
MAX_INVENTORY_BYTES = 2 * 1024 * 1024
MAX_COMPRESSION_RATIO = 10000


def checked_members(archive):
    members = archive.infolist()
    if len(members) > MAX_MEMBERS:
        raise ValueError('bundle exceeds entry limit; export a smaller group of records')
    names = [member.filename for member in members]
    if len(names) != len(set(names)):
        raise ValueError('duplicate bundle entries')
    total = 0
    for member in members:
        name = member.filename
        if (not re.fullmatch(r'(?:trust\.pub|evidence/[^/\\\x00-\x1f]+|runs/[a-f0-9]{32}/[^/\\\x00-\x1f]+)', name)
                or any(part in {'.', '..'} for part in name.split('/'))
                or member.flag_bits & 1
                or member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}):
            raise ValueError('unsafe or unsupported bundle entry')
        limit = (32 if name == 'trust.pub' else 128 if name.endswith('/signature.hex')
                 else MAX_INVENTORY_BYTES if name.endswith('/inventory.json') else MAX_MEMBER_BYTES)
        if (member.file_size > limit or member.file_size < 0
                or (name == 'trust.pub' and member.file_size != 32)
                or (name.endswith('/signature.hex') and member.file_size != 128)
                or member.file_size > max(1, member.compress_size) * MAX_COMPRESSION_RATIO):
            raise ValueError('bundle entry exceeds size or compression limit')
        total += member.file_size
        if total > MAX_TOTAL_BYTES:
            raise ValueError('bundle exceeds expanded byte limit; export a smaller group of records')
    return names


def read_member(archive, name):
    """Metadata was checked first; bound actual decompression too."""
    try:
        limit = archive.getinfo(name).file_size
    except KeyError:
        raise ValueError('bundle referenced artifact missing') from None
    with archive.open(name) as stream:
        body = stream.read(limit + 1)
    if len(body) != limit:
        raise ValueError('bundle member length differs from metadata')
    return body


def references(report):
    ids = [r['run_id'] for r in report.get('rows', []) if r.get('run_id')]
    ids += [c['qualification_run_id'] for c in report.get('freeze', {}).get('cases', [])
            if c.get('qualification_run_id')]
    if any(not isinstance(item, str) or not re.fullmatch(r'[a-f0-9]{32}', item) for item in ids):
        raise ValueError('invalid signed evidence reference')
    return list(dict.fromkeys(ids))


def export_bundle(store, run_id, output):
    report = store.load(run_id)
    referenced = list(dict.fromkeys([run_id] + references(report)))
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
    if Path(path).stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError('bundle exceeds archive byte limit; export a smaller group of records')
    with zipfile.ZipFile(path) as archive:
        names = checked_members(archive)
        if 'trust.pub' not in names:
            raise ValueError('bundle trust anchor missing')
        public_bytes = read_member(archive, 'trust.pub')
        if trusted_public is not None and trusted_public != public_bytes:
            raise ValueError('bundle trust anchor differs from trusted public key')
        public = Ed25519PublicKey.from_public_bytes(public_bytes)
        seals = [name for name in names if name.endswith('/inventory.json')]
        if not seals:
            raise ValueError('no signed evidence in bundle')
        expected_names = {'trust.pub'}
        reports = {}
        for seal_path in seals:
            prefix = seal_path.rsplit('/', 1)[0] + '/'
            seal = read_member(archive, seal_path)
            public.verify(bytes.fromhex(read_member(archive, prefix + 'signature.hex').decode()), seal)
            inventory = json.loads(seal)
            if not isinstance(inventory, dict) or any(not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value)
                                                       for value in inventory.values()):
                raise ValueError('invalid signed bundle inventory')
            if 'report.json' not in inventory:
                raise ValueError('signed report missing from bundle')
            expected_names.update({seal_path, prefix + 'signature.hex'})
            for name, expected in inventory.items():
                if '/' in name or '\\' in name or name in {'.', '..'} or hashlib.sha256(read_member(archive, prefix + name)).hexdigest() != expected:
                    raise ValueError('bundle artifact integrity failure')
                expected_names.add(prefix + name)
            report = json.loads(read_member(archive, prefix + 'report.json'))
            if not isinstance(report, dict):
                raise ValueError('invalid signed bundle report')
            if report.get('id') in reports or not re.fullmatch(r'[a-f0-9]{32}', report.get('id', '')):
                raise ValueError('duplicate or invalid signed report identity')
            if prefix != 'evidence/' and prefix != 'runs/' + report['id'] + '/':
                raise ValueError('signed report path differs from its identity')
            reports[report['id']] = report
        if set(names) != expected_names:
            raise ValueError('unsigned entries in evidence bundle')
        if any(item not in reports for report in reports.values() for item in references(report)):
            raise ValueError('referenced signed evidence missing from bundle')
        return {'integrity': 'VALID', 'signed_records': len(seals),
                'trust_verified': trusted_public is not None,
                'trust_fingerprint': hashlib.sha256(public_bytes).hexdigest()}
