"""Run the local upstream reference-fix demo with zero model/cloud calls."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pratirodh.evidence import Store
from pratirodh.projects.requests_demo import IMAGE_TAG, run_demo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    image = subprocess.check_output(['docker', '--context', 'default', 'image', 'inspect',
        IMAGE_TAG, '--format', '{{.Id}}'], text=True, timeout=15).strip()
    rows = run_demo(args.output / 'requests-cve-2018-18074-local-demo', Store(args.output / 'evidence'), image,
        progress=lambda stage: print(stage, flush=True))
    result = {'scope': 'Local upstream reference-fix demonstration; not independent qualification',
        'model_calls': 0, 'runs': rows}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'requests-summary.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if len(rows) == 2 and all(r['matched_expectation'] for r in rows) else 2


if __name__ == '__main__':
    raise SystemExit(main())
