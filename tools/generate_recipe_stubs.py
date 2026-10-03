"""Generate pending qualification recipe stubs for all 24 upstream cases."""
import json
import os
from pathlib import Path

ROOT = Path('.')
manifest = json.load(open('benchmark/upstream-v2/manifest.json'))
cases = manifest['cases']

created = []
for case in cases:
    cid = case['id']
    acq_dir_v2 = ROOT / 'run_output' / 'upstream-acquisition-v2' / cid
    acq_dir = ROOT / 'run_output' / 'upstream-acquisition' / cid
    acq = acq_dir_v2 if acq_dir_v2.exists() else acq_dir

    prov_path = acq / 'provenance.json'
    if not prov_path.exists():
        print(f'MISSING provenance: {cid}')
        continue

    p = json.load(prov_path.open())
    recipe_dir = ROOT / 'benchmark' / 'recipes' / cid
    recipe_dir.mkdir(parents=True, exist_ok=True)
    recipe_path = recipe_dir / 'recipe.json'

    if recipe_path.exists():
        print(f'EXISTS (skip): {cid}')
        continue

    desc = case['cve'] + ' ' + case['project'] + ' (' + case['cwe'] + ')'
    stub = {
        'case': cid,
        'description': desc,
        'approved': False,
        'REVIEW_REQUIRED': 'Set approved=true after verifying controls, source map, and audit definitions',
        'adaptations': 'PENDING: Document source adaptations and harness approach',
        'license_review': {
            'identifier': 'PENDING',
            'files': [],
            'notes': 'Review license files in acquisition directory'
        },
        'source_revision': p.get('vulnerable_revision', 'PENDING'),
        'fix_revision': p.get('fixed_revision', 'PENDING'),
        'target': 'target',
        'manifest': 'manifest.json',
        'audit': 'audit.json',
        'source_map': {
            'PENDING': 'Map editable and protected paths with context_lines from intake review'
        },
        'dependency_constraints': {'PENDING': 'Pin all dependencies'},
        'resource_limits': {'cpu_seconds': 30, 'memory_mb': 256, 'network': 'loopback-only'},
        'controls': {
            'legitimate_behavior': ['PENDING'],
            'vulnerable_reproduction': ['PENDING'],
            'fixed_check': ['PENDING']
        }
    }
    recipe_path.write_text(json.dumps(stub, indent=2) + '\n')
    created.append(cid)

print('Created', len(created), 'recipe stubs')
