"""Source review and executable qualification, without inventing readiness."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from .engine import check, qualify, verify, matches
from .manifest import load, protected, argv, oracle
from .patching import apply, make_diff
from .preflight import attest_worker, separate
from .worker import DockerProjectWorker
from .budget import WorkflowBudget
from ..evidence import canonical, digest, new_id, tree_hash


def git(directory, *arguments):
    output = subprocess.run(['git', '-C', str(directory), *arguments], check=True,
                            capture_output=True, encoding='utf-8', timeout=60).stdout
    return output if arguments[0] == 'show' else output.rstrip('\n')


def review_source(case, directory):
    """Inspect acquired source bytes and fix scope; execute no upstream code."""
    directory = Path(directory)
    provenance = json.loads((directory / 'provenance.json').read_text(encoding='utf-8'))
    source = directory / 'upstream'
    errors = []
    if provenance['repository'] != case['repository_url'] or provenance['fixed_revision'] != case['fix_revision']:
        errors.append('ACQUISITION_DIFFERS_FROM_COHORT')
    if git(source, 'rev-parse', 'HEAD') != provenance['vulnerable_revision']:
        errors.append('ACQUIRED_REVISION_CHANGED')
    if git(source, 'rev-parse', provenance['fixed_revision'] + '^') != provenance['vulnerable_revision']:
        errors.append('FIX_PARENT_DIFFERS_FROM_SOURCE')
    changed = git(source, 'diff', '--name-only', provenance['vulnerable_revision'], provenance['fixed_revision']).splitlines()
    editable_changes = [name for name in changed if not protected(name)]
    if not editable_changes:
        errors.append('REFERENCE_FIX_HAS_NO_EDITABLE_SOURCE_CHANGE')
    source_hashes = provenance.get('source_hashes', {})
    if not source_hashes:
        errors.append('SOURCE_INVENTORY_MISSING')
    else:
        for name, expected in source_hashes.items():
            path = source / name
            if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != expected:
                errors.append('SOURCE_INVENTORY_CHANGED:' + name)
    license_files = list(provenance.get('license_files', []))
    for name in case.get('additional_license_paths', []):
        from ..contracts import safe_relative
        safe_relative(name)
        if name not in source_hashes:
            errors.append('SUPPLEMENTAL_LICENSE_NOT_IN_SOURCE_INVENTORY')
        else:
            license_files.append({'path': name, 'sha256': source_hashes[name]})
    if not license_files:
        errors.append('LICENSE_EVIDENCE_MISSING')
    for item in license_files:
        path = source / item['path']
        if not path.is_file() or digest(path.read_bytes()) != item['sha256']:
            errors.append('LICENSE_EVIDENCE_CHANGED')
    return {'id': case['id'], 'status': 'SOURCE_REVIEW_BLOCKED' if errors else 'SOURCE_REVIEWED',
            'errors': errors, 'source_revision': provenance['vulnerable_revision'],
            'fix_revision': provenance['fixed_revision'], 'changed_files': changed,
            'editable_changes': editable_changes, 'license_files': license_files,
            'provenance_digest': digest(canonical(provenance)),
            'source_inventory_digest': digest(canonical(source_hashes)),
            'qualification': 'PENDING_EXECUTABLE_CONTROLS',
            'updated': datetime.now(timezone.utc).isoformat()}


def qualify_case(case, acquisition, target, manifest_path, audit_path, source_map, license_review, store, recipe_digest=None):
    """Run vulnerable, fixed, normal-use and protected-audit controls on guests."""
    review = review_source(case, acquisition)
    if review['errors']:
        raise ValueError('source review failed before executable qualification')
    if license_review.get('approved') is not True or not license_review.get('identifier') or not license_review.get('rationale'):
        raise ValueError('explicit license review required')
    manifest, original = load(target, manifest_path)
    if manifest['worker']['mode'] != 'dedicated':
        raise ValueError('upstream qualification requires a dedicated execution worker')
    if set(manifest['editable']) != set(source_map):
        raise ValueError('every editable path must map to acquired upstream source')
    if len(set(source_map.values())) != len(source_map):
        raise ValueError('source mapping must be one-to-one')
    if set(review['editable_changes']) - set(source_map.values()):
        raise ValueError('source mapping must cover every editable reference-fix change')
    upstream = Path(acquisition) / 'upstream'
    fixed = dict(original)
    for local, remote in source_map.items():
        from ..contracts import safe_relative
        safe_relative(local)
        safe_relative(remote)
        if local not in original or original[local] != git(upstream, 'show', review['source_revision'] + ':' + remote):
            raise ValueError('adapted source differs from declared upstream revision: ' + local)
        fixed[local] = git(upstream, 'show', review['fix_revision'] + ':' + remote)
    fixed = apply(original, make_diff(original, fixed), manifest['editable'])
    audit = json.loads(Path(audit_path).read_text(encoding='utf-8'))
    if Path(audit_path).resolve().is_relative_to(Path(target).resolve()) or set(audit['files']) & original.keys():
        raise ValueError('protected audit inputs must remain outside source')
    if not any(c.get('role') == 'security' for c in audit['checks']) or not any(c.get('role') == 'control' for c in audit['checks']):
        raise ValueError('protected audit needs explicit security and legitimate controls')
    for assertion in audit['checks']:
        argv(assertion['command'])
        oracle(assertion)
        if assertion.get('role') not in {'security', 'control'}:
            raise ValueError('audit assertion must declare security or control role')
        if assertion['role'] == 'security':
            violation = assertion.get('violation')
            if not isinstance(violation, dict):
                raise ValueError('audit security assertions require an explicit violation oracle')
            oracle(violation)
            if (violation['exit'], violation['stdout']) == (assertion['exit'], assertion['stdout']):
                raise ValueError('audit safe and violation oracles must differ')
    execution_identity = attest_worker(manifest['worker']['context'], manifest['image'])
    audit_identity = attest_worker(audit['context'], audit['image'])
    separate(execution_identity, audit_identity)
    worker = DockerProjectWorker(manifest)
    budget = WorkflowBudget(manifest['limits'])
    baseline = [check(worker, original, c, budget, build=manifest['commands']['build']) for c in manifest['commands']['test']]
    vulnerable = [qualify(worker, original, prop, budget, manifest['commands']['build']) for prop in manifest['properties']]
    corrected = verify(worker, fixed, manifest, manifest['properties'], budget)
    audit_manifest = dict(manifest, image=audit['image'], worker={'mode': 'dedicated', 'context': audit['context']})
    audit_worker = DockerProjectWorker(audit_manifest)
    audits = {}
    for name, files in [('vulnerable', original), ('fixed', fixed)]:
        audits[name] = [dict(check(audit_worker, dict(files, **audit['files']), c['command'], budget, c,
                                  manifest['commands']['build']), role=c['role']) for c in audit['checks']]
        for observation, assertion in zip(audits[name], audit['checks']):
            observation['violation_observed'] = (assertion['role'] == 'security'
                and matches(observation.get('actual', {}), assertion['violation']))
    passed = (bool(vulnerable) and all(c['status'] == 'PASS' for c in baseline + corrected)
              and all(c['status'] == 'QUALIFIED' for c in vulnerable)
              and all(c['status'] == 'PASS' for c in audits['fixed'])
              and all(c['status'] == 'PASS' for c in audits['vulnerable'] if c['role'] == 'control')
              and all(c['violation_observed'] for c in audits['vulnerable'] if c['role'] == 'security')
              and all(c['status'] != 'ERROR' for c in audits['vulnerable']))
    report = {'id': new_id(), 'created': datetime.now(timezone.utc).isoformat(), 'scenario': 'upstream-qualification',
              'case': case['id'], 'decision': 'READY_FOR_REVIEW' if passed else 'INSUFFICIENT_EVIDENCE',
              'status': 'QUALIFIED' if passed else 'QUALIFICATION_FAILED', 'source_review': review,
              'license_review': license_review, 'source_map': source_map,
              'recipe_digest': recipe_digest,
              'manifest_digest': digest(Path(manifest_path).read_bytes()),
              'audit_digest': digest(Path(audit_path).read_bytes()),
              'source_revision': manifest['revision'], 'source_inventory': manifest['inventory'],
              'controller_digest': tree_hash(Path(__file__).parents[1]),
              'execution_identity': execution_identity, 'audit_identity': audit_identity,
              'baseline': baseline, 'vulnerable': vulnerable, 'fixed': corrected, 'audit': audits,
              'model_calls': 0, 'scope': 'Upstream controls using a supplied reference fix; not AI repair accuracy'}
    store.save(report, {'qualification.json': json.dumps(report, indent=2)})
    return report
