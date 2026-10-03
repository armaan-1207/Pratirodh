"""Review all acquired case inventories and reference-fix scope without execution."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pratirodh.projects.qualification import review_source
from pratirodh.evidence import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('benchmark/upstream-v2/manifest.json'))
    parser.add_argument('--output', type=Path, default=Path('run_output/upstream-validation/intake-review.json'))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    rows = []
    for case in manifest['cases']:
        directory = ROOT / case.get('acquisition', 'run_output/upstream-acquisition/' + case['id'])
        try:
            row = review_source(case, directory)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            row = {'id': case['id'], 'status': 'SOURCE_REVIEW_BLOCKED', 'errors': [type(error).__name__]}
        rows.append(row)
        print(case['id'], row['status'], flush=True)
    result = {'cohort': manifest['cohort'], 'manifest_digest': digest(args.manifest.read_bytes()),
              'updated': datetime.now(timezone.utc).isoformat(), 'cases': rows,
              'reviewed': sum(r['status'] == 'SOURCE_REVIEWED' for r in rows),
              'qualified': 0, 'disclosure': 'Static source review only; executable qualification remains pending'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, indent=2))
    return 0 if result['reviewed'] == len(rows) else 2


if __name__ == '__main__':
    raise SystemExit(main())
