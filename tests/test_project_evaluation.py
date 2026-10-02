import json
from pathlib import Path
import pytest
from pratirodh.evidence import Store
from pratirodh.projects.evaluation import freeze, final_audit
from pratirodh.projects.examples import create_example
from pratirodh.projects.engine import run_project
from test_projects import FixtureWorker, IMAGE


def corpus(tmp_path):
    target = tmp_path / 'source'
    manifest_path, patch = create_example(target, 'python', IMAGE)
    audit = {'context': 'separate-audit', 'files': {'audit/assertion.py': 'raise SystemExit(0)'},
             'checks': [{'command': ['python', 'audit/assertion.py'], 'exit': 0, 'stdout': ''}]}
    audit_path = tmp_path / 'audit.json'
    audit_path.write_text(json.dumps(audit))
    case = {'id': 'upstream-fixture', 'language': 'python', 'split': 'evaluation', 'target': 'source',
            'manifest': 'source/pratirodh-project.json', 'audit': 'audit.json',
            'provenance': {'license': 'MIT', 'source_url': 'https://example.com/advisory',
                           'upstream_fix_url': 'https://example.com/fix', 'adaptations': 'TEST ONLY; not eligible external evidence'}}
    path = tmp_path / 'campaign.json'
    path.write_text(json.dumps({'version': 1, 'cases': [case]}))
    return path, target, manifest_path, patch, audit_path


def test_freeze_partial_and_audit_never_generation_input(tmp_path):
    path, target, manifest, patch, audit = corpus(tmp_path)
    frozen = freeze(path)
    assert frozen['complete_24_case_cohort'] is False
    assert 'assertion.py' not in json.dumps(frozen)
    store = Store(tmp_path / 'evidence')
    report = run_project(target, manifest, patch=patch, worker=FixtureWorker(), store=store)
    assert report['decision'] == 'READY_FOR_REVIEW'
    observed = {}
    class AuditWorker(FixtureWorker):
        def __init__(self, config):
            super().__init__()
            observed['context'] = config['worker']['context']
        def execute(self, files, commands, budget):
            observed['files'] = set(files)
            return super().execute(files, commands, budget)
    result = final_audit(report, frozen['cases'][0], path, store, AuditWorker)
    assert result['status'] == 'PASS'
    assert observed['context'] == 'separate-audit'
    assert 'audit/assertion.py' in observed['files']
    audit.write_text('{}')
    with pytest.raises(ValueError, match='frozen final audit changed'):
        final_audit(report, frozen['cases'][0], path, store, AuditWorker)


@pytest.mark.parametrize('problem', ['missing-license', 'audit-in-target', 'same-worker'])
def test_evaluation_rejects_leakage_and_missing_provenance(tmp_path, problem):
    path, target, manifest, patch, audit = corpus(tmp_path)
    data = json.loads(path.read_text())
    if problem == 'missing-license':
        data['cases'][0]['provenance'].pop('license')
    elif problem == 'audit-in-target':
        nested = target / 'audit.json'
        nested.write_text(audit.read_text())
        data['cases'][0]['audit'] = 'source/audit.json'
        # Audit would also invalidate intake. Either rejection protects the boundary.
    else:
        value = json.loads(audit.read_text())
        value['context'] = 'default'
        audit.write_text(json.dumps(value))
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        freeze(path)


def test_read_only_dashboard_blocks_mutation(tmp_path, monkeypatch):
    from pratirodh.web import create_app
    monkeypatch.setenv('PRATIRODH_READ_ONLY', '1')
    app = create_app(Store(tmp_path / 'evidence'))
    client = app.test_client()
    assert client.get('/').status_code == 200
    with client.session_transaction() as session:
        csrf = session['csrf']
    assert client.post('/projects/inspect', data={'csrf': csrf, 'source': str(tmp_path)}).status_code == 403


