"""Synthetic acceptance gate proofs, never actual operator activation."""
import copy
from datetime import datetime, timezone
import hashlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from tools.check_operations_activation import check, canonical, main

NOW = datetime(2026, 10, 7, 18, tzinfo=timezone.utc)
SOURCE = 'a' * 64


def fixture():
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    p = dict(schema='pratirodh.operations-attestation.v1', source_sha256=SOURCE,
             issued_at='2026-10-07T17:00:00Z', expires_at='2026-10-08T17:00:00Z',
             owner='synthetic-operator', public_activation='DEFERRED')
    p['backups'] = dict(encrypted=True, off_host=True, independent_recovery_secret=True,
        complete_inventory_verified=True, historical_signatures_verified=True, tamper_rejected=True,
        daily_recovery_points=7, rpo_minutes=1440, rto_minutes=60)
    p['signer'] = dict(dedicated_identity=True, host_permissions_verified=True,
        worker_key_exclusion_verified=True, rotation_rehearsed=True,
        revocation_rehearsed=True, historical_anchor_retained=True)
    p['alerts'] = dict(external_receiver=True, named_recipient=True,
        actual_application_event=True, outage_observable=True, delivery_seconds=300, ack_seconds=900)
    for name in ('backups', 'signer', 'alerts'):
        p[name]['drill_at'] = '2026-10-07T16:00:00Z'
    return key, public, p


def encode(key, payload):
    p = copy.deepcopy(payload)
    receipts = {}
    for name in ('backups', 'signer', 'alerts'):
        observed = {k: v for k, v in p[name].items() if k != 'receipt_sha256'}
        evidence = canonical(dict(schema='pratirodh.operations-drill.v1', control=name,
                                  source_sha256=SOURCE, observations=observed))
        digest = hashlib.sha256(evidence).hexdigest()
        receipts[digest] = evidence
        p[name]['receipt_sha256'] = digest
    data = canonical({'payload': p, 'signature': key.sign(canonical(p)).hex()})
    return data, receipts


def test_complete_signed_receipts_only_enable_review():
    key, public, p = fixture()
    data, receipts = encode(key, p)
    result = check(data, public, SOURCE, receipts, NOW)
    assert result['status'] == 'READY_FOR_OPERATOR_REVIEW'
    assert result['public_activation'] == 'DEFERRED'
    assert result['independent_external_verification'] == 'NOT_ESTABLISHED'
    assert p['owner'] not in json.dumps(result)


@pytest.mark.parametrize('change', ['stale', 'future', 'too_long', 'source', 'unknown', 'public', 'drill', 'type'])
def test_invalid_operator_claims_rejected(change):
    key, public, p = fixture()
    if change == 'stale': p['expires_at'] = '2026-10-07T18:00:00Z'
    if change == 'future': p['issued_at'] = '2026-10-07T19:00:00Z'
    if change == 'too_long': p['expires_at'] = '2026-11-07T17:00:00Z'
    if change == 'source': p['source_sha256'] = 'b' * 64
    if change == 'unknown': p['token'] = 'secret'
    if change == 'public': p['public_activation'] = 'APPROVED'
    if change == 'drill': p['alerts']['drill_at'] = '2026-09-01T16:00:00Z'
    if change == 'type': p['alerts']['external_receiver'] = 1
    data, receipts = encode(key, p)
    with pytest.raises(ValueError): check(data, public, SOURCE, receipts, NOW)


@pytest.mark.parametrize(('control', 'field', 'value'), [
    ('backups', 'off_host', False), ('backups', 'daily_recovery_points', 6),
    ('backups', 'rpo_minutes', 1441), ('backups', 'rto_minutes', 61),
    ('signer', 'revocation_rehearsed', False), ('signer', 'host_permissions_verified', False),
    ('alerts', 'named_recipient', False), ('alerts', 'actual_application_event', False),
    ('alerts', 'delivery_seconds', 301), ('alerts', 'ack_seconds', 901)])
def test_unmet_control_blocks_even_signed(control, field, value):
    key, public, p = fixture()
    p[control][field] = value
    data, receipts = encode(key, p)
    assert check(data, public, SOURCE, receipts, NOW)['status'] == 'BLOCKED'


def test_wrong_anchor_and_missing_or_changed_receipt():
    key, public, p = fixture()
    data, receipts = encode(key, p)
    wrong = Ed25519PrivateKey.generate().public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    with pytest.raises(ValueError): check(data, wrong, SOURCE, receipts, NOW)
    with pytest.raises(ValueError): check(data, public, SOURCE, {}, NOW)
    changed = {k: v + b' ' for k, v in receipts.items()}
    with pytest.raises(ValueError): check(data, public, SOURCE, changed, NOW)


def test_duplicate_field_and_oversize_rejected():
    key, public, p = fixture()
    data, receipts = encode(key, p)
    with pytest.raises(ValueError): check(b'{"payload":{},"payload":{}}', public, SOURCE, receipts, NOW)
    with pytest.raises(ValueError): check(b'x' * 65537, public, SOURCE, receipts, NOW)


def test_cli_missing_external_inputs_fail_sanitized(monkeypatch, capsys, tmp_path):
    secret_path = tmp_path / 'private-recipient-token'
    monkeypatch.setattr('sys.argv', ['check', '--attestation', str(secret_path),
        '--trusted-public', str(secret_path), '--source-sha256', SOURCE,
        '--receipt-dir', str(tmp_path)])
    assert main() == 1
    output = capsys.readouterr().out
    assert 'private-recipient' not in output
    assert json.loads(output)['status'] == 'BLOCKED'
