"""Preparation must preserve originals and refuse unsafe or conflicting output."""
import io
import json
import tarfile
from pathlib import Path
import pytest
from scripts import reconstruct_targets as prep
from pratirodh.projects.examples import create_example


def fixture(tmp_path, monkeypatch, extra=None):
    case = tmp_path / 'case'
    case.mkdir()
    source = tmp_path / 'source'
    manifest, _ = create_example(source, 'python', 'sha256:' + 'a' * 64)
    (case / 'source-manifest.json').write_bytes(manifest.read_bytes())
    (case / 'recipe.json').write_text(json.dumps({'harness_files': {}, 'source_map': {}}))
    (case / 'target-source.json').write_text(json.dumps({'id': 'case', 'source_revision': 'a' * 40,
        'fix_revision': 'b' * 40, 'repository': 'https://github.com/example/project',
        'snapshot_exclusions': ['tests/test_stub.py', 'image.png']}))
    contents = {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob('*') if p.is_file() and p != manifest}
    contents['tests/test_stub.py'] = b'raise RuntimeError("obsolete")\n'
    contents.update(extra or {})
    tar = io.BytesIO()
    with tarfile.open(fileobj=tar, mode='w') as archive:
        for name, body in contents.items():
            info = tarfile.TarInfo(name); info.size = len(body)
            archive.addfile(info, io.BytesIO(body))
    monkeypatch.setattr(prep.subprocess, 'check_output',
                        lambda args, **kw: str(source) if 'rev-parse' in args else tar.getvalue())
    return case, source, contents


def test_snapshot_does_not_modify_acquisition_and_refuses_overwrite(tmp_path, monkeypatch):
    case, source, _ = fixture(tmp_path, monkeypatch)
    before = {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    result = prep.prepare_case(case, source)
    assert result['status'] == 'PREPARED'
    assert result['qualification'] == 'NOT_RUN'
    assert not (case / 'prepared/target/tests/test_stub.py').exists()
    assert before == {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    with pytest.raises(FileExistsError):
        prep.prepare_case(case, source)


def test_binary_is_retained_and_reported_as_intake_blocker(tmp_path, monkeypatch):
    case, source, _ = fixture(tmp_path, monkeypatch, {'image.png': b'\xff\xfe\x00'})
    result = prep.prepare_case(case, source)
    assert result['status'] == 'BLOCKED'
    assert (case / 'prepared/target/image.png').read_bytes() == b'\xff\xfe\x00'
    assert any('UTF-8' in message for message in result['blockers'])


def test_archive_traversal_cannot_write_outside_snapshot(tmp_path, monkeypatch):
    case, source, _ = fixture(tmp_path, monkeypatch, {'../escaped.py': b'bad'})
    with pytest.raises(ValueError):
        prep.prepare_case(case, source)
    assert not (case / 'escaped.py').exists()


def test_missing_inputs_and_dry_run_preserve_files(tmp_path, monkeypatch, capsys):
    case, source, _ = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(prep.sys, 'argv', ['prepare', '--recipes', str(tmp_path), '--dry-run'])
    assert prep.main() == 0
    assert not (case / 'prepared').exists()
    monkeypatch.setattr(prep.subprocess, 'check_output', lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError('missing source')))
    result = prep.reconstruct_all(tmp_path, source_root=tmp_path)
    assert result['summary']['blocked'] == 1
    assert '--source-root' in result['cases'][0]['blockers'][0]
    assert not (case / 'prepared').exists()
