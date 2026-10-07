"""Install reviewed, hash-bound npm tooling during image construction only."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request


def main():
    root = Path('/usr/local/lib/node_modules/npm')
    for pin in json.loads(Path('/opt/pratirodh/npm-worker-pins.json').read_text()):
        if not pin['url'].startswith('https://registry.npmjs.org/'):
            raise ValueError('npm build input must use the official HTTPS registry')
        # Reviewed build inputs only; HTTPS origin and payload SHA-256 are checked.
        with urllib.request.urlopen(pin['url'], timeout=60) as response:  # nosec B310
            payload = response.read(32 * 1024 * 1024 + 1)
        if len(payload) > 32 * 1024 * 1024 or hashlib.sha256(payload).hexdigest() != pin['sha256']:
            raise ValueError('npm build input failed integrity verification')
        destination = root if pin['name'] == 'npm' else root / 'node_modules' / pin['name']
        with tempfile.TemporaryDirectory() as temporary:
            with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
                archive.extractall(temporary, filter='data')
            source = Path(temporary) / 'package'
            package = json.loads((source / 'package.json').read_text())
            if (package['name'], package['version']) != (pin['name'], pin['version']):
                raise ValueError('npm build input identity mismatch')
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source, destination)


if __name__ == '__main__':
    main()
