import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pratirodh.projects.manifest import inventory
from pratirodh.projects.recipes import validate_recipe

base = ROOT / 'benchmark/recipes/python-cve-2018-18074'
target = base / 'target'

# Ensure binary non-UTF8 files are excluded from target
for bin_file in [target / "ext/requests-logo.ai", target / "docs/_static/requests-logo-small.png", target / "docs/_static/requests-sidebar.png"]:
    if bin_file.exists():
        bin_file.unlink()

harness_path = base / 'overlay/tests/test_harness.py'
with open(harness_path, 'r', encoding='utf-8') as f:
    harness_text = f.read()

audit_path = base / 'audit/test_redirects_audit.py'
with open(audit_path, 'r', encoding='utf-8') as f:
    audit_text = f.read()

# Ensure overlay and target have normalized LF
with open(harness_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(harness_text)
with open(target / 'tests/test_harness.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(harness_text)
with open(audit_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(audit_text)

# Run inventory
files, hashes, rev = inventory(target)

# Update recipe.json
recipe = json.loads((base / 'recipe.json').read_text(encoding='utf-8'))
recipe['harness_files'] = {'tests/test_harness.py': harness_text}
(base / 'recipe.json').write_text(json.dumps(recipe, indent=2) + '\n', encoding='utf-8')

# Build manifest.json
manifest = {
  'version': 2,
  'adapter': 'python',
  'revision': rev,
  'inventory': hashes,
  'image': 'sha256:b8386eea9d7bb2898e9e2a342232ddd220bef78c91b1576886b436f2065fa558',
  'worker': {'mode': 'dedicated', 'context': 'pratirodh-execution'},
  'commands': {
    'build': [['python', '-c', "import ast,pathlib; [ast.parse(p.read_text()) for p in pathlib.Path('.').rglob('*.py') if p.name != 'conftest.py']"]],
    'test': [['python', 'tests/test_harness.py', 'control']],
    'startup': []
  },
  'editable': ['requests/sessions.py'],
  'properties': [
    {
      'id': 'auth_header_stripped_on_redirect',
      'kind': 'data-isolation',
      'description': 'Authorization header must not be forwarded to a different origin or downgraded scheme on HTTP redirect',
      'provenance': {
        'kind': 'operator',
        'reference': 'PRATIRODH python-cve-2018-18074 intake recipe',
        'approved': True
      },
      'target_files': ['requests/sessions.py'],
      'harness_review': {
        'approved': True,
        'reference': 'Deterministic transport adapter verifies Authorization header stripping on scheme downgrade and port change while preserving same-origin auth and HTTP->HTTPS upgrade'
      },
      'control': {
        'command': ['python', 'tests/test_harness.py', 'control'],
        'exit': 0,
        'stdout': 'CONTROL_PASS\n'
      },
      'reproducer': {
        'command': ['python', 'tests/test_harness.py', 'reproducer'],
        'exit': 0,
        'stdout': 'SAFE\n',
        'violation': {'exit': 1, 'stdout': 'VIOLATION\n'}
      },
      'variations': [
        {
          'command': ['python', 'tests/test_harness.py', 'variation'],
          'exit': 0,
          'stdout': 'SAFE\n'
        }
      ]
    }
  ],
  'mutations': [
    {
      'family': 'port-scheme-check-removed',
      'file': 'requests/sessions.py',
      'property': 'auth_header_stripped_on_redirect',
      'find': 'return old_parsed.port != new_parsed.port or old_parsed.scheme != new_parsed.scheme',
      'replace': 'return False'
    }
  ],
  'formal': [],
  'limits': {
    'seconds': 600,
    'reserve_seconds': 180,
    'model_calls': 2,
    'candidates': 3,
    'command_seconds': 120,
    'memory_mb': 2048,
    'cpus': 2,
    'pids': 64,
    'disk_mb': 256,
    'output_bytes': 65536
  },
  'dependencies': {
    'prepared': True,
    'image_digest': 'sha256:b8386eea9d7bb2898e9e2a342232ddd220bef78c91b1576886b436f2065fa558',
    'resolved': {}
  },
  'model': {
    'profile': 'laptop',
    'runtime': 'ollama',
    'endpoint': 'http://127.0.0.1:11434',
    'name': 'qwen2.5-coder:7b',
    'weights_digest': 'sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364',
    'runtime_digest': 'sha256:0b0650a962dda61ec0598141ea11e3b688d225e926c9c00bc2c299d0ed34c4f8',
    'quantization': 'Q4_K_M',
    'available_memory_gb': 8,
    'preflight_latency_seconds': None
  }
}
(base / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

# Build audit.json
audit = {
  'context': 'pratirodh-audit',
  'image': 'sha256:24be6e5fdc4850e26b87586e8baf25cabd3e623021b18e2aaa53e4163f1db8e4',
  'files': {
    'test_redirects_audit.py': audit_text
  },
  'checks': [
    {
      'role': 'control',
      'command': ['python', 'test_redirects_audit.py', 'control'],
      'exit': 0,
      'stdout': 'CONTROL_PASS\n'
    },
    {
      'role': 'security',
      'command': ['python', 'test_redirects_audit.py', 'security'],
      'exit': 0,
      'stdout': 'SAFE\n',
      'violation': {'exit': 1, 'stdout': 'VIOLATION\n'}
    }
  ]
}
(base / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')

print('Validating recipe ...')
validated = validate_recipe(recipe, base)
print('SUCCESS! Validated manifest revision:', validated['revision'])
