"""Validate and freeze the upstream intake manifest with a content digest."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=Path('benchmark/upstream-v1/manifest.json'))
    parser.add_argument('--lock', type=Path)
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text(encoding='utf-8'))
    cases = payload.get('cases', [])
    if payload.get('target_count') != 24 or len(cases) != 24:
        raise SystemExit('manifest must contain exactly 24 cases')
    expected = {'Python': 8, 'JavaScript': 8, 'C/C++': 8}
    counts = {language: sum(item.get('language') == language for item in cases)
              for language in expected}
    if counts != expected:
        raise SystemExit(f'language cohorts are not balanced: {counts}')
    if payload.get('comparison', {}).get('equal_budget') is not True:
        raise SystemExit('comparison arms must declare equal_budget=true')
    digest = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    lock = args.lock or args.manifest.with_suffix('.sha256')
    lock.write_text(f'sha256:{digest}  {args.manifest.name}\n', encoding='utf-8')
    print(json.dumps({'manifest': str(args.manifest), 'digest': f'sha256:{digest}', 'lock': str(lock), 'counts': counts}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
