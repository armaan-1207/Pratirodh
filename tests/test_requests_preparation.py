"""Preparation must preserve pinned source and reject missing inputs."""
from pathlib import Path
import json
import subprocess

import pytest
from pratirodh.projects import requests_demo as demo
from pratirodh.projects.manifest import load


def test_prepare_reduces_source_and_preserves_acquisition(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, 'ROOT', tmp_path)
    source = 'def redirect():\n    return False\n'
    fixed = 'def redirect():\n    return old_parsed.port != new_parsed.port or old_parsed.scheme != new_parsed.scheme\n'
    def git_run(args, **kwargs):
        revision, name = args[-1].split(':', 1)
        body = 'Upstream license\n' if name == 'LICENSE' else fixed if revision == demo.FIX_REVISION else source
        return subprocess.CompletedProcess(args, 0, stdout=body)
    monkeypatch.setattr(demo.subprocess, 'run', git_run)
    monkeypatch.setattr(demo.subprocess, 'check_output', lambda *a, **kw: 'requests/sessions.py\n')
    path, incomplete, corrected = demo.prepare(tmp_path / 'prepared', 'sha256:' + 'a' * 64)
    manifest, files = load(path.parent, path)
    assert files['requests/sessions.py'] == source
    assert manifest['editable'] == ['requests/sessions.py']
    assert 'pip._vendor' not in files['tests/test_harness.py']
    assert "s.trust_env = False" in files['tests/test_harness.py']
    assert 'wrong Requests source imported' in files['tests/test_harness.py']
    assert 'types.ModuleType' not in files['tests/test_harness.py']
    provenance = json.loads(files['upstream-provenance.json'])
    assert provenance['vulnerable_revision'] == demo.SOURCE_REVISION
    assert provenance['fix_revision'] == demo.FIX_REVISION
    assert corrected and incomplete == ''  # weakened fake fix equals this test's original
    with pytest.raises(FileExistsError):
        demo.prepare(path.parent, 'sha256:' + 'a' * 64)


def test_missing_acquisition_does_not_create_a_demo_target(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, 'ROOT', tmp_path)
    def unavailable(*a, **kw):
        raise subprocess.CalledProcessError(128, a[0])
    monkeypatch.setattr(demo.subprocess, 'run', unavailable)
    target = tmp_path / 'prepared'
    with pytest.raises(subprocess.CalledProcessError):
        demo.prepare(target, 'sha256:' + 'a' * 64)
    assert not target.exists()
