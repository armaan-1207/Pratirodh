"""Conservative static preparation checks; never execute upstream harnesses."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pratirodh.contracts import safe_relative
from pratirodh.projects.manifest import argv, inventory, load, oracle


def issue(errors, code, message):
    item = {'code': code, 'message': str(message)}
    if item not in errors:
        errors.append(item)


def read_json(path, errors):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('expected a JSON object')
        return data
    except (OSError, UnicodeError, ValueError) as exc:
        issue(errors, 'INVALID_JSON', f'{path.name}: {exc}')
        return {}


def source_tree(name, body, errors):
    if name.endswith('.py'):
        try:
            tree = ast.parse(body, filename=name)
            if not any(not (isinstance(n, (ast.Pass, ast.Expr)) and (
                    isinstance(n, ast.Pass) or isinstance(n.value, ast.Constant))) for n in tree.body):
                issue(errors, 'EMPTY_SOURCE', name + ': no executable statements')
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_'):
                    substantive = [n for n in node.body if not isinstance(n, ast.Pass) and not (
                        isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str))]
                    if not substantive:
                        issue(errors, 'EMPTY_TEST', name + '::' + node.name)
            return tree
        except (SyntaxError, ValueError, UnicodeError) as exc:
            issue(errors, 'INVALID_SOURCE', f'{name}: {exc}')
    elif Path(name).suffix in {'.js', '.mjs', '.cjs', '.ts', '.c', '.cpp', '.h'}:
        # Syntax validation for C/C++ and JS requires prepared toolchains; deferred to worker qualification
        pass
    return None


def command_targets(command, files, errors, label):
    try:
        argv(command)
        exe = Path(command[0]).name.lower()
        if exe.startswith('python') or exe in {'pytest', 'pytest.exe'}:
            targets = [x for x in command[1:] if x.split('::')[0].endswith('.py')]
            if '-c' in command:
                targets = []
        elif exe in {'node', 'node.exe'}:
            targets = [x for x in command[1:] if x.endswith(('.js', '.mjs', '.cjs'))]
        elif exe in {'ctest', 'make', 'cmake'}:
            # C/C++ build systems rely on the directory structure and compiled targets, skip explicit file matching
            return set(files.keys())
        else:
            targets = []
        if not targets:
            issue(errors, 'UNRESOLVED_CHECK_TARGET', label + ': no statically resolved script')
        resolved = set()
        for target in targets:
            name, *selectors = target.removeprefix('/work/source/').split('::')
            safe_relative(name)
            if name not in files:
                issue(errors, 'MISSING_CHECK_TARGET', label + ': ' + name)
                continue
            resolved.add(name)
            tree = source_tree(name, files[name], errors)
            for selector in selectors:
                selector = selector.split('[')[0]
                tree = next((n for n in getattr(tree, 'body', []) if isinstance(
                    n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == selector), None)
                if tree is None:
                    issue(errors, 'MISSING_CHECK_SELECTOR', label + ': ' + target)
                    break
        return resolved
    except (TypeError, ValueError) as exc:
        issue(errors, 'INVALID_COMMAND', f'{label}: {exc}')
        return set()


def check_case(case):
    errors = []
    recipe = read_json(case / 'recipe.json', errors)
    for field, default in [('target', 'target'), ('manifest', 'manifest.json'), ('audit', 'audit.json')]:
        try:
            safe_relative(recipe.get(field, default))
            if not (case / recipe.get(field, default)).resolve().is_relative_to(case.resolve()):
                raise ValueError('input escapes recipe directory')
        except (TypeError, ValueError) as error:
            issue(errors, 'ESCAPING_INPUT', error)
    if any(row['code'] == 'ESCAPING_INPUT' for row in errors):
        return {'status': 'BLOCKED', 'qualification': 'NOT_CHECKED', 'behavioral_review': 'REQUIRED',
                'audit_independence': 'NOT_VERIFIED', 'contexts': {}, 'blockers': errors}
    manifest_path = case / recipe.get('manifest', 'manifest.json')
    target_path = case / recipe.get('target', 'target')
    manifest = read_json(manifest_path, errors)
    audit = read_json(case / recipe.get('audit', 'audit.json'), errors)
    files = {}
    try:
        _, files = load(target_path, manifest_path)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        issue(errors, 'INVALID_MANIFEST', exc)
        try:
            files, _, _ = inventory(target_path)
        except (OSError, ValueError, UnicodeError) as exc:
            issue(errors, 'INVALID_TARGET', exc)
    license_review = recipe.get('license_review')
    if not isinstance(license_review, dict) or license_review.get('approved') is not True or not license_review.get('identifier'):
        issue(errors, 'LICENSE_NOT_APPROVED', 'recipe requires an approved license identifier')
    for field in ('source_revision', 'fix_revision'):
        if not re.fullmatch(r'[0-9a-f]{40}', str(recipe.get(field, ''))):
            issue(errors, 'INVALID_REVISION', field)
    properties = manifest.get('properties')
    if not isinstance(properties, list) or not properties:
        issue(errors, 'MISSING_PROPERTIES', 'no development security properties')
    else:
        for prop in properties:
            if not isinstance(prop, dict):
                issue(errors, 'INVALID_PROPERTY', 'expected an object')
                continue
            checks = [prop.get('control'), prop.get('reproducer')]
            variations = prop.get('variations', [])
            checks += variations if isinstance(variations, list) else []
            for check in checks:
                command_targets(check.get('command') if isinstance(check, dict) else None, files, errors, 'development')
    audit_files = audit.get('files')
    if not isinstance(audit_files, dict) or not audit_files:
        issue(errors, 'EMPTY_AUDIT', 'no supplied audit source files')
        audit_files = {}
    valid_files = {}
    for name, body in audit_files.items():
        try:
            safe_relative(name)
            if not isinstance(body, str) or not body.strip():
                raise ValueError('source must be a nonempty string')
            body.encode('utf-8')
            if re.fullmatch(r'[0-9a-fA-F]{64}', body.strip()) or body.strip().lower() in {'placeholder', 'todo', 'tbd'}:
                raise ValueError('placeholder or digest supplied instead of source')
            valid_files[name] = body
            source_tree(name, body, errors)
            if name in files:
                issue(errors, 'AUDIT_SOURCE_COLLISION', name)
        except (TypeError, ValueError, UnicodeError) as exc:
            issue(errors, 'INVALID_AUDIT_FILE', f'{name}: {exc}')
    if 'digest' in audit:
        digest = hashlib.sha256()
        for name, body in sorted(valid_files.items()):
            digest.update(name.encode('utf-8'))
            digest.update(body.encode('utf-8'))
        if audit['digest'] != digest.hexdigest():
            issue(errors, 'AUDIT_DIGEST_MISMATCH', 'embedded source digest differs')
    worker = manifest.get('worker')
    context = worker.get('context') if isinstance(worker, dict) else None
    audit_context = audit.get('context')
    if not isinstance(audit_context, str) or not audit_context or audit_context in {context, 'default', 'desktop-linux'}:
        issue(errors, 'INVALID_AUDIT_CONTEXT', 'audit requires a separate dedicated context')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', str(audit.get('image', ''))):
        issue(errors, 'INVALID_AUDIT_IMAGE', 'audit requires a pinned image digest')
    checks = audit.get('checks')
    roles = set()
    if not isinstance(checks, list) or not checks:
        issue(errors, 'MISSING_AUDIT_CHECKS', 'no audit commands')
        checks = []
    for check in checks:
        if not isinstance(check, dict):
            issue(errors, 'INVALID_AUDIT_CHECK', 'expected an object')
            continue
        if isinstance(check.get('role'), str):
            roles.add(check['role'])
        try:
            oracle(check)
            if 'violation' in check:
                oracle(check['violation'])
        except (ValueError, TypeError, AttributeError) as exc:
            issue(errors, 'INVALID_AUDIT_ORACLE', exc)
        targets = command_targets(check.get('command'), dict(files, **valid_files), errors, 'audit')
        if not targets.intersection(valid_files):
            issue(errors, 'AUDIT_TARGET_UNRESOLVED', 'audit command does not directly reference supplied audit source')
    if not roles.intersection({'control', 'legitimate_control'}) or not roles.intersection({'security', 'security_variation'}):
        issue(errors, 'MISSING_AUDIT_ROLES', 'control and security checks are required')
    return {'status': 'BLOCKED' if errors else 'STRUCTURALLY_READY', 'qualification': 'NOT_CHECKED',
            'behavioral_review': 'REQUIRED', 'audit_independence': 'NOT_VERIFIED',
            'contexts': {'execution': context, 'audit': audit_context}, 'blockers': errors}


def probe_worker(context, timeout):
    try:
        result = subprocess.run(['docker', '--context', context, 'info', '--format', '{{.ID}}'],
                                capture_output=True, text=True, timeout=timeout, check=False)
        return 'REACHABLE' if result.returncode == 0 and result.stdout.strip() else 'UNAVAILABLE'
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'
    except OSError:
        return 'UNAVAILABLE'


def report(recipes, check_workers=False, worker_timeout=5):
    cases = {p.name: check_case(p) for p in sorted(Path(recipes).glob('*')) if p.is_dir()}
    contexts = {c for case in cases.values() for c in case['contexts'].values() if isinstance(c, str) and c}
    counts = Counter(b['code'] for case in cases.values() for b in case['blockers'])
    ready = sum(case['status'] == 'STRUCTURALLY_READY' for case in cases.values())
    return {'scope': 'STATIC_PREPARATION_ONLY', 'qualification': 'NOT_CHECKED',
            'summary': {'total': len(cases), 'structurally_ready': ready, 'blocked': len(cases) - ready,
                        'blocker_counts': dict(sorted(counts.items()))},
            'workers': {c: probe_worker(c, worker_timeout) if check_workers else 'NOT_CHECKED' for c in sorted(contexts)},
            'cases': cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipes', type=Path, default=ROOT / 'benchmark/recipes')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check-workers', action='store_true', help='bounded read-only Docker daemon probes')
    parser.add_argument('--worker-timeout', type=int, choices=range(1, 31), default=5)
    args = parser.parse_args()
    result = report(args.recipes, args.check_workers, args.worker_timeout)
    body = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as output:
            output.write(body)
    print(body, end='')
    return 2 if result['summary']['blocked'] or not result['summary']['total'] else 0


if __name__ == '__main__':
    sys.exit(main())
