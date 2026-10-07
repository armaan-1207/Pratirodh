"""Synthetic key-loss and recovery proofs; never read operator key material."""
import shutil

import pytest
from cryptography.exceptions import InvalidSignature

from pratirodh.evidence import Store


def report(run_id):
    return {'id': run_id, 'created': '2026-10-07', 'decision': 'REJECT',
            'scenario': 'Synthetic operations boundary proof'}


def test_missing_key_cannot_silently_replace_existing_trust(tmp_path):
    original = Store(tmp_path / 'original')
    original.save(report('a' * 32), {})
    restored_path = tmp_path / 'public-recovery'
    shutil.copytree(original.root, restored_path, ignore=shutil.ignore_patterns('signing.key'))
    recovered = Store(restored_path)
    assert recovered.load('a' * 32) == report('a' * 32)
    with pytest.raises(ValueError, match='missing signing key'):
        recovered.save(report('b' * 32), {})
    assert not (restored_path / 'signing.key').exists()
    assert not recovered.run_path('b' * 32).exists()


def test_wrong_recovery_key_fails_closed_before_new_evidence(tmp_path):
    original = Store(tmp_path / 'original')
    original.save(report('a' * 32), {})
    alternate = Store(tmp_path / 'alternate')
    alternate.save(report('b' * 32), {})
    restored_path = tmp_path / 'recovery'
    shutil.copytree(original.root, restored_path)
    (restored_path / 'signing.key').write_bytes((alternate.root / 'signing.key').read_bytes())
    recovered = Store(restored_path)
    # Historical signatures verify independently of the unusable private key.
    assert recovered.load('a' * 32) == report('a' * 32)
    with pytest.raises(ValueError, match='trust anchor does not match'):
        recovered.save(report('c' * 32), {})
    assert not recovered.run_path('c' * 32).exists()


def test_separate_key_epochs_require_the_correct_historical_anchor(tmp_path):
    old = Store(tmp_path / 'old-epoch')
    new = Store(tmp_path / 'new-epoch')
    old.save(report('a' * 32), {})
    new.save(report('b' * 32), {})
    assert (old.root / 'trust.pub').read_bytes() != (new.root / 'trust.pub').read_bytes()
    assert old.load('a' * 32) == report('a' * 32)
    assert new.load('b' * 32) == report('b' * 32)
    wrong_path = tmp_path / 'wrong-anchor'
    shutil.copytree(old.root, wrong_path, ignore=shutil.ignore_patterns('signing.key'))
    (wrong_path / 'trust.pub').write_bytes((new.root / 'trust.pub').read_bytes())
    with pytest.raises(InvalidSignature):
        Store(wrong_path).load('a' * 32)
