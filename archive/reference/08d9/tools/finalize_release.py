"""Publish measured release checks only after all required cohorts finish."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'run_output'


def main():
    benchmark = json.loads((OUTPUT / 'benchmark-upgrade.json').read_text())
    local = json.loads((OUTPUT / 'local-evaluation.json').read_text())
    assert len(benchmark['rows']) == 576
    assert benchmark['metrics']['full']['correct_ready'] == 36
    assert benchmark['metrics']['full']['incorrect_ready'] == 0
    assert len(local['rows']) == 8
    assert {r['cwe'] for r in local['rows']} == {'CWE-22', 'CWE-89', 'CWE-78', 'CWE-798'}
    assert all(r['additional_requests'] == 64 for r in benchmark['rows'] if r['mode'] in {'full', 'unguided'})
    tests = (OUTPUT / 'tests-upgrade-final.log').read_text()
    passed = int(re.search(r'(\d+) passed', tests).group(1))
    assert passed == 24 and 'failed' not in tests
    audit = json.loads((OUTPUT / 'audit-upgrade.json').read_text())
    dependencies = json.loads((OUTPUT / 'dependencies-upgrade.json').read_text())
    assert not audit['results'] and not any(d['vulns'] for d in dependencies['dependencies'])
    firewall = json.loads((OUTPUT / 'firewall-python-check.json').read_text())
    assert firewall == {'loopback': 'connected', 'external': 'PermissionError'}
    deployment = json.loads((OUTPUT / 'deployment-check.json').read_text())
    demo = json.loads((OUTPUT / 'demo.json').read_text())
    record = {'release': '0.2.0', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'tests': {'passed': passed, 'docker_integration': True},
              'static_audit': {'medium_high_findings': 0, 'scope': 'pratirodh; intentional fixtures and historic code excluded'},
              'dependency_audit': {'known_advisories': 0, 'scope': 'pinned requirements-deploy.txt'},
              'benchmark': {'evaluations': len(benchmark['rows']), 'metrics': benchmark['metrics'],
                            'cohort': benchmark['cohort'], 'limitations': benchmark['limitations']},
              'local_model': {'metrics': local['metrics'], 'rows': local['rows'], 'curated': False},
              'offline_firewall': {'dedicated_python': firewall, 'native_ollama': 'operator-applied active outbound block; cloud features disabled'},
              'deployment': deployment, 'demo': demo,
              'limitations': ['Trusted single-file Flask fixtures only; four CWE classes.',
                              'Related synthetic families and public labels constrain generalization.',
                              'Timing includes concurrent evaluation load and is not a controlled latency benchmark.',
                              'Pattern-based mutation qualification can abstain on alternative coding styles.',
                              'Review labels do not authenticate identity. No automatic promotion.',
                              'No cloud generation, public hosting, narrated MP4, or finished PPT is claimed.']}
    for name in ['RELEASE_CHECKS', 'BENCHMARK_RESULTS']:
        path = ROOT / 'docs' / (name + '.json')
        historical = ROOT / 'docs' / (name + '_0_1.json')
        if path.exists() and not historical.exists():
            historical.write_bytes(path.read_bytes())
    (ROOT / 'docs/RELEASE_CHECKS.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    (ROOT / 'docs/BENCHMARK_RESULTS.json').write_text(json.dumps({'curated': benchmark, 'local_generation': local}, indent=2), encoding='utf-8')
    print(json.dumps({'tests': passed, 'evaluations': len(benchmark['rows']), 'local': local['metrics']}, indent=2))


if __name__ == '__main__':
    main()
