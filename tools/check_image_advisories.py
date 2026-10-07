"""Fail new or changed high/critical findings; require dated, bound review records."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path


def key(role, result, vulnerability):
    return (role, result['Type'], vulnerability['VulnerabilityID'],
            vulnerability['PkgName'], vulnerability['InstalledVersion'],
            vulnerability.get('PkgPath', ''))


def check(policy, reports, root, today=None):
    today = today or date.today()
    if today > date.fromisoformat(policy['expires_on']):
        raise ValueError('Container advisory review expired; renew the review before release')
    for name, expected in policy['inputs'].items():
        if hashlib.sha256((root / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise ValueError(f'Container security input changed; review required: {name}')
    reviewed = {tuple(row['key']): row for row in policy['findings']}
    if set(reports) != {'dashboard', 'runner', 'worker', 'requests-demo'}:
        raise ValueError('All four container reports are required')
    counts = {}
    for role, report in reports.items():
        if report.get('SchemaVersion') != 2 or not report.get('Results'):
            raise ValueError(f'Missing or unsupported scanner report: {role}')
        count = 0
        for result in report['Results']:
            for vulnerability in result.get('Vulnerabilities', []):
                if vulnerability['Severity'] not in {'HIGH', 'CRITICAL'}:
                    continue
                record = reviewed.get(key(role, result, vulnerability))
                if not record or not record.get('reason') or not record.get('source'):
                    raise ValueError(f'Unreviewed container advisory: {key(role, result, vulnerability)}')
                if vulnerability['Severity'] != record['severity']:
                    raise ValueError(f'Advisory severity changed: {vulnerability["VulnerabilityID"]}')
                # A new distribution fix supersedes any previous residual-risk review.
                if vulnerability.get('FixedVersion', '') != record.get('fixed_version', ''):
                    raise ValueError(f'Advisory fix availability changed: {vulnerability["VulnerabilityID"]}')
                count += 1
        counts[role] = count
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', type=Path, default=Path('run_output/container-scan'))
    parser.add_argument('--policy', type=Path, default=Path('docs/CONTAINER_ADVISORY_TRIAGE.json'))
    args = parser.parse_args()
    roles = ('dashboard', 'runner', 'worker', 'requests-demo')
    reports = {role: json.loads((args.reports / f'{role}-trivy.json').read_text()) for role in roles}
    counts = check(json.loads(args.policy.read_text()), reports, Path(__file__).resolve().parents[1])
    print(json.dumps({'reviewed_residual_findings': counts, 'status': 'no unreviewed high/critical findings'}))


if __name__ == '__main__':
    main()
