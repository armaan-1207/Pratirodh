"""Export pinned historical source and install its dependencies only in Docker."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'edffe24'


def source_archive(path=None):
    lock = json.loads((ROOT / 'docs/HISTORICAL_BASELINE.json').read_text())
    if path is not None:
        archive = Path(path).read_bytes()
    else:
        try:
            archive = subprocess.check_output(['git', 'archive', REVISION], cwd=ROOT, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as exc:
            raise ValueError('Historical source is not included in the clean release history. Supply --archive with the pinned source tar; see README.') from exc
    if hashlib.sha256(archive).hexdigest() != lock['archive_sha256']:
        raise ValueError('Historical archive does not match the immutable baseline SHA256')
    return archive, lock


def build(path=None):
    archive, lock = source_archive(path)
    destination = Path(tempfile.mkdtemp(prefix='historical-build-'))
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            if member.isfile():
                path = destination / member.name
                if not path.resolve().is_relative_to(destination.resolve()):
                    raise ValueError('invalid archive member')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(tar.extractfile(member).read())
    hashes = {hashlib.sha256(p.relative_to(destination).as_posix().encode()).hexdigest(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in destination.rglob('*') if p.is_file()}
    (destination / 'baseline-dependencies.txt').write_text('\n'.join(lock['dependencies'])+'\n', encoding='utf-8')
    shutil.copyfile(ROOT / 'tools/historical_worker.py', destination / 'historical_worker.py')
    (destination / 'Dockerfile.baseline').write_text('''FROM python:3.11-slim@sha256:e41613d42d4891e4930f79523f93f81bbc7632584ec65e36ab055f41a800b41e
WORKDIR /baseline
COPY . /baseline
RUN pip install --no-cache-dir -r baseline-dependencies.txt
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 65534:65534
ENTRYPOINT ["python", "/baseline/historical_worker.py"]
''', encoding='utf-8')
    subprocess.run(['docker', 'build', '-t', 'pratirodh-historical:edffe24', '-f',
                    str(destination / 'Dockerfile.baseline'), str(destination)], check=True)
    image = subprocess.check_output(['docker', 'image', 'inspect', 'pratirodh-historical:edffe24',
                                    '--format', '{{.Id}}'], text=True).strip()
    dependencies = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none',
        '--entrypoint', 'python', 'pratirodh-historical:edffe24', '-m', 'pip', 'freeze'], text=True)
    manifest = {'revision': lock['revision'],
                'pratirodh_revision': '8f57db6', 'source_hashes': hashes, 'image': image,
                'archive_sha256': hashlib.sha256(archive).hexdigest(), 'dependencies': dependencies.splitlines(),
                'wrapper_sha256': hashlib.sha256((ROOT / 'tools/historical_worker.py').read_bytes()).hexdigest(),
                'configuration': {'native_gate': True, 'native_corpus': True, 'promotion': False,
                                  'network': 'none', 'post_fuzz_runs': 500, 'post_fuzz_seconds': 10}}
    manifest['source_path_encoding'] = 'SHA256 of repository-relative POSIX path; values are file SHA256 hashes'
    # Preserve the measured baseline record. Rebuild gets a separate snapshot.
    (ROOT / 'run_output').mkdir(exist_ok=True)
    (ROOT / 'run_output/HISTORICAL_BASELINE_REBUILD.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', help='Separately supplied immutable historical git-archive tar')
    args = parser.parse_args()
    build(args.archive)
