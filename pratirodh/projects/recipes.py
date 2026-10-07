"""Validate reviewed recipe completeness before starting costly workers."""
import json
from pathlib import Path
from .manifest import load, argv, oracle
from .evaluation import DEFAULT_BUDGET


def validate_recipe(recipe, base):
    if recipe.get('approved') is not True or not recipe.get('adaptations'):
        raise ValueError('recipe requires explicit approval and adaptation disclosure')
    if 'PENDING' in json.dumps(recipe):
        raise ValueError('recipe contains unresolved PENDING entries')
    base = Path(base).resolve()
    for name in ('target', 'manifest', 'audit'):
        path = (base / recipe[name]).resolve()
        if not path.is_relative_to(base):
            raise ValueError('recipe input escapes its directory')
    manifest, files = load(base / recipe['target'], base / recipe['manifest'])
    if any(manifest['limits'][k] != v for k, v in DEFAULT_BUDGET.items()):
        raise ValueError('recipe must use the equal 600/180-second attempt budget')
    if not manifest['properties'] or not manifest['mutations']:
        raise ValueError('reviewed properties and mutation challenges are required')
    if set(recipe.get('source_map', {})) != set(manifest['editable']):
        raise ValueError('source mapping must cover every editable file')
    review = recipe.get('license_review', {})
    if review.get('approved') is not True or not review.get('identifier') or not review.get('files'):
        raise ValueError('recorded license review and files are required')
    audit_path = (base / recipe['audit']).resolve()
    if audit_path.is_relative_to((base / recipe['target']).resolve()):
        raise ValueError('audit inputs must remain outside model-visible target')
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    checks = audit.get('checks', [])
    if not {'control', 'security'} <= {c.get('role') for c in checks} or not audit.get('files'):
        raise ValueError('separate behavioral audit harness, controls and security checks required')
    for check in checks:
        argv(check['command'])
        oracle(check)
        if check['role'] == 'security':
            oracle(check.get('violation', {}))
    if set(audit['files']) & files.keys():
        raise ValueError('audit harness must not replace target files')
    return manifest
