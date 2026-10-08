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


def test_diagnostics_report_every_conflict_without_weakening_intake(tmp_path, monkeypatch):
    extras = {'image.png': b'\xff\xfe\x00', 'second.pdf': b'\xff\x00',
              'fixture.key': b'-----BEGIN PRIVATE KEY-----\nfixture\n',
              'oversized.txt': b'a' * (1024 * 1024 + 1)}
    case, source, _ = fixture(tmp_path, monkeypatch, extras)
    result = prep.prepare_case(case, source)
    assert result['status'] == 'BLOCKED' and result['qualification'] == 'NOT_RUN'
    report = result['intake_diagnostics']
    assert report['scope'] == 'ADVISORY_ONLY'
    conflicts = {item['path']: item for item in report['conflicts']}
    assert set(conflicts) == set(extras)
    assert any('1048576' in reason for reason in conflicts['oversized.txt']['reasons'])
    assert any('private key' in reason for reason in conflicts['fixture.key']['reasons'])
    for name, body in extras.items():
        assert (case / 'prepared/target' / name).read_bytes() == body


def test_diagnostics_expose_aggregate_limits(tmp_path):
    for number in range(1001):
        (tmp_path / f'{number:04}.txt').write_bytes(b'a' * 11000)
    report = prep.intake_diagnostics(tmp_path)
    assert report['files'] == 1001 and report['bytes'] == 11011000
    assert report['file_limit_exceeded'] and report['byte_limit_exceeded']
    assert report['conflicts'] == []


def test_diagnostics_do_not_read_controller_rejected_links(tmp_path, monkeypatch):
    linked = tmp_path / 'linked.txt'
    linked.write_text('must not be read')
    original_is_symlink = Path.is_symlink
    original_open = Path.open
    monkeypatch.setattr(Path, 'is_symlink',
                        lambda path: path == linked or original_is_symlink(path))

    def guarded_open(path, *args, **kwargs):
        if path == linked:
            raise AssertionError('diagnostics followed a controller-rejected link')
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', guarded_open)
    report = prep.intake_diagnostics(tmp_path)
    assert report['files'] == 0 and report['bytes'] == 0
    assert report['conflicts'] == [{'path': 'linked.txt', 'bytes': None,
        'reasons': ['project symlinks and junctions are not accepted: linked.txt']}]


def test_diagnostics_do_not_traverse_controller_rejected_junctions(tmp_path, monkeypatch):
    linked = tmp_path / 'linked'
    linked.mkdir()
    original_iterdir = Path.iterdir
    monkeypatch.setattr(Path, 'is_junction', lambda path: path == linked, raising=False)

    def guarded_iterdir(path):
        if path == linked:
            raise AssertionError('diagnostics traversed a controller-rejected junction')
        return original_iterdir(path)

    monkeypatch.setattr(Path, 'iterdir', guarded_iterdir)
    report = prep.intake_diagnostics(tmp_path)
    assert report['files'] == 0 and report['bytes'] == 0
    assert report['conflicts'] == [{'path': 'linked', 'bytes': None,
        'reasons': ['project symlinks and junctions are not accepted: linked']}]


def test_unsupported_archive_links_are_disclosed_without_materializing(tmp_path, monkeypatch):
    case, source, _ = fixture(tmp_path, monkeypatch)
    original = prep.subprocess.check_output(['git', 'archive'])
    output = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(original)) as source_archive:
        with tarfile.open(fileobj=output, mode='w') as archive:
            for member in source_archive:
                archive.addfile(member, source_archive.extractfile(member))
            link = tarfile.TarInfo('docs/linked')
            link.type = tarfile.SYMTYPE
            link.linkname = '../../outside'
            archive.addfile(link)
    monkeypatch.setattr(prep.subprocess, 'check_output',
                        lambda args, **kw: str(source) if 'rev-parse' in args else output.getvalue())
    result = prep.prepare_case(case, source)
    assert result['status'] == 'BLOCKED' and result['qualification'] == 'NOT_RUN'
    assert result['unsupported_archive_entries'] == [
        {'path': 'docs/linked', 'link_target': '../../outside', 'archive_type': '2'}]
    assert not (case / 'prepared/target/docs/linked').exists()


def test_long_snapshot_paths_preserve_complete_fixture(tmp_path, monkeypatch):
    name = 'fixtures/' + '/'.join(['nested-directory'] * 12) + '/canary.txt'
    case, source, _ = fixture(tmp_path, monkeypatch, {name: b'preserve me\n'})
    destination = case / 'prepared/target' / name
    assert len(str(destination)) > 260
    before = {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    result = prep.prepare_case(case, source)
    assert prep.snapshot_path(destination).read_bytes() == b'preserve me\n'
    assert result['qualification'] == 'NOT_RUN'
    assert before == {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob('*') if p.is_file()}


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
