import json
import time
from pratirodh.evidence import Store
from pratirodh.projects import evaluation
from test_project_evaluation import corpus


def test_expired_external_deadline_never_starts_attempt(tmp_path, monkeypatch):
    path, *_ = corpus(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError('expired campaign must not execute')
    monkeypatch.setattr(evaluation, 'run_project', forbidden)
    monkeypatch.setattr(evaluation, 'final_audit', forbidden)
    state = evaluation.campaign(path, tmp_path / 'checkpoint.json', store=Store(tmp_path / 'evidence'),
        seconds=20, audit_reserve=5, deadline=time.monotonic() - 1)
    assert state['status'] == 'PARTIAL'
    assert state['rows'] == []
    assert len(state['unstarted']) == 12
    assert state['release_complete'] is False


def test_resume_keeps_prior_consumption_with_later_external_deadline(tmp_path, monkeypatch):
    path, *_ = corpus(tmp_path)
    output = tmp_path / 'checkpoint.json'
    store = Store(tmp_path / 'evidence')
    state = evaluation.campaign(path, output, store=store, seconds=20, audit_reserve=5,
                                deadline=time.monotonic() - 1)
    state['elapsed_seconds'] = 19
    output.write_text(json.dumps(state))
    monkeypatch.setattr(evaluation, 'run_project', lambda *a, **kw: (_ for _ in ()).throw(AssertionError('budget reset')))
    resumed = evaluation.campaign(path, output, store=store, seconds=20, audit_reserve=5,
                                 deadline=time.monotonic() + 1000, resume=True)
    assert resumed['rows'] == []
    assert resumed['elapsed_seconds'] >= 19
