"""Restart must reuse trustworthy evidence and never repair a corrupted store."""
import importlib.util
import json
from pathlib import Path

import pytest

from pratirodh.evidence import Store

spec = importlib.util.spec_from_file_location('start_demo', Path(__file__).parents[1] / 'scripts/start_demo.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def signed_store(tmp_path):
    store = Store(tmp_path / 'evidence')
    store.save({'id': 'a' * 32, 'created': '2026-10-09T00:00:00Z',
                'decision': 'INSUFFICIENT_EVIDENCE'}, {'notes.txt': 'test record'})
    return store


def test_restart_reuses_verified_store_and_fresh_preserves_it(tmp_path):
    store = signed_store(tmp_path)
    verified, count = launcher.verified_store(store.root)
    launcher.remember_store(tmp_path, verified)
    assert count == 1
    assert launcher.selected_store(tmp_path) == store.root
    assert launcher.selected_store(tmp_path, fresh=True) is None
    assert launcher.verified_store(store.root)[1] == 1


def test_invalid_store_never_creates_or_repairs_files(tmp_path):
    missing = tmp_path / 'missing'
    with pytest.raises(ValueError, match='missing'):
        launcher.verified_store(missing)
    assert not missing.exists()
    store = signed_store(tmp_path)
    report = store.run_path('a' * 32) / 'report.json'
    report.chmod(0o600)
    report.write_text('{}')
    before = {p.relative_to(store.root): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    with pytest.raises(ValueError, match='verification failed'):
        launcher.verified_store(store.root)
    assert before == {p.relative_to(store.root): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}


def test_corrupt_launcher_state_requires_explicit_selection(tmp_path):
    (tmp_path / 'run_output').mkdir()
    (tmp_path / 'run_output/launcher-state.json').write_text(json.dumps({'version': 1, 'store': '../untrusted'}))
    with pytest.raises(ValueError, match='saved launcher state'):
        launcher.selected_store(tmp_path)
    assert launcher.selected_store(tmp_path, explicit=tmp_path / 'chosen') == tmp_path / 'chosen'


def test_unindexed_records_are_rejected(tmp_path):
    store = signed_store(tmp_path)
    (store.root / 'runs' / ('b' * 32)).mkdir()
    with pytest.raises(ValueError, match='verification failed'):
        launcher.verified_store(store.root)


def test_demo_preparation_preserves_model_and_explicit_choice_replaces_it(tmp_path):
    first = signed_store(tmp_path / 'first')
    second = signed_store(tmp_path / 'second')
    launcher.remember_store(tmp_path, first, 'qwen2.5-coder:7b')
    launcher.remember_store(tmp_path, second)
    state = json.loads((tmp_path / 'run_output/launcher-state.json').read_text())
    assert state['store'] == str(second.root)
    assert state['model'] == 'qwen2.5-coder:7b'
    launcher.remember_store(tmp_path, second, 'another-installed-model')
    assert json.loads((tmp_path / 'run_output/launcher-state.json').read_text())['model'] == 'another-installed-model'
