import pytest

from pratirodh.projects.model import context


def test_large_files_and_later_source_are_identified_without_audit_leakage():
    files = {'large.py': 'value = 1\n' * 2000,
             'second.py': 'security_relevant = True\n',
             'tests/test_hidden.py': 'PROTECTED_AUDIT_SENTINEL'}
    manifest = {'editable': ['large.py', 'second.py'], 'properties': [],
                'context_lines': {'large.py': 1000}}
    prompt = context(files, manifest, {})
    assert prompt.startswith('SOURCE_CONTEXT_MODE=EXACT_PATCH\n')
    assert 'FILE large.py sha256:' in prompt
    assert 'PARTIAL FILE lines 1000-' in prompt
    assert 'FILE second.py sha256:' in prompt
    assert 'security_relevant = True' in prompt
    assert 'PROTECTED_AUDIT_SENTINEL' not in prompt
    assert len(prompt.encode()) <= 24000


def test_oversized_line_is_explicit_failure_instead_of_empty_source():
    with pytest.raises(ValueError, match='source line exceeds excerpt allowance'):
        context({'large.js': 'x' * 20000}, {'editable': ['large.js'], 'properties': []}, {})


def test_invalid_excerpt_location_does_not_hide_source():
    manifest = {'editable': ['large.py'], 'properties': [], 'context_lines': {'large.py': 99999}}
    with pytest.raises(ValueError, match='invalid reviewed source excerpt location'):
        context({'large.py': 'x = 1\n' * 4000}, manifest, {})
