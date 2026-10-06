import json
from datetime import datetime, timezone, timedelta

from pratirodh.upstream_status import load_status


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')


def test_consolidated_cohort_is_visible_without_removed_manifest(tmp_path):
    write(tmp_path, 'benchmark/upstream-cohort.json', {'cohort': 'upstream-v2', 'cases': [
        {'id': 'python-cve-example', 'split': 'evaluation', 'repository_url': 'https://github.com/example/project'}]})
    write(tmp_path, 'run_output/upstream-validation/preparation.json', {
        'updated': datetime.now(timezone.utc).isoformat(),
        'summary': {'total': 1, 'structurally_ready': 1}})
    status = load_status(tmp_path)
    assert len(status['cases']) == 1
    assert status['preparation']['summary']['structurally_ready'] == 1
    assert status['qualified'] == status['accepted'] == 0
    assert status['scheduled'] == 12
    assert status['signature_verified'] is False


def test_worker_power_uses_each_vm_and_expires(tmp_path):
    write(tmp_path, 'run_output/azure-validation/attestations.json', {'workers': [
        {'role': 'Model controller'}, {'role': 'Execution'}, {'role': 'Final audit'}]})
    power = {'status': 'OBSERVED', 'updated': datetime.now(timezone.utc).isoformat(), 'observations': [
        {'name': 'pratirodh-model', 'state': 'VM deallocated'},
        {'name': 'pratirodh-execution', 'state': 'VM running'},
        {'name': 'pratirodh-audit', 'state': 'VM running'}]}
    write(tmp_path, 'run_output/azure-validation/power-state.json', power)
    assert [w['status'] for w in load_status(tmp_path)['workers']] == ['VM deallocated', 'VM running', 'VM running']
    power['updated'] = (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat()
    write(tmp_path, 'run_output/azure-validation/power-state.json', power)
    assert all(w['status'] == 'STALE_OBSERVATION' for w in load_status(tmp_path)['workers'])


def test_model_readiness_uses_its_own_observation_and_expires(tmp_path):
    write(tmp_path, 'run_output/azure-validation/attestations.json', {'workers': [
        {'role': 'Model controller', 'status': 'PREFLIGHT_PASS'}]})
    now = datetime.now(timezone.utc)
    write(tmp_path, 'run_output/upstream-validation/model-preflight.json', {
        'role': 'model', 'status': 'PASS', 'observed_at': now.isoformat(), 'inference_validated': True})
    worker = load_status(tmp_path)['workers'][0]
    assert worker['attestation_status'] == 'PASS'
    assert worker['identity']['inference_validated'] is True
    write(tmp_path, 'run_output/upstream-validation/model-preflight.json', {
        'role': 'model', 'status': 'PASS', 'observed_at': (now - timedelta(minutes=6)).isoformat()})
    assert load_status(tmp_path)['workers'][0]['attestation_status'] == 'HISTORICAL_IDENTITY'
