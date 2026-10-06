"""Test command wiring using inert fixtures, without importing upstream FATE."""
import ast
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "benchmark/recipes/python-cve-2020-25459"


@pytest.mark.parametrize("mode,expected", [
    ("control", "CONTROL_PASS\n"),
    ("security", "SECURITY_PASS\n"),
    ("variation", "VARIATION_PASS\n"),
])
def test_runner_success_has_exact_output(tmp_path, mode, expected):
    result = run_fixture(tmp_path, "def test_legitimate(): pass\n"
                         "def test_leak_blocked(): print('target logging')\n"
                         "def test_variation(): pass\n", mode)
    assert result.returncode == 0
    assert result.stdout == expected


def run_fixture(tmp_path, source, mode="security"):
    runner = tmp_path / "run_data_leak_audit.py"
    runner.write_bytes((CASE / "audit/run_data_leak_audit.py").read_bytes())
    (tmp_path / "test_data_leak_audit.py").write_text(source, encoding="utf-8")
    return subprocess.run([sys.executable, str(runner), mode], cwd=tmp_path,
                          text=True, capture_output=True, timeout=5)


def test_expected_violation_is_distinct_from_harness_error(tmp_path):
    result = run_fixture(tmp_path, "def test_leak_blocked():\n    assert False, 'Weight leaked'\n")
    assert (result.returncode, result.stdout) == (1, "SECURITY_VIOLATION\n")


@pytest.mark.parametrize("source", [
    "raise ImportError('missing dependency')\n",
    "def test_leak_blocked():\n    assert False, 'unrelated failure'\n",
    "def test_leak_blocked():\n    raise RuntimeError('broken harness')\n",
    "def other_function(): pass\n",
])
def test_harness_failures_do_not_count_as_violation(tmp_path, source):
    result = run_fixture(tmp_path, source)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "HARNESS_ERROR:" in result.stderr


def test_case_commands_resolve_and_authoring_preserves_them():
    import importlib.util
    spec = importlib.util.spec_from_file_location("case_author", ROOT / "archive/upstream-tools/author_upstream_manifests.py")
    author = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(author)
    definition = author.HARNESSES[CASE.name]
    manifest = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
    audit = json.loads((CASE / "audit.json").read_text(encoding="utf-8"))
    assert manifest["properties"] == definition["properties"]
    assert manifest["mutations"] == definition["mutations"]
    assert audit["checks"] == definition["audit_checks"]
    for prop in manifest["properties"]:
        for assertion in [prop["control"], prop["reproducer"], *prop["variations"]]:
            assert (CASE / "overlay" / assertion["command"][1]).is_file()
    for check in audit["checks"]:
        assert check["command"][1] in audit["files"]
    for body in audit["files"].values():
        ast.parse(body)
    recipe = json.loads((CASE / "recipe.json").read_text(encoding="utf-8"))
    assert recipe["harness_files"]["tests/run_data_leak.py"] == (CASE / "overlay/tests/run_data_leak.py").read_text(encoding="utf-8")
    assert "path_traversal" not in json.dumps(manifest["properties"])
