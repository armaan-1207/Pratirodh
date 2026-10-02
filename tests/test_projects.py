import copy
import json
from pathlib import Path
import threading
import zipfile

import pytest
from pratirodh.evidence import Store, digest
from pratirodh.projects.budget import WorkflowBudget
from pratirodh.projects.engine import run_project, project_fresh, formal_checks
from pratirodh.projects.examples import create_example
from pratirodh.projects.manifest import inventory, load, validate, inspect
from pratirodh.projects.model import LocalModel, context
from pratirodh.projects.patching import apply, make_diff
from pratirodh.projects.export import export_bundle
from pratirodh.projects.worker import DockerProjectWorker

IMAGE = 'sha256:' + 'a' * 64


@pytest.fixture
def project(tmp_path):
    root = tmp_path / 'project'
    manifest, patch = create_example(root, 'python', IMAGE)
    return root, manifest, patch, Store(tmp_path / 'evidence')


class FixtureWorker:
    """Protocol simulator only. Does not execute arbitrary imported source."""
    def __init__(self, flaky=False, broken=False, mode='normal'):
        self.observations = []
        self.flaky = flaky
        self.broken = broken
        self.mode = mode
        self.count = 0

    def identity(self):
        return IMAGE

    def execute(self, files, commands, budget):
        budget.remaining()
        observations = []
        for command in commands:
            self.count += 1
            stdout, code = '', 0
            if self.broken:
                code = 2
            elif 'portal.py' in command:
                owner, user = command[-2:]
                if 'return "admin"' in files['users.py'] and user == 'guest':
                    user = 'admin'
                allowed = 'return True' in files['policy.py'] or owner == user
                stdout = 'GRANTED\n' if allowed else 'DENIED\n'
                if self.flaky and self.count % 3 == 0:
                    stdout = 'HARNESS ERROR\n'
                if self.mode == 'false-harness':
                    stdout, code = '', 1
            elif 'bandit' in command:
                stdout = '{"results": []}'
            elif command[0] == 'cbmc':
                stdout = 'VERIFICATION FAILED' if self.mode == 'formal-fail' else '' if self.mode == 'formal-empty' else 'VERIFICATION SUCCESSFUL'
                code = 10 if self.mode == 'formal-fail' else 0
            observations.append({'status': 'COMPLETE', 'exit': code, 'stdout': stdout, 'stderr': '', 'seconds': .01})
            if code:
                break
        self.observations.append({'commands': commands, 'observations': observations})
        return observations


@pytest.mark.parametrize('language', ['python', 'node', 'cpp'])
def test_multi_file_patch_and_intake(tmp_path, language):
    root = tmp_path / language
    manifest, patch = create_example(root, language, IMAGE)
    data, files = load(root, manifest)
    updated = apply(files, patch, data['editable'])
    assert sum(files[n] != updated[n] for n in files) == 2
    assert inventory(root)[0] == files


@pytest.mark.parametrize('workflow', ['repair', 'discover'])
def test_verified_workflow_signed_and_exported(project, workflow):
    root, manifest, patch, store = project
    report = run_project(root, manifest, workflow, patch=patch, worker=FixtureWorker(), store=store)
    assert report['decision'] == 'READY_FOR_REVIEW'
    assert len(report['harness_validation'][0]['reproductions']) == 3
    assert all(m['caught'] and m['status'] == 'CONFIRMED_UNSAFE' for m in report['candidates'][0]['mutations'])
    assert store.load(report['id']) == report
    assert project_fresh(report)
    exported = export_bundle(store, report['id'], root.parent / 'bundle.zip')
    with zipfile.ZipFile(exported) as archive:
        assert 'trust.pub' in archive.namelist()
        assert not any('signing.key' in name for name in archive.namelist())
    (root / 'users.py').write_text('def normalize(user):\n    return user\n')
    assert not project_fresh(report)


@pytest.mark.parametrize('failure', ['broken', 'flaky', 'false-harness'])
def test_baseline_and_false_failures_never_ready(project, failure):
    root, manifest, patch, store = project
    worker = FixtureWorker(broken=failure == 'broken', flaky=failure == 'flaky', mode=failure)
    report = run_project(root, manifest, patch=patch, worker=worker, store=store)
    assert report['decision'] == 'INSUFFICIENT_EVIDENCE'
    assert not report['candidates']
    assert store.load(report['id'])['decision'] == report['decision']


