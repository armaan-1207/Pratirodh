import difflib
import os
from pathlib import Path

import pytest

from pratirodh.contracts import load_contract
from pratirodh.engine import run
from pratirodh.evidence import Store
from pratirodh.mutations import construct

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'benchmark/scenarios/cwe-22-development-01'
SOURCE = '''from flask import Flask, request
from pathlib import Path
app = Flask(__name__)
ROOT = Path(__file__).parent
@app.route('/documents', methods=['GET'])
def documents():
    name = request.args.get('file', '')
    root = (ROOT / 'public').resolve()
    requested = root / name
    try:
        canonical_path = requested.resolve()
        if canonical_path.is_relative_to(root):
            return canonical_path.read_text(encoding='utf-8')
        else:
            return 'Access denied', 403
    except (FileNotFoundError, IsADirectoryError):
        return 'Missing', 404
'''


def test_structural_mutations_refuse_ambiguous_or_unreviewed_shapes():
    mutations = load_contract(CASE / 'contract.json')['mutations']
    for mutation in mutations:
        assert construct(SOURCE, mutation, 'CWE-89')[0] is None
        assert construct(SOURCE + '\n' + SOURCE, mutation, 'CWE-22')[0] is None
        assert construct(SOURCE, dict(mutation, replace='unreviewed'), 'CWE-22')[0] is None
    assert construct(SOURCE.replace('requested.resolve()', 'requested'), mutations[1], 'CWE-22')[0] is None


@pytest.mark.parametrize('negative', [False, True])
def test_renamed_path_repair_qualifies_both_mutations_in_docker(tmp_path, negative):
    if os.getenv('PRATIRODH_DOCKER_TESTS') != '1':
        pytest.skip('enable Docker integration explicitly')
    source = SOURCE
    if negative:
        source = source.replace("if canonical_path.is_relative_to(root):\n            return canonical_path.read_text(encoding='utf-8')\n        else:\n            return 'Access denied', 403",
                                "if not canonical_path.is_relative_to(root):\n            return 'Access denied', 403\n        return canonical_path.read_text(encoding='utf-8')")
    original = (CASE / 'app.py').read_text(encoding='utf-8')
    patch = ''.join(difflib.unified_diff(original.splitlines(True), source.splitlines(True), fromfile='a/app.py', tofile='b/app.py'))
    report = run(CASE, CASE / 'contract.json', patch=patch, store=Store(tmp_path / 'store'))
    assert report['decision'] == 'READY_FOR_REVIEW', report['gaps']
    mutations = report['candidates'][0]['mutations']
    assert len(mutations) == 2
    assert all(m['status'] == 'CONFIRMED_UNSAFE' and not m['missed_after'] for m in mutations)
    assert all(m['witness']['case']['id'] == 'probe-symlink' for m in mutations)
    assert all(m['construction'] == 'reviewed-python-path-ast-v1' for m in mutations)
