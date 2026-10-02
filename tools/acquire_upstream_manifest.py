"""Acquire pinned public cases, checkpoint provenance, and retain failed intakes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=Path('benchmark/upstream-v1/manifest.json'))
    parser.add_argument('--output', type=Path, default=Path('run_output/upstream-acquisition'))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in manifest['cases']:
        record = args.output / case['id'] / 'provenance.json'
        row = {'id': case['id'], 'updated': datetime.now(timezone.utc).isoformat()}
        if not case.get('fix_revision'):
            row['status'] = 'REVISION_REVIEW_REQUIRED'
        else:
            if not record.exists():
                command = [sys.executable, str(Path(__file__).with_name('acquire_upstream_case.py')),
                           '--repository', case['repository_url'], '--fix', case['fix_revision'],
                           '--advisory', case['advisory_url'], '--id', case['id'], '--output', str(args.output)]
                try:
                    result = subprocess.run(command, capture_output=True, text=True, timeout=240)
                    row['error'] = result.stderr[-2000:] if result.returncode else ''
                except subprocess.TimeoutExpired:
                    row['error'] = 'Source acquisition timed out; partial checkout retained for inspection.'
            if record.exists():
                row.update(status='SOURCE_ACQUIRED', provenance=json.loads(record.read_text(encoding='utf-8')))
            else:
                row['status'] = 'ACQUISITION_FAILED'
        rows.append(row)
        checkpoint = args.output / 'acquisition.json'
        temporary = checkpoint.with_suffix('.tmp')
        temporary.write_text(json.dumps({'cases': rows}, indent=2), encoding='utf-8')
        temporary.replace(checkpoint)
        print(case['id'], row['status'], flush=True)


if __name__ == '__main__':
    main()
