"""Acquire real upstream source at a fixing commit's parent, without executing it.

Acquisition is not qualification: vulnerable/fixed and independent audit harnesses
must pass on dedicated workers before a case can enter the comparison cohort.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import os


def git(directory, *arguments):
    return subprocess.check_output(['git', '-C', str(directory), *arguments], text=True).strip()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository', required=True)
    p.add_argument('--fix', required=True)
    p.add_argument('--advisory', required=True)
    p.add_argument('--id', required=True)
    p.add_argument('--output', type=Path, default=Path('run_output/upstream-acquisition'))
    a = p.parse_args()
    if not re.fullmatch(r'https://github.com/[\w.-]+/[\w.-]+', a.repository):
        p.error('Use a public GitHub repository URL without credentials.')
    if not re.fullmatch(r'[a-f0-9]{40}', a.fix) or not re.fullmatch(r'[A-Za-z0-9_-]+', a.id):
        p.error('A full fixing SHA and safe case ID are required.')
    if not a.advisory.startswith('https://'):
        p.error('An HTTPS advisory URL is required.')
    root = a.output.resolve() / a.id
    root.mkdir(parents=True, exist_ok=True)
    checkout = root / 'upstream'
    if checkout.exists():
        if not (checkout / '.git').is_dir() or git(checkout, 'remote', 'get-url', 'origin') != a.repository:
            p.error('Existing checkout does not match the declared repository.')
        if (root / 'provenance.json').exists():
            p.error('Completed source acquisition will not be overwritten.')
    else:
        checkout.mkdir()
        git(checkout, 'init', '--quiet')
        git(checkout, 'remote', 'add', 'origin', a.repository)
    git(checkout, '-c', 'core.hooksPath=' + os.devnull, 'fetch', '--depth=2', 'origin', a.fix)
    fixed = git(checkout, 'rev-parse', 'FETCH_HEAD')
    if fixed != a.fix:
        raise ValueError('Upstream fixing revision did not match requested SHA.')
    vulnerable = git(checkout, 'rev-parse', f'{fixed}^')
    git(checkout, '-c', 'core.longpaths=true', '-c', 'core.hooksPath=' + os.devnull,
        'checkout', '--quiet', '--detach', vulnerable)
    paths = git(checkout, 'ls-files').splitlines()
    licenses = []
    for name in paths:
        if re.fullmatch(r'(LICENSE|LICENCE|COPYING|NOTICE)(\..*)?', Path(name).name, re.I):
            payload = (checkout / name).read_bytes()
            licenses.append({'path': name, 'sha256': hashlib.sha256(payload).hexdigest()})
    patch = git(checkout, 'diff', vulnerable, fixed)
    (root / 'reference-fix.diff').write_text(patch + '\n', encoding='utf-8')
    record = {'status': 'SOURCE_ACQUIRED_NOT_QUALIFIED', 'repository': a.repository,
              'advisory': a.advisory, 'fix_url': f'{a.repository}/commit/{fixed}',
              'fixed_revision': fixed, 'vulnerable_revision': vulnerable,
              'license_files': licenses, 'license_review': 'PENDING',
              'source_hashes': {name: hashlib.sha256((checkout / name).read_bytes()).hexdigest()
                                for name in paths if (checkout / name).is_file() and not (checkout / name).is_symlink()},
              'reference_fix_sha256': hashlib.sha256((root / 'reference-fix.diff').read_bytes()).hexdigest(),
              'gates': {'vulnerable_reproduction': 'PENDING', 'fixed_reproduction': 'PENDING',
                        'legitimate_behavior': 'PENDING', 'independent_audit': 'PENDING'},
              'reference_fix_policy': 'Keep outside model-visible target and held-out audit inputs.'}
    (root / 'provenance.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
