"""Audit installed and vendored Python distributions without executing target code."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

INVENTORY = '''import email,json,site
from pathlib import Path
rows=[]
for base in site.getsitepackages():
 for path in sorted(Path(base).rglob("*.dist-info/METADATA")):
  metadata=email.message_from_string(path.read_text(encoding="utf-8"))
  rows.append(dict(name=metadata["Name"],version=metadata["Version"],path=str(path)))
print(json.dumps(rows))'''


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
        findings = []
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
            findings.extend(batch_findings)
        (args.output / f'{index}-summary.json').write_text(json.dumps(dict(image=image, findings=findings), indent=2), encoding='utf-8')
        failed = failed or bool(findings)
        print(f'{image}: {len(packages)} installed/vendored distributions; ' + ('findings' if findings else 'no known advisories'))
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
