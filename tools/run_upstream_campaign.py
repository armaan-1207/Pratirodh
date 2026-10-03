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
    parser.add_argument('--manifest', type=Path, default=Path('benchmark/upstream-v2/manifest.json'))
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

    # Validate cloud budget before any execution.
    window_deadline = None
    if args.usage_ledger:
        from pratirodh.projects.cloud_budget import window as cloud_window
        ledger = json.loads(args.usage_ledger.read_text(encoding='utf-8'))
        allowance = cloud_window(ledger)
        if allowance['seconds'] < 60:
            print(json.dumps({'status': 'BLOCKED_BUDGET', 'reason': 'Approved usage allowance exhausted',
                              'allowance': allowance}))
            return 2
        window_seconds = min(args.window_seconds, allowance['seconds'])
        if not 1 <= window_seconds <= 14400:
            print(json.dumps({'status': 'BLOCKED_BUDGET', 'reason': 'Window must be between 1 and 14400 seconds',
                              'available_seconds': allowance['seconds']}))
            return 2
        from datetime import datetime, timezone, timedelta
        window_deadline = datetime.now(timezone.utc) + timedelta(seconds=window_seconds)
        args.guard_output.mkdir(parents=True, exist_ok=True)
        guard_record = {'status': 'ARMED', 'deadline': window_deadline.isoformat(),
                        'window_seconds': window_seconds, 'allowance': allowance,
                        'usage_ledger': str(args.usage_ledger.resolve())}
        (args.guard_output / 'window.json').write_text(json.dumps(guard_record, indent=2), encoding='utf-8')
        print(f'Cloud window: {window_seconds}s available, deadline {window_deadline.isoformat()}', flush=True)

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
    from pratirodh.projects.evaluation import campaign
    cancelled = threading.Event()
    previous = signal.signal(signal.SIGINT, lambda *unused: cancelled.set())
    try:
        result = campaign(args.execution_manifest, args.output, resume=args.resume, cancelled=cancelled,
                          progress=lambda state: print(json.dumps(state), flush=True))
    finally:
        signal.signal(signal.SIGINT, previous)
        if window_deadline is not None:
            from datetime import datetime, timezone
            elapsed = (datetime.now(timezone.utc) - window_deadline).total_seconds()
            (args.guard_output / 'window.json').write_text(
                json.dumps({**guard_record, 'status': 'CAMPAIGN_COMPLETE',
                            'overtime_seconds': max(0, elapsed)}, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'release_complete': result['release_complete'],
                      'metrics': result['metrics']}, indent=2))
    return 0 if result['release_complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())

