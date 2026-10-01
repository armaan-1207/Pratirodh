"""Compatibility wrapper. Never calls legacy promotion, patcher, ledger or cloud code."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, '/baseline')
from detect.sast import run_detection
from detect.fuzzer import run_atheris_fuzzer
from prove.pov_replay import pov_replay
from prove.differential import run_differential
from prove.regression import run_regression
from gate.scorer import score
from reason.engine import reason


def main(payload):
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        os.chdir(root)
        for name, value in payload.get('fixtures', {}).items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding='utf-8')
        for name, value in payload.get('symlinks', {}).items():
            (root / name).symlink_to(value)
        original, candidate = root / 'app.py', root / 'candidate.py'
        original.write_text(payload['source'], encoding='utf-8')
        candidate.write_text(payload['candidate'], encoding='utf-8')
        os.environ['ADMIN_SECRET'] = 'test_secret_for_differential_replay'
        findings = run_detection(str(original))
        matched = [f for f in findings if f['cwe'] == payload['cwe']]
        if not matched:
            return {'decision': 'UNSUPPORTED', 'gap': 'No historical matching detection', 'findings': findings}
        if payload.get('action') == 'propose':
            # Preserve the historical template selection. Cloud fallback is prohibited.
            spec = reason(matched[0], allow_cloud_fallback=False)
            return {'spec': spec, 'findings': findings, 'decision': 'PROPOSED' if spec.get('status') == 'REASONED' else 'GENERATION_UNAVAILABLE', 'promotion_applied': False}
        patch = {'status': 'PATCHED', 'file': str(original), 'shadow_path': str(candidate),
                 'backup_path': str(original), 'unified_diff': payload['patch'],
                 'llm_generated': payload.get('origin') in {'local-model', 'cloud-model'}}
        pov = pov_replay(patch, matched[0])
        differential = run_differential(str(original), str(candidate), str(original), payload['cwe'])
        regression = run_regression(str(root), patch)
        crashes = run_atheris_fuzzer(str(candidate))
        fuzz = {'status': 'SKIPPED' if crashes is None else 'FAIL' if crashes else 'PASS',
                'crashes': crashes}
        result = score(pov, differential, regression, patch, fuzz)
        missing_routes = sum(d.get('orig_status') == 404 and d.get('patch_status') == 404
                             for d in differential.get('details', []))
        return dict(result, checks={'pov': pov, 'differential': differential, 'regression': regression,
                                    'fuzz': fuzz}, findings=findings,
                    elapsed_seconds=round(time.monotonic() - started, 3),
                    request_executions=differential.get('total_cases', 0) * 2,
                    fuzz_execution_count='native Atheris count unavailable', promotion_applied=False,
                    compatibility_gaps={'native_requests_with_both_routes_missing': missing_routes,
                                        'upstream_regression_suite': 'NOT_ADAPTED'})


if __name__ == '__main__':
    payload = json.load(sys.stdin)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            output = main(payload)
    except Exception as exc:
        output = {'decision': 'UNADAPTABLE', 'gap': type(exc).__name__ + ': ' + str(exc)[:300],
                  'promotion_applied': False}
    print(json.dumps(output))
