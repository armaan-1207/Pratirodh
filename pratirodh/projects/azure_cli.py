"""Invoke an installed Azure CLI, including Windows batch launchers."""
import os
import shutil
from pathlib import Path


def find_azure_cli():
    return shutil.which('az') or shutil.which('az.cmd')


def azure_command(executable, *arguments):
    # The MSI batch launcher delegates to this bundled Python. Invoke it
    # directly: cmd /c can strip the executable quotes in paths with spaces.
    if os.name == 'nt' and str(executable).lower().endswith(('.cmd', '.bat')):
        python = Path(executable).resolve().parent.parent / 'python.exe'
        if Path(executable).name.lower() != 'az.cmd' or not python.is_file():
            raise FileNotFoundError('Azure CLI MSI Python runtime is unavailable')
        return [str(python), '-IBm', 'azure.cli', *arguments]
    return [str(executable), *arguments]
