"""Regression checks for the release advisory review gate."""
from copy import deepcopy
from datetime import date
import hashlib
import pytest
from tools.check_image_advisories import check, key


def inputs(tmp_path):
    (tmp_path / 'Dockerfile').write_bytes(b'reviewed build')
    vulnerability = {'VulnerabilityID': 'CVE-TEST', 'PkgName': 'library',
                     'InstalledVersion': '1', 'Severity': 'HIGH'}
    result = {'Type': 'debian', 'Vulnerabilities': [vulnerability]}
    reports = {role: {'SchemaVersion': 2, 'Results': [deepcopy(result)]}
               for role in ('dashboard', 'runner', 'worker', 'requests-demo')}
    policy = {'expires_on': '2026-11-06',
              'inputs': {'Dockerfile': hashlib.sha256(b'reviewed build').hexdigest()},
              'findings': [{'key': list(key(role, result, vulnerability)),
                            'severity': 'HIGH',
                            'reason': 'Reviewed isolated use; residual risk retained',
                            'source': 'https://security-tracker.debian.org/tracker/CVE-TEST'}
                           for role in reports]}
    return policy, reports


def test_reviewed_residual_is_counted_not_claimed_fixed(tmp_path):
    policy, reports = inputs(tmp_path)
    assert check(policy, reports, tmp_path, date(2026, 10, 7))['worker'] == 1


@pytest.mark.parametrize('change', ['unknown', 'version', 'severity', 'fix', 'missing', 'expired', 'build'])
def test_changed_security_state_blocks_release(tmp_path, change):
    policy, reports = inputs(tmp_path)
    today = date(2026, 10, 7)
    vulnerability = reports['worker']['Results'][0]['Vulnerabilities'][0]
    if change == 'unknown':
        vulnerability['VulnerabilityID'] = 'CVE-NEW'
    elif change == 'version':
        vulnerability['InstalledVersion'] = '2'
    elif change == 'severity':
        vulnerability['Severity'] = 'CRITICAL'
    elif change == 'fix':
        vulnerability['FixedVersion'] = '3'
    elif change == 'missing':
        del reports['runner']
    elif change == 'expired':
        today = date(2026, 11, 7)
    elif change == 'build':
        (tmp_path / 'Dockerfile').write_bytes(b'changed build')
    with pytest.raises(ValueError):
        check(policy, reports, tmp_path, today)
