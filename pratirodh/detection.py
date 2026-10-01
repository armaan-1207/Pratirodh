"""Static candidates only; findings are never presented as reproduced exploits."""
import ast
import json
from pathlib import Path
import subprocess
import sys

MAPPING = {'B105': 'CWE-798', 'B106': 'CWE-798', 'B107': 'CWE-798', 'B201': 'CWE-489',
           'B301': 'CWE-502', 'B403': 'CWE-502', 'B307': 'CWE-94', 'B602': 'CWE-78',
           'B604': 'CWE-78', 'B605': 'CWE-78', 'B608': 'CWE-89', 'B609': 'CWE-78'}


def scan(target):
    root = Path(target).resolve()
    if not root.exists():
        raise ValueError('scan target does not exist')
    result = subprocess.run([sys.executable, '-m', 'bandit', '-r', str(root), '-f', 'json',
                             '-x', '.venv,.git,run_output'], capture_output=True, text=True, timeout=45)
    if result.returncode not in {0, 1}:
        raise RuntimeError('static detection unavailable')
    raw = json.loads(result.stdout)
    if raw.get('errors'):
        raise RuntimeError('static detection encountered unreadable or invalid source')
    findings = []
    for f in raw['results']:
        findings.append({'file': str(Path(f['filename']).resolve()), 'line': f['line_number'],
                         'rule': f['test_id'], 'cwe': MAPPING.get(f['test_id'], 'CWE-' + str(f.get('issue_cwe', {}).get('id', 'UNKNOWN'))),
                         'severity': f['issue_severity'], 'source': 'bandit', 'status': 'UNVERIFIED'})
    paths = [root] if root.is_file() else sorted(root.rglob('*.py'))
    for path in paths:
        if any(p in {'.git', '.venv', 'run_output'} for p in path.parts):
            continue
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and any(word in t.id.lower() for word in ('password', 'secret', 'credential', 'token')) for t in node.targets):
                value = node.value
                embedded = isinstance(value, ast.Constant) and isinstance(value.value, str) and bool(value.value)
                fallback = isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) and value.func.attr == 'getenv' and len(value.args) > 1 and isinstance(value.args[1], ast.Constant) and bool(value.args[1].value)
                if embedded or fallback:
                    findings.append({'file': str(path.resolve()), 'line': node.lineno, 'rule': 'AST-CREDENTIAL',
                                     'cwe': 'CWE-798', 'severity': 'MEDIUM', 'source': 'custom-ast', 'status': 'UNVERIFIED'})
            if isinstance(node, ast.Call) and ((isinstance(node.func, ast.Name) and node.func.id == 'open') or
                (isinstance(node.func, ast.Attribute) and node.func.attr in {'read_text', 'read_bytes'})):
                if isinstance(node.func, ast.Attribute) or (node.args and not isinstance(node.args[0], ast.Constant)):
                    line = node.lineno
                    if node.args and isinstance(node.args[0], ast.Name):
                        assignments = [a for a in ast.walk(tree) if isinstance(a, ast.Assign) and a.lineno < node.lineno
                                       and any(isinstance(t, ast.Name) and t.id == node.args[0].id for t in a.targets)
                                       and isinstance(a.value, (ast.Call, ast.BinOp))]
                        if assignments: line = max(assignments, key=lambda a:a.lineno).lineno
                    findings.append({'file': str(path.resolve()), 'line': line, 'rule': 'AST-PATH',
                                     'cwe': 'CWE-22', 'severity': 'MEDIUM', 'source': 'custom-ast', 'status': 'UNVERIFIED'})
    for index, finding in enumerate(findings):
        finding['id'] = f'F{index + 1:03d}'
        finding['verification_supported'] = finding['cwe'] in {'CWE-22', 'CWE-89', 'CWE-78', 'CWE-798'}
    return findings
