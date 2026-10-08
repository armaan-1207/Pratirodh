"""Check signed operator acceptance before a separate activation review.

No resource is provisioned. Signed attestations establish accountability, not
independent verification that an external service exists or works.
"""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MAX_INPUT = 65536
HEX = re.compile(r'[0-9a-f]{64}\Z')
LABEL = re.compile(r'[A-Za-z0-9_.-]{1,80}\Z')


def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate fields')
        result[key] = value
    return result


def fields(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError('unexpected or missing fields')


def timestamp(value):
    if not isinstance(value, str) or not value.endswith('Z'):
        raise ValueError('UTC timestamp required')
    result = datetime.fromisoformat(value[:-1] + '+00:00')
    if result.utcoffset() != timedelta(0):
        raise ValueError('UTC timestamp required')
    return result


def check(data, trusted_public, source_sha256, receipts=None, now=None):
    """Return only sanitized status; reject unsupported or stale attestations."""
    now = now or datetime.now(timezone.utc)
    if not isinstance(source_sha256, str) or not HEX.fullmatch(source_sha256):
        raise ValueError('expected source digest required')
    if not isinstance(data, bytes) or len(data) > MAX_INPUT:
        raise ValueError('attestation input exceeds bound')
    envelope = json.loads(data, object_pairs_hook=unique_pairs)
    fields(envelope, {'payload', 'signature'})
    if not isinstance(trusted_public, bytes) or len(trusted_public) != 32:
        raise ValueError('independent Ed25519 public anchor required')
    signature = envelope['signature']
    if not isinstance(signature, str) or not re.fullmatch(r'[0-9a-f]{128}', signature):
        raise ValueError('invalid signature encoding')
    try:
        Ed25519PublicKey.from_public_bytes(trusted_public).verify(
            bytes.fromhex(signature), canonical(envelope['payload']))
    except InvalidSignature:
        raise ValueError('attestation signature rejected') from None
    p = envelope['payload']
    fields(p, {'schema', 'source_sha256', 'issued_at', 'expires_at', 'owner',
               'public_activation', 'backups', 'signer', 'alerts'})
    if p['schema'] != 'pratirodh.operations-attestation.v1':
        raise ValueError('unsupported schema')
    if p['source_sha256'] != source_sha256:
        raise ValueError('source binding mismatch')
    if not isinstance(p['owner'], str) or not LABEL.fullmatch(p['owner']):
        raise ValueError('operator owner label required')
    issued, expires = timestamp(p['issued_at']), timestamp(p['expires_at'])
    if not issued <= now < expires or expires - issued > timedelta(days=7):
        raise ValueError('attestation stale or outside seven-day window')
    if p['public_activation'] != 'DEFERRED':
        raise ValueError('public activation is outside this gate scope')
    checks = {}
    receipts = receipts or {}
    boolean_fields = {
        'backups': {'encrypted', 'off_host', 'independent_recovery_secret',
                    'complete_inventory_verified', 'historical_signatures_verified',
                    'tamper_rejected'},
        'signer': {'dedicated_identity', 'host_permissions_verified',
                   'worker_key_exclusion_verified', 'rotation_rehearsed',
                   'revocation_rehearsed', 'historical_anchor_retained'},
        'alerts': {'external_receiver', 'named_recipient',
                   'actual_application_event', 'outage_observable'},
    }
    numerical_fields = {
        'backups': {'daily_recovery_points': (7, 365), 'rpo_minutes': (0, 1440),
                    'rto_minutes': (0, 60)},
        'signer': {},
        'alerts': {'delivery_seconds': (0, 300), 'ack_seconds': (0, 900)},
    }
    for name in ('backups', 'signer', 'alerts'):
        control = p[name]
        fields(control, boolean_fields[name] | set(numerical_fields[name]) |
               {'drill_at', 'receipt_sha256'})
        if not isinstance(control['receipt_sha256'], str) or not HEX.fullmatch(control['receipt_sha256']):
            raise ValueError('control receipt digest required')
        evidence = receipts.get(control['receipt_sha256'])
        if not isinstance(evidence, bytes) or len(evidence) > MAX_INPUT or hashlib.sha256(evidence).hexdigest() != control['receipt_sha256']:
            raise ValueError('bound control receipt unavailable or changed')
        receipt = json.loads(evidence, object_pairs_hook=unique_pairs)
        fields(receipt, {'schema', 'control', 'source_sha256', 'observations'})
        if (receipt['schema'] != 'pratirodh.operations-drill.v1' or
                receipt['control'] != name or receipt['source_sha256'] != source_sha256 or
                receipt['observations'] != {k: v for k, v in control.items() if k != 'receipt_sha256'}):
            raise ValueError('control receipt does not bind the accepted observations')
        drill = timestamp(control['drill_at'])
        if not issued - timedelta(days=7) <= drill <= issued:
            raise ValueError('control drill is stale or future dated')
        valid = True
        for key in boolean_fields[name]:
            if type(control[key]) is not bool:
                raise ValueError('boolean control evidence required')
            valid = valid and control[key]
        for key, (low, high) in numerical_fields[name].items():
            value = control[key]
            if type(value) is not int or value < 0:
                raise ValueError('nonnegative integer measurement required')
            valid = valid and low <= value <= high
        checks[name] = 'OPERATOR_ATTESTED' if valid else 'BLOCKED'
    return {'status': 'READY_FOR_OPERATOR_REVIEW' if all(
        v == 'OPERATOR_ATTESTED' for v in checks.values()) else 'BLOCKED',
        'controls': checks, 'public_activation': 'DEFERRED',
        'independent_external_verification': 'NOT_ESTABLISHED',
        'source_sha256': source_sha256,
        'attestation_sha256': hashlib.sha256(data).hexdigest()}


def bounded_read(path, limit):
    with path.open('rb') as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError('input exceeds bound')
    return content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attestation', type=Path, required=True)
    parser.add_argument('--trusted-public', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--receipt-dir', type=Path, required=True,
                        help='Operator-controlled directory of digest-named drill JSON files')
    args = parser.parse_args()
    try:
        data = bounded_read(args.attestation, MAX_INPUT)
        envelope = json.loads(data, object_pairs_hook=unique_pairs)
        receipts = {}
        for name in ('backups', 'signer', 'alerts'):
            digest = envelope['payload'][name]['receipt_sha256']
            if not isinstance(digest, str) or not HEX.fullmatch(digest):
                raise ValueError('invalid receipt digest')
            receipts[digest] = bounded_read(args.receipt_dir / (digest + '.json'), MAX_INPUT)
        result = check(data, bounded_read(args.trusted_public, 32),
                       args.source_sha256, receipts)
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError):
        # No user-provided paths, JSON fields, endpoint or exception text.
        result = {'status': 'BLOCKED', 'reason': 'ATTESTATION_INVALID_OR_UNAVAILABLE',
                  'public_activation': 'DEFERRED'}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'READY_FOR_OPERATOR_REVIEW' else 1


if __name__ == '__main__':
    raise SystemExit(main())
