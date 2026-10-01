import json
from pathlib import Path
import pytest
from pratirodh.provider import OllamaModel
from pratirodh.contracts import load_contract, evaluate, violation
from pratirodh.fuzzing import generate
from pratirodh.detection import scan, MAPPING
from pratirodh.engine import run, replay
from pratirodh.review import review
from pratirodh.evidence import Store

ROOT = Path(__file__).resolve().parents[1]


def test_local_provider_no_fallback_or_proxy(monkeypatch):
    model = OllamaModel()
    monkeypatch.setattr(model, 'request', lambda *a, **k: {'models': []})
    with pytest.raises(RuntimeError):
        model.identity()
    assert model.url == 'http://127.0.0.1:11434'
    assert MAPPING['B307'] == 'CWE-94'
    assert MAPPING['B201'] == 'CWE-489'
    assert 'B603' not in MAPPING


def test_provider_structured_output_errors_and_budget(monkeypatch):
    from pratirodh.execution import Budget
    model = OllamaModel()
    monkeypatch.setattr(model, 'identity', lambda: {'digest': 'test', 'model': model.model})
    monkeypatch.setattr(model, 'request', lambda *a, **k: {'message': {'content': '[]'}})
    with pytest.raises(RuntimeError):
        model.suggest('source', Budget())
    assert model.usage[-1]['status'] == 'ERROR'
    with pytest.raises(ValueError):
        model.suggest('x' * 16001, Budget())


def test_local_repair_uses_chat_roles_and_schema(monkeypatch):
    from pratirodh.execution import Budget
    model = OllamaModel()
    monkeypatch.setattr(model, 'identity', lambda: {'digest': 'test', 'model': model.model})
    requests = []
    def request(route, data, timeout):
        requests.append((route, data))
        return {'message': {'content': '{"source":"print(1)"}'}}
    monkeypatch.setattr(model, 'request', request)
    assert model.suggest('entire repaired Python file', Budget())['source'] == 'print(1)'
    assert requests[0][0] == '/api/chat'
    assert [m['role'] for m in requests[0][1]['messages']] == ['system', 'user']
    assert requests[0][1]['format']['required'] == ['source']


def test_effect_oracle_never_accepts_missing_observation():
    contract = load_contract(ROOT / 'benchmark/scenarios/cwe-78-development-01/contract.json')
    case = contract['cases'][-1]
    assert evaluate(case, {'status': 200, 'body': 'ok'}, contract)['status'] == 'ERROR'
    check = evaluate(case, {'status': 200, 'body': 'ok', 'files': {'marker.txt': True}}, contract)
    assert violation(check)
    assert not violation(evaluate(case, {'error': 'timeout'}, contract))


def test_fuzzing_is_seeded_and_profile_safe():
    contract = load_contract(ROOT / 'benchmark/scenarios/cwe-798-development-01/contract.json')
    assert generate(contract, 7) == generate(contract, 7)
    assert generate(contract, 7) != generate(contract, 8)
    assert len(generate(contract)) == 64
    assert all(c['assertion'] == 'safe' for c in generate(contract))


def test_detector_reports_candidates_and_unsupported(tmp_path):
    (tmp_path / 'app.py').write_text('import pickle\nx = pickle.loads(b"a")\n')
    findings = scan(tmp_path)
    assert any(f['cwe'] == 'CWE-502' and not f['verification_supported'] for f in findings)
    assert all(f['status'] == 'UNVERIFIED' for f in findings)


@pytest.mark.parametrize('cwe', ['78', '798'])
def test_new_classes_real_docker(cwe, tmp_path):
    import os
    if os.getenv('PRATIRODH_DOCKER_TESTS') != '1':
        pytest.skip('enable Docker integration explicitly')
    directory = ROOT / f'benchmark/scenarios/cwe-{cwe}-development-01'
    store = Store(tmp_path / 'evidence')
    report = run(directory, directory / 'contract.json', (directory / 'patches/correct.diff').read_text(), store=store)
    assert report['decision'] == 'READY_FOR_REVIEW', report['gaps']
    assert report['candidates'][0]['fuzzing']['additional_executions'] == 64
    assert replay(report['id'], 'legitimate', store=store)['check']['status'] == 'PASS'
    reviewed = review(report['id'], 'approve', 'test operator', 'verified fixture', store=store)
    assert store.load(reviewed['id'])['identity_verified'] is False
    candidate = report['candidates'][0]
    for label in ['incomplete', 'insecure-alternative', 'functionality-breaking']:
        rejected = run(directory, directory / 'contract.json', (directory / f'patches/{label}.diff').read_text(), store=store)
        assert rejected['decision'] != 'READY_FOR_REVIEW'


def test_stale_review_refused(tmp_path):
    store = Store(tmp_path)
    report = {'id': 'b' * 32, 'created': 'today', 'scenario': 'fixture', 'decision': 'READY_FOR_REVIEW', 'bindings': {}}
    store.save(report, {})
    with pytest.raises(ValueError):
        review(report['id'], 'approve', 'operator', 'reason', store=store)
