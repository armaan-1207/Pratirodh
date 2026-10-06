"""Build portable campaign inputs from explicit cohort assignments and recipes.

Generation does not qualify cases or execute models, targets, or workers.
The evaluator's freeze step still validates the live target inventories.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pratirodh.contracts import safe_relative


def read_object(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'{path}: expected an object')
    return data


def upstream_url(value):
    parsed = urlparse(value if isinstance(value, str) else '')
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('upstream provenance requires an HTTPS URL without credentials')
    return value


def local_path(case, value, directory=False):
    safe_relative(value)
    path = (case / value).resolve()
    if not path.is_relative_to(case.resolve()) or not (path.is_dir() if directory else path.is_file()):
        raise ValueError(f'{case.name}: missing or escaping artifact {value}')
    return path


def build_campaign(recipes, cohort_path, output):
    recipes, output = Path(recipes).resolve(), Path(output).resolve()
    cohort = read_object(Path(cohort_path))
    if cohort.get('version') != 1 or not isinstance(cohort.get('cases'), list) or not cohort['cases']:
        raise ValueError('explicit version 1 cohort assignments required')
    records = cohort['cases']
    ids = [c['id'] for c in records]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate cohort case')
    available = {p.name for p in recipes.iterdir() if p.is_dir()}
    if available != set(ids):
        raise ValueError('recipe directories and explicit cohort assignments differ')
    cases = []
    for record in sorted(records, key=lambda c: c['id']):
        name = safe_relative(record['id'])
        if '/' in name or record['split'] not in {'development', 'evaluation'}:
            raise ValueError('invalid cohort id or split')
        case = recipes / name
        recipe = read_object(case / 'recipe.json')
        if recipe.get('case') != name or recipe.get('approved') is not True:
            raise ValueError(f'{name}: approved matching recipe required')
        license_review = recipe.get('license_review', {})
        if license_review.get('approved') is not True or not license_review.get('identifier'):
            raise ValueError(f'{name}: license approval required')
        for field in ('source_revision', 'fix_revision'):
            if not re.fullmatch(r'[0-9a-f]{40}', str(recipe.get(field, ''))):
                raise ValueError(f'{name}: invalid {field}')
        if recipe['fix_revision'] != record['fix_revision']:
            raise ValueError(f'{name}: recipe and cohort reference fix disagree')
        target = local_path(case, recipe['target'], directory=True)
        manifest_path = local_path(case, recipe['manifest'])
        audit_path = local_path(case, recipe['audit'])
        if audit_path.is_relative_to(target):
            raise ValueError(f'{name}: audit must remain outside target')
        manifest = read_object(manifest_path)
        read_object(audit_path)
        language = {'javascript': 'node', 'python': 'python', 'cpp': 'cpp'}.get(name.split('-')[0])
        if language is None or manifest.get('adapter') != language:
            raise ValueError(f'{name}: language and adapter disagree')
        revision = manifest.get('revision', '')
        if not re.fullmatch(r'[0-9a-f]{64}', str(revision)):
            raise ValueError(f'{name}: inventory revision required')
        relative = lambda path: Path(os.path.relpath(path, output.parent)).as_posix()
        cases.append({'id': name, 'language': language, 'split': record['split'],
                      'target': relative(target), 'manifest': relative(manifest_path), 'audit': relative(audit_path),
                      'source_revision': revision,
                      'manifest_digest': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                      'audit_digest': hashlib.sha256(audit_path.read_bytes()).hexdigest(),
                      'description': recipe.get('description', ''),
                      'provenance': {'license': license_review['identifier'],
                                     'source_url': upstream_url(record['advisory_url']),
                                     'repository_url': upstream_url(record['repository_url']),
                                     'upstream_fix_url': upstream_url(record['fix_url']),
                                     'upstream_source_revision': recipe['source_revision'],
                                     'upstream_fix_revision': recipe['fix_revision'],
                                     'adaptations': recipe.get('adaptations', '')}})
    counts = Counter((c['language'], c['split']) for c in cases)
    complete = all(counts[(lang, split)] == count for lang in ('python', 'node', 'cpp')
                   for split, count in (('development', 2), ('evaluation', 6)))
    return {'version': 1, 'cohort': cohort.get('cohort'), 'complete_24_case_cohort': complete,
            'require_qualification': complete,
            'qualification': 'NOT_CHECKED', 'release_complete': False, 'cases': cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipes', type=Path, default=ROOT / 'benchmark/recipes')
    parser.add_argument('--cohort', type=Path, default=ROOT / 'benchmark/upstream-cohort.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'benchmark/campaign.json')
    args = parser.parse_args()
    campaign = build_campaign(args.recipes, args.cohort, args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(campaign, indent=2) + '\n')
    temporary.replace(args.output)
    print(f'Generated {args.output}: {len(campaign["cases"])} cases; qualification NOT_CHECKED')


if __name__ == '__main__':
    main()
