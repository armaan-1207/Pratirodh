from pratirodh.projects import azure_cli
from pathlib import Path
import pytest


def test_windows_batch_launcher_keeps_path_and_arguments_separate(monkeypatch):
    monkeypatch.setattr(azure_cli.os, 'name', 'nt')
    monkeypatch.setenv('COMSPEC', r'C:\Windows\System32\cmd.exe')
    monkeypatch.setattr(Path, 'is_file', lambda path: True)
    path = r'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'
    assert azure_cli.azure_command(path, 'vm', 'deallocate', '--name', 'pratirodh-audit') == [
        str(Path(path).resolve().parent.parent / 'python.exe'), '-IBm', 'azure.cli',
        'vm', 'deallocate', '--name', 'pratirodh-audit']


def test_missing_batch_runtime_fails_closed(monkeypatch):
    monkeypatch.setattr(azure_cli.os, 'name', 'nt')
    monkeypatch.setattr(Path, 'is_file', lambda path: False)
    with pytest.raises(FileNotFoundError):
        azure_cli.azure_command(r'C:\Missing\az.cmd', 'vm', 'deallocate')


def test_native_cli_does_not_use_shell(monkeypatch):
    monkeypatch.setattr(azure_cli.os, 'name', 'posix')
    assert azure_cli.azure_command('/usr/bin/az', 'account', 'show') == ['/usr/bin/az', 'account', 'show']
