"""Exercise generated inputs through the evaluator without running workers."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from pratirodh.projects.evaluation import freeze
from pratirodh.projects.examples import create_example

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('generate_campaign', ROOT / 'scripts/generate_campaign.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def write(path, data):
    path.write_text(json.dumps(data), encoding='utf-8')


@pytest.fixture
def inputs(tmp_path):
    case = tmp_path / 'recipes/python-fixture'
    manifest_path, _ = create_example(case / 'target', 'python', 'sha256:' + 'a' * 64, 'execution-worker')
    manifest_path.rename(case / 'manifest.json')
    recipe = {'case': case.name, 'approved': True, 'target': 'target', 'manifest': 'manifest.json',
              'audit': 'audit.json', 'source_revision': 'a' * 40, 'fix_revision': 'b' * 40,
              'license_review': {'approved': True, 'identifier': 'MIT'}, 'adaptations': 'Synthetic test only'}
    write(case / 'recipe.json', recipe)
    write(case / 'audit.json', {'context': 'audit-worker', 'files': {'audit.py': 'assert True\n'},
                              'checks': [{'command': ['python', 'audit.py'], 'exit': 0, 'stdout': ''}]})
    cohort = {'version': 1, 'cohort': 'synthetic-test', 'cases': [{'id': case.name, 'split': 'evaluation',
              'repository_url': 'https://example.invalid/repo', 'advisory_url': 'https://example.invalid/advisory',
              'fix_url': 'https://example.invalid/repo/commit/' + 'b' * 40, 'fix_revision': 'b' * 40}]}
    cohort_path = tmp_path / 'cohort.json'
    write(cohort_path, cohort)
    return case, cohort_path, tmp_path / 'campaign.json'


def test_generated_campaign_freezes_without_execution(inputs):
    case, cohort, output = inputs
    data = generator.build_campaign(case.parent, cohort, output)
    write(output, data)
    frozen = freeze(output)
    assert frozen['cases'][0]['source_revision'] == data['cases'][0]['source_revision']
    assert data['cases'][0]['source_revision'] != 'b' * 40
    assert frozen['complete_24_case_cohort'] is False
    assert data['qualification'] == 'NOT_CHECKED'
    assert data['release_complete'] is False
    for field in ('manifest', 'audit'):
        path = output.parent / data['cases'][0][field]
        assert data['cases'][0][field + '_digest'] == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize('problem', ['duplicate', 'unknown-case', 'unapproved-license', 'wrong-fix',
                                     'missing-audit', 'escaping-target', 'wrong-adapter'])
def test_bad_inputs_fail_before_output(inputs, problem):
    case, cohort_path, output = inputs
    cohort = json.loads(cohort_path.read_text())
    recipe = json.loads((case / 'recipe.json').read_text())
    if problem == 'duplicate':
        cohort['cases'].append(cohort['cases'][0])
    elif problem == 'unknown-case':
        cohort['cases'][0]['id'] = 'python-absent'
    elif problem == 'unapproved-license':
        recipe['license_review']['approved'] = False
    elif problem == 'wrong-fix':
        recipe['fix_revision'] = 'c' * 40
    elif problem == 'missing-audit':
        (case / 'audit.json').unlink()
    elif problem == 'escaping-target':
        recipe['target'] = '../other'
    else:
        manifest = json.loads((case / 'manifest.json').read_text())
        manifest['adapter'] = 'cpp'
        write(case / 'manifest.json', manifest)
    write(cohort_path, cohort)
    write(case / 'recipe.json', recipe)
    with pytest.raises((ValueError, FileNotFoundError)):
        generator.build_campaign(case.parent, cohort_path, output)
    assert not output.exists()


def test_cli_works_outside_repository_and_is_repeatable(inputs, tmp_path):
    case, cohort, output = inputs
    command = [sys.executable, str(ROOT / 'scripts/generate_campaign.py'), '--recipes', str(case.parent),
               '--cohort', str(cohort), '--output', str(output)]
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    before = output.read_bytes()
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert output.read_bytes() == before
    recipe = json.loads((case / 'recipe.json').read_text())
    recipe['approved'] = False
    write(case / 'recipe.json', recipe)
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert output.read_bytes() == before


def test_real_cohort_preserves_assignments_and_pinned_preparation_inputs():
    cohort = json.loads((ROOT / 'benchmark/upstream-cohort.json').read_text(encoding='utf-8'))
    records = cohort['cases']
    expected = {'python-cve-2021-21330', 'python-cve-2022-0767', 'javascript-cve-2021-37712',
                'javascript-cve-2021-23369', 'cpp-cve-2023-50472', 'cpp-cve-2018-25032'}
    assert {c['id'] for c in records if c['split'] == 'development'} == expected
    assert len(records) == 24
    for record in records:
        directory = ROOT / 'benchmark/recipes' / record['id']
        recipe = json.loads((directory / 'recipe.json').read_text(encoding='utf-8'))
        source = json.loads((directory / 'target-source.json').read_text(encoding='utf-8'))
        assert source['repository'] == record['repository_url']
        assert source['fix_revision'] == record['fix_revision'] == recipe['fix_revision']
        assert recipe['target'] == 'prepared/target'
        assert (directory / 'source-manifest.json').is_file()
        assert (directory / recipe['audit']).is_file()
        assert recipe['integration_scope'].endswith('runtime qualification not established')
