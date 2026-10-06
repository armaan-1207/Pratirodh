from pratirodh.projects import azure_cli
from pathlib import PureWindowsPath
from types import SimpleNamespace
import pytest


class WindowsLauncherPath(PureWindowsPath):
    def resolve(self):
        return self

    def is_file(self):
        return True


def windows_launcher(monkeypatch):
    # Replace module bindings, not process-wide os.name or pathlib behavior.
    monkeypatch.setattr(azure_cli, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(azure_cli, 'Path', WindowsLauncherPath)


def test_windows_batch_launcher_keeps_path_and_arguments_separate(monkeypatch):
    windows_launcher(monkeypatch)
    path = r'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'
    assert azure_cli.azure_command(path, 'vm', 'deallocate', '--name', 'pratirodh-audit') == [
        r'C:\Program Files\Microsoft SDKs\Azure\CLI2\python.exe', '-IBm', 'azure.cli',
        'vm', 'deallocate', '--name', 'pratirodh-audit']


def test_missing_batch_runtime_fails_closed(monkeypatch):
    windows_launcher(monkeypatch)
    monkeypatch.setattr(WindowsLauncherPath, 'is_file', lambda path: False)
    with pytest.raises(FileNotFoundError):
        azure_cli.azure_command(r'C:\Missing\az.cmd', 'vm', 'deallocate')


def test_native_cli_does_not_use_shell(monkeypatch):
    monkeypatch.setattr(azure_cli, 'os', SimpleNamespace(name='posix'))
    assert azure_cli.azure_command('/usr/bin/az', 'account', 'show') == ['/usr/bin/az', 'account', 'show']
