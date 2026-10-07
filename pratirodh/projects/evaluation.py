"""Frozen, licensed campaign inputs and a separate final-audit worker."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import re
import threading
from ..contracts import safe_relative
from ..evidence import Store, canonical, digest, new_id, tree_hash
from .budget import WorkflowBudget
from .engine import check, run_project
from .manifest import load, argv, oracle
from .worker import DockerProjectWorker

LANGUAGES = {'python', 'node', 'cpp'}
DEFAULT_BUDGET = {'seconds': 600, 'reserve_seconds': 180, 'model_calls': 2, 'candidates': 3}
DEFAULT_CAMPAIGN_BUDGET = {'seconds': 172800, 'audit_reserve_seconds': 28800}


def schedule(cases):
    """Round-robin repetitions; development inputs never become evaluation rows."""
    return [(case, workflow, arm, repetition) for repetition in range(3)
            for case in cases if case['split'] == 'evaluation'
            for workflow in ('repair', 'discover') for arm in ('expanded', 'model-only')]


def campaign_budget(value):
    seconds = value.get('seconds', DEFAULT_CAMPAIGN_BUDGET['seconds'])
    reserve = value.get('audit_reserve_seconds', DEFAULT_CAMPAIGN_BUDGET['audit_reserve_seconds'])
    if type(seconds) is not int or not 1 <= seconds <= 172800:
        raise ValueError('campaign allowance must be between one second and 48 hours')
    if type(reserve) is not int or not 0 <= reserve < seconds:
        raise ValueError('audit reserve must be smaller than campaign allowance')
    return {'seconds': seconds, 'audit_reserve_seconds': reserve}


def freeze(path, allowance=None, store=None):
    path = Path(path).resolve()
    campaign = json.loads(path.read_text(encoding='utf-8'))
    if campaign.get('version') != 1:
        raise ValueError('unsupported evaluation manifest')
    cases = campaign['cases']
    declared_budget = campaign.get('attempt_budget', DEFAULT_BUDGET)
    upstream = campaign.get('require_qualification') is True or len(cases) == 24
    if upstream and declared_budget != DEFAULT_BUDGET:
        raise ValueError('upstream arms require the approved equal attempt budget')
    allowance = campaign_budget(allowance or campaign.get('campaign_budget', DEFAULT_CAMPAIGN_BUDGET))
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('duplicate evaluation case')
    frozen = []
    for case in cases:
        if case['language'] not in LANGUAGES or case['split'] not in {'development', 'evaluation'}:
            raise ValueError('invalid language/split')
        provenance = case['provenance']
        if not provenance.get('license') or not provenance.get('source_url', '').startswith('https://') or not provenance.get('upstream_fix_url', '').startswith('https://'):
            raise ValueError('licensed upstream advisory/fix provenance required')
        target = (path.parent / case['target']).resolve()
        manifest_path = (path.parent / case['manifest']).resolve()
        manifest, _ = load(target, manifest_path)
        if any(manifest['limits'].get(key) != value for key, value in declared_budget.items()) and (upstream or campaign.get('attempt_budget')):
            raise ValueError('project limits differ from declared equal attempt budget')
        if manifest['adapter'] != case['language']:
            raise ValueError('case language and adapter disagree')
        audit_path = (path.parent / case['audit']).resolve()
        if audit_path.is_relative_to(target):
            raise ValueError('final audit must live outside generation/development source')
        audit = json.loads(audit_path.read_text(encoding='utf-8'))
        audit_image = audit.get('image', manifest['image'])
        if not isinstance(audit_image, str) or not re.fullmatch(r'sha256:[a-f0-9]{64}', audit_image):
            raise ValueError('audit image must be pinned')
        if audit.get('context') == manifest['worker']['context'] or audit.get('context') in {'default', 'desktop-linux'}:
            raise ValueError('final audit needs a separate dedicated worker context')
        for name in audit['files']:
            safe_relative(name)
        for assertion in audit['checks']:
            argv(assertion['command'])
            oracle(assertion)
        if not audit['checks']:
            raise ValueError('final audit assertions required')
        frozen.append(dict(case, source_revision=manifest['revision'], manifest_digest=digest(manifest_path.read_bytes()),
                           audit_digest=digest(audit_path.read_bytes())))
    expected = all(sum(c['language'] == lang and c['split'] == split for c in cases) == count
                   for lang in LANGUAGES for split, count in [('development', 2), ('evaluation', 6)])
    if expected or campaign.get('require_qualification') is True:
        qualification_store = store or Store(Path(__file__).resolve().parents[2] / 'run_output/pratirodh')
        for case in frozen:
            if not case.get('qualification_run_id'):
                raise ValueError('signed executable qualification required for every upstream case')
            record = qualification_store.load(case['qualification_run_id'])
            recipe_path = (path.parent / case['qualification_recipe']).resolve() if case.get('qualification_recipe') else None
            if (record.get('scenario') != 'upstream-qualification' or record.get('status') != 'QUALIFIED'
                    or record.get('case') != case['id'] or record.get('manifest_digest') != case['manifest_digest']
                    or record.get('audit_digest') != case['audit_digest']
                    or record.get('source_revision') != case['source_revision']
                    or record.get('controller_digest') != tree_hash(Path(__file__).parents[1])
                    or recipe_path is None or record.get('recipe_digest') != digest(recipe_path.read_bytes())):
                raise ValueError('qualification evidence does not bind frozen campaign inputs')
    return {'version': 1, 'cases': frozen, 'complete_24_case_cohort': expected,
            'digest': digest(canonical({'cases': frozen, 'attempt_budget': declared_budget,
                                      'campaign_budget': allowance,
                                      'controller': tree_hash(Path(__file__).parents[1])})), 'source': str(path),
            'controller_digest': tree_hash(Path(__file__).parents[1]),
            'attempt_budget': declared_budget, 'campaign_budget': allowance,
            'disclosure': 'Held out from project development; model training exposure cannot be ruled out.'}


def final_audit(report, case, campaign_path, store=None, worker_factory=DockerProjectWorker, deadline=None):
    store = store or Store()
    base = Path(campaign_path).resolve().parent
    audit_path = (base / case['audit']).resolve()
    if digest(audit_path.read_bytes()) != case['audit_digest']:
        raise ValueError('frozen final audit changed')
    # Reload signature and every artifact before passing candidate to the audit worker.
    report = store.load(report['id'])
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    manifest = dict(report['manifest'], image=audit.get('image', report['manifest']['image']),
                    worker={'mode': 'dedicated', 'context': audit['context']})
    results = []
    identity = None
    for index, candidate in enumerate(report['candidates']):
        source = store.run_path(report['id']) / f'candidate-{index}-source.json'
        if not source.exists():
            results.append({'candidate': index, 'status': 'NOT_EXECUTABLE', 'decision': candidate['decision']})
            continue
        files = json.loads(source.read_text(encoding='utf-8'))
        if set(audit['files']) & files.keys():
            raise ValueError('audit files must not replace source or development inputs')
        files.update(audit['files'])
        worker = worker_factory(manifest)
        budget = WorkflowBudget(manifest['limits'], deadline=deadline)
        budget.remaining()
        identity = worker.identity()
        checks = [check(worker, files, assertion['command'], budget, assertion, manifest['commands']['build']) for assertion in audit['checks']]
        results.append({'candidate': index, 'status': 'PASS' if all(c['status'] == 'PASS' for c in checks) else 'FAIL',
                        'decision': candidate['decision'], 'checks': checks})
    ready = [r for r in results if r['decision'] == 'READY_FOR_REVIEW']
    status = ('PASS' if ready and all(r['status'] == 'PASS' for r in ready) else 'FAIL' if ready
              else 'CORRECT_REJECTED_OR_UNRESOLVED' if any(r['status'] == 'PASS' for r in results) else 'NOT_READY')
    return {'status': status, 'candidates': results, 'property_scope': audit.get('properties'),
            'worker_context': audit['context'], 'worker_image': manifest['image'], 'worker_identity': identity,
            'audit_definition_digest': case['audit_digest'], 'updated': datetime.now(timezone.utc).isoformat()}


def campaign(path, output, store=None, seconds=None, audit_reserve=None, resume=False, allow_demo=False,
             cancelled=None, progress=None, deadline=None):
    definition = json.loads(Path(path).read_text(encoding='utf-8'))
    allowance = dict(definition.get('campaign_budget', DEFAULT_CAMPAIGN_BUDGET))
    if seconds is not None:
        allowance['seconds'] = seconds
    if audit_reserve is not None:
        allowance['audit_reserve_seconds'] = audit_reserve
    allowance = campaign_budget(allowance)
    seconds, audit_reserve = allowance['seconds'], allowance['audit_reserve_seconds']
    cancelled = cancelled or threading.Event()
    progress = progress or (lambda state: None)
    store = store or Store()
    frozen = freeze(path, allowance, store)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    state = {'freeze': frozen, 'rows': [], 'pending': [], 'status': 'PARTIAL', 'elapsed_seconds': 0,
             'release_complete': False, 'unstarted': [], 'active': None,
             'language_status': {lang: 'EXPERIMENTAL' for lang in LANGUAGES}}
    if resume and output.exists():
        previous = json.loads(output.read_text(encoding='utf-8'))
        if previous['freeze']['digest'] != frozen['digest']:
            raise ValueError('evaluation changed; use a new version rather than retuning a frozen campaign')
        state = previous
    # A process lost between launching an attempt and saving its report must not
    # silently receive a new model/candidate allowance on resume.
    if state.get('active'):
        interrupted = dict(state['active'])
        interrupted.update(decision='INSUFFICIENT_EVIDENCE', audit='UNRESOLVED',
                           reason='INTERRUPTED_BEFORE_CHECKPOINT',
                           seconds=frozen['attempt_budget']['seconds'],
                           model_calls=frozen['attempt_budget']['model_calls'],
                           consumption_policy='Conservatively charged full allowance; attempt is not retried')
        failure = {'id': new_id(), 'created': datetime.now(timezone.utc).isoformat(),
                   'scenario': 'campaign-attempt-failure', **interrupted, 'candidates': [], 'findings': []}
        store.save(failure, {'attempt.json': json.dumps(failure, indent=2)})
        interrupted['run_id'] = failure['id']
        state['elapsed_seconds'] += frozen['attempt_budget']['seconds']
        state['rows'].append(interrupted)
        state['active'] = None
    tasks = schedule(frozen['cases'])
    expected_keys = {(c['id'], w, a, r) for c, w, a, r in tasks}
    row_keys = [(r['case'], r['workflow'], r['arm'], r['repetition']) for r in state['rows']]
    if len(set(row_keys)) != len(row_keys) or not set(row_keys).issubset(expected_keys):
        raise ValueError('checkpoint contains duplicate or unscheduled attempts')
    if not isinstance(state['elapsed_seconds'], (int, float)) or state['elapsed_seconds'] < 0:
        raise ValueError('invalid checkpoint time consumption')
    # Distinct context names alone do not establish independent guest kernels.
    if any(load(Path(path).resolve().parent / c['target'],
                Path(path).resolve().parent / c['manifest'])[0]['worker']['mode'] == 'dedicated'
           for c in frozen['cases']):
        from .preflight import attest_campaign
        state['worker_preflight'] = attest_campaign(path, frozen)
    started = time.monotonic()
    prior_elapsed = state['elapsed_seconds']
    campaign_deadline = started + max(0, seconds - prior_elapsed)
    if deadline is not None:
        import math
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError('external deadline must be a finite monotonic time')
        campaign_deadline = min(campaign_deadline, deadline)
    execution_deadline = campaign_deadline - audit_reserve
    completed = {(r['case'], r['workflow'], r['arm'], r['repetition']) for r in state['rows']}

    def save():
        state['updated'] = datetime.now(timezone.utc).isoformat()
        state['elapsed_seconds'] = prior_elapsed + time.monotonic() - started
        temporary = output.with_suffix(output.suffix + '.tmp')
        temporary.write_text(json.dumps(state, indent=2), encoding='utf-8')
        temporary.replace(output)
        progress({'attempted': len(state['rows']), 'scheduled': len(tasks),
                  'pending_audits': len(state['pending']), 'active': state.get('active')})

    for case, workflow, arm, repetition in tasks:
        key = (case['id'], workflow, arm, repetition)
        if key in completed:
            continue
        if cancelled.is_set() or time.monotonic() >= execution_deadline:
            break
        row = {'case': case['id'], 'language': case['language'], 'workflow': workflow, 'arm': arm, 'repetition': repetition}
        state['active'] = row
        save()
        attempt_started = time.monotonic()
        provider, budget = None, None
        try:
            base = Path(path).resolve().parent
            manifest_path = (base / case['manifest']).resolve()
            target = (base / case['target']).resolve()
            manifest, files = load(target, manifest_path)
            if manifest['revision'] != case['source_revision'] or digest(manifest_path.read_bytes()) != case['manifest_digest']:
                raise ValueError('frozen source/manifest changed')
            if arm == 'model-only':
                # Same model/budget and the same independent verifier/final audit.
                # Baseline skips static/discovery feedback when producing its first proposal.
                from .model import LocalModel, context
                provider = LocalModel(manifest['model'])
                budget = WorkflowBudget(manifest['limits'], cancelled, deadline=execution_deadline)
                from .patching import proposal_diff
                answer = provider.suggest(context(files, manifest, {'description': case.get('description', '')}), budget)
                proposal = proposal_diff(answer, files, manifest['editable'])
                report = run_project(target, manifest_path, workflow, problem={'description': case.get('description', '')},
                                     patch=proposal, store=store, allow_demo=allow_demo, model=provider,
                                     initial_consumption={'model_calls': budget.model_calls, 'seconds': time.monotonic() - budget.start},
                                     proposal_origin='local-model-baseline', deadline=execution_deadline, cancelled=cancelled)
                row['proposal_calls'] = budget.model_calls
                row['proposal_usage'] = provider.usage
                row['proposal_seconds'] = time.monotonic() - budget.start
            else:
                report = run_project(target, manifest_path, workflow, problem={'description': case.get('description', '')},
                                     store=store, allow_demo=allow_demo, deadline=execution_deadline, cancelled=cancelled)
            row.update(run_id=report['id'], decision=report['decision'], findings=report['findings'],
                       seconds=report['elapsed_seconds'], model_calls=report['model_calls'], reason=report['reason'])
            if report['candidates']:
                state['pending'].append({'row_key': list(key), 'run_id': report['id'], 'case': case})
            row['audit'] = 'PENDING' if report['candidates'] else 'NOT_READY'
        except (Exception, KeyboardInterrupt) as exc:
            row.update(decision='INSUFFICIENT_EVIDENCE', audit='UNRESOLVED', error=type(exc).__name__,
                       seconds=time.monotonic() - attempt_started,
                       model_calls=budget.model_calls if budget else 0,
                       reason='CANCELLED' if isinstance(exc, (KeyboardInterrupt, InterruptedError)) else 'ATTEMPT_FAILURE')
            if provider is not None:
                row['proposal_usage'] = provider.usage
            failure = {'id': new_id(), 'created': datetime.now(timezone.utc).isoformat(),
                       'scenario': 'campaign-attempt-failure', **row, 'candidates': [], 'findings': []}
            store.save(failure, {'attempt.json': json.dumps(failure, indent=2)})
            row['run_id'] = failure['id']
            if isinstance(exc, (KeyboardInterrupt, InterruptedError)):
                cancelled.set()
        state['rows'].append(row)
        state['active'] = None
        completed.add(key)
        save()
    for pending in list(state['pending']):
        if cancelled.is_set() or time.monotonic() >= campaign_deadline:
            break
        key = tuple(pending['row_key'])
        row = next(r for r in state['rows'] if (r['case'], r['workflow'], r['arm'], r['repetition']) == key)
        try:
            audit = final_audit(store.load(pending['run_id']), pending['case'], path, store, deadline=campaign_deadline)
            row['audit'] = audit['status']
            row['audit_observations'] = audit
        except Exception as exc:
            row.update(audit='UNRESOLVED', audit_error=type(exc).__name__)
        else:
            row.pop('audit_error', None)
            state['pending'].remove(pending)
        save()
    state['unstarted'] = [{'case': c['id'], 'workflow': w, 'arm': a, 'repetition': r} for c, w, a, r in tasks
                          if (c['id'], w, a, r) not in completed]
    for lang in LANGUAGES:
        rows = [r for r in state['rows'] if r['language'] == lang and r['arm'] == 'expanded']
        if (all(any(r['workflow'] == w and r['decision'] == 'READY_FOR_REVIEW' and r['audit'] == 'PASS' for r in rows)
                for w in ('repair', 'discover')) and all(r['audit'] == 'PASS' for r in rows if r['decision'] == 'READY_FOR_REVIEW')):
            state['language_status'][lang] = 'ACCEPTANCE_DEMONSTRATED'
    interrupted_rows = any(r.get('reason') == 'INTERRUPTED_BEFORE_CHECKPOINT' for r in state['rows'])
    state['status'] = 'COMPLETE' if not state['unstarted'] and not state['pending'] and not interrupted_rows else 'CANCELLED' if cancelled.is_set() else 'PARTIAL'
    state['release_complete'] = (frozen['complete_24_case_cohort'] and state['status'] == 'COMPLETE'
        and all(v == 'ACCEPTANCE_DEMONSTRATED' for v in state['language_status'].values())
        and all(r['audit'] == 'PASS' for r in state['rows'] if r['decision'] == 'READY_FOR_REVIEW'))
    state['metrics'] = {'scheduled': len(tasks), 'attempted': len(state['rows']), 'unstarted': len(state['unstarted']),
                        'pending_audits': len(state['pending']),
                        'working_repairs': sum(r['decision'] == 'READY_FOR_REVIEW' and r['audit'] == 'PASS' for r in state['rows']),
                        'unsafe_or_broken_ready': sum(r['decision'] == 'READY_FOR_REVIEW' and r['audit'] == 'FAIL' for r in state['rows']),
                        'correct_rejected_or_unresolved': sum(r['audit'] == 'CORRECT_REJECTED_OR_UNRESOLVED' for r in state['rows']),
                        'confirmed_discoveries': sum(bool(r.get('findings')) for r in state['rows'] if r['workflow'] == 'discover'),
                        'missed_known_violations': sum(r.get('reason') == 'NO_VIOLATION_FOUND' for r in state['rows'] if r['workflow'] == 'discover'),
                        'unresolved': sum(r['decision'] == 'INSUFFICIENT_EVIDENCE' or r['audit'] == 'UNRESOLVED' for r in state['rows'])}
    state['by_language_and_arm'] = {lang: {arm: [r for r in state['rows'] if r['language'] == lang and r['arm'] == arm]
                                         for arm in ('expanded', 'model-only')} for lang in LANGUAGES}
    save()
    evidence = {'id': new_id(), 'created': datetime.now(timezone.utc).isoformat(), 'scenario': 'external-campaign',
                'decision': 'READY_FOR_REVIEW' if state['release_complete'] else 'INSUFFICIENT_EVIDENCE', **state}
    store.save(evidence, {'campaign.json': json.dumps(state, indent=2)})
    state['signed_run_id'] = evidence['id']
    # Save the exact signed snapshot without altering its timestamp or elapsed
    # time. The reference is outside the signed snapshot to avoid self-binding.
    temporary = output.with_suffix(output.suffix + '.tmp')
    temporary.write_text(json.dumps(state, indent=2), encoding='utf-8')
    temporary.replace(output)
    return state
