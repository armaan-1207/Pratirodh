import io
import zipfile

import pytest

from pratirodh.evidence import Store
from pratirodh.projects.engine import run_project
from pratirodh.projects.examples import create_example
from pratirodh.web import create_app
from test_projects import FixtureWorker, IMAGE


class ImmediatePool:
    def __init__(self, **kwargs):
        pass

    def submit(self, function):
        function()


@pytest.fixture
def dashboard(tmp_path, monkeypatch):
    import pratirodh.web as web
    import pratirodh.projects.engine as engine
    monkeypatch.setattr(web, 'ThreadPoolExecutor', ImmediatePool)
    monkeypatch.setattr(web.subprocess, 'check_output', lambda *a, **k: IMAGE)
    original = engine.run_project
    def controlled_run(*args, **kwargs):
        kwargs['worker'] = FixtureWorker()
        return original(*args, **kwargs)
    monkeypatch.setattr(engine, 'run_project', controlled_run)
    store = Store(tmp_path / 'evidence')
    app = create_app(store)
    app.testing = True
    return app.test_client(), store


def test_live_demo_rejects_incomplete_and_exports_signed_repair(dashboard):
    client, store = dashboard
    assert client.get('/').status_code == 200
    with client.session_transaction() as session:
        token = session['csrf']
    response = client.post('/project-demo', data={'csrf': token, 'language': 'python', 'workflow': 'repair'})
    assert response.status_code == 302
    page = client.get(response.location)
    assert b'id="job-status">COMPLETE' in page.data
    assert b'Incomplete repair rejected; corrected repair ready for review.' in page.data
    reports = [store.load(i) for i in store.list()]
    assert {r['decision'] for r in reports} == {'REJECT', 'READY_FOR_REVIEW'}
    ready = next(r for r in reports if r['decision'] == 'READY_FOR_REVIEW')
    assert client.get('/runs/' + ready['id']).status_code == 200
    exported = client.get('/runs/' + ready['id'] + '/export')
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.data)) as archive:
        assert 'trust.pub' in archive.namelist()
        assert 'evidence/signature.hex' in archive.namelist()
        assert not any('signing.key' in n for n in archive.namelist())


def test_demo_rejects_unregistered_inputs_and_missing_csrf(dashboard):
    client, store = dashboard
    client.get('/')
    assert client.post('/project-demo', data={'language': 'python', 'workflow': 'repair'}).status_code == 403
    with client.session_transaction() as session:
        token = session['csrf']
    assert client.post('/project-demo', data={'csrf': token, 'language': '../../escape', 'workflow': 'repair'}).status_code == 400
    assert not store.list()
    assert client.get('/', headers={'Host': 'external.example'}).status_code == 403


def test_read_only_demo_is_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv('PRATIRODH_READ_ONLY', '1')
    client = create_app(Store(tmp_path / 'evidence')).test_client()
    assert b'READ-ONLY REVIEW' in client.get('/').data
    with client.session_transaction() as session:
        token = session['csrf']
    assert client.post('/project-demo', data={'csrf': token, 'language': 'python', 'workflow': 'repair'}).status_code == 403
    assert client.get('/healthz').json == {'status': 'ok', 'read_only': True}


def test_export_blocks_tampered_evidence(tmp_path):
    store = Store(tmp_path / 'evidence')
    root = tmp_path / 'source'
    manifest, patch = create_example(root, 'python', IMAGE)
    report = run_project(root, manifest, patch=patch, worker=FixtureWorker(), store=store)
    path = store.run_path(report['id']) / 'report.json'
    path.chmod(0o666)
    path.write_text('{}')
    client = create_app(store).test_client()
    assert client.get('/runs/' + report['id'] + '/export').status_code == 409
