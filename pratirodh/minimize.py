"""Bounded reduction of a recorded canary witness, never an invented failure."""
import copy
import json
from .contracts import evaluate_output, violation
from .evidence import Store, fresh
from .execution import DockerExecutor, Budget


def minimize(run_id, case_id, candidate=0, store=None, executor=None):
    store, executor = store or Store(), executor or DockerExecutor()
    report = store.load(run_id)
    if not fresh(report, executor):
        raise ValueError('evidence is stale')
    recorded = next(c for c in report['candidates'][candidate]['checks'] if c.get('case', {}).get('id') == case_id)
    if recorded['status'] != 'FAIL' or recorded['case']['kind'] != 'attack':
        raise ValueError('minimization requires a recorded security failure')
    path = store.run_path(run_id)
    contract = json.loads((path / 'contract.json').read_text(encoding='utf-8'))
    source = (path / f'candidate-{candidate}.py').read_text(encoding='utf-8')
    best = recorded['case']
    variants = []
    for transport in ('query', 'form', 'json'):
        for key, value in best.get(transport, {}).items():
            if not isinstance(value, str):
                continue
            for reduced in (value.strip(), value[:len(value)//2], value[len(value)//2:], value.replace(' ', ''), ''):
                if reduced == value:
                    continue
                variant = copy.deepcopy(best)
                variant[transport][key] = reduced
                variant['id'] = f'minimize-{len(variants)}'
                variants.append(variant)
    variants = variants[:8]
    if not variants:
        return {'run_id': run_id, 'case': best, 'attempts': 0, 'minimality': 'bounded reduction only'}
    output = executor.batch([source], contract, variants, Budget())[0]
    checks = evaluate_output(output, variants, contract)
    confirmed = [c for c in checks if violation(c)]
    if confirmed:
        best = min([recorded] + confirmed, key=lambda c: len(json.dumps(c['case'])))['case']
    return {'run_id': run_id, 'case': best, 'attempts': len(variants), 'observations': checks,
            'minimality': 'bounded reduction; global minimality is not established'}
