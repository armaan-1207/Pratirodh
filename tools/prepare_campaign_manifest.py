"""Assemble frozen execution inputs from all 24 signed qualifications."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pratirodh.evidence import Store, digest
from pratirodh.projects.evaluation import freeze


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--intake', type=Path, default=ROOT / 'benchmark/upstream-v2/manifest.json')
    parser.add_argument('--index', type=Path, default=ROOT / 'run_output/upstream-validation/qualification-index.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'run_output/upstream-validation/execution-manifest.json')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output; frozen campaign inputs are never overwritten')
    definition = json.loads(args.intake.read_text(encoding='utf-8'))
    index = json.loads(args.index.read_text(encoding='utf-8'))
    if index.get('manifest_digest') != digest(args.intake.read_bytes()):
        parser.error('qualification index does not match current intake')
    store = Store(ROOT / 'run_output/pratirodh')
    cases = []
    for case in definition['cases']:
        row = index.get('cases', {}).get(case['id'], {})
        if not row.get('run_id'):
            parser.error('missing executable qualification: ' + case['id'])
        report = store.load(row['run_id'])
        if report.get('status') != 'QUALIFIED' or report.get('case') != case['id']:
            parser.error('case qualification failed: ' + case['id'])
        recipe_path = Path(row['recipe'])
        recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
        if report.get('recipe_digest') != digest(recipe_path.read_bytes()):
            parser.error('recipe changed since qualification: ' + case['id'])
        base = recipe_path.parent
        relative = lambda p: Path(os.path.relpath(p, args.output.resolve().parent)).as_posix()
        cases.append({'id': case['id'], 'language': {'Python': 'python', 'JavaScript': 'node', 'C/C++': 'cpp'}[case['language']],
            'split': case['split'], 'target': relative((base / recipe['target']).resolve()),
            'manifest': relative(Path(row['execution_manifest'])), 'audit': relative(Path(row['audit'])),
            'qualification_run_id': row['run_id'], 'description': recipe.get('description', case['cwe']),
            'qualification_recipe': relative(recipe_path.resolve()),
            'provenance': {'license': report['license_review']['identifier'], 'source_url': case['advisory_url'],
                           'upstream_fix_url': case['fix_url'], 'adaptations': recipe['adaptations']}})
    data = {'version': 1, 'cohort': definition['cohort'], 'require_qualification': True,
            'intake_manifest_digest': digest(args.intake.read_bytes()), 'cases': cases,
            'attempt_budget': {k: definition['comparison']['arm_budget'][k]
                               for k in ('seconds', 'reserve_seconds', 'model_calls', 'candidates')},
            'campaign_budget': {k: definition['comparison'][k] for k in ('seconds', 'audit_reserve_seconds')}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    frozen = freeze(args.output, store=store)
    args.output.with_suffix('.frozen.json').write_text(json.dumps(frozen, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'cases': len(cases), 'digest': frozen['digest'], 'output': str(args.output)}, indent=2))


if __name__ == '__main__':
    main()
