import json
from pathlib import Path, PurePosixPath

SUPPORTED = {"CWE-89", "CWE-22", "CWE-78", "CWE-798"}


def safe_relative(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value:
        raise ValueError("paths must be relative and remain inside their designated root")
    return value


def validate_case(case, assertions):
    if not isinstance(case.get("id"), str) or not case["id"]:
        raise ValueError("case needs an id")
    if case.get("assertion") not in assertions:
        raise ValueError("case references an untrusted assertion")
    if case.get("method", "GET") not in {"GET", "POST"}:
        raise ValueError("only GET and POST are supported")
    if not isinstance(case.get("path"), str) or not case["path"].startswith("/") or case['path'].startswith('//'):
        raise ValueError("case must reference a local route")
    if set(case) - {"id", "path", "method", "query", "form", "json", "assertion", "kind", "profile"}:
        raise ValueError("unsupported case fields")
    if len(json.dumps(case)) > 8192:
        raise ValueError("case exceeds size limit")
    for key in ("query", "form", "json"):
        if key in case and not isinstance(case[key], dict):
            raise ValueError("request inputs must be objects")


def load_contract(path):
    raw = Path(path).read_bytes()
    if len(raw) > 262144:
        raise ValueError('contract exceeds size limit')
    contract = json.loads(raw)
    if contract.get("version") not in {1, 2} or contract.get("cwe") not in SUPPORTED:
        raise ValueError("unsupported contract version or vulnerability")
    safe_relative(contract["entrypoint"])
    if not isinstance(contract.get('id'), str) or not contract['id'] or '/' in contract['id'] or '\\' in contract['id'] or '..' in contract['id']:
        raise ValueError('invalid scenario identifier')
    if any(not isinstance(v, str) or not v or len(v) > 256 for v in contract.get('forbidden_source', [])):
        raise ValueError('invalid forbidden source marker')
    if not contract["entrypoint"].endswith(".py"):
        raise ValueError("entrypoint must be Python")
    if contract.get("editable") != [contract["entrypoint"]]:
        raise ValueError("v1 permits changes only to the entrypoint")
    for name in contract["fixtures"]:
        safe_relative(name)
    for name, destination in contract.get("symlinks", {}).items():
        safe_relative(name)
        # Fixture symlinks may traverse within the ephemeral fixture tree only.
        if destination.startswith(("/", "\\")) or ":" in destination:
            raise ValueError("symlink destination must be relative")
        resolved = (Path("/fixture") / Path(name).parent / destination).resolve()
        if not resolved.is_relative_to(Path("/fixture").resolve()):
            raise ValueError("symlink escapes fixture tree")
    assertions = contract["assertions"]
    profiles = contract.get('profiles', {'default': {}})
    if not isinstance(profiles, dict) or not profiles or len(profiles) > 4:
        raise ValueError('one to four synthetic environment profiles required')
    for values in profiles.values():
        if not isinstance(values, dict) or any(not k.startswith('PRATIRODH_FIXTURE_') or not isinstance(v, str)
                                               or len(v) > 256 for k, v in values.items()):
            raise ValueError('only bounded synthetic fixture environment variables permitted')
    for assertion in assertions.values():
        if assertion.get("type") not in {"exact", "security"}:
            raise ValueError("unsupported assertion type")
        if assertion["type"] == "security" and not (assertion.get("forbidden") or assertion.get('absent_files') or assertion.get('denied_body')):
            raise ValueError("security assertion must specify protected canaries")
        for name in assertion.get('absent_files', []):
            safe_relative(name)
        statuses = assertion.get('statuses', []) if assertion['type'] == 'security' else [assertion.get('status')]
        if not statuses or any(not isinstance(s, int) or not 200 <= s < 500 for s in statuses):
            raise ValueError('assertions cannot accept server errors or invalid statuses')
    cases = contract["cases"] + contract.get("probes", [])
    if len(cases) > 24:
        raise ValueError('too many mandatory case definitions')
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case id")
    for case in cases:
        validate_case(case, assertions)
        if case.get('profile', 'default') not in profiles:
            raise ValueError('unknown environment profile')
        expected_type = "security" if case["kind"] == "attack" else "exact"
        if assertions[case["assertion"]]["type"] != expected_type:
            raise ValueError("case kind and assertion type disagree")
    if not any(c["kind"] == "attack" for c in contract["cases"]):
        raise ValueError("missing attack tests")
    if not any(c["kind"] == "benign" for c in contract["cases"]):
        raise ValueError("missing legitimate-use regression tests")
    mutations = contract.get("mutations", [])
    if not mutations or len(mutations) > 6 or len({m["family"] for m in mutations}) != len(mutations):
        raise ValueError("one to six distinct mutation families are required")
    for mutation in mutations:
        if not mutation.get("find") or mutation["find"] == mutation.get("replace"):
            raise ValueError("mutation must change a nonempty source block")
        if not mutation.get("witnesses") or set(mutation["witnesses"]) - set(ids):
            raise ValueError("mutation requires known witness cases")
        if any(next(c for c in cases if c["id"] == cid)["kind"] != "attack" for cid in mutation["witnesses"]):
            raise ValueError("mutation witnesses must be security cases")
    return contract


def evaluate(case, actual, contract):
    expected = contract["assertions"][case["assertion"]]
    if actual.get("error") or "status" not in actual or not isinstance(actual.get("body"), str):
        status = "ERROR"
    elif expected["type"] == "exact":
        status = "PASS" if actual["status"] == expected["status"] and actual["body"] == expected["body"] else "FAIL"
    else:
        status = "PASS" if actual["status"] in expected["statuses"] and not any(
            value in actual["body"] for value in expected.get("forbidden", [])) and not any(
            actual.get('files', {}).get(name, True) for name in expected.get('absent_files', [])) and (
            not expected.get('denied_body') or actual['body'] != expected['denied_body']) else "FAIL"
        if expected.get('absent_files') and 'files' not in actual:
            status = 'ERROR'
    return {"case": case, "expected": expected, "actual": actual, "status": status}


def evaluate_output(output, cases, contract):
    results = output.get("results", [])
    if len(results) != len(cases) or [r.get("id") for r in results] != [c["id"] for c in cases]:
        return [evaluate(c, {"error": output.get("error", "missing or mismatched result")}, contract) for c in cases]
    return [evaluate(c, actual, contract) for c, actual in zip(cases, results)]


def violation(check):
    """Only observed forbidden behaviour qualifies a security witness."""
    if check['status'] != 'FAIL' or check['case']['kind'] != 'attack':
        return False
    actual, expected = check['actual'], check['expected']
    return (any(marker in actual.get('body', '') for marker in expected.get('forbidden', []))
            or any(actual.get('files', {}).get(name, False) for name in expected.get('absent_files', []))
            or bool(expected.get('denied_body') and actual.get('body') == expected['denied_body']))

