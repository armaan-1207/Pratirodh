import json
import pytest

from pratirodh.projects.preflight import attest_worker, separate


def test_context_aliases_cannot_establish_separate_guests():
    execution = {'context': 'execution', 'daemon_id': 'daemon-1', 'boot_id_digest': 'same-boot',
                 'machine_id_digest': 'same-machine'}
    audit = dict(execution, context='audit', daemon_id='daemon-2')
    with pytest.raises(ValueError, match='boot_id_digest'):
        separate(execution, audit)
    audit.update(boot_id_digest='other-boot', machine_id_digest='other-machine')
    separate(execution, audit)


def test_live_preflight_requires_matching_image_and_guest_identity():
    image = 'sha256:' + 'a' * 64
    def run(argv):
        if argv[:3] == ['docker', 'context', 'inspect']:
            return json.dumps([{'Endpoints': {'docker': {'Host': 'ssh://pratirodh@execution'}}}])
        if argv[0] == 'ssh':
            assert 'StrictHostKeyChecking=yes' in argv
            return '12345678-1234-1234-1234-123456789abc\n' + '1' * 32
        if 'info' in argv:
            return json.dumps({'ID': 'daemon-1', 'KernelVersion': '6.8', 'OSType': 'linux'})
        return image
    identity = attest_worker('execution', image, run)
    assert identity['status'] == 'PASS'
    assert identity['kernel_version'] == '6.8'
    with pytest.raises(ValueError, match='image identity mismatch'):
        attest_worker('execution', 'sha256:' + 'b' * 64, run)
    with pytest.raises(ValueError, match='dedicated'):
        attest_worker('default', image, run)


def test_tcp_endpoint_cannot_claim_ssh_guest_attestation():
    def run(argv):
        return json.dumps([{'Endpoints': {'docker': {'Host': 'tcp://127.0.0.1:2375'}}}])
    with pytest.raises(ValueError, match='SSH Docker endpoint'):
        attest_worker('execution', 'sha256:' + 'a' * 64, run)
