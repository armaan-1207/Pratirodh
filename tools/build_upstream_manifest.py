"""Build the reviewable 24-case upstream intake manifest.

The file is deliberately an intake manifest. A case becomes executable only after
license review, source acquisition, vulnerable/fixed reproduction, and independent
audit qualification have all passed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PYTHON = [
    ('CVE-2021-21330', 'aio-libs/aiohttp', '2545222a3853e31ace15d87ae0e2effb7da0c96b', 'CWE-601'),
    ('CVE-2022-0767', 'janeczku/calibre-web', '965352c8d96c9eae7a6867ff76b0db137d04b0b8', 'CWE-918'),
    ('CVE-2020-25459', 'FederatedAI/FATE', '6feccf6d752184a6f9365d56a76fe627983e7139', 'CWE-22'),
    ('CVE-2021-32633', 'zopefoundation/Zope', '1f8456bf1f908ea46012537d52bd7e752a532c91', 'CWE-79'),
    ('CVE-2021-33203', 'django/django', '20c67a0693c4ede2b09af02574823485e82e4c8f', 'CWE-89'),
    ('CVE-2025-43859', 'python-hyper/h11', '114803a29ce50116dc47951c690ad4892b1a36ed', 'CWE-444'),
    ('CVE-2018-7750', 'paramiko/paramiko', 'fa29bd8446c8eab237f5187d28787727b4610516', 'CWE-20'),
    ('CVE-2018-18074', 'requests/requests', 'c45d7c49ea75133e52ab22a8e9e13173938e36ff', 'CWE-601'),
]
JAVASCRIPT = [
    ('CVE-2021-37712', 'isaacs/node-tar', '1739408d3122af897caefd09662bce2ea477533b', 'CWE-22'),
    ('CVE-2021-23369', 'handlebars-lang/handlebars.js', 'b6d3de7123eebba603e321f04afdbae608e8fea8', 'CWE-94'),
    ('CVE-2021-29300', 'ronomon/opened', '7effe011d4fea8fac7f78c00615e0a6e69af68ec', 'CWE-22'),
    ('CVE-2021-23664', 'isomorphic-git/cors-proxy', '1b1c91e71d946544d97ccc7cf0ac62b859e03311', 'CWE-918'),
    ('CVE-2019-10767', 'ioBroker/ioBroker.js-controller', 'f6e292c6750a491a5000d0f851b2fede4f9e2fda', 'CWE-22'),
    ('CVE-2018-6835', 'ether/etherpad-lite', '626e58cc5af1db3691b41fca7b06c28ea43141b1', 'CWE-79'),
    ('CVE-2019-15599', 'pkrumins/node-tree-kill', 'deee138a8cbc918463d8af5ce8c2bec33c3fd164', 'CWE-78'),
    ('CVE-2024-56334', 'sebhildebrandt/systeminformation', 'f7af0a67b78e7894335a6cad510566a25e06ae41', 'CWE-200'),
]
# Fix revisions verified against upstream commits and security advisories.
C_CPP = [
    ('CVE-2023-50472', 'DaveGamble/cJSON', '280982222ef40cd79ff6ffdcf7499a59f66d5dfc', 'CWE-476'),
    ('CVE-2018-25032', 'madler/zlib', '5c44459c3b28a9bd3283aaceab7c615f8020c531', 'CWE-787'),
    ('CVE-2022-43680', 'libexpat/libexpat', 'eedc5f6de8e219130032c8ff2ff17580e18bd0c1', 'CWE-416'),
    ('CVE-2019-1000019', 'libarchive/libarchive', '65a23f5dbee4497064e9bb467f81138a62b0dae1', 'CWE-125'),
    ('CVE-2023-4863', 'webmproject/libwebp', '902bc9190331343b2017211debcec8d2ab87e17a', 'CWE-787'),
    ('CVE-2024-25062', 'GNOME/libxml2', '92721970884fcc13305cb8e23cdc5f0dd7667c2c', 'CWE-416'),
    ('CVE-2014-9130', 'yaml/libyaml', 'e6aa721cc0e5a48f408c52355559fd36780ba32a', 'CWE-617'),
    ('CVE-2020-12762', 'json-c/json-c', 'd07b91014986900a3a75f306d302e13e005e9d67', 'CWE-190'),
]


def case(language, cve, project, fix, cwe):
    owner, repo = project.split('/', 1)
    if fix.startswith('http'):
        fix_url = fix
        fix_revision = None
        status = 'SOURCE_CANDIDATE_REVISION_REVIEW_REQUIRED'
    else:
        fix_url = f'https://github.com/{project}/commit/{fix}'
        fix_revision = fix
        status = 'SOURCE_PENDING_ACQUISITION'
    return {
        'id': f'{language.lower().replace("c/c++", "cpp")}-{cve.lower()}', 'language': language, 'split': 'evaluation',
        'cve': cve, 'project': project, 'repository_url': f'https://github.com/{project}',
        'advisory_url': f'https://github.com/advisories/{cve}', 'fix_url': fix_url,
        'fix_revision': fix_revision, 'cwe': cwe, 'license': 'PENDING_UPSTREAM_LICENSE_REVIEW',
        'license_evidence': [], 'status': status, 'source_revision': None,
        'audit': {'context': 'pratirodh-audit', 'status': 'PENDING', 'files': [], 'checks': []},
        'qualification': {'vulnerable': 'PENDING', 'fixed': 'PENDING', 'legitimate': 'PENDING', 'independent_audit': 'PENDING'},
        'disclosure': 'Upstream source and reference fix remain outside model-visible input until qualification.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('benchmark/upstream-v1/manifest.json'))
    args = parser.parse_args()
    cases = [case('Python', *row) for row in PYTHON] + [case('JavaScript', *row) for row in JAVASCRIPT] + [case('C/C++', *row) for row in C_CPP]
    for language in ('Python', 'JavaScript', 'C/C++'):
        for row in [c for c in cases if c['language'] == language][:2]:
            row['split'] = 'development'
    assert len(cases) == 24 and {c['language'] for c in cases} == {'Python', 'JavaScript', 'C/C++'}
    payload = {'version': 1, 'cohort': 'upstream-v1', 'status': 'INTAKE_PENDING_QUALIFICATION',
               'target_count': 24, 'counts': {'Python': 8, 'JavaScript': 8, 'C/C++': 8},
               'comparison': {'arms': ['expanded', 'model-only'], 'workflows': ['repair', 'discover'], 'repetitions': 3,
                              'seconds': 172800, 'audit_reserve_seconds': 28800,
                              'equal_budget': True,
                              'arm_budget': {'seconds': 600, 'reserve_seconds': 180, 'model_calls': 2, 'candidates': 3,
                                             'execution_worker': 'pratirodh-project-worker:0.2',
                                             'audit_worker': 'pratirodh-project-worker:0.2'}}, 'cases': cases,
               'selection_changes': [{'previous': 'pnggroup/libpng CVE-2023-4863', 'replacement': 'webmproject/libwebp CVE-2023-4863', 'reason': 'Original project attribution was incorrect.'}, {'previous': 'json-c/json-c CVE-2024-5741', 'replacement': 'json-c/json-c CVE-2020-12762', 'reason': 'Original CVE concerns Checkmk XSS, not json-c.'}, {'previous': 'yaml/libyaml CVE-2024-35325', 'replacement': 'yaml/libyaml CVE-2014-9130', 'reason': 'Choose upstream-confirmed fix with an explicit security regression.'}],
               'release_gate': ['all_24_cases_qualified', 'both_arms_completed', 'independent_audit_passed']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(f'wrote {args.output} with {len(cases)} cases')


if __name__ == '__main__':
    main()
