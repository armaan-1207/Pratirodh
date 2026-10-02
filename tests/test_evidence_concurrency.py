from concurrent.futures import ThreadPoolExecutor
import pytest
from pratirodh.evidence import Store


def test_concurrent_controller_writers_share_stable_trust_anchor(tmp_path):
    store = Store(tmp_path / 'evidence')
    reports = [{'id': format(i, '032x'), 'created': '2026-10-02', 'decision': 'INSUFFICIENT_EVIDENCE', 'scenario': 'parallel'}
               for i in range(1, 5)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda r: store.save(r, {'observations.json': '{}'}), reports))
    assert len(results) == 4
    assert all(store.load(r['id']) == r for r in reports)


@pytest.mark.parametrize('name', ['../escape', 'signature.hex', 'inventory.json', 'report.json'])
def test_reserved_artifacts_rejected_before_storage(tmp_path, name):
    store = Store(tmp_path / 'evidence')
    with pytest.raises(ValueError):
        store.save({'id': 'a' * 32}, {name: 'data'})
    assert not store.root.exists()