def test_no_violation_is_not_secure(project):
    root, manifest, patch, store = project
    data, files = load(root, manifest)
    fixed = apply(files, patch, data['editable'])
    for name in data['editable']:
        (root / name).write_text(fixed[name], encoding='utf-8')
    _, hashes, revision = inventory(root)
    data.update(revision=revision, inventory=hashes)
    manifest.write_text(json.dumps(data))
    report = run_project(root, manifest, worker=FixtureWorker(), store=store)
    assert report['reason'] == 'NO_VIOLATION_FOUND'
    assert report['decision'] == 'INSUFFICIENT_EVIDENCE'
    assert 'No violation found within this search' in report['gaps']


@pytest.mark.parametrize('name', ['tests/test_portal.py', '../outside.py', 'requirements.txt', 'pratirodh-project.json'])
def test_patch_escape_and_protected_inputs(project, name):
    root, manifest, patch, store = project
    data, files = load(root, manifest)
    diff = '--- a/' + name + '\n+++ b/' + name + '\n@@ -1 +1 @@\n-before\n+after\n'
    with pytest.raises(ValueError):
        apply(files, diff, data['editable'])


def test_candidate_suppression_is_rejected(project):
    root, manifest, patch, store = project
    data, files = load(root, manifest)
    diff = make_diff(files, dict(files, **{'policy.py': files['policy.py'] + '# nosec\n'}))
    report = run_project(root, manifest, patch=diff, worker=FixtureWorker(), store=store)
    assert report['decision'] == 'REJECT'


@pytest.mark.parametrize('mutation', ['missing', 'equivalent'])
def test_unqualified_mutations_never_caught(project, mutation):
    root, manifest, patch, store = project
    data = json.loads(manifest.read_text())
    if mutation == 'missing':
        data['mutations'][0]['find'] = 'unavailable pattern'
    else:
        data['mutations'][0]['replace'] = 'return normalize(user) == owner'
    manifest.write_text(json.dumps(data))
    report = run_project(root, manifest, patch=patch, worker=FixtureWorker(), store=store)
    assert report['decision'] == 'INSUFFICIENT_EVIDENCE'
    assert report['candidates'][0]['mutations'][0]['caught'] is False


def test_missing_property_and_unapproved_property(project):
    root, manifest, patch, store = project
    data = json.loads(manifest.read_text())
    data['properties'][0]['provenance']['kind'] = 'model'
    manifest.write_text(json.dumps(data))
    report = run_project(root, manifest, patch=patch, worker=FixtureWorker(), store=store)
    assert report['reason'] == 'INVALID_PROJECT_OR_MANIFEST'
    data['properties'] = []
    data['mutations'] = []
    manifest.write_text(json.dumps(data))
    report = run_project(root, manifest, patch=patch, worker=FixtureWorker(), store=store)
    assert report['reason'] == 'MISSING_PROPERTY'


def test_cancellation_retains_evidence_and_resume(project):
    root, manifest, patch, store = project
    cancel = threading.Event()
    cancel.set()
    report = run_project(root, manifest, patch=patch, worker=FixtureWorker(), store=store, cancelled=cancel)
    assert report['reason'] == 'CANCELLED'
    assert store.load(report['id'])['decision'] == 'INSUFFICIENT_EVIDENCE'
    resumed = run_project(root, manifest, patch=patch, worker=FixtureWorker(), store=store, resume=report['id'])
    assert resumed['decision'] == 'READY_FOR_REVIEW'
    assert resumed['resumed_from'] == report['id']


def test_budget_reserve_and_calls():
    budget = WorkflowBudget({'seconds': 20, 'reserve_seconds': 10, 'model_calls': 1, 'candidates': 3})
    assert budget.model_call() <= 10
    with pytest.raises(TimeoutError):
        budget.model_call()
    budget.deadline = budget.start + 5
    assert not budget.proposing()


def test_model_failure_retained_no_cloud_fallback(project):
    root, manifest, patch, store = project
    class FailedModel:
        usage = []
        def suggest(self, prompt, budget):
            budget.model_call()
            raise RuntimeError('local server unavailable')
    report = run_project(root, manifest, worker=FixtureWorker(), store=store, model=FailedModel())
    assert report['reason'] == 'PROVIDER_FAILURE'
    assert report['decision'] == 'INSUFFICIENT_EVIDENCE'
    assert report['model_calls'] == 3
    assert len(report['candidates']) == 3


def test_generated_repair_protocol_and_prompt_audit_exclusion(project):
    root, manifest, patch, store = project
    class ProtocolModel:
        usage = []
        def suggest(self, prompt, budget):
            budget.model_call()
            assert 'test_legitimate' not in prompt
            assert 'harness_review' not in prompt
            assert 'GRANTED' not in prompt.split('FILE policy.py')[0]
            return {'patch': patch}
    report = run_project(root, manifest, worker=FixtureWorker(), store=store, model=ProtocolModel())
    assert report['decision'] == 'READY_FOR_REVIEW'
    assert report['candidates'][0]['origin'] == 'local-model'
    assert report['model_calls'] == 1


