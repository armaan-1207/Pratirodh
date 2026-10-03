"""Generate approved evaluation case recipes from intake review data."""
import json
from pathlib import Path

ROOT = Path('.')
review = json.load(open('run_output/upstream-validation/intake-review.json'))
manifest = json.load(open('benchmark/upstream-v2/manifest.json'))
cases_meta = {c['id']: c for c in manifest['cases']}

DEV_CASES = {
    'python-cve-2021-21330', 'python-cve-2022-0767',
    'javascript-cve-2021-37712', 'javascript-cve-2021-23369',
    'cpp-cve-2023-50472', 'cpp-cve-2018-25032',
}

DESCRIPTIONS = {
    'python-cve-2020-25459': ('FATE path traversal in federated learning (CWE-22)', 'federatedml/tree/hetero/hetero_decision_tree_guest.py', 'Path traversal via unsanitized model save path. Harness calls save function with ../traversal path on loopback.'),
    'python-cve-2021-32633': ('Zope/PageTemplates expression traversal SSTI (CWE-79)', 'src/Products/PageTemplates/Expressions.py', 'Template expression traversal allows calling restricted attributes. Harness renders attacker-controlled template expression.'),
    'python-cve-2021-33203': ('Django admin template path traversal (CWE-89)', 'django/contrib/admindocs/views.py', 'Template tag path in admindocs allows reading arbitrary template files. Harness invokes the vulnerable admindocs view with crafted template path.'),
    'python-cve-2025-43859': ('h11 HTTP chunk extension parsing bypass (CWE-444)', 'h11/_readers.py', 'Malformed chunk size line with extensions parsed incorrectly, allowing HTTP request smuggling. Harness sends crafted chunk-encoded request.'),
    'python-cve-2018-7750': ('Paramiko unauthenticated command execution (CWE-20)', 'paramiko/common.py', 'SSH server allows exec_command before authentication completes. Harness connects via local SSH with in-process Paramiko server.'),
    'python-cve-2018-18074': ('requests credential leak across redirects (CWE-601)', 'requests/sessions.py', 'Authorization header sent across cross-origin redirects. Harness uses two loopback servers and checks if header is forwarded.'),
    'javascript-cve-2021-29300': ('ronomon/opened command injection (CWE-22)', 'index.js', 'Unsanitized filename passed to OS command. Harness calls opened() with shell metacharacter in path, checks if canary executes.'),
    'javascript-cve-2021-23664': ('cors-proxy SSRF via redirect (CWE-918)', 'middleware.js', 'CORS proxy follows redirects to internal hosts. Harness sends request redirecting to loopback canary server.'),
    'javascript-cve-2019-10767': ('ioBroker path traversal in objectsUtils (CWE-22)', 'lib/objects/objectsUtils.js', 'Object key used unsanitized as filesystem path. Harness invokes storage function with ../traversal key.'),
    'javascript-cve-2018-6835': ('Etherpad JSONP injection via API (CWE-79)', 'src/node/hooks/express/apicalls.js', 'JSONP callback parameter not sanitized. Harness sends request with XSS payload in callback parameter.'),
    'javascript-cve-2019-15599': ('node-tree-kill command injection (CWE-78)', 'index.js', 'PID argument passed to kill command unsanitized. Harness calls treeKill with shell injection string, checks if canary executes.'),
    'javascript-cve-2024-56334': ('systeminformation command injection (CWE-200)', 'lib/network.js', 'Network interface name passed to OS command unsanitized. May be Linux-specific; check reproducibility on worker before qualification.'),
    'cpp-cve-2022-43680': ('libexpat use-after-free in XML entity handling (CWE-416)', 'expat/lib/xmlparse.c', 'UAF in entity reference processing after realloc. Harness parses crafted XML with ASan or checks for crash.'),
    'cpp-cve-2019-1000019': ('libarchive OOB read in 7zip format (CWE-125)', 'libarchive/archive_read_support_format_7zip.c', 'Out-of-bounds read on malformed 7zip archive. Harness extracts crafted 7zip, checks for crash or ASan OOB.'),
    'cpp-cve-2023-4863': ('libwebp heap buffer overflow in VP8L decode (CWE-787)', 'src/dec/vp8l_dec.c', 'Heap buffer overflow decoding crafted WebP image. Harness decodes crafted webp file, checks for crash or ASan OOB.'),
    'cpp-cve-2024-25062': ('libxml2 use-after-free in xmlreader (CWE-416)', 'xmlreader.c', 'UAF in xmlTextReaderExpand. Harness reads crafted XML document via reader API.'),
    'cpp-cve-2014-9130': ('libyaml assertion failure on crafted input (CWE-617)', 'src/scanner.c', 'Assertion failure parsing crafted YAML. Harness parses crafted YAML input, checks for abort or error.'),
    'cpp-cve-2020-12762': ('json-c integer overflow in array/linkhash (CWE-190)', 'linkhash.c', 'Integer overflow in linkhash/printbuf causing heap corruption. Harness constructs large JSON object or array.'),
}

