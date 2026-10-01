"""Prepare a dedicated Windows CPython executable for program-specific firewall rules."""
from pathlib import Path
import shutil
import sys

if sys.platform != 'win32':
    raise SystemExit('Windows-only helper; use OS-specific process isolation elsewhere')
root = Path(__file__).resolve().parents[1]
destination = root / '.venv/Scripts'
if not (root / '.venv/pyvenv.cfg').exists():
    raise SystemExit('Create and install the project virtual environment first')
base = Path(sys.base_prefix)
shutil.copy2(base / 'python.exe', destination / 'offline-python.exe')
for source in list(base.glob('python3*.dll')) + list(base.glob('vcruntime*.dll')):
    shutil.copy2(source, destination / source.name)
print(destination / 'offline-python.exe')
