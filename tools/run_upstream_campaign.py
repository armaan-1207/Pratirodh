"""Run the frozen upstream campaign only after every case passes intake gates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=Path('benchmark/upstream-v1/manifest.json'))
    parser.add_argument('--execution-manifest', type=Path, help='Generated runnable manifest after qualification')
    parser.add_argument('--output', type=Path, default=Path('run_output/upstream-validation/campaign.json'))
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    cases = manifest.get('cases', [])
    if len(cases) != 24 or any(c.get('status') not in {'QUALIFIED', 'AUDITED'} for c in cases):
        result = {'status': 'BLOCKED_INTAKE', 'reason': 'Every one of the 24 cases needs license, vulnerable, fixed, legitimate, and independent-audit qualification before execution.', 'counts': {'total': len(cases), 'qualified': sum(c.get('status') in {'QUALIFIED', 'AUDITED'} for c in cases)}}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result, indent=2))
        return 2
    if not args.execution_manifest:
        parser.error('--execution-manifest is required after qualification')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pratirodh.projects.evaluation import campaign
    result = campaign(args.execution_manifest, args.output, resume=args.resume)
    print(json.dumps({'status': result['status'], 'release_complete': result['release_complete'], 'metrics': result['metrics']}, indent=2))
    return 0 if result['release_complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