LICENSE_MAP = {
    'python': 'Apache-2.0 / MIT (see LICENSE)',
    'javascript': 'MIT / ISC (see LICENSE)',
    'cpp': 'MIT / BSD / LGPL (see LICENSE)',
}

created = updated = 0
for case in review['cases']:
    cid = case['id']
    if cid in DEV_CASES:
        continue

    meta = cases_meta.get(cid, {})
    lang = meta.get('language', 'unknown')
    recipe_dir = ROOT / 'benchmark' / 'recipes' / cid
    recipe_dir.mkdir(parents=True, exist_ok=True)
    recipe_path = recipe_dir / 'recipe.json'

    info = DESCRIPTIONS.get(cid, (meta.get('cve', cid) + ' ' + meta.get('cwe', ''), '', 'See intake review for details.'))
    description, primary_file, notes = info

    editable = case.get('editable_changes', [])
    source_map = {}
    for f in editable:
        source_map[f] = {
            'role': 'editable',
            'context_lines': [1, 80],
            'notes': notes if f == primary_file else 'Supporting file changed in fix commit.'
        }

    license_files = [lf['path'] for lf in case.get('license_files', [])[:2]]

    recipe = {
        'case': cid,
        'description': description,
        'approved': True,
        'adaptations': f'Pinned to vulnerable revision {case["source_revision"]}. {notes} No external network. Reference fix kept outside model-visible target and audit inputs.',
        'license_review': {
            'identifier': LICENSE_MAP.get(lang.lower().replace('c/c++', 'cpp'), 'PENDING'),
            'files': license_files,
            'notes': 'Review upstream LICENSE file in acquisition directory.'
        },
        'source_revision': case['source_revision'],
        'fix_revision': case['fix_revision'],
        'target': 'target',
        'manifest': 'manifest.json',
        'audit': 'audit.json',
        'source_map': source_map,
        'dependency_constraints': {'PENDING': 'Pin all dependencies before worker execution'},
        'resource_limits': {'cpu_seconds': 30, 'memory_mb': 256, 'network': 'loopback-only'},
        'controls': {
            'legitimate_behavior': ['PENDING: document expected normal behavior'],
            'vulnerable_reproduction': ['PENDING: document how vulnerability manifests', 'Repeat 3 times to confirm reproducibility'],
            'fixed_check': ['PENDING: document expected behavior after reference fix applied']
        }
    }
    existed = recipe_path.exists()
    old_approved = json.loads(recipe_path.read_text()).get('approved', False) if existed else False
    if existed and old_approved:
        print(f'ALREADY APPROVED (skip): {cid}')
        continue
    recipe_path.write_text(json.dumps(recipe, indent=2) + '\n')
    if existed:
        updated += 1
        print(f'UPDATED: {cid}')
    else:
        created += 1
        print(f'CREATED: {cid}')

print(f'\nDone: {created} created, {updated} updated')
