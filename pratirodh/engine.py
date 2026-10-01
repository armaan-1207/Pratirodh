"""Contract-based verification for controlled Flask fixtures, with abstention."""
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from .contracts import load_contract, evaluate_output, validate_case, violation
from .fuzzing import generate, VERSION
from .evidence import Store, bindings, fresh, new_id
from .execution import Budget, DockerExecutor
from .patches import apply_diff, static_scan


def decision(checks, gaps):
    if any(c['status'] == 'FAIL' for c in checks):
        return 'REJECT'
    if gaps or not checks or any(c['status'] != 'PASS' for c in checks):
        return 'INSUFFICIENT_EVIDENCE'
    return 'READY_FOR_REVIEW'


def run(target, contract_path, patch=None, store=None, mode='full', executor=None, model=None, findings=None, origin=None, seed=0, strategy="ollama", seconds=None, progress=None):
    if mode not in {'static', 'fixed', 'ai', 'full', 'unguided'}:
        raise ValueError('unknown verification mode')
    if strategy not in {'combined', 'ollama', 'template'}:
        raise ValueError('unknown repair strategy')
    if patch is None and strategy == 'combined' and model is not None and getattr(model, 'origin', '') != 'local-model':
        raise ValueError('combined repair requires the restricted local model adapter')
    target, contract_path = Path(target).resolve(), Path(contract_path).resolve()
    store, executor = store or Store(), executor or DockerExecutor()
    budget = Budget(seconds=seconds or (600 if patch is None else 300), max_model_calls=2 if patch is None else 4)
    report = dict(id=new_id(), created=datetime.now(timezone.utc).isoformat(),
                  target_path=str(target), contract_path=str(contract_path), scenario=target.name,
                  cwe='unknown', mode=mode, strategy=strategy, candidates=[], gaps=[], model_calls=0, model_usage=[],
                  decision='INSUFFICIENT_EVIDENCE', bindings={}, findings=findings or [], stages=[],
                  fuzz_generator=VERSION, fuzz_seed=seed, request_executions=0)
    artifacts = {}
    def notify(stage, candidate=0, generator=''):
        if progress:
            try:
                progress(stage=stage, candidate=candidate, generator=generator)
            except Exception:
                pass  # A display observer cannot change verification or its evidence.
    try:
        contract = load_contract(contract_path)
        report.update(scenario=contract['id'], cwe=contract['cwe'])
        source_path = target / contract['entrypoint']
        if source_path.is_symlink() or not source_path.resolve().is_relative_to(target):
            raise ValueError('entrypoint escapes target')
        source = source_path.read_text(encoding='utf-8')
        if len(source.encode('utf-8')) > 262144:
            raise ValueError('target source exceeds 256 KB limit')
        artifacts.update({'original.py': source, 'contract.json': json.dumps(contract, indent=2)})
        report['bindings'] = bindings(target, contract_path, executor.identity())
        all_cases = contract['cases'] + contract.get('probes', [])

        def execute(sources, cases):
            if len(cases) > 100:
                raise ValueError('request definition budget exceeded')
            outputs = executor.batch(sources, contract, cases, budget)
            report['request_executions'] += len(sources) * len(cases)
            return [evaluate_output(out, cases, contract) for out in outputs]

        notify('reproduce')
        baseline = execute([source], contract['cases'])[0]
        report['baseline'] = baseline
        if any(c['status'] != 'PASS' for c in baseline if c['case']['kind'] == 'benign'):
            raise RuntimeError('baseline legitimate behavior did not pass')
        if not any(violation(c) for c in baseline):
            raise RuntimeError('declared security violation was not reproduced in baseline')
        report['stages'].append({'stage': 'reproduce', 'status': 'PASS'})

        feedback = ''
        from .candidates import TemplateGenerator, ModelGenerator
        matching = [f for f in findings or [] if f.get('cwe') == contract['cwe'] and f.get('file') == str(source_path.resolve())]
        matching.sort(key=lambda f: ({'HIGH':0,'MEDIUM':1,'LOW':2}.get(f.get('severity'),3), f.get('line',0)))
        finding = matching[0] if matching else None
        generators = ([None] if patch is not None else
                      ([TemplateGenerator(isolated=True)] if strategy in {'combined', 'template'} else []) +
                      ([ModelGenerator(model), ModelGenerator(model)] if strategy in {'combined', 'ollama'} else []))
        for index, generator in enumerate(generators):
            notify('generate' if patch is None else 'verify', index + 1,
                   'template' if isinstance(generator, TemplateGenerator) else 'local-model' if patch is None else 'curated')
            candidate = dict(origin=origin or ('supplied' if patch is not None else 'template' if isinstance(generator, TemplateGenerator) else getattr(model, 'origin', 'local-model')), patch='',
                             checks=[], gaps=[], mutations=[], strengthened_cases=[])
            report['candidates'].append(candidate)
            try:
                if patch is None:
                    defaults = {'CWE-22': 'Permit reads only within the public directory after canonicalizing paths and following symlinks. Preserve the existing endpoint and legitimate download responses.',
                                'CWE-89': 'Use SQLite parameter placeholders for user input, never concatenate or interpolate request inputs into SQL. Preserve the current endpoint and legitimate search results.'}
                    public_requirements = contract.get('requirements', [defaults.get(contract['cwe'], 'Preserve legitimate behaviour and prohibit the declared ' + contract['cwe'] + ' violation.')])
                    prompt = ('The following Python application is vulnerable. FIX the vulnerability by changing its code. '
                              'Return JSON with a source string containing the entire repaired Python file. '
                              'Do not return the unchanged vulnerable source. Preserve its legitimate functionality. '
                              + '\nRepair requirements:\n' + json.dumps(public_requirements)
                              + '\nVulnerable file ' + contract['entrypoint'] + ':\n' + source
                              + '\nPrevious verification feedback:\n' + feedback)
                    proposal = generator.generate(source, contract['entrypoint'], finding, prompt, budget)
                    candidate.update(origin=proposal.origin, generation=proposal.record())
                    if proposal.outcome != 'GENERATED':
                        candidate['gaps'].append(proposal.detail)
                        candidate['decision'] = 'INSUFFICIENT_EVIDENCE'
                        continue
                    candidate_patch = proposal.patch
                else:
                    candidate_patch = patch
                candidate['patch'] = candidate_patch
                artifacts[f'candidate-{index}.diff'] = candidate_patch
                try:
                    updated = apply_diff(source, candidate_patch, contract['entrypoint'])
                except (ValueError, SyntaxError) as exc:
                    candidate['checks'].append({'status': 'FAIL', 'error': str(exc), 'type': 'patch-policy'})
                    candidate['decision'] = 'REJECT'
                    feedback = 'No valid allowed repair diff was produced. Change the vulnerable code and return a complete repaired source file.'
                    continue
                artifacts[f'candidate-{index}.py'] = updated
                cases = list(contract['cases'])
                if mode == 'static':
                    cases = [c for c in cases if c['kind'] == 'benign']
                if mode == 'ai':
                    if model is None:
                        raise RuntimeError('AI test baseline requires a configured model')
                    suggestions = model.suggest('Return JSON with cases, a list of at most 20 structured GET/POST '
                                                'attack cases using only these assertion ids. No test code. '
                                                + json.dumps(contract['assertions']) + '\nSource:\n' + updated, budget)
                    generated = suggestions.get('cases', [])
                    if not isinstance(generated, list) or len(generated) > 20:
                        raise ValueError('invalid model cases')
                    for c in generated:
                        validate_case(c, contract['assertions'])
                        if c.get('kind') != 'attack' or contract['assertions'][c['assertion']]['type'] != 'security':
                            raise ValueError('model cases must reference security assertions')
                    if len({c['id'] for c in cases + generated}) != len(cases + generated):
                        raise ValueError('duplicate model case ids')
                    cases += generated
                notify('verify', index + 1, candidate['origin'])
                candidate['checks'] = execute([updated], cases)[0]
                candidate['checks'].append(static_scan(updated, budget))
                if contract.get('forbidden_source'):
                    candidate['checks'].append({'type': 'embedded-credential', 'status': 'FAIL' if any(
                        value in updated for value in contract['forbidden_source']) else 'PASS'})
                additional = 0
                if mode == 'full':
                    notify('challenge', index + 1, candidate['origin'])
                    # Every reviewed probe is tested against the real candidate, even if mutation creation fails.
                    known = {c['id'] for c in cases}
                    extra = [c for c in contract.get('probes', []) if c['id'] not in known]
                    candidate['strengthened_cases'] = extra
                    if extra:
                        candidate['checks'].extend(execute([updated], extra)[0])
                        additional += len(extra)
                    final_cases = cases + extra
                    for mutation in contract['mutations']:
                        record = dict(family=mutation['family'], status='UNAVAILABLE', missed_before=False)
                        candidate['mutations'].append(record)
                        if updated.count(mutation['find']) != 1:
                            candidate['gaps'].append(mutation['family'] + ': source pattern unavailable')
                            continue
                        weakened = updated.replace(mutation['find'], mutation['replace'], 1)
                        try:
                            ast.parse(weakened)
                        except SyntaxError:
                            record['status'] = 'INVALID'
                            candidate['gaps'].append(mutation['family'] + ': invalid mutant')
                            continue
                        artifacts[f'mutant-{index}-{len(candidate["mutations"])}.py'] = weakened
                        if additional + len(all_cases) > 64:
                            candidate['gaps'].append('mutation qualification budget exhausted')
                            continue
                        qualification = execute([weakened], all_cases)[0]
                        additional += len(all_cases)
                        benign_ok = all(c['status'] == 'PASS' for c in qualification if c['case']['kind'] == 'benign')
                        witness = next((c for c in qualification if c['case']['id'] in mutation['witnesses']
                                        and violation(c)), None)
                        if not benign_ok or witness is None:
                            record['status'] = 'UNCONFIRMED'
                            candidate['gaps'].append(mutation['family'] + ': unsafe witness not qualified')
                            continue
                        record.update(status='CONFIRMED_UNSAFE', witness=witness)
                        initial_ids = {c['id'] for c in cases}
                        final_ids = {c['id'] for c in final_cases}
                        record['missed_before'] = all(c['status'] == 'PASS' for c in qualification if c['case']['id'] in initial_ids)
                        record['missed_after'] = all(c['status'] == 'PASS' for c in qualification if c['case']['id'] in final_ids)
                        if record['missed_after']:
                            candidate['gaps'].append(mutation['family'] + ': confirmed unsafe mutant survived')
                if mode in {'full', 'unguided'}:
                    notify('security-checks', index + 1, candidate['origin'])
                    fuzz = generate(contract, seed, 64 - additional)
                    fuzz_checks = execute([updated], fuzz)[0]
                    candidate['checks'].extend(fuzz_checks)
                    if any(c['status'] == 'ERROR' for c in fuzz_checks):
                        candidate['gaps'].append('fuzzing contains unavailable observations')
                    additional += len(fuzz)
                    candidate['fuzzing'] = {'seed': seed, 'generator': VERSION, 'additional_executions': additional,
                                            'limit': 64, 'strategy': mode}
                candidate['decision'] = decision(candidate['checks'], candidate['gaps'])
            except Exception as exc:
                candidate.setdefault('generation', {'generator': 'historical-template' if isinstance(generator, TemplateGenerator) else 'model', 'origin': candidate['origin'], 'source_revision': report['bindings'].get('target'), 'finding': finding, 'outcome': 'ERROR', 'detail': type(exc).__name__})
                candidate['gaps'].append(type(exc).__name__ + ': ' + str(exc)[:400])
                candidate['decision'] = decision(candidate['checks'], candidate['gaps'])
            feedback = json.dumps({'decision': candidate['decision'], 'gaps': candidate['gaps'],
                                   'failed_properties': [c.get('type', c.get('expected', {}).get('type')) for c in candidate['checks'] if c['status'] != 'PASS']})
            if candidate['decision'] == 'READY_FOR_REVIEW':
                break
            if time.monotonic() >= budget.deadline:
                report['gaps'].append('workflow budget exhausted; remaining candidates unstarted')
                break
        outcomes = [c['decision'] for c in report['candidates']]
        report['decision'] = ('READY_FOR_REVIEW' if 'READY_FOR_REVIEW' in outcomes else
                              'INSUFFICIENT_EVIDENCE' if 'INSUFFICIENT_EVIDENCE' in outcomes else 'REJECT')
        report['gaps'] += [g for c in report['candidates'] for g in c['gaps']]
    except Exception as exc:
        report['gaps'].append(type(exc).__name__ + ': ' + str(exc)[:400])
    report.update(elapsed_seconds=round(time.monotonic() - budget.start, 3), model_calls=budget.model_calls,
                  model_usage=getattr(model, 'usage', []))
    report['stages'].extend([{'stage': 'propose', 'status': 'COMPLETE' if report['candidates'] else 'UNAVAILABLE'},
                            {'stage': 'verify', 'status': report['decision']}, {'stage': 'human-review', 'status': 'PENDING'}])
    artifacts['observed.json'] = json.dumps(report, indent=2)
    notify('sign', len(report['candidates']))
    store.save(report, artifacts)
    return report


def replay(run_id, case_id, store=None, candidate=0, executor=None):
    store, executor = store or Store(), executor or DockerExecutor()
    report = store.load(run_id)
    if not fresh(report, executor):
        raise ValueError('evidence is stale; create a new verification run')
    selected = report['candidates'][candidate]
    case = next(c['case'] for c in selected['checks'] if c.get('case', {}).get('id') == case_id)
    path = store.run_path(run_id)
    contract = json.loads((path / 'contract.json').read_text(encoding='utf-8'))
    source = (path / f'candidate-{candidate}.py').read_text(encoding='utf-8')
    output = executor.batch([source], contract, [case], Budget())[0]
    check = evaluate_output(output, [case], contract)[0]
    return dict(run_id=run_id, check=check, recorded_status=next(c['status'] for c in selected['checks']
                if c.get('case', {}).get('id') == case_id), executed_at=datetime.now(timezone.utc).isoformat())
