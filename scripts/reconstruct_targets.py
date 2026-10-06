"""Prepare disposable snapshots from pinned source without editing acquisitions.

No target code, model, cloud worker, or qualification is executed here.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pratirodh.contracts import safe_relative
from pratirodh.projects.manifest import inventory, load


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def acquire(info, cache):
    parsed = urlparse(info['repository'])
    if parsed.scheme != 'https' or parsed.hostname != 'github.com' or parsed.username or parsed.password:
        raise ValueError('source must be a public HTTPS GitHub repository')
    source = Path(cache) / safe_relative(info['id']) / 'upstream'
    if not source.exists():
        source.mkdir(parents=True)
        subprocess.run(['git', 'init', str(source)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(source), 'remote', 'add', 'origin', info['repository']], check=True)
    origin = subprocess.check_output(['git', '-C', str(source), 'remote', 'get-url', 'origin'], text=True).strip()
    if origin.rstrip('/') != info['repository'].rstrip('/'):
        raise ValueError('existing source cache has an unexpected repository')
    for revision in (info['source_revision'], info['fix_revision']):
        if not re.fullmatch('[0-9a-f]{40}', revision):
            raise ValueError('full pinned source and fix revisions required')
        probe = subprocess.run(['git', '-C', str(source), 'cat-file', '-e', revision + '^{commit}'], capture_output=True)
        if probe.returncode:
            subprocess.run(['git', '-C', str(source), 'fetch', '--depth=1', 'origin', revision], check=True, timeout=180)
    return source


def prepare_case(case, source):
    case, source = Path(case).resolve(), Path(source).resolve()
    info, recipe = read(case / 'target-source.json'), read(case / 'recipe.json')
    output = case / 'prepared'
    if output.exists():
        raise FileExistsError('prepared output already exists; preserve it or use a new checkout: ' + str(output))
    if not re.fullmatch('[0-9a-f]{40}', info['source_revision']):
        raise ValueError('full pinned source revision required')
    # git archive reads objects; it does not reset or clean the source checkout.
    payload = subprocess.check_output(['git', '-C', str(source), 'archive', info['source_revision']], timeout=60)
    temporary = case / 'prepared.tmp'
    temporary.mkdir(exist_ok=False)
    target = temporary / 'target'
    target.mkdir()
    omissions, blockers = [], []
    try:
        with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
            for member in archive:
                name = safe_relative(member.name.rstrip('/'))
                destination = target / name
                if not destination.resolve().is_relative_to(target):
                    raise ValueError('escaping archive path')
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.extractfile(member).read())
                else:
                    blockers.append('Unsupported upstream link or special file: ' + name)
        # Omit only known obsolete placeholder harnesses from the disposable copy.
        # All other observed deletions remain in the source and snapshot.
        for name in info.get('snapshot_exclusions', []):
            if name in {'tests/test_hack.py', 'tests/test_stub.py', 'tests/test_stub.js'}:
                p = target / safe_relative(name)
                if p.is_file():
                    p.unlink()
                    omissions.append(name)
        overlays = {}
        for p in sorted((case / 'overlay').rglob('*')):
            if not p.is_file():
                continue
            name = safe_relative(p.relative_to(case / 'overlay').as_posix())
            if p.is_symlink() or p.name == '.env' or p.suffix in {'.pem', '.key', '.p12'}:
                raise ValueError('unsafe overlay input: ' + name)
            overlays[name] = p.read_bytes()
        for name, body in recipe.get('harness_files', {}).items():
            name = safe_relative(name)
            expected = body.encode('utf-8')
            if name in overlays and overlays[name].replace(b'\r\n', b'\n') != expected.replace(b'\r\n', b'\n'):
                blockers.append('Captured overlay differs from embedded historical harness: ' + name)
            # Captured current files take precedence; the mismatch remains explicit.
            overlays.setdefault(name, expected)
        for name, body in overlays.items():
            p = target / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
        manifest = read(case / 'source-manifest.json')
        try:
            _, hashes, revision = inventory(target)
            manifest.update(inventory=hashes, revision=revision)
            path = temporary / 'manifest.json'
            path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
            load(target, path)
        except (OSError, ValueError) as error:
            blockers.append(str(error))
        for local, remote in recipe.get('source_map', {}).items():
            try:
                safe_relative(local); safe_relative(remote)
                original = subprocess.check_output(['git', '-C', str(source), 'show', info['source_revision'] + ':' + remote])
                actual = (target / local).read_bytes()
                if actual.replace(b'\r\n', b'\n') != original.replace(b'\r\n', b'\n'):
                    blockers.append('Editable source differs from declared upstream revision: ' + local)
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                blockers.append('Invalid source mapping ' + local + ': ' + str(error))
        receipt = {'case': case.name, 'scope': 'STATIC_PREPARATION_ONLY', 'qualification': 'NOT_RUN',
                   'status': 'BLOCKED' if blockers else 'PREPARED', 'blockers': blockers,
                   'source_revision': info['source_revision'], 'fix_revision': info['fix_revision'],
                   'overlay_sha256': {n: hashlib.sha256(b).hexdigest() for n, b in overlays.items()},
                   'omitted_placeholder_harnesses': omissions,
                   'upstream_assets': 'Retained; unsupported fixtures require explicit qualification work'}
        (temporary / 'preparation.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        temporary.rename(output)
        return receipt
    except Exception:
        # Leave partial output for inspection; never replace a previous snapshot.
        raise


def reconstruct_all(recipes=None, source_root=None, cache=None, case_id=None):
    recipes = Path(recipes or ROOT / 'benchmark/recipes')
    rows = []
    for case in sorted(recipes.iterdir()):
        if not (case / 'target-source.json').is_file() or (case_id and case.name != case_id):
            continue
        try:
            source = Path(source_root) / case.name / 'target' if source_root else acquire(read(case / 'target-source.json'), cache or ROOT / 'run_output/upstream-source-cache')
            rows.append(prepare_case(case, source))
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            rows.append({'case': case.name, 'status': 'BLOCKED', 'scope': 'STATIC_PREPARATION_ONLY',
                         'qualification': 'NOT_RUN', 'blockers': [str(error)]})
    return {'scope': 'STATIC_PREPARATION_ONLY', 'qualification': 'NOT_RUN', 'cases': rows,
            'summary': {'total': len(rows), 'prepared': sum(r['status'] == 'PREPARED' for r in rows),
                        'blocked': sum(r['status'] == 'BLOCKED' for r in rows)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipes', type=Path, default=ROOT / 'benchmark/recipes')
    parser.add_argument('--source-root', type=Path, help='Read existing local case/target Git objects without modifying them')
    parser.add_argument('--cache', type=Path, default=ROOT / 'run_output/upstream-source-cache')
    parser.add_argument('--case')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({'scope': 'PLAN_ONLY', 'cases': [p.name for p in sorted(args.recipes.iterdir()) if (p / 'target-source.json').is_file() and (not args.case or p.name == args.case)]}))
        return 0
    result = reconstruct_all(args.recipes, args.source_root, args.cache, args.case)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))
    return 2 if not result['summary']['total'] or result['summary']['blocked'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
