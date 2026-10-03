"""Create a versioned correction of reference revisions; preserve upstream-v1."""
import json
from pathlib import Path


CORRECTIONS = {
    'cpp-cve-2023-50472': ('276a4620c1b3107635fd9a7aa91ae2a72d5eb1c4',
                         'https://github.com/DaveGamble/cJSON/pull/809'),
    'cpp-cve-2022-43680': ('5290462a7ea1278a8d5c0d5b2860d4e244f997e4',
                         'https://github.com/libexpat/libexpat/commit/5290462a7ea1278a8d5c0d5b2860d4e244f997e4'),
}


def main():
    root = Path(__file__).resolve().parents[1]
    destination = root / 'benchmark/upstream-v2/manifest.json'
    if destination.exists():
        raise SystemExit('upstream-v2 already exists; do not replace a reviewed cohort')
    previous = root / 'benchmark/upstream-v1/manifest.json'
    manifest = json.loads(previous.read_text(encoding='utf-8'))
    manifest.update(cohort='upstream-v2', supersedes='upstream-v1',
                    change_reason='Correct cJSON test-only and Expat changelog-only reference revisions; same 24 CVEs and splits')
    manifest['comparison']['seconds'] = 172800
    manifest['comparison']['audit_reserve_seconds'] = 28800
    manifest['require_qualification'] = True
    changes = []
    for case in manifest['cases']:
        if case['id'] == 'cpp-cve-2018-25032':
            case['additional_license_paths'] = ['README', 'zlib.h']
        elif case['id'] == 'cpp-cve-2024-25062':
            case['additional_license_paths'] = ['Copyright']
        if case['id'] in CORRECTIONS:
            revision, evidence = CORRECTIONS[case['id']]
            changes.append({'case': case['id'], 'previous_fix': case['fix_revision'],
                            'corrected_fix': revision, 'reference': evidence})
            case['fix_revision'] = revision
            case['fix_url'] = case['repository_url'] + '/commit/' + revision
            case['acquisition'] = 'run_output/upstream-acquisition-v2/' + case['id']
            case['reference_review'] = evidence
        else:
            case['acquisition'] = 'run_output/upstream-acquisition/' + case['id']
        case['status'] = 'INTAKE_PENDING_QUALIFICATION'
        case.pop('source_revision', None)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (destination.parent / 'REVISION_CHANGES.json').write_text(json.dumps(changes, indent=2) + '\n', encoding='utf-8')
    print(destination)


if __name__ == '__main__':
    main()
