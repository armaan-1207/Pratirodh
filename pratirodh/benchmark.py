"""Disclosed curated benchmark; AI results are a separate, optional cohort."""
import json
from pathlib import Path
from .engine import run
from .provider import CloudModel
from concurrent.futures import ThreadPoolExecutor, as_completed


def benchmark(split='all', cloud=False, model=None, output='run_output/benchmark.json'):
    if split == 'held-out':
        split = 'heldout'
    root = Path(__file__).resolve().parents[1] / 'benchmark'
    catalogue = json.loads((root / 'catalogue.json').read_text())
    result = {'cohort': 'curated synthetic patches', 'rows': [], 'metrics': {},
              'ai_baseline': 'RUN' if cloud else 'NOT_RUN',
              'limitations': 'Related synthetic scenarios and public labels limit generalization. Full and unguided have equal additional request budgets; full spends part on qualification. Mandatory tests and candidate patches are identical.'}
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    tasks = []
    for scenario in catalogue:
        if split != 'all' and scenario['split'] != split:
            continue
        directory = root / 'scenarios' / scenario['id']
        for label in scenario['labels']:
            for mode in ['static', 'fixed', 'full', 'unguided'] + (['ai'] if cloud else []):
                tasks.append((scenario, directory, label, mode))

    def evaluate_task(task):
                scenario, directory, label, mode = task
                provider = CloudModel(model=model) if mode == 'ai' else None
                report = run(directory, directory / 'contract.json',
                             (directory / 'patches' / (label + '.diff')).read_text(encoding='utf-8'),
                             mode=mode, model=provider)
                candidates = report['candidates']
                return dict(scenario=scenario['id'], split=scenario['split'], label=label,
                    mode=mode, decision=report['decision'], run_id=report['id'], gaps=report['gaps'],
                    seconds=report['elapsed_seconds'], model_calls=report['model_calls'], model_usage=report['model_usage'],
                    requests=report['request_executions'], additional_requests=sum(c.get('fuzzing', {}).get('additional_executions', 0) for c in candidates),
                    missed_before=sum(m['missed_before'] for c in candidates for m in c.get('mutations', [])),
                    missed_after=sum(m.get('missed_after', False) for c in candidates for m in c.get('mutations', [])))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(evaluate_task, task) for task in tasks]
        for future in as_completed(futures):
                row = future.result()
                result['rows'].append(row)
                result['metrics'] = metrics(result['rows'])
                path.write_text(json.dumps(result, indent=2), encoding='utf-8')
                print('Completed', row['scenario'], row['label'], row['mode'], row['decision'], flush=True)
    return result


def metrics(rows):
    output = {}
    for mode in sorted({r['mode'] for r in rows}):
        subset = [r for r in rows if r['mode'] == mode]
        output[mode] = dict(total=len(subset), correct_total=sum(r['label'] == 'correct' for r in subset),
            correct_ready=sum(r['label'] == 'correct' and r['decision'] == 'READY_FOR_REVIEW' for r in subset),
            incorrect_total=sum(r['label'] != 'correct' for r in subset),
            incorrect_ready=sum(r['label'] != 'correct' and r['decision'] == 'READY_FOR_REVIEW' for r in subset),
            correct_rejected=sum(r['label'] == 'correct' and r['decision'] == 'REJECT' for r in subset),
            abstentions=sum(r['decision'] == 'INSUFFICIENT_EVIDENCE' for r in subset),
            seconds=round(sum(r['seconds'] for r in subset), 2))
    return output
