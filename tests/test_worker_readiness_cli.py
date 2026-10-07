import json
import subprocess
import sys

from tools import check_campaign_workers as cli


def run_cli(tmp_path, monkeypatch):
    output = tmp_path / 'readiness.json'
    monkeypatch.setattr(sys, 'argv', ['check', '--execution-image', 'sha256:' + 'a' * 64,
        '--audit-image', 'sha256:' + 'b' * 64, '--output', str(output)])
    monkeypatch.setattr(cli.time, 'sleep', lambda seconds: None)
    result = cli.main()
    return result, json.loads(output.read_text())


def test_transport_retry_records_failure_before_pass(tmp_path, monkeypatch):
    calls = []
    def attest(context, image):
        calls.append(context)
        if len(calls) == 1:
            raise subprocess.CalledProcessError(255, ['ssh'], stderr='Connection timed out')
        return dict(context=context, image=image, status='PASS', daemon_id=context,
                    boot_id_digest=context, machine_id_digest=context)
    monkeypatch.setattr(cli, 'attest_worker', attest)
    result, data = run_cli(tmp_path, monkeypatch)
    assert result == 0
    assert len(data['workers'][0]['transport_failures']) == 1
    assert len(calls) == 3


def test_identity_mismatch_is_not_retried(tmp_path, monkeypatch):
    calls = []
    def attest(context, image):
        calls.append(context)
        raise ValueError('worker image identity mismatch')
    monkeypatch.setattr(cli, 'attest_worker', attest)
    result, data = run_cli(tmp_path, monkeypatch)
    assert result == 2
    assert data['status'] == 'BLOCKED'
    assert len(calls) == 2
