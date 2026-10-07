"""Acquire pinned public Requests source and prepare its isolated demo image.

Source acquisition does not run target code or qualify an upstream case.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pratirodh.projects.requests_demo import CASE, IMAGE_TAG, SOURCE_REVISION, FIX_REVISION


def main():
    acquisition = ROOT / 'run_output/upstream-acquisition' / CASE
    checkout = acquisition / 'upstream'
    if not checkout.exists():
        subprocess.run([sys.executable, str(ROOT / 'tools/acquire_upstream_case.py'),
            '--repository', 'https://github.com/psf/requests', '--fix', FIX_REVISION,
            '--advisory', 'https://nvd.nist.gov/vuln/detail/CVE-2018-18074', '--id', CASE], cwd=ROOT, check=True)
    origin = subprocess.check_output(['git', '-C', str(checkout), 'remote', 'get-url', 'origin'], text=True).strip()
    if origin not in {'https://github.com/psf/requests', 'https://github.com/requests/requests'}:
        raise ValueError('existing acquisition has an unexpected source repository')
    for revision in (SOURCE_REVISION, FIX_REVISION):
        subprocess.run(['git', '-C', str(checkout), 'cat-file', '-e', revision + ':requests/sessions.py'], check=True)
    subprocess.run(['docker', '--context', 'default', 'build', '-t', IMAGE_TAG,
        '-f', str(ROOT / 'pratirodh/projects/RequestsDemo.Dockerfile'),
        str(ROOT / 'pratirodh/projects')], check=True)
    print('Pinned Requests inputs and demo image prepared. No target code or model was run.')


if __name__ == '__main__':
    main()
