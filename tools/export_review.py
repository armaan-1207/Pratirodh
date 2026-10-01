"""Export verified public bundles without exporting the signing key."""
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pratirodh.evidence import Store, digest


def main():
    root = Path(__file__).resolve().parents[1] / 'run_output'
    store = Store(root / 'pratirodh')
    root.mkdir(exist_ok=True)
    destination = (root / 'review').resolve()
    if not destination.is_relative_to(root.resolve()):
        raise ValueError('export destination escapes workspace output')
    temporary = Path(tempfile.mkdtemp(prefix='review-', dir=root))
    (temporary / 'runs').mkdir()
    pinned = []
    demo_path = root / 'demo.json'
    if demo_path.exists():
        demo = json.loads(demo_path.read_text())
        pinned += [r['id'] for r in demo.get('runs', []) + demo.get('extended', [])]
        pinned += [demo['stale_run']] if demo.get('stale_run') else []
        pinned += [demo['review']['id']] if demo.get('review') else []
    local_path = root / 'local-evaluation.json'
    if local_path.exists():
        pinned += [r['run_id'] for r in json.loads(local_path.read_text())['rows']]
    ids = list(dict.fromkeys(pinned + store.list()))[:30]
    reports = [store.load(run_id) for run_id in ids]
    shutil.copyfile(store.root / 'trust.pub', temporary / 'trust.pub')
    for report in reports:
        shutil.copytree(store.run_path(report['id']), temporary / 'runs' / report['id'])
    with sqlite3.connect(temporary / 'index.sqlite') as database:
        database.execute('CREATE TABLE runs (id TEXT PRIMARY KEY, created TEXT, decision TEXT, scenario TEXT)')
        database.executemany('INSERT INTO runs VALUES (?, ?, ?, ?)',
                            [(r['id'], r['created'], r['decision'], r['scenario']) for r in reports])
    database.close()
    if destination.exists():
        destination.rename(root / ('review-backup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')))
    temporary.rename(destination)
    assert not (destination / 'signing.key').exists()
    print(json.dumps({'exported_runs': len(reports), 'destination': str(destination),
                      'trust_fingerprint': digest((destination / 'trust.pub').read_bytes())}, indent=2))


if __name__ == '__main__':
    main()
