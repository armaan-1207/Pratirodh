"""Fast operator-reported replacement candidates, verified like model diffs."""
from .patching import make_diff


def propose(files, editable, replacements):
    if not isinstance(replacements, list) or not 0 < len(replacements) <= 20:
        raise ValueError('template requires one to twenty exact replacements')
    updated = dict(files)
    for item in replacements:
        name = item['file']
        if name not in editable or not item.get('find') or files[name].count(item['find']) != 1:
            raise ValueError('template source pattern unavailable or outside edit policy')
        updated[name] = updated[name].replace(item['find'], item['replace'], 1)
    return make_diff(files, updated)
