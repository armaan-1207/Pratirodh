"""Failure controls for the operator's isolated deployment verifier."""
from types import SimpleNamespace
import subprocess
import sys
import pytest

from tools import verify_local_deployment as verification


def test_optimized_python_refuses_to_emit_success():
    result = subprocess.run([sys.executable, '-O', verification.__file__, '--help'],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert 'deployment verification requires assertions' in result.stderr
    assert '"PASS"' not in result.stdout


def test_docker_errors_never_echo_environment_credentials(monkeypatch):
    monkeypatch.setattr(verification.subprocess, 'run', lambda *a, **k:
                        SimpleNamespace(returncode=1, stdout='private', stderr='password-secret'))
    with pytest.raises(RuntimeError, match='Docker operation failed: run') as failure:
        verification.docker('run', '-e', 'PRATIRODH_PASSWORD=password-secret')
    assert 'password-secret' not in str(failure.value)


def test_alert_collector_delivers_one_sanitized_threshold_alert():
    receipt = verification.alert_delivery()
    assert receipt['delivered'] == 1 and receipt['sanitized']
    assert receipt['threshold'] == 5
    assert 'public delivery not configured' in receipt['scope']