def test_campaign_retains_partial_and_unstarted_runs(tmp_path, monkeypatch):
    import time
    from pratirodh.projects import evaluation
    path, target, manifest, patch, audit = corpus(tmp_path)
    def no_provider_run(*args, **kwargs):
        time.sleep(.2)
        return {'id': 'a' * 32, 'decision': 'INSUFFICIENT_EVIDENCE', 'findings': [], 'elapsed_seconds': .2,
                'model_calls': 0, 'reason': 'PROVIDER_FAILURE', 'candidates': []}
    monkeypatch.setattr(evaluation, 'run_project', no_provider_run)
    result = evaluation.campaign(path, tmp_path / 'result.json', store=Store(tmp_path / 'evidence'), seconds=1, audit_reserve=0)
    assert result['status'] == 'PARTIAL'
    assert result['unstarted']
    assert result['rows']
    assert result['release_complete'] is False
    assert all(row['decision'] == 'INSUFFICIENT_EVIDENCE' for row in result['rows'])
    data = json.loads(path.read_text())
    data['cases'][0]['provenance']['license'] = 'changed-license'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='evaluation changed'):
        evaluation.campaign(path, tmp_path / 'result.json', store=Store(tmp_path / 'evidence'), resume=True)


def test_campaign_normalizes_files_and_retries_audits(tmp_path, monkeypatch):
    from pratirodh.projects import evaluation, model
    from pratirodh.projects.manifest import load
    from pratirodh.projects.patching import apply
    path, target, manifest, patch, audit = corpus(tmp_path)
    config, files = load(target, manifest)
    updated = apply(files, patch, config['editable'])
    class FilesModel:
        def __init__(self, config):
            self.usage = []
        def suggest(self, prompt, budget):
            budget.model_call()
            return {'files': {n: updated[n] for n in files if updated[n] != files[n]}}
    monkeypatch.setattr(model, 'LocalModel', FilesModel)
    original_run = evaluation.run_project
    def run_fixture(*args, **kwargs):
        kwargs['worker'] = FixtureWorker()
        kwargs['model'] = FilesModel({})
        return original_run(*args, **kwargs)
    monkeypatch.setattr(evaluation, 'run_project', run_fixture)
    original_audit = evaluation.final_audit
    def unavailable(*args, **kwargs):
        raise ConnectionError('audit guest temporarily unavailable')
    monkeypatch.setattr(evaluation, 'final_audit', unavailable)
    store = Store(tmp_path / 'evidence')
    output = tmp_path / 'result.json'
    first = evaluation.campaign(path, output, store=store, seconds=1800, audit_reserve=0)
    assert len(first['rows']) == 12
    assert len(first['pending']) == 12
    assert first['status'] == 'PARTIAL'
    assert all(r['decision'] == 'READY_FOR_REVIEW' for r in first['rows'])
    def audit_fixture(*args, **kwargs):
        kwargs['worker_factory'] = lambda manifest: FixtureWorker()
        return original_audit(*args, **kwargs)
    monkeypatch.setattr(evaluation, 'final_audit', audit_fixture)
    resumed = evaluation.campaign(path, output, store=store, seconds=1800, audit_reserve=0, resume=True)
    assert len(resumed['rows']) == 12
    assert resumed['pending'] == []
    assert resumed['status'] == 'COMPLETE'
    assert all(r['audit'] == 'PASS' for r in resumed['rows'])
    assert resumed['release_complete'] is False  # One synthetic test case is not a release cohort.


def test_expired_campaign_deadline_prevents_worker_execution(tmp_path):
    import time
    path, target, manifest, patch, audit = corpus(tmp_path)
    worker = FixtureWorker()
    store = Store(tmp_path / 'evidence')
    report = run_project(target, manifest, patch=patch, worker=worker, store=store,
                         deadline=time.monotonic() - 1)
    assert report['decision'] == 'INSUFFICIENT_EVIDENCE'
    assert report['reason'] == 'BUDGET_EXHAUSTION'
    assert not worker.observations
    store.load(report['id'])
