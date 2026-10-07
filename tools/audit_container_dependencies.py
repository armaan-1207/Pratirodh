"""Audit installed and vendored Python distributions without executing target code."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

INVENTORY = '''import email,json,site,re
from pathlib import Path
rows=[]
for base in site.getsitepackages():
 for path in sorted(Path(base).rglob("*.dist-info/METADATA")):
  metadata=email.message_from_string(path.read_text(encoding="utf-8"))
  rows.append(dict(name=metadata["Name"],version=metadata["Version"],path=str(path)))
 for manifest in sorted(Path(base).rglob("_vendor/vendor.txt")):
  for name,version in re.findall(r"(?m)^\\s*([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)",manifest.read_text()):
   module = 'pkg_resources' if name.lower() == 'setuptools' else name.lower().replace('-', '_')
   source = manifest.parent/module
   if not source.exists() and not source.with_suffix('.py').exists():
    raise ValueError('vendor manifest has no installed module: '+name)
   partial = name.lower() == 'setuptools' and not (manifest.parent/'setuptools').exists()
   rows.append(dict(name=name,version=version,path=str(manifest),pkg_resources_only=partial))
print(json.dumps(rows))'''


def applicable(rows, package, version, advisory):
    """Two reviewed absent-module advisories; other candidates remain failures."""
    normalize = lambda name: re.sub(r'[-_.]+', '-', name).lower()
    copies = [row for row in rows if normalize(row['name']) == normalize(package) and row['version'] == version]
    ids = {advisory['id'], *advisory.get('aliases', [])}
    return not (normalize(package) == 'setuptools' and copies
                and all(row.get('pkg_resources_only') for row in copies)
                and bool(ids & {'CVE-2025-47273', 'PYSEC-2025-49', 'GHSA-5rjg-fvgr-3xxf',
                                'CVE-2026-59890', 'PYSEC-2026-3447', 'GHSA-h35f-9h28-mq5c'}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--images', nargs='+', required=True)
    parser.add_argument('--output', type=Path, default=Path('run_output/image-python-audits'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    failed = False
    for index, image in enumerate(args.images):
        if image.startswith('-') or not re.fullmatch(r'[A-Za-z0-9_.:/@-]+', image):
            raise ValueError('invalid local image reference')
        result = subprocess.run(['docker', 'run', '--rm', '--pull=never', '--network', 'none',
            '--entrypoint', 'python', image, '-c', INVENTORY], check=True, capture_output=True,
            text=True, encoding='utf-8', timeout=120)
        rows = json.loads(result.stdout)
        packages = sorted({(re.sub(r'[-_.]+', '-', row['name']).lower(), row['version']) for row in rows})
        if not packages or any(not re.fullmatch(r'[A-Za-z0-9_.-]+', name)
                               or not re.fullmatch(r'[A-Za-z0-9_.+!-]+', version) for name, version in packages):
            raise ValueError('invalid installed distribution inventory')
        (args.output / f'{index}-inventory.json').write_text(json.dumps(dict(image=image, packages=rows), indent=2), encoding='utf-8')
        # Vendored and top-level copies may have different versions. Audit
        # every version in separate batches; never collapse to only the newest.
        batches = []
        for name, version in packages:
            batch = next((item for item in batches if name not in item), None)
            if batch is None:
                batch = {}
                batches.append(batch)
            batch[name] = version
        findings, reviewed_partial = [], []
        for batch_index, batch in enumerate(batches):
            output = args.output / f'{index}-{batch_index}-audit.json'
            with tempfile.TemporaryDirectory() as directory:
                requirements = Path(directory) / 'requirements.txt'
                requirements.write_text(''.join(f'{name}=={version}\n' for name, version in batch.items()), encoding='utf-8')
                for attempt in range(2):
                    output.unlink(missing_ok=True)
                    audit = subprocess.run([sys.executable, '-m', 'pip_audit', '-r', str(requirements),
                        '--no-deps', '--disable-pip', '--timeout', '60', '--format', 'json', '--output', str(output)],
                        timeout=180, capture_output=True, text=True, encoding='utf-8')
                    if audit.returncode in {0, 1} and output.exists():
                        break
                    if attempt == 0:
                        time.sleep(2)
            if audit.returncode not in {0, 1} or not output.exists():
                raise RuntimeError('image package audit could not complete')
            data = json.loads(output.read_text(encoding='utf-8'))
            if any(item.get('skip_reason') for item in data['dependencies']):
                raise RuntimeError('image audit skipped an installed distribution')
            batch_findings = [dict(package=item['name'], version=item['version'], advisory=vuln)
                              for item in data['dependencies'] for vuln in item.get('vulns', [])]
            if audit.returncode and not batch_findings:
                raise RuntimeError('image package audit failed without a valid advisory result')
            for item in batch_findings:
                if applicable(rows, item['package'], item['version'], item['advisory']):
                    findings.append(item)
                else:
                    reviewed_partial.append(dict(item, reason='Only pip bundled pkg_resources is installed; setuptools.package_index and FileList/sdist modules affected by the two reviewed advisories are absent'))
        identity = lambda item: (item['package'], item['version'], item['advisory']['id'])
        findings = list({identity(item): item for item in findings}.values())
        reviewed_partial = list({identity(item): item for item in reviewed_partial}.values())
        (args.output / f'{index}-summary.json').write_text(json.dumps(dict(image=image, findings=findings,
            reviewed_partial_components=reviewed_partial), indent=2), encoding='utf-8')
        failed = failed or bool(findings)
        print(f'{image}: {len(packages)} installed/vendored distributions; ' + ('applicable findings' if findings else 'no applicable advisories') + f'; {len(reviewed_partial)} reviewed partial-component candidates')
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
