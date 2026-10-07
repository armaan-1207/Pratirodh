"""Deallocate the three approved VMs at a fixed UTC deadline.

Run independently of the UI. This is an operational backstop, not a monetary
Azure spending cap; storage and public-IP charges persist after deallocation.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pratirodh.projects.cloud_budget import window, load_ledger
from pratirodh.projects.azure_cli import azure_command


def record(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--deadline', required=True)
    p.add_argument('--az', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--usage-ledger', type=Path, required=True)
    a = p.parse_args()
    deadline = datetime.fromisoformat(a.deadline)
    if deadline.tzinfo is None:
        p.error('Deadline must include a UTC offset.')
    remaining = (deadline - datetime.now(timezone.utc)).total_seconds()
    allowance = window(load_ledger(a.usage_ledger))
    if remaining > allowance['seconds']:
        p.error('shutdown deadline exceeds remaining spending allowance')
    if not 0 < remaining <= 14400:
        p.error('This guard permits an initial window of at most four hours.')
    a.output.mkdir(parents=True, exist_ok=True)
    record(a.output / 'guard.json', {'pid': os.getpid(),
        'deadline': deadline.isoformat(), 'status': 'ARMED', 'window_seconds': remaining,
        'approved_total_usage_usd': allowance['approved_usd'], 'scope': 'Bounded qualification/campaign window',
        'allowance': allowance, 'usage_ledger': str(a.usage_ledger.resolve())})
    print('Shutdown guard armed until ' + deadline.isoformat(), flush=True)
    while datetime.now(timezone.utc) < deadline:
        time.sleep(min(30, max(0, (deadline - datetime.now(timezone.utc)).total_seconds())))
    results = []
    for role in ['model', 'execution', 'audit']:
        name = f'pratirodh-{role}'
        try:
            result = subprocess.run(azure_command(a.az, 'vm', 'deallocate', '--resource-group',
                'pratirodh-validation', '--name', name, '--output', 'none'),
                capture_output=True, text=True, timeout=600)
            results.append({'name': name, 'exit_code': result.returncode})
        except (OSError, subprocess.SubprocessError) as error:
            results.append({'name': name, 'exit_code': None, 'error': type(error).__name__})
        record(a.output / 'guard-result.json', results)
    record(a.output / 'guard.json', {'pid': os.getpid(), 'deadline': deadline.isoformat(),
        'status': 'DEALLOCATED' if all(r['exit_code'] == 0 for r in results) else 'DEALLOCATION_FAILED',
        'results': results})


if __name__ == '__main__':
    main()
