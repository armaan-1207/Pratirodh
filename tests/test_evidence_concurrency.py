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


def test_empty_lock_contends_without_writing_locked_region(tmp_path, monkeypatch):
    import os
    from pratirodh.projects import leases
    from pratirodh.execution import Budget

    monkeypatch.setattr(leases.tempfile, 'gettempdir', lambda: str(tmp_path))
    root = tmp_path / 'pratirodh-controller-locks'
    root.mkdir()
    path = root / 'empty-0.lock'
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        contender = leases.Lease('empty')
        assert not contender.acquire(Budget(2), seconds=.15)
        assert contender.fd is None
        assert path.stat().st_size == 0
    finally:
        os.close(fd)
    assert contender.acquire(Budget(2))
    contender.release()


def test_evidence_index_connections_close_after_save_and_list(tmp_path, monkeypatch):
    import sqlite3
    from pratirodh import evidence

    connections = []
    connect = sqlite3.connect

    def capture(*args, **kwargs):
        connection = connect(*args, **kwargs)
        connections.append(connection)
        return connection

    monkeypatch.setattr(evidence.sqlite3, 'connect', capture)
    store = Store(tmp_path / 'evidence')
    report = dict(id='a' * 32, created='2026-10-07', decision='INSUFFICIENT_EVIDENCE')
    store.save(report, {})
    assert store.list() == [report['id']]
    assert store.load(report['id']) == report
    assert len(connections) == 2
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match='closed'):
            connection.execute('SELECT 1')
