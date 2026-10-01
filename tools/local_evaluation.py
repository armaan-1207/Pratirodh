"""Record every genuine local repair attempt in a separate cohort."""
import json
from pathlib import Path
from pratirodh.engine import run
from pratirodh.provider import OllamaModel
from pratirodh.detection import scan

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / 'run_output/local-evaluation.json'
    result = {'cohort': 'real local Ollama generation', 'rows': [], 'curated': False}
    catalogue = json.loads((ROOT / 'benchmark/catalogue.json').read_text())
    for cwe in ['CWE-22', 'CWE-89', 'CWE-78', 'CWE-798']:
        scenarios = [s for s in catalogue if s['cwe'] == cwe and s['split'] == 'development'][:2]
        for scenario in scenarios:
            directory = ROOT / 'benchmark/scenarios' / scenario['id']
            report = run(directory, directory / 'contract.json', model=OllamaModel(), findings=scan(directory / 'app.py'))
            result['rows'].append({'scenario': scenario['id'], 'cwe': cwe, 'run_id': report['id'],
                                   'decision': report['decision'], 'seconds': report['elapsed_seconds'],
                                   'model_usage': report['model_usage'], 'gaps': report['gaps'],
                                   'request_executions': report['request_executions']})
            output.write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(scenario['id'], report['decision'], report['elapsed_seconds'], flush=True)
    result['metrics'] = {'total': len(result['rows']), 'ready': sum(r['decision'] == 'READY_FOR_REVIEW' for r in result['rows']),
                         'rejected': sum(r['decision'] == 'REJECT' for r in result['rows']),
                         'insufficient': sum(r['decision'] == 'INSUFFICIENT_EVIDENCE' for r in result['rows'])}
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
