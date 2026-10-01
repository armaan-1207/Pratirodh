"""Build reviewed minimal reproductions. Never run this against a frozen measurement.

These are original synthetic Flask adaptations of documented mechanisms, not
upstream code copies or tests of the complete upstream applications.
"""
import difflib
import hashlib
import hmac
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    cohort = ROOT / 'benchmark/external-v1'
    rows = json.loads((cohort / 'sources.json').read_text())
    selected = []
    definitions = [
        ('GHSA-xg73-94fp-g449', 'CWE-22', 'development', 'download validation called with wrong argument'),
        ('GHSA-62mm-xwmv-crhg', 'CWE-22', 'evaluation', 'static-file route lacks resolved path containment'),
        ('GHSA-hmr4-m2h5-33qx', 'CWE-89', 'development', 'StringAgg delimiter SQL interpolation'),
        ('GHSA-p64x-8rxx-wf6q', 'CWE-89', 'evaluation', 'Extract lookup SQL interpolation'),
        ('GHSA-ffw3-6378-cqgp', 'CWE-78', 'development', 'shell command incorporates prediction input path'),
        ('GHSA-j5h9-9r39-43q5', 'CWE-78', 'evaluation', 'shell echo incorporates days input'),
        ('GHSA-33f4-mjch-7fpr', 'CWE-798', 'evaluation', 'shared webhook signing secret'),
    ]
    for advisory, cwe, split, mechanism in definitions:
        sid = 'external-' + advisory.lower()
        directory = cohort / 'cases' / sid
        directory.mkdir(parents=True, exist_ok=True)
        canary = 'EXTERNAL_PRIVATE_' + advisory
        prefix = 'from flask import Flask, request\nimport os\napp = Flask(__name__)\n'
        fixtures, profiles, symlinks = {}, {'default': {}}, {}
        param, benign, attack, hidden = '', '', '', ''
        if cwe == 'CWE-22':
            param, benign, attack, hidden = 'file', 'notes.txt', '../private/record.txt', 'link.txt'
            fixtures = {'public/notes.txt': 'public notes', 'private/record.txt': canary,
                        'public-other/record.txt': canary}
            symlinks = {'public/link.txt': '../private/record.txt'}
            source = prefix + '''@app.get('/resource')
def resource():
    filename = request.args.get('file', 'notes.txt')
    base_dir = os.path.join(os.path.dirname(__file__), 'public')
    filepath = os.path.join(base_dir, filename)
    try:
        with open(filepath, encoding='utf-8') as stream:
            return stream.read()
    except OSError:
        return 'missing', 404
'''
            if split == 'development':
                source = source.replace("    filepath =", "    validate_path_is_safe(validate_path_is_safe)\n    filepath =")
                source += "\ndef validate_path_is_safe(value):\n    if isinstance(value, str) and '..' in value:\n        raise ValueError('unsafe path')\n"
            old = '    filepath = os.path.join(base_dir, filename)\n'
            new = '''    filepath = os.path.realpath(os.path.join(base_dir, filename))
    real_base = os.path.realpath(base_dir)
    if not (filepath == real_base or filepath.startswith(real_base + os.sep)):
        return 'Access denied', 403
'''
            requirement = 'Serve public files only after canonicalization and symlink resolution with directory containment; retain public notes downloads.'
            legitimate_body = 'public notes'
            unsafe = new.replace('filepath.startswith(real_base + os.sep)', 'filepath.startswith(real_base)')
            incomplete = old.replace('    filepath', "    if '..' in filename:\n        return 'denied', 403\n    filepath")
            mutation_find, mutation_replace = 'filepath.startswith(real_base + os.sep)', 'filepath.startswith(real_base)'
            probe_value = '../public-other/record.txt'
        elif cwe == 'CWE-89':
            prefix += 'import sqlite3\n'
            param, benign = ('delimiter', '|') if split == 'development' else ('lookup', 'year')
            expression = "group_concat(value, '{value}')" if split == 'development' else "date_part('{value}', value)"
            source = prefix + '''@app.get('/resource')
def resource():
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE records (value TEXT)')
    conn.execute("INSERT INTO records VALUES ('2024-05-06')")
    conn.execute('CREATE TABLE private (value TEXT)')
    conn.execute('INSERT INTO private VALUES (?)', (''' + repr(canary) + ''',))
    conn.create_function('date_part', 2, lambda kind, date: date[:4] if kind == 'year' else date[5:7])
    value = request.args.get(''' + repr(param) + ''', ''' + repr(benign) + ''')
    query = f"SELECT ''' + expression + ''' FROM records"
    try:
        cur = conn.execute(query)
        return str(cur.fetchone()[0])
    except sqlite3.Error:
        return 'invalid', 400
'''
            old = '    query = f"SELECT ' + expression + ' FROM records"\n'
            fixedexpr = expression.replace("'{value}'", '?')
            new = '    query = "SELECT ' + fixedexpr + ' FROM records"\n'
            correct = source.replace(old, new).replace('conn.execute(query)', 'conn.execute(query, (value,))')
            incomplete = source.replace(old, "    if 'UNION' in value:\n        return 'invalid', 400\n" + old)
            unsafe = source.replace(old, "    if 'union' in value:\n        return 'invalid', 400\n" + old)
            attack = "x') FROM records UNION SELECT value FROM private -- " if split == 'development' else "x', value) FROM records UNION SELECT value FROM private -- "
            hidden = attack.replace('UNION SELECT', 'uNiOn SeLeCt')
            # Fetch all rows so union leakage is observable regardless of row ordering.
            source = source.replace('str(cur.fetchone()[0])', "'|'.join(str(row[0]) for row in cur.fetchall())")
            correct = correct.replace('str(cur.fetchone()[0])', "'|'.join(str(row[0]) for row in cur.fetchall())")
            incomplete = incomplete.replace('str(cur.fetchone()[0])', "'|'.join(str(row[0]) for row in cur.fetchall())")
            unsafe = unsafe.replace('str(cur.fetchone()[0])', "'|'.join(str(row[0]) for row in cur.fetchall())")
            requirement = 'Treat the aggregation delimiter or date lookup as data using SQL parameters; keep current endpoint and output for valid values.'
            legitimate_body = '2024-05-06' if split == 'development' else '2024'
            mutation_find, mutation_replace = 'conn.execute(query, (value,))', 'conn.execute(query.replace("?", "\\\'" + value + "\\\'"))'
            probe_value = hidden
        elif cwe == 'CWE-78':
            prefix += 'import subprocess\n'
            param, benign, attack, hidden = 'days', 'Monday', 'Monday; printf audit > marker.txt', 'Monday\nprintf audit > marker.txt'
            source = prefix + '''@app.get('/resource')
def resource():
    days = request.args.get('days', 'Monday')
    output = subprocess.check_output(f"echo -n {days}", shell=True, text=True)
    return output
'''
            old = '    output = subprocess.check_output(f"echo -n {days}", shell=True, text=True)\n'
            new = '    output = subprocess.check_output(["echo", "-n", days], text=True)\n'
            incomplete = "    if ';' in days:\n        return 'invalid', 400\n" + old
            unsafe = "    days = days.replace(';', '')\n" + old
            requirement = 'Run echo with literal argv rather than a shell; preserve the returned legitimate day and prohibit command effects.'
            legitimate_body = 'Monday'
            mutation_find, mutation_replace = new.strip(), old.strip()
            probe_value = hidden
        else:
            prefix += 'import hmac\nimport hashlib\n'
            profiles = {'default': {'PRATIRODH_FIXTURE_WEBHOOK_SECRET': 'rotated-key'}, 'missing': {}}
            param, benign = 'signature', hmac.new(b'rotated-key', b'event', hashlib.sha256).hexdigest()
            attack = hmac.new(b'public-shared-key', b'event', hashlib.sha256).hexdigest()
            hidden = attack
            source = prefix + '''webhook_secret = 'public-shared-key'
@app.get('/resource')
def resource():
    signature = request.args.get('signature', '')
    expected = hmac.new(webhook_secret.encode(), b'event', hashlib.sha256).hexdigest()
    if hmac.compare_digest(signature, expected):
        return 'event accepted'
    return 'denied', 403
'''
            # An old shared key must authenticate on the vulnerable original for calibration,
            # but legitimate configured-key behavior must also survive the repair.
            source = source.replace("    expected =", "    configured = os.environ.get('PRATIRODH_FIXTURE_WEBHOOK_SECRET')\n    if configured and hmac.compare_digest(signature, hmac.new(configured.encode(), b'event', hashlib.sha256).hexdigest()):\n        return 'event accepted'\n    expected =")
            old = "webhook_secret = 'public-shared-key'\n"
            new = "webhook_secret = os.environ.get('PRATIRODH_FIXTURE_WEBHOOK_SECRET')\n"
            correct = source.replace(old, new).replace("    expected =", "    if not webhook_secret:\n        return 'denied', 403\n    expected =")
            incomplete = source
            unsafe = source.replace(old, "webhook_secret = os.getenv('PRATIRODH_FIXTURE_WEBHOOK_SECRET', 'public-shared-key')\n")
            requirement = 'Authenticate webhook events with the configured synthetic environment key only; deny missing keys and old shared-key signatures; preserve valid configured signatures.'
            legitimate_body = 'event accepted'
            mutation_find, mutation_replace = new.strip(), old.strip()
            probe_value = attack
        if cwe not in {'CWE-89', 'CWE-798'}:
            correct = source.replace(old, new)
            incomplete = source.replace(old, incomplete)
            unsafe = source.replace(old, unsafe)
        case = lambda cid, val, kind='attack', profile='default': dict(id=cid, path='/resource', query={param: val}, kind=kind, assertion='legitimate' if kind == 'benign' else 'safe', profile=profile)
        assertion = {'type': 'security', 'statuses': [200,400,403,404], 'forbidden': [canary]}
        if cwe == 'CWE-78': assertion = {'type': 'security', 'statuses': [200,400,403,404], 'absent_files': ['marker.txt']}
        if cwe == 'CWE-798': assertion = {'type': 'security', 'statuses': [200,400,403,404], 'denied_body': 'event accepted'}
        contract = dict(version=2, id=sid, cwe=cwe, entrypoint='app.py', editable=['app.py'], fixtures=fixtures, symlinks=symlinks, profiles=profiles,
            requirements=[requirement], assertions={'legitimate': {'type':'exact','status':200,'body':legitimate_body}, 'safe': assertion},
            cases=[case('legitimate', benign, 'benign'), case('seed-attack', attack, profile='missing' if cwe == 'CWE-798' else 'default')],
            probes=[case('probe-variant', probe_value, profile='missing' if cwe == 'CWE-798' else 'default')],
            mutations=[{'family':'mechanism-restored','find':mutation_find,'replace':mutation_replace,'witnesses':['probe-variant']}])
        audit = dict(contract)
        audit['cases'] = [case('audit-legitimate', benign, 'benign'), case('audit-attack', hidden, profile='missing' if cwe == 'CWE-798' else 'default'), case('audit-probe', probe_value, profile='missing' if cwe == 'CWE-798' else 'default')]
        if cwe == 'CWE-22': audit['cases'].append(case('audit-normalized', './notes.txt', 'benign'))
        audit['probes'] = []
        auditdir = ROOT / 'benchmark/audit-v1'
        auditdir.mkdir(exist_ok=True)
        (auditdir / (sid + '.json')).write_text(json.dumps(audit,indent=2),encoding='utf-8')
        (directory/'app.py').write_text(source,encoding='utf-8',newline='\n')
        (directory/'contract.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
        patchdir = directory/'patches';patchdir.mkdir(exist_ok=True)
        broken = correct.replace('@app.get(\'/resource\')', "@app.get('/removed')")
        for label, candidate in [('correct',correct),('incomplete',incomplete),('insecure-alternative',unsafe),('functionality-breaking',broken)]:
            # An unchanged incomplete source still needs a valid candidate diff.
            if candidate == source: candidate += '\n# incomplete repair: vulnerability remains\n'
            diff = ''.join(difflib.unified_diff(source.splitlines(True),candidate.splitlines(True),fromfile='a/app.py',tofile='b/app.py'))
            (patchdir/(label+'.diff')).write_text(diff,encoding='utf-8',newline='\n')
        provenance = next(r for r in rows if r['advisory']==advisory)
        selected.append(dict(provenance,id=sid,cwe=cwe,split=split,cohort='real-world-derived reproductions',mechanism=mechanism,
             adaptation='Original minimal Flask implementation; synthetic data; local SQLite replaces upstream SQL backends, echo replaces prediction processes, HMAC replaces Go webhook transport. No upstream source copied. Known repairs are team-authored and may be stronger than upstream fixes.',
             fixture_license='CC0-1.0', path=str(directory.relative_to(ROOT)).replace('\\','/')))
    manifest = dict(version='external-v1',target_cases=16,cases=selected,
        shortfall={cwe:4-sum(c['cwe']==cwe for c in selected) for cwe in ['CWE-22','CWE-89','CWE-78','CWE-798']},
        exclusions=[{'source':'GHSA-h3h8-3v2v-rg7m','reason':'Referenced fix removes token disclosure, not the shared session signing key; excluded from CWE-798 comparison.'},
                    {'source':'GHSA-f38v-77qj-h4jq','reason':'No identifiable upstream fixed commit in advisory references.'},
                    {'source':'GHSA-73h3-mf4w-8647','reason':'Archive extraction mechanism not preserved by current read-only file fixtures.'},
                    {'source':'GHSA-2f96-g7mh-g2hx','reason':'Git option abbreviation needs Git transport; echo fixture would erase mechanism.'}],
        limitations=['Team-authored evaluation, not third-party certification.','Small convenience sample; quota shortfalls remain.','Two Django and two MLflow cases are related projects.','Development and previously inspected curated cohorts are separate from evaluation.'])
    (cohort/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')


if __name__ == '__main__': build()