def test_formal_failure_and_empty_success_unresolved(project):
    root, manifest, patch, store = project
    data = json.loads(manifest.read_text())
    data['formal'] = [{'tool': 'cbmc', 'property': 'tenant-isolation', 'assumptions': ['synthetic input'],
                       'bounds': {'unwind': 4}, 'command': ['cbmc', 'policy.cpp', '--unwind', '4', '--unwinding-assertions']}]
    manifest.write_text(json.dumps(data))
    for mode, decision in [('formal-fail', 'REJECT'), ('formal-empty', 'INSUFFICIENT_EVIDENCE')]:
        report = run_project(root, manifest, patch=patch, worker=FixtureWorker(mode=mode), store=store)
        assert report['decision'] == decision


@pytest.mark.parametrize('endpoint', ['https://example.com', 'http://192.168.1.2:11434', 'http://user:password@localhost', 'http://localhost/redirect'])
def test_local_models_reject_remote_endpoints(project, endpoint):
    config = json.loads(project[1].read_text())['model']
    config.update(endpoint=endpoint, weights_digest=IMAGE, runtime_digest=IMAGE)
    with pytest.raises(ValueError):
        LocalModel(config)


def test_worker_requires_explicit_demo_or_dedicated(project):
    data = json.loads(project[1].read_text())
    with pytest.raises(ValueError):
        DockerProjectWorker(data)
    data['worker']['mode'] = 'dedicated'
    with pytest.raises(ValueError):
        DockerProjectWorker(data)


def test_intake_unknown_and_secret_files(tmp_path):
    (tmp_path / 'main.go').write_text('package main')
    assert inspect(tmp_path)['status'] == 'UNSUPPORTED_PROJECT'
    (tmp_path / '.env').write_text('SECRET=fixture')
    with pytest.raises(ValueError):
        inventory(tmp_path)


def test_web_project_routes_and_csrf(project):
    from pratirodh.web import create_app
    app = create_app(project[3])
    app.testing = True
    client = app.test_client()
    assert client.get('/projects').status_code == 200
    assert client.post('/projects/inspect', data={'source': str(project[0])}).status_code == 403
    with client.session_transaction() as session:
        csrf = session['csrf']
    response = client.post('/projects/inspect', data={'csrf': csrf, 'source': str(project[0])})
    assert response.status_code == 200
    assert b'Manifest to review' in response.data
    report = run_project(project[0], project[1], patch=project[2], worker=FixtureWorker(), store=project[3])
    assert client.get('/runs/' + report['id']).status_code == 200
    assert client.get('/', headers={'Host': 'evil.example'}).status_code == 403


def test_historical_evidence_still_readable(project):
    report = {'id': 'f' * 32, 'created': '2026-01-01', 'decision': 'REJECT', 'scenario': 'historical'}
    project[3].save(report, {'original.py': 'pass'})
    assert project[3].load(report['id']) == report


@pytest.mark.parametrize('answer', [{'patch': {}}, {'files': {'tests/test_portal.py': 'pass'}}, {}])
def test_malformed_proposals_keep_signed_failure_evidence(project, answer):
    root, manifest, patch, store = project
    class Malformed:
        usage = []
        def suggest(self, prompt, budget):
            budget.model_call()
            return answer
    report = run_project(root, manifest, worker=FixtureWorker(), store=store, model=Malformed())
    assert report['decision'] == 'INSUFFICIENT_EVIDENCE'
    assert store.load(report['id']) == report
    assert (store.run_path(report['id']) / 'proposal-0.json').exists()


def test_model_harness_proposals_cannot_authorize_execution(project):
    root, manifest, patch, store = project
    data = json.loads(manifest.read_text())
    data.update(model_analysis=True, generate_harnesses=True, properties=[], mutations=[])
    manifest.write_text(json.dumps(data))
    class Proposer:
        usage = []
        def suggest(self, prompt, budget, schema=None):
            budget.model_call()
            return {'findings': ['unconfirmed allegation']} if schema else {'files': {'fuzz/unreviewed.py': 'raise RuntimeError("UNTRUSTED")'}}
    worker = FixtureWorker()
    result = run_project(root, manifest, worker=worker, store=store, model=Proposer())
    assert result['reason'] == 'MISSING_PROPERTY'
    assert result['decision'] == 'INSUFFICIENT_EVIDENCE'
    assert result['model_calls'] == 2
    assert result['generated_harnesses']['status'] == 'PROPOSAL_REQUIRES_APPROVAL'
    assert not result['candidates']
    assert all('unreviewed.py' not in json.dumps(o['commands']) for o in worker.observations)
