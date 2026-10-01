import hashlib
import json
from pathlib import Path
import pytest
from tools import build_baseline


def test_supplied_archive_must_match_immutable_hash_before_build(monkeypatch,tmp_path):
    data=b"pinned source archive"
    lock={'archive_sha256':hashlib.sha256(data).hexdigest()}
    (tmp_path/'docs').mkdir()
    (tmp_path/'docs/HISTORICAL_BASELINE.json').write_text(json.dumps(lock))
    archive=tmp_path/'source.tar'; archive.write_bytes(data)
    monkeypatch.setattr(build_baseline,'ROOT',tmp_path)
    assert build_baseline.source_archive(archive)==(data,lock)
    archive.write_bytes(b'changed source')
    with pytest.raises(ValueError,match='immutable baseline'):
        build_baseline.build(archive)


def test_clean_history_explains_missing_source(monkeypatch,tmp_path):
    (tmp_path/'docs').mkdir()
    (tmp_path/'docs/HISTORICAL_BASELINE.json').write_text('{}')
    monkeypatch.setattr(build_baseline,'ROOT',tmp_path)
    def missing(*args,**kwargs):
        raise build_baseline.subprocess.CalledProcessError(1,args[0])
    monkeypatch.setattr(build_baseline.subprocess,'check_output',missing)
    with pytest.raises(ValueError,match='Supply --archive'):
        build_baseline.source_archive()
