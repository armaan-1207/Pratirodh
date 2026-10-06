"""Run the frozen upstream campaign only after every case passes intake gates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import signal
import threading


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=Path('benchmark/upstream-cohort.json'))
    parser.add_argument('--execution-manifest', type=Path, help='Generated runnable manifest after qualification')
    parser.add_argument('--output', type=Path, default=Path('run_output/upstream-validation/campaign.json'))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--usage-ledger', type=Path,
                        help='Validated Azure usage ledger (required before any VM execution window)')
    parser.add_argument('--guard-output', type=Path, default=Path('run_output/upstream-validation/guard'),
                        help='Directory for the shutdown guard records')
    parser.add_argument('--window-seconds', type=int, default=14400,
                        help='Maximum window length in seconds (max 4 hours, bounded by remaining allowance)')
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    cases = manifest.get('cases', [])
    from pratirodh.upstream_status import load_status
    qualified = load_status(Path(__file__).resolve().parents[1])['qualified']
    if len(cases) != 24 or qualified != 24:
        result = {'status': 'BLOCKED_INTAKE',
                  'reason': 'Every one of the 24 cases needs license, vulnerable, fixed, legitimate, '
                            'and independent-audit qualification before execution.',
                  'counts': {'total': len(cases), 'qualified': qualified}}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result, indent=2))
        return 2
    if not args.execution_manifest:
        parser.error('--execution-manifest is required after qualification')
    if not args.usage_ledger:
        parser.error('--usage-ledger is required before cloud execution')
    from pratirodh.projects.evaluation import campaign
    from pratirodh.projects.cloud_window import execution_window
    try:
        deadline, guard = execution_window(args.usage_ledger, args.guard_output, args.window_seconds)
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({'status': 'BLOCKED_BUDGET_OR_GUARD', 'error': type(error).__name__}))
        return 2
    print(json.dumps({'guard': guard['status'], 'deadline': guard['deadline']}), flush=True)
    cancelled = threading.Event()
    previous = signal.signal(signal.SIGINT, lambda *unused: cancelled.set())
    try:
        result = campaign(args.execution_manifest, args.output, resume=args.resume, cancelled=cancelled,
                          deadline=deadline, progress=lambda state: print(json.dumps(state), flush=True))
    finally:
        signal.signal(signal.SIGINT, previous)
    print(json.dumps({'status': result['status'], 'release_complete': result['release_complete'],
                      'metrics': result['metrics']}, indent=2))
    return 0 if result['release_complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())

