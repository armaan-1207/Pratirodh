"""Build twelve controlled synthetic fixtures; never uses real credentials."""
import difflib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'benchmark'


def case(cid, query, assertion, kind='attack', profile='default'):
    return {'id': cid, 'path': '/check', 'query': query, 'assertion': assertion, 'kind': kind, 'profile': profile}


def build():
    catalogue = [s for s in json.loads((ROOT / 'catalogue.json').read_text()) if s['cwe'] not in {'CWE-78', 'CWE-798'}]
    for cwe in ['CWE-78', 'CWE-798']:
        for split in ['development', 'heldout']:
            for index in range(1, 4):
                sid = f'{cwe.lower()}-{split}-{index:02d}'
                contract = {'version': 2, 'id': sid, 'cwe': cwe, 'entrypoint': 'app.py', 'editable': ['app.py'],
                            'fixtures': {}, 'assertions': {}, 'cases': [], 'probes': [], 'mutations': []}
                if cwe == 'CWE-78':
                    token = f'allowed{index}'
                    header = 'from flask import Flask, request\nimport subprocess\napp = Flask(__name__)\n@app.get("/check")\ndef check():\n    name = request.args.get("name", "")\n'
                    original = header + '    return subprocess.check_output("printf %s " + name, shell=True, text=True)\n'
                    safe = f'    if name != "{token}":\n        return "Denied", 403\n    return subprocess.check_output(["printf", "%s", name], text=True)\n'
                    correct = header + safe
                    incomplete = header + '    if ";" in name:\n        return "Denied", 403\n' + original[len(header):]
                    contract.update(requirements=[f'Return {token} for name={token}; reject every other name. Never allow request input to execute shell commands or create marker.txt.'],
                        assertions={'ok': {'type': 'exact', 'status': 200, 'body': token},
                                    'safe': {'type': 'security', 'statuses': [400, 403], 'absent_files': ['marker.txt']}},
                        cases=[case('legitimate', {'name': token}, 'ok', 'benign'), case('seed-command', {'name': token + '; touch marker.txt'}, 'safe')],
                        probes=[case('probe-separator', {'name': token + ' && touch marker.txt'}, 'safe'),
                                case('probe-substitution', {'name': token + '$(touch marker.txt)'}, 'safe')],
                        mutations=[{'family': 'shell-restored', 'find': safe, 'replace': original[len(header):], 'witnesses': ['seed-command']}])
                    alternative = original.replace('shell=True', 'shell=True') + '# insecure alternative\n'
                else:
                    old = f'SYNTHETIC_OLD_{sid}'
                    configured, rotated = f'SYNTHETIC_NEW_{sid}', f'SYNTHETIC_ROTATED_{sid}'
                    header = 'from flask import Flask, request\nimport os\napp = Flask(__name__)\n@app.get("/check")\ndef check():\n'
                    original = header + f'    password = os.getenv("PRATIRODH_FIXTURE_SECRET", "{old}")\n    supplied = request.args.get("key", "")\n    if supplied != password:\n        return "Denied", 401\n    return "Authorized"\n'
                    safe = '    password = os.getenv("PRATIRODH_FIXTURE_SECRET")\n    if not password:\n        return "Denied", 401\n    supplied = request.args.get("key", "")\n    if supplied != password:\n        return "Denied", 401\n    return "Authorized"\n'
                    correct = header + safe
                    incomplete = correct.replace('if supplied != password:', 'if not supplied.startswith(password):')
                    alternative = original + '# insecure alternative\n'
                    contract.update(requirements=['Use only PRATIRODH_FIXTURE_SECRET supplied by the environment. Missing or empty configuration must deny access. Accept only the exact configured credential; reject old and incorrect credentials after rotation. Preserve Authorized/Denied response bodies and 200/401 statuses. Remove embedded credentials from source.'],
                        forbidden_source=[old], profiles={'default': {'PRATIRODH_FIXTURE_SECRET': configured}, 'missing': {}, 'rotated': {'PRATIRODH_FIXTURE_SECRET': rotated}},
                        assertions={'ok': {'type': 'exact', 'status': 200, 'body': 'Authorized'},
                                    'safe': {'type': 'security', 'statuses': [401, 403], 'denied_body': 'Authorized'}},
                        cases=[case('legitimate', {'key': configured}, 'ok', 'benign'),
                               case('legitimate-rotated', {'key': rotated}, 'ok', 'benign', 'rotated'),
                               case('seed-missing', {'key': old}, 'safe', profile='missing'),
                               case('seed-wrong', {'key': 'wrong'}, 'safe')],
                        probes=[case('probe-prefix', {'key': configured + 'x'}, 'safe'),
                                case('probe-old', {'key': old}, 'safe', profile='rotated'),
                                case('probe-empty', {'key': ''}, 'safe', profile='missing')],
                        mutations=[{'family': 'credential-check-removed', 'find': 'if supplied != password:', 'replace': 'if False:', 'witnesses': ['seed-wrong']}])
                broken = 'from flask import Flask\napp = Flask(__name__)\n@app.get("/check")\ndef check():\n    return "Denied", 403\n'
                patches = {'correct': correct, 'incomplete': incomplete, 'insecure-alternative': alternative, 'functionality-breaking': broken}
                directory = ROOT / 'scenarios' / sid
                (directory / 'patches').mkdir(parents=True, exist_ok=True)
                (directory / 'app.py').write_text(original, encoding='utf-8')
                (directory / 'contract.json').write_text(json.dumps(contract, indent=2), encoding='utf-8')
                for label, source in patches.items():
                    diff = ''.join(difflib.unified_diff(original.splitlines(True), source.splitlines(True), fromfile='a/app.py', tofile='b/app.py'))
                    (directory / 'patches' / (label + '.diff')).write_text(diff, encoding='utf-8')
                catalogue.append({'id': sid, 'cwe': cwe, 'split': split, 'labels': list(patches)})
    (ROOT / 'catalogue.json').write_text(json.dumps(catalogue, indent=2), encoding='utf-8')


if __name__ == '__main__':
    build()
