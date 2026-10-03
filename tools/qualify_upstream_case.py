"""Execute a reviewed upstream qualification recipe on separate worker guests."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pratirodh.projects.qualification import qualify_case
from pratirodh.evidence import Store, digest, new_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'benchmark/upstream-v2/manifest.json')
    parser.add_argument('--case', required=True)
    parser.add_argument('--recipe', required=True, type=Path)
    parser.add_argument('--index', type=Path, default=ROOT / 'run_output/upstream-validation/qualification-index.json')
    parser.add_argument('--usage-ledger', type=Path,
                        help='Validated Azure usage ledger; required before executing on cloud workers')
    args = parser.parse_args()

    # Validate cloud budget before touching any worker.
    if args.usage_ledger:
        from pratirodh.projects.cloud_budget import window as cloud_window
        ledger = json.loads(args.usage_ledger.read_text(encoding='utf-8'))
        allowance = cloud_window(ledger)
        if allowance['seconds'] < 60:
            parser.error('Approved usage allowance exhausted: ' + str(allowance))
        print(f'Cloud allowance validated: ${allowance["available_usd"]:.2f} remaining '
              f'({allowance["seconds"]}s window)', flush=True)

    definition = json.loads(args.manifest.read_text(encoding='utf-8'))
    case = next((c for c in definition['cases'] if c['id'] == args.case), None)
    if case is None:
        parser.error('unknown case: ' + args.case)
    recipe = json.loads(args.recipe.read_text(encoding='utf-8'))
    if recipe.get('approved') is not True or not recipe.get('adaptations'):
        parser.error('recipe must record reviewed source adaptations and explicit approval')
    base = args.recipe.resolve().parent
    store = Store(ROOT / 'run_output/pratirodh')
    try:
        result = qualify_case(case, ROOT / case['acquisition'], base / recipe['target'],
                              base / recipe['manifest'], base / recipe['audit'], recipe['source_map'],
                              recipe['license_review'], store, recipe_digest=digest(args.recipe.read_bytes()))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        result = {'id': new_id(), 'created': datetime.now(timezone.utc).isoformat(),
                  'scenario': 'upstream-qualification', 'case': case['id'],
                  'decision': 'INSUFFICIENT_EVIDENCE', 'status': 'QUALIFICATION_FAILED',
                  'reason': 'QUALIFICATION_INPUT_OR_WORKER_FAILURE', 'error': type(error).__name__,
                  'recipe_digest': digest(args.recipe.read_bytes()), 'model_calls': 0}
        store.save(result, {'qualification.json': json.dumps(result, indent=2)})
    index = json.loads(args.index.read_text(encoding='utf-8')) if args.index.exists() else {'cases': {}}
    manifest_digest = digest(args.manifest.read_bytes())
    if index.get('manifest_digest') not in {None, manifest_digest}:
        parser.error('qualification index belongs to a different cohort; choose a new index')
    index.update(manifest_digest=manifest_digest, updated=datetime.now(timezone.utc).isoformat())
    index['cases'][case['id']] = {'run_id': result['id'], 'status': result['status'],
                                 'recipe': str(args.recipe.resolve()),
                                 'execution_manifest': str((base / recipe['manifest']).resolve()),
                                 'audit': str((base / recipe['audit']).resolve())}
    args.index.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.index.with_suffix('.tmp')
    temporary.write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')
    temporary.replace(args.index)
    print(json.dumps({'case': case['id'], 'run_id': result['id'], 'status': result['status']}, indent=2))
    return 0 if result['status'] == 'QUALIFIED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
