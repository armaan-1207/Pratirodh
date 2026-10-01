import json
from pathlib import Path
import pytest
from pratirodh.contracts import evaluate, load_contract
from pratirodh.engine import decision, run, replay
from pratirodh.evidence import Store, fresh
from pratirodh.execution import DockerExecutor
from pratirodh.patches import apply_diff
from pratirodh.web import create_app

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / 'benchmark/scenarios/cwe-22-development-01'


def test_gate_never_offsets_failed_or_missing_checks():
    assert decision([{'status': 'PASS'}, {'status': 'FAIL'}], []) == 'REJECT'
    assert decision([], []) == 'INSUFFICIENT_EVIDENCE'
    assert decision([{'status': 'PASS'}], ['mutation not qualified']) == 'INSUFFICIENT_EVIDENCE'
    assert decision([{'status': 'ERROR'}], []) == 'INSUFFICIENT_EVIDENCE'


def test_security_response_change_is_not_security_success():
    contract = load_contract(SCENARIO / 'contract.json')
    case = contract['cases'][-1]
    assert evaluate(case, {'status': 500, 'body': 'different error'}, contract)['status'] == 'FAIL'
    assert evaluate(case, {'status': 200, 'body': contract['assertions']['private-data']['forbidden'][0]}, contract)['status'] == 'FAIL'
    assert evaluate(case, {'error': 'timeout'}, contract)['status'] == 'ERROR'


def test_patch_cannot_change_contract():
    source = (SCENARIO / 'app.py').read_text()
    patch = (SCENARIO / 'patches/correct.diff').read_text().replace('a/app.py', 'a/contract.json').replace('b/app.py', 'b/contract.json')
    with pytest.raises(ValueError):
        apply_diff(source, patch, 'app.py')


def test_all_contracts_and_patches_are_valid():
    catalogue = json.loads((ROOT / 'benchmark/catalogue.json').read_text())
    assert len(catalogue) == 36
    for scenario in catalogue:
        directory = ROOT / 'benchmark/scenarios' / scenario['id']
        contract = load_contract(directory / 'contract.json')
        source = (directory / contract['entrypoint']).read_text(encoding='utf-8')
        for label in scenario['labels']:
            apply_diff(source, (directory / 'patches' / (label + '.diff')).read_text(), contract['entrypoint'])


def test_signed_evidence_rejects_tampering(tmp_path):
    store = Store(tmp_path)
    report = {'id': 'a' * 32, 'created': '2026-10-01', 'decision': 'REJECT'}
    store.save(report, {'source.py': 'print(1)'})
    assert store.load(report['id']) == report
    path = store.run_path(report['id']) / 'source.py'
    path.chmod(0o666)
    path.write_text('print(2)')
    with pytest.raises(ValueError):
        store.load(report['id'])


def test_unavailable_executor_abstains_and_retains_evidence(tmp_path):
    class Missing:
        def identity(self):
            raise RuntimeError('runner unavailable')
    store = Store(tmp_path)
    report = run(SCENARIO, SCENARIO / 'contract.json', 'invalid', store=store, executor=Missing())
    assert report['decision'] == 'INSUFFICIENT_EVIDENCE'
    assert store.load(report['id'])['gaps']


def test_dashboard_csrf_host_and_registered_ids(tmp_path):
    app = create_app(Store(tmp_path))
    client = app.test_client()
    assert client.get('/').status_code == 200
    assert client.get('/', headers={'Host': 'external.invalid'}).status_code == 403
    assert client.post('/demo', data={'scenario': 'bad'}).status_code == 403
    with client.session_transaction() as session:
        csrf = session['csrf']
    assert client.post('/demo', data={'scenario': '../../bad', 'csrf': csrf}).status_code == 400


@pytest.mark.skipif(__import__('os').getenv('PRATIRODH_DOCKER_TESTS') != '1', reason='opt-in Docker integration')
@pytest.mark.parametrize('cwe', ['22', '89'])
def test_real_container_demo_and_replay(tmp_path, cwe):
    directory = ROOT / f'benchmark/scenarios/cwe-{cwe}-development-01'
    store = Store(tmp_path / 'evidence')
    source_before = (directory / 'app.py').read_bytes()
    reports = {}
    for mode, label in [('fixed', 'incomplete'), ('full', 'incomplete'), ('full', 'correct')]:
        reports[mode, label] = run(directory, directory / 'contract.json',
                                  (directory / 'patches' / (label + '.diff')).read_text(), store=store, mode=mode)
    # Fixed cases may be rejected by static analysis; they are still a weaker baseline.
    assert reports['full', 'incomplete']['decision'] == 'REJECT'
    correct = reports['full', 'correct']
    assert correct['decision'] == 'READY_FOR_REVIEW', correct['gaps']
    assert all(m['status'] == 'CONFIRMED_UNSAFE' and not m['missed_after'] for m in correct['candidates'][0]['mutations'])
    result = replay(correct['id'], 'legitimate', store=store)
    assert result['check']['status'] == 'PASS'
    assert (directory / 'app.py').read_bytes() == source_before
    report = dict(correct, bindings={})
    assert not fresh(report, DockerExecutor())
