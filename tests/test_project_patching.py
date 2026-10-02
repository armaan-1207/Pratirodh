import pytest
from pratirodh.projects.patching import apply, make_diff, proposal_diff


@pytest.mark.parametrize('old,new', [('value = 1', 'value = 2'), ('value = 1\n', 'value = 2'), ('value = 1', 'value = 2\n')])
def test_diff_preserves_missing_terminal_newlines(old, new):
    files = {'module.py': old}
    patch = make_diff(files, {'module.py': new})
    assert apply(files, patch, ['module.py'])['module.py'] == new


def test_model_files_and_diff_use_same_patch_policy():
    original = {'app.py': 'value = 1\n', 'tests/test_app.py': 'assert True\n'}
    fixed = dict(original, **{'app.py': 'value = 2\n'})
    patch = make_diff(original, fixed)
    assert proposal_diff({'files': {'app.py': fixed['app.py']}}, original, ['app.py']) == patch
    assert proposal_diff({'patch': patch}, original, ['app.py']) == patch
    assert apply(original, patch, ['app.py']) == fixed
    with pytest.raises(ValueError, match='protected'):
        proposal_diff({'files': {'tests/test_app.py': 'assert False\n'}}, original, ['app.py'])
