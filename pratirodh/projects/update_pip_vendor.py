"""Apply hash-verified wheel modules to pip's bundled dependency namespace."""
import importlib
from pathlib import Path
import re
import shutil
import zipfile
import pip._vendor


def main():
    root = Path(pip._vendor.__file__).parent
    manifest = root / 'vendor.txt'
    pins = {'urllib3': '2.8.0', 'msgpack': '1.2.1'}
    for name, version in pins.items():
        wheel, = Path('/opt/pip-vendor-wheels').glob(name + '-*.whl')
        destination = root / name
        shutil.rmtree(destination)
        with zipfile.ZipFile(wheel) as archive:
            for entry in archive.infolist():
                path = Path(entry.filename)
                if path.parts[0] != name or entry.is_dir():
                    continue
                if path.is_absolute() or '..' in path.parts:
                    raise ValueError('unsafe wheel module path')
                # pip deliberately uses msgpack's pure-Python implementation.
                if path.suffix in {'.so', '.pyd'}:
                    continue
                output = root / path
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(archive.read(entry))
        module = importlib.import_module('pip._vendor.' + name)
        if module.__version__ != version:
            raise ValueError('vendored module version mismatch')
        if name == 'msgpack' and module.unpackb(module.packb({'probe': 1}), raw=False) != {'probe': 1}:
            raise ValueError('vendored msgpack round trip failed')
        body, count = re.subn(r'(?m)^(\s*' + re.escape(name) + r'==)[^\s]+',
                             lambda match: match[1] + version, manifest.read_text())
        if count != 1:
            raise ValueError('unexpected pip vendor manifest')
        manifest.write_text(body)


if __name__ == '__main__':
    main()
