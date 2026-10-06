"""Read live independent worker identities; never starts cloud resources."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import subprocess
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pratirodh.projects.preflight import attest_worker, separate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-context', default='pratirodh-execution')
    parser.add_argument('--audit-context', default='pratirodh-audit')
    parser.add_argument('--execution-image', required=True)
    parser.add_argument('--audit-image', required=True)
    parser.add_argument('--output', type=Path, default=Path('run_output/upstream-validation/worker-preflight.json'))
    args = parser.parse_args()
    results = []
    for role, context, image in [('execution', args.execution_context, args.execution_image),
                                 ('audit', args.audit_context, args.audit_image)]:
        failures = []
        for attempt in range(3):
            try:
                result = dict(attest_worker(context, image), role=role)
                break
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                result = {'role': role, 'context': context, 'status': 'BLOCKED', 'error': type(error).__name__}
                if isinstance(error, subprocess.CalledProcessError):
                    result['detail'] = (error.stderr or '')[-2000:]
                failures.append(dict(result, observed_at=datetime.now(timezone.utc).isoformat()))
                transport_failure = isinstance(error, subprocess.TimeoutExpired) or (
                    isinstance(error, subprocess.CalledProcessError) and
                    any(message in (error.stderr or '').lower() for message in
                        ('connection timed out', 'connection reset', 'connection closed')))
                if not transport_failure or attempt == 2:
                    break
                time.sleep(2)
        result['transport_failures'] = failures
        results.append(result)
    status = 'BLOCKED'
    if all(r['status'] == 'PASS' for r in results):
        try:
            separate(*results)
            status = 'PASS'
        except ValueError:
            status = 'SHARED_WORKER_IDENTITY'
    result = {'status': status, 'updated': datetime.now(timezone.utc).isoformat(), 'workers': results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if status == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
