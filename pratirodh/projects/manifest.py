"""Controller-owned intake and edit policy; repository text grants no authority."""
import fnmatch
import hashlib
import json
from pathlib import Path
import re

from ..contracts import safe_relative
from ..evidence import canonical, digest

SKIP = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache',
        'run_output', 'build', 'dist', '.pratirodh'}
CONTROL = {'pratirodh-project.json', 'pratirodh-report.json'}
PROFILES = {
    'laptop': {'model': 'Qwen2.5-Coder-7B-Instruct', 'context': 8192, 'memory_gb': 8},
    'alternative': {'model': 'Qwen3.5-9B', 'context': 8192, 'memory_gb': 12, 'experimental': True},
    'linux-large': {'model': 'Qwen3-Coder-30B-A3B-Instruct', 'context': 8192, 'memory_gb': 24},
    'prototype-small': {'model': 'Qwen2.5-Coder-3B-Instruct', 'context': 8192, 'memory_gb': 4, 'experimental': True},
}
SOURCE_SUFFIXES = {'.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.c', '.cc', '.cpp', '.h', '.hpp'}


def protected(name):
    path = Path(name)
    return (path.suffix not in SOURCE_SUFFIXES or any(
        p.lower() in {'test', 'tests', 'audit', 'audits', 'fixtures', 'fuzz', '.github', '.pratirodh'}
        for p in path.parts) or bool(re.search(r'(^|[/_.-])(test|spec|conftest|harness)([/_.-]|$)', name.lower())))


