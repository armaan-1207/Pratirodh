"""Web integration safeguards for the local reference-fix demonstration."""
from test_demo_dashboard import dashboard
from test_projects import IMAGE
from pratirodh.projects.examples import create_example, incomplete_patch
from pratirodh.projects.engine import run_project
from pratirodh.evidence import Store
from pratirodh.web import create_app


def test_requests_action_runs_both_candidates_without_model_calls(dashboard, monkeypatch):
    client, store = dashboard
    import pratirodh.projects.requests_demo as module
    from test_projects import FixtureWorker
    def prepare(root, image):
        manifest, fixed = create_example(root, 'python', image)
        return manifest, incomplete_patch(root, manifest, fixed), fixed
    monkeypatch.setattr(module, 'prepare', prepare)
    monkeypatch.setattr(module, 'run_project', lambda *a, **kw: run_project(*a, worker=FixtureWorker(), **kw))
    page = client.get('/workspace')
    assert b'Challenge the redirect repair' in page.data
    with client.session_transaction() as session:
        token = session['csrf']
    response = client.post('/requests-demo', data={'csrf': token})
    assert response.status_code == 302
    job = client.get(response.location)
    assert b'id="job-status">COMPLETE' in job.data
    assert b'Incomplete redirect repair' in job.data
    assert b'Upstream reference fix' in job.data
    reports = [store.load(i) for i in store.list()]
    assert {r['decision'] for r in reports} == {'REJECT', 'READY_FOR_REVIEW'}
    assert all(r['assurance'] == 'DEMO_ONLY' and r['model_calls'] == 0 for r in reports)
    status = client.get(response.location.replace('/jobs/', '/api/jobs/')).json
    assert status['status'] == 'COMPLETE'
    assert [row['decision'] for row in status['results']] == ['REJECT', 'READY_FOR_REVIEW']
    assert status['runs'] == [row['id'] for row in status['results']]
    ready = next(report for report in reports if report['decision'] == 'READY_FOR_REVIEW')
    exported = client.get('/runs/' + ready['id'] + '/export')
    assert exported.status_code == 200
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(exported.data)) as archive:
        assert not any('signing.key' in name for name in archive.namelist())
        assert 'trust.pub' in archive.namelist()


def test_requests_action_requires_csrf_and_honors_read_only(tmp_path, monkeypatch):
    store = Store(tmp_path / 'evidence')
    client = create_app(store).test_client()
    client.get('/workspace')
    assert client.post('/requests-demo').status_code == 403
    monkeypatch.setenv('PRATIRODH_READ_ONLY', '1')
    readonly = create_app(store).test_client()
    readonly.get('/workspace')
    with readonly.session_transaction() as session:
        token = session['csrf']
    assert readonly.post('/requests-demo', data={'csrf': token}).status_code == 403
    assert not store.list()


def test_missing_requests_image_reports_error_without_creating_success(dashboard, monkeypatch):
    client, store = dashboard
    import pratirodh.web as web
    def unavailable(*args, **kwargs):
        raise FileNotFoundError('prepared image missing')
    monkeypatch.setattr(web.subprocess, 'check_output', unavailable)
    client.get('/workspace')
    with client.session_transaction() as session:
        token = session['csrf']
    response = client.post('/requests-demo', data={'csrf': token})
    page = client.get(response.location)
    assert b'id="job-status">ERROR' in page.data
    assert b'prepared requests-demo image' in page.data
    assert not store.list()
