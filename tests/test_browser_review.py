"""Review UI contracts; synthetic records are isolated from release evidence."""
import importlib
import stat

import pytest

from pratirodh.evidence import Store
from pratirodh.web import create_app


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.delenv('PRATIRODH_READ_ONLY', raising=False)
    monkeypatch.delenv('PRATIRODH_PASSWORD', raising=False)
    monkeypatch.delenv('PRATIRODH_ENV', raising=False)
    store = Store(tmp_path)
    run_id = 'a' * 32
    store.save(dict(id=run_id, created='2026-10-10T00:00:00Z', scenario='cwe-89-development-01',
                    cwe='CWE-89', mode='full', decision='READY_FOR_REVIEW',
                    elapsed_seconds=1, model_calls=1, candidates=[], gaps=[]), {})
    web = importlib.import_module('pratirodh.web')
    review = importlib.import_module('pratirodh.review')
    state = {'fresh': True}
    monkeypatch.setattr(web, 'fresh', lambda *a: state['fresh'])
    monkeypatch.setattr(web, 'freshness_changes', lambda *a: [] if state['fresh'] else ['runner'])
    monkeypatch.setattr(review, 'fresh', lambda *a: state['fresh'])
    client = create_app(store).test_client()
    client.get('/workspace')
    with client.session_transaction() as session:
        csrf = session['csrf']
    return client, store, run_id, dict(csrf=csrf, reviewer='Synthetic test reviewer',
                                     rationale='Reviewed protected checks', action='approve'), state


def test_browser_approval_is_separately_signed_and_does_not_replace_run(setup):
    client, store, run_id, data, _ = setup
    before = (store.run_path(run_id) / 'report.json').read_bytes()
    response = client.post(f'/runs/{run_id}/review', data=data)
    assert response.status_code == 303
    record = store.load(response.headers['Location'].rsplit('/', 1)[1])
    assert record['decision'] == 'HUMAN_APPROVE'
    assert record['run_id'] == run_id and record['identity_verified'] is False
    assert (store.run_path(run_id) / 'report.json').read_bytes() == before
    assert b'No patch was applied' in client.get(response.headers['Location']).data


def test_stale_approval_is_blocked_but_rejection_can_be_recorded(setup):
    client, store, run_id, data, state = setup
    state['fresh'] = False
    assert client.post(f'/runs/{run_id}/review', data=data).status_code == 409
    assert len(store.list()) == 1
    response = client.post(f'/runs/{run_id}/review', data=dict(data, action='reject'))
    assert response.status_code == 303
    assert store.load(response.headers['Location'].rsplit('/', 1)[1])['decision'] == 'HUMAN_REJECT'


def test_csrf_and_readonly_protect_review_mutation(setup, monkeypatch):
    client, store, run_id, data, _ = setup
    assert client.post(f'/runs/{run_id}/review', data=dict(data, csrf='wrong')).status_code == 403
    monkeypatch.setenv('PRATIRODH_READ_ONLY', '1')
    readonly = create_app(store).test_client()
    page = readonly.get(f'/runs/{run_id}')
    assert b'Recording decisions is disabled' in page.data
    assert b'Approve repair</button>' not in page.data
    with readonly.session_transaction() as session:
        token = session['csrf']
    assert readonly.post(f'/runs/{run_id}/review', data=dict(data, csrf=token)).status_code == 403
    assert len(store.list()) == 1


@pytest.mark.parametrize('change', [dict(action='apply'), dict(reviewer=' '),
                                  dict(rationale=''), dict(reviewer='x' * 101),
                                  dict(rationale='x' * 2001)])
def test_invalid_review_metadata_never_creates_a_record(setup, change):
    client, store, run_id, data, _ = setup
    assert client.post(f'/runs/{run_id}/review', data=dict(data, **change)).status_code == 400
    assert len(store.list()) == 1


def test_review_rationale_is_escaped_and_nested_reviews_are_rejected(setup):
    client, store, run_id, data, _ = setup
    response = client.post(f'/runs/{run_id}/review', data=dict(data, rationale='<script>alert(1)</script>'))
    page = client.get(response.headers['Location']).data
    assert b'&lt;script&gt;' in page and b'<script>alert(1)</script>' not in page
    assert client.post(response.headers['Location'] + '/review', data=data).status_code == 400


def test_invalid_signature_cannot_be_reviewed(setup):
    client, store, run_id, data, _ = setup
    report_path = store.run_path(run_id) / 'report.json'
    report_path.chmod(stat.S_IWRITE | stat.S_IREAD)
    report_path.write_bytes(b'{}')
    assert client.post(f'/runs/{run_id}/review', data=dict(data, action='reject')).status_code == 409
    assert len(store.list()) == 1


@pytest.mark.parametrize('decision', ['REJECT', 'INSUFFICIENT_EVIDENCE'])
def test_fresh_nonready_result_cannot_be_approved(setup, decision):
    client, store, _, data, _ = setup
    run_id = 'b' * 32
    store.save(dict(id=run_id, created='2026-10-10T00:00:00Z', scenario='synthetic', decision=decision), {})
    assert client.post(f'/runs/{run_id}/review', data=data).status_code == 409
    assert len(store.list()) == 2


def test_project_result_does_not_enter_fixture_review_boundary(setup):
    client, store, _, data, _ = setup
    run_id = 'b' * 32
    store.save(dict(id=run_id, created='2026-10-10T00:00:00Z', version=2, decision='READY_FOR_REVIEW'), {})
    assert client.post(f'/runs/{run_id}/review', data=data).status_code == 400
    assert len(store.list()) == 2
