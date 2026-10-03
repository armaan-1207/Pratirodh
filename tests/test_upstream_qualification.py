import json

import pytest

from pratirodh.evidence import Store
from pratirodh.projects import qualification
from pratirodh.projects.examples import create_example
from pratirodh.projects.manifest import load
from pratirodh.projects.patching import apply
from test_projects import IMAGE


def setup_case(tmp_path, monkeypatch, vulnerable_stdout='VIOLATION\n'):
    target = tmp_path / 'source'
    manifest_path, patch = create_example(target, 'python', IMAGE, 'execution')
    manifest, original = load(target, manifest_path)
    fixed = apply(original, patch, manifest['editable'])
    source_map = {name: name for name in manifest['editable']}
    review = {'errors': [], 'source_revision': 'vulnerable', 'fix_revision': 'fixed',
              'editable_changes': list(source_map)}
    monkeypatch.setattr(qualification, 'review_source', lambda *args: review)
    monkeypatch.setattr(qualification, 'git', lambda directory, command, spec:
                        (original if spec.startswith('vulnerable:') else fixed)[spec.split(':', 1)[1]])
    monkeypatch.setattr(qualification, 'attest_worker', lambda context, image:
                        dict(context=context, image=image, daemon_id=context,
                             boot_id_digest=context, machine_id_digest=context))
    monkeypatch.setattr(qualification, 'DockerProjectWorker', lambda manifest: manifest)
    monkeypatch.setattr(qualification, 'qualify', lambda *args: {'status': 'QUALIFIED'})
    monkeypatch.setattr(qualification, 'verify', lambda *args: [{'status': 'PASS'}])
    audit = {'context': 'audit', 'image': IMAGE, 'files': {'audit/check.py': '# protected'},
             'checks': [{'role': 'control', 'command': ['python', 'audit/check.py', 'normal'],
                         'exit': 0, 'stdout': 'NORMAL\n'},
                        {'role': 'security', 'command': ['python', 'audit/check.py', 'security'],
                         'exit': 0, 'stdout': 'SAFE\n', 'violation': {'exit': 1, 'stdout': 'VIOLATION\n'}}]}
    audit_path = tmp_path / 'audit.json'
    audit_path.write_text(json.dumps(audit))

    def observation(worker, files, command, budget, oracle=None, build=None):
        if oracle is None:
            return {'status': 'PASS'}
        vulnerable = files['policy.py'] == original['policy.py']
        actual = {'status': 'COMPLETE', 'exit': 1 if vulnerable and command[-1] == 'security' else 0,
                  'stdout': vulnerable_stdout if vulnerable and command[-1] == 'security' else oracle['stdout']}
        return {'status': 'PASS' if qualification.matches(actual, oracle) else 'FAIL', 'actual': actual}

    monkeypatch.setattr(qualification, 'check', observation)
    return target, manifest_path, audit_path, source_map


@pytest.mark.parametrize('stdout,expected', [('VIOLATION\n', 'QUALIFIED'), ('HARNESS BROKEN\n', 'QUALIFICATION_FAILED')])
def test_audit_failure_requires_exact_violation(tmp_path, monkeypatch, stdout, expected):
    target, manifest, audit, source_map = setup_case(tmp_path, monkeypatch, stdout)
    store = Store(tmp_path / 'evidence')
    result = qualification.qualify_case({'id': 'fixture'}, tmp_path, target, manifest, audit, source_map,
        {'approved': True, 'identifier': 'MIT', 'rationale': 'fixture'}, store)
    assert result['status'] == expected
    assert store.load(result['id'])['source_revision'] == load(target, manifest)[0]['revision']


def test_audit_without_violation_oracle_cannot_execute(tmp_path, monkeypatch):
    target, manifest, audit, source_map = setup_case(tmp_path, monkeypatch)
    definition = json.loads(audit.read_text())
    del definition['checks'][1]['violation']
    audit.write_text(json.dumps(definition))
    monkeypatch.setattr(qualification, 'attest_worker', lambda *args: pytest.fail('must validate before executing'))
    with pytest.raises(ValueError, match='violation oracle'):
        qualification.qualify_case({'id': 'fixture'}, tmp_path, target, manifest, audit, source_map,
            {'approved': True, 'identifier': 'MIT', 'rationale': 'fixture'}, Store(tmp_path / 'evidence'))


def test_unmapped_reference_fix_cannot_qualify(tmp_path, monkeypatch):
    target, manifest, audit, source_map = setup_case(tmp_path, monkeypatch)
    monkeypatch.setattr(qualification, 'review_source', lambda *args:
        {'errors': [], 'editable_changes': [*source_map, 'missing.py']})
    with pytest.raises(ValueError, match='every editable reference-fix change'):
        qualification.qualify_case({'id': 'fixture'}, tmp_path, target, manifest, audit, source_map,
            {'approved': True, 'identifier': 'MIT', 'rationale': 'fixture'}, Store(tmp_path / 'evidence'))
