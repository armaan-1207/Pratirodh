"""Create fresh presentation runs and a separate intentionally stale record."""
import json
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pratirodh.engine import run, replay
from pratirodh.evidence import Store, fresh
from pratirodh.execution import DockerExecutor
from pratirodh.minimize import minimize
from pratirodh.review import review


def main():
    root = Path(__file__).resolve().parents[1]
    directory = root / 'benchmark/scenarios/cwe-22-development-01'
    output = {'scenario': directory.name, 'runs': []}
    for mode, label in [('fixed', 'incomplete'), ('full', 'incomplete'), ('full', 'correct')]:
        report = run(directory, directory / 'contract.json',
                     (directory / 'patches' / (label + '.diff')).read_text(), mode=mode, origin='curated')
        output['runs'].append({'id': report['id'], 'mode': mode, 'patch': label,
                               'decision': report['decision'], 'seconds': report['elapsed_seconds']})
        print(mode, label, report['decision'], flush=True)
    assert [r['decision'] for r in output['runs']] == ['READY_FOR_REVIEW', 'REJECT', 'READY_FOR_REVIEW']
    output['replay'] = replay(output['runs'][1]['id'], 'probe-symlink')
    output['minimization'] = minimize(output['runs'][1]['id'], 'probe-symlink')
    expiry = root / '.qa/expiry-demo'
    expiry.mkdir(parents=True, exist_ok=True)
    for name in ['app.py', 'contract.json']:
        shutil.copyfile(directory / name, expiry / name)
    report = run(expiry, expiry / 'contract.json', (directory / 'patches/correct.diff').read_text())
    assert report['decision'] == 'READY_FOR_REVIEW'
    path = expiry / 'app.py'
    path.write_text(path.read_text() + '\n# Relevant source change for evidence expiry demonstration.\n')
    assert not fresh(report, DockerExecutor())
    try:
        replay(report['id'], 'legitimate')
        raise AssertionError('stale replay was permitted')
    except ValueError:
        pass
    output['stale_run'] = report['id']
    output['extended'] = []
    for cwe in ['78', '798']:
        fixture = root / f'benchmark/scenarios/cwe-{cwe}-development-01'
        for label in ['incomplete', 'correct']:
            report = run(fixture, fixture / 'contract.json', (fixture / f'patches/{label}.diff').read_text(), origin='curated')
            assert report['decision'] == ('READY_FOR_REVIEW' if label == 'correct' else 'REJECT'), report['gaps']
            output['extended'].append({'id': report['id'], 'cwe': cwe, 'patch': label, 'decision': report['decision']})
    output['review'] = review(output['extended'][-1]['id'], 'approve', 'PRATIRODH demo operator',
                              'Reviewed synthetic credential profiles and fresh verification evidence; no source promotion.')
    (root / 'run_output/demo.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    print('Demo replay, reduction, and stale replay denial verified', flush=True)


if __name__ == '__main__':
    main()
