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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--deadline', required=True)
    p.add_argument('--az', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    deadline = datetime.fromisoformat(a.deadline)
    if deadline.tzinfo is None:
        p.error('Deadline must include a UTC offset.')
    a.output.mkdir(parents=True, exist_ok=True)
    while datetime.now(timezone.utc) < deadline:
        time.sleep(min(30, max(0, (deadline - datetime.now(timezone.utc)).total_seconds())))
    results = []
    for role in ['model', 'execution', 'audit']:
        name = f'pratirodh-{role}'
        result = subprocess.run([a.az, 'vm', 'deallocate', '--resource-group',
            'pratirodh-validation', '--name', name, '--output', 'none'],
            capture_output=True, text=True, timeout=600)
        results.append({'name': name, 'exit_code': result.returncode, 'stderr': result.stderr})
    (a.output / 'guard-result.json').write_text(json.dumps(results, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
