"""Local reference-fix demonstration; never grants upstream qualification."""
import json
from pathlib import Path
import subprocess

from .manifest import inspect, load
from .patching import make_diff
from .engine import run_project
from ..evidence import digest

CASE = 'python-cve-2018-18074'
IMAGE_TAG = 'pratirodh-requests-demo:0.2'
ROOT = Path(__file__).resolve().parents[2]
SOURCE_REVISION = 'dd754d13de250a6af8a68a6a83a8b4419fd429c6'
FIX_REVISION = 'c45d7c49ea75133e52ab22a8e9e13173938e36ff'


def prepare(root, image):
    """Copy a validated, reduced source snapshot without changing acquisition."""
    acquisition = ROOT / 'run_output/upstream-acquisition' / CASE / 'upstream'
    def blob(revision, path='requests/sessions.py'):
        return subprocess.run(['git', '-C', str(acquisition), 'show', revision + ':' + path],
            capture_output=True, text=True, encoding='utf-8', check=True, timeout=30).stdout.replace('\r\n', '\n')
    vulnerable = blob(SOURCE_REVISION)
    corrected = blob(FIX_REVISION)
    mutation = {'family': 'port-scheme-check-removed', 'file': 'requests/sessions.py',
        'property': 'auth_header_stripped_on_redirect',
        'find': 'return old_parsed.port != new_parsed.port or old_parsed.scheme != new_parsed.scheme',
        'replace': 'return False'}
    if corrected.count(mutation['find']) != 1:
        raise ValueError('reference fix does not match the declared mutation')
    paths = subprocess.check_output(['git', '-C', str(acquisition), 'ls-tree', '-r', '--name-only',
        SOURCE_REVISION, '--', 'requests'], text=True, encoding='utf-8', timeout=30).splitlines()
    if not paths or len(paths) > 100:
        raise ValueError('unexpected pinned Requests package inventory')
    files = {name: blob(SOURCE_REVISION, name) for name in paths if name.endswith('.py')}
    files['requests/sessions.py'] = vulnerable
    files['LICENSE'] = blob(SOURCE_REVISION, 'LICENSE')
    files['tests/test_harness.py'] = Path(__file__).with_name('requests_redirect_harness.py').read_text(encoding='utf-8')
    files['setup.cfg'] = '[metadata]\nname = pratirodh-requests-reference-demo\n'
    provenance = {'case': CASE, 'repository': 'https://github.com/psf/requests',
        'vulnerable_revision': SOURCE_REVISION, 'fix_revision': FIX_REVISION,
        'source_sha256': digest(vulnerable), 'reference_fix_sha256': digest(corrected),
        'scope': 'Reduced upstream library snapshot, supplied reference fix, local Docker demo; no independent audit',
        'adaptations': ['Only Requests package, license and harness are copied; acquisition is preserved.',
            'In-memory HTTP transport; no TLS/network claim.', 'urllib3 1.26.20 for Python 3.11 compatibility; chardet 3.0.4, idna 2.10, certifi 2024.8.30.']}
    files['upstream-provenance.json'] = json.dumps(provenance, indent=2) + '\n'
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8', newline='\n')
    definition = inspect(root)
    definition.update(status='OPERATOR_APPROVED_REFERENCE_DEMO', image=image,
        worker={'mode': 'demo', 'context': 'default'}, demo_scope=provenance,
        dependencies={'prepared': True, 'image_digest': image,
            'resolved': {'urllib3': '1.26.20', 'chardet': '3.0.4', 'idna': '2.10', 'certifi': '2024.8.30'}})
    definition['commands']['build'] = [['python', '-c',
        "import ast,pathlib; [ast.parse(p.read_text()) for p in pathlib.Path('requests').rglob('*.py')]"]]
    definition['commands']['test'] = [['python', 'tests/test_harness.py', 'control']]
    definition['editable'] = ['requests/sessions.py']
    definition['properties'] = [{'id': mutation['property'], 'kind': 'data-isolation',
        'description': 'Credentials must stop at scheme downgrade and same-host port changes',
        'provenance': {'kind': 'operator', 'reference': 'PRATIRODH Requests redirect contract v1', 'approved': True},
        'target_files': ['requests/sessions.py'],
        'harness_review': {'approved': True, 'reference': 'In-memory transport exercises pinned Requests redirect logic and inspects target headers'},
        'control': {'command': ['python', 'tests/test_harness.py', 'control'], 'exit': 0, 'stdout': 'CONTROL_PASS\n'},
        'reproducer': {'command': ['python', 'tests/test_harness.py', 'reproducer'], 'exit': 0, 'stdout': 'SAFE\n',
            'violation': {'exit': 1, 'stdout': 'VIOLATION\n'}},
        'variations': [{'command': ['python', 'tests/test_harness.py', 'variation'], 'exit': 0, 'stdout': 'SAFE\n'}]}]
    definition['mutations'] = [mutation]
    definition['model_analysis'] = definition['generate_harnesses'] = False
    # The manifest requires a positive cap. Supplied patches and disabled model
    # features guarantee zero actual calls; the report records observed usage.
    definition['limits'].update(model_calls=1, candidates=1)
    manifest_path = root / 'pratirodh-project.json'
    manifest_path.write_text(json.dumps(definition, indent=2) + '\n', encoding='utf-8')
    load(root, manifest_path)
    fixed = dict(files, **{'requests/sessions.py': corrected})
    incomplete = dict(files, **{'requests/sessions.py': corrected.replace(mutation['find'], mutation['replace'], 1)})
    return manifest_path, make_diff(files, incomplete), make_diff(files, fixed)


def run_demo(root, store, image, cancelled=None, progress=None, result_callback=None):
    manifest, incomplete, fixed = prepare(root, image)
    rows = []
    for label, patch, expected in [('Incomplete redirect repair', incomplete, 'REJECT'),
                                   ('Upstream reference fix', fixed, 'READY_FOR_REVIEW')]:
        if cancelled is not None and cancelled.is_set():
            break
        report = run_project(root, manifest, workflow='repair', patch=patch, store=store,
            allow_demo=True, cancelled=cancelled,
            progress=(lambda stage, label=label: progress(label + ' · ' + stage)) if progress else None)
        row = {'label': label, 'id': report['id'], 'decision': report['decision'],
            'expected': expected, 'matched_expectation': report['decision'] == expected}
        rows.append(row)
        if result_callback:
            result_callback(row)
    return rows