def inventory(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('project directory does not exist')
    files, total = {}, 0
    for path in sorted(root.rglob('*')):
        name = path.relative_to(root).as_posix()
        if any(p in SKIP for p in path.relative_to(root).parts) or name in CONTROL:
            continue
        safe_relative(name)
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise ValueError('project symlinks and junctions are not accepted: ' + name)
        if not path.is_file():
            continue
        if path.name == '.env' or path.suffix in {'.pem', '.key', '.p12'}:
            raise ValueError('remove credentials/private keys before intake: ' + name)
        payload = path.read_bytes()
        total += len(payload)
        if len(payload) > 1024 * 1024 or total > 10 * 1024 * 1024 or len(files) >= 1000:
            raise ValueError('project exceeds intake file/disk budget')
        try:
            files[name] = payload.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError('prototype requires UTF-8 source/fixtures: ' + name) from None
    if not files:
        raise ValueError('empty project')
    hashes = {name: digest(body) for name, body in files.items()}
    return files, hashes, digest(canonical(hashes))


def inspect(root):
    files, hashes, revision = inventory(root)
    if 'CMakeLists.txt' in files:
        language, build, test = 'cpp', [['cmake', '-S', '.', '-B', '/work/build', '-DCMAKE_C_COMPILER=clang', '-DCMAKE_CXX_COMPILER=clang++',
                                      '-DCMAKE_C_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie',
                                      '-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie',
                                      '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined -no-pie'],
                                      ['cmake', '--build', '/work/build', '-j2']], [['ctest', '--test-dir', '/work/build', '--output-on-failure']]
    elif 'package.json' in files and 'package-lock.json' in files:
        package = json.loads(files['package.json'])
        if not package.get('scripts', {}).get('test'):
            return {'status': 'UNSUPPORTED_PROJECT', 'missing': ['declared npm test script']}
        language, build, test = 'node', [], [['npm', 'test', '--', '--runInBand']] if 'jest' in package['scripts']['test'] else [['npm', 'test']]
        if 'tsconfig.json' in files:
            build = [['node', 'node_modules/typescript/bin/tsc', '--noEmit']]
    elif any(n.endswith('.py') for n in files) and any(n in files for n in ('pyproject.toml', 'requirements.txt', 'setup.cfg')):
        language, build, test = 'python', [['python', '-c', "import ast,pathlib; [ast.parse(p.read_text()) for p in pathlib.Path('.').rglob('*.py')]"]], [['python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider']]
    else:
        return {'status': 'UNSUPPORTED_PROJECT', 'missing': ['Python pytest project, locked npm project, or CMake/CTest project']}
    return {'version': 2, 'status': 'NEEDS_APPROVAL', 'revision': revision, 'inventory': hashes,
            'adapter': language, 'image': 'sha256:' + '0' * 64,
            'worker': {'mode': 'dedicated', 'context': 'pratirodh-worker'},
            'commands': {'build': build, 'test': test, 'startup': []},
            'editable': [n for n in files if not protected(n)], 'properties': [], 'mutations': [], 'formal': [],
            'model_analysis': False, 'generate_harnesses': False,
            'dependencies': {'prepared': False, 'resolved': {}, 'image_digest': ''},
            'limits': {'seconds': 1800, 'reserve_seconds': 600, 'model_calls': 8, 'candidates': 3,
                       'command_seconds': 120, 'memory_mb': 2048, 'cpus': 2, 'pids': 64,
                       'disk_mb': 256, 'output_bytes': 65536},
            'model': {'profile': 'laptop', 'runtime': 'ollama', 'endpoint': 'http://127.0.0.1:11434',
                      'name': 'qwen2.5-coder:7b', 'weights_digest': '', 'runtime_digest': '',
                      'quantization': 'Q4_K_M', 'available_memory_gb': 8, 'preflight_latency_seconds': None}}


def argv(value):
    if not isinstance(value, list) or not value or len(value) > 64 or not all(
            isinstance(x, str) and x and len(x) < 4096 and '\x00' not in x for x in value):
        raise ValueError('approved commands must be nonempty argument arrays')
    return value


def validate(manifest, files, hashes, revision):
    if manifest.get('version') != 2:
        raise ValueError('unsupported project manifest version')
    if manifest.get('adapter') not in {'python', 'node', 'cpp'}:
        raise ValueError('unsupported language adapter')
    if any(type(manifest.get(key, False)) is not bool for key in ('model_analysis', 'generate_harnesses')):
        raise ValueError('model analysis and harness generation must be explicit booleans')
    if manifest.get('revision') != revision or manifest.get('inventory') != hashes:
        raise ValueError('source inventory changed; inspect and approve a new manifest')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', manifest.get('image', '')) or manifest['image'] == 'sha256:' + '0' * 64:
        raise ValueError('execution image must be pinned to a real digest')
    deps = manifest.get('dependencies', {})
    if deps.get('prepared') is not True or deps.get('image_digest') != manifest['image'] or not isinstance(deps.get('resolved'), dict):
        raise ValueError('missing separately prepared dependency inventory')
    for phase in ('build', 'test', 'startup'):
        commands = manifest.get('commands', {}).get(phase)
        if not isinstance(commands, list) or len(commands) > 10:
            raise ValueError('missing/oversized approved command phase')
        for command in commands:
            argv(command)
    if not manifest['commands']['test']:
        raise ValueError('normal-use tests are required')
    if manifest['commands']['startup']:
        from urllib.parse import urlparse
        ready = urlparse(manifest.get('service_ready_url', ''))
        if ready.scheme != 'http' or ready.hostname not in {'127.0.0.1', 'localhost'} or ready.username or ready.password:
            raise ValueError('startup requires a worker-loopback HTTP readiness URL')
    editable = manifest.get('editable', [])
    if not editable or len(editable) != len(set(editable)):
        raise ValueError('explicit editable source paths required')
    for name in editable:
        safe_relative(name)
        if name not in files or protected(name):
            raise ValueError('protected or missing editable source: ' + name)
    limits = manifest.get('limits', {})
    bounds = {'seconds': (1, 1800), 'reserve_seconds': (0, 600), 'model_calls': (1, 8), 'candidates': (1, 3),
              'command_seconds': (1, 300), 'memory_mb': (128, 4096), 'cpus': (1, 4), 'pids': (8, 128),
              'disk_mb': (16, 512), 'output_bytes': (1024, 65536)}
    for key, (low, high) in bounds.items():
        if type(limits.get(key)) is not int or not low <= limits[key] <= high:
            raise ValueError('invalid resource limit: ' + key)
    if limits['reserve_seconds'] >= limits['seconds']:
        raise ValueError('verification reserve must be less than total budget')
    properties = manifest.get('properties', [])
    if not isinstance(properties, list) or len(properties) > 20:
        raise ValueError('invalid security properties')
    ids = set()
    for prop in properties:
        if not isinstance(prop.get('id'), str) or prop['id'] in ids:
            raise ValueError('property IDs must be unique strings')
        ids.add(prop['id'])
        provenance = prop.get('provenance', {})
        if provenance.get('kind') not in {'operator', 'trusted-specification'} or not provenance.get('reference') or provenance.get('approved') is not True:
            raise ValueError('model-proposed properties require operator/specification approval')
        if prop.get('kind') not in {'data-isolation', 'authorization', 'crash', 'memory-safety', 'explicit'}:
            raise ValueError('classify the demonstrated violation independently of optional CWE')
        for key in ('control', 'reproducer'):
            check = prop[key]
            argv(check['command'])
            oracle(check)
        violation = prop['reproducer'].get('violation')
        if not isinstance(violation, dict):
            raise ValueError('independent violation oracle required to distinguish harness errors')
        oracle(violation)
        if (violation['exit'], violation['stdout']) == (prop['reproducer']['exit'], prop['reproducer']['stdout']):
            raise ValueError('violation and safe oracles must differ')
        variations = prop.get('variations', [])
        if not variations or len(variations) > 20:
            raise ValueError('independent approved variations required')
        for check in variations:
            argv(check['command'])
            oracle(check)
        if not prop.get('target_files') or any(n not in editable for n in prop['target_files']):
            raise ValueError('harness must identify intended editable application files')
        if prop.get('harness_review', {}).get('approved') is not True or not prop['harness_review'].get('reference'):
            raise ValueError('harness invocation/target origin review required')
    mutations = manifest.get('mutations', [])
    if len(mutations) > 6:
        raise ValueError('at most six mutation families')
    for item in mutations:
        if item.get('file') not in editable or item.get('property') not in ids or not item.get('find') or item['find'] == item.get('replace'):
            raise ValueError('invalid mutation challenge')
    if len({m['family'] for m in mutations}) != len(mutations):
        raise ValueError('duplicate mutation family')
    for check in manifest.get('fuzz', []):
        if check.get('tool') not in {'atheris', 'jazzer.js', 'libFuzzer', 'schemathesis'} or check.get('approved') is not True or not check.get('reference'):
            raise ValueError('fuzz harnesses require reviewed invocation and explicit approval')
        argv(check['command'])
    for check in manifest.get('formal', []):
        if check.get('tool') not in {'crosshair', 'cbmc'} or check.get('property') not in ids or not check.get('assumptions') or not check.get('bounds'):
            raise ValueError('formal checks require a property, assumptions and explicit bounds')
        argv(check['command'])
        if check['command'][0] != check['tool']:
            raise ValueError('formal command must invoke the declared tool')
        if check['tool'] == 'cbmc' and ('--unwinding-assertions' not in check['command'] or '--unwind' not in check['command']):
            raise ValueError('CBMC requires explicit unwind bounds and unwinding assertions')
    worker = manifest.get('worker', {})
    if worker.get('mode') not in {'dedicated', 'demo'} or not re.fullmatch(r'[A-Za-z0-9_.-]+', worker.get('context', '')):
        raise ValueError('explicit dedicated worker Docker context required')
    return manifest


def oracle(check):
    if type(check.get('exit')) is not int or not 0 <= check['exit'] <= 255:
        raise ValueError('expected exit code required')
    if not isinstance(check.get('stdout'), str):
        raise ValueError('exact independent stdout assertion required')
    if len(check['stdout']) > 65536:
        raise ValueError('assertion exceeds output limit')


def load(root, path):
    files, hashes, revision = inventory(root)
    manifest = json.loads(Path(path).read_text(encoding='utf-8'))
    return validate(manifest, files, hashes, revision), files
