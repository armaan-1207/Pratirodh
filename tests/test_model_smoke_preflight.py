"""Smoke evaluation must preserve an honest outcome before contacting a model."""
import importlib.util
import json
from pathlib import Path
import sys


def test_low_memory_records_block_without_contacting_runtime(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'scripts/evaluate_local_prototype.py'
    spec = importlib.util.spec_from_file_location('smoke_evaluator', path)
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    output = tmp_path / 'smoke'
    monkeypatch.setattr(sys, 'argv', ['evaluate', '--output', str(output)])
    monkeypatch.setattr(evaluator, 'available_memory_gb', lambda: 2.5)
    def forbidden(*args, **kwargs):
        raise AssertionError('resource preflight must precede runtime access')
    monkeypatch.setattr(evaluator.shutil, 'which', forbidden)
    assert evaluator.main() == 2
    report = json.loads((output / 'summary.json').read_text())
    assert report['status'] == 'MEMORY_PREFLIGHT_BLOCKED'
    assert report['runs'] == []
    assert report['available_memory_gb'] == 2.5
