"""Separate supervisor process. Final requests/assertions never return to repair feedback."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pratirodh.execution import DockerExecutor, Budget
from pratirodh.contracts import evaluate_output, violation


def audit(source, specification, seconds=120):
    cases = specification['cases']
    outputs = DockerExecutor().batch([source], specification, cases, Budget(seconds=seconds))[0]
    checks = evaluate_output(outputs, cases, specification)
    unsafe = any(violation(c) for c in checks)
    broken = any(c['status']=='FAIL' for c in checks if c['case']['kind']=='benign')
    working = all(c['status']=='PASS' for c in checks)
    return dict(outcome='WORKING' if working else 'UNSAFE_AND_BROKEN' if unsafe and broken else 'UNSAFE' if unsafe else 'BROKEN' if broken else 'INDETERMINATE',
                unsafe=unsafe, broken=broken, working=working, requests=len(cases), checks=checks)


if __name__ == '__main__':
    job = json.load(sys.stdin)
    try:
        result = audit(job['source'], json.loads((ROOT/'benchmark/audit-v1'/(job['scenario']+'.json')).read_text()), job.get('seconds',120))
    except Exception as exc:
        result = dict(outcome='INDETERMINATE', unsafe=False, broken=False, working=False, requests=0, gap=type(exc).__name__+': '+str(exc)[:300])
    print(json.dumps(result))
