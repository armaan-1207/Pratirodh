"""Tests for cloud budget validation and runner integration."""
import json
from datetime import datetime, timezone, timedelta
import pytest

from pratirodh.projects.cloud_budget import window

from pathlib import Path
WDIR = str(Path(__file__).resolve().parents[1])


def ledger(reported_usd=5.0, hourly_usd=0.50, age_seconds=60):
    """Build a valid cloud_budget ledger matching the actual field schema."""
    now = datetime.now(timezone.utc)
    observed = (now - timedelta(seconds=age_seconds)).isoformat()
    created = (now - timedelta(hours=1)).isoformat()
    return {
        'resource_group': 'pratirodh-validation',
        'approved_usd': 30,
        'reported_cost_usd_upper_bound': reported_usd,
        'hourly_upper_bound_usd': hourly_usd,
        'shutdown_reserve_usd': 2.0,
        'observed_at': observed,
        'resource_creation_utc': created,
        'basis': 'RETAIL_UPPER_BOUND_WITH_RECORDED_BILLING',
    }


def test_remaining_allowance_limits_window_length():
    """$30 cap minus $5 spend minus $2 reserve leaves $23 => 46hr window but capped to 4hr."""
    result = window(ledger(reported_usd=5.0, hourly_usd=0.50))
    assert result['available_usd'] > 0
    assert result['seconds'] <= 14400  # max 4 hours per window
    assert result['seconds'] > 0


def test_unverified_real_ledger_cannot_arm_execution_window():
    data = ledger()
    data['verification_status'] = 'BLOCKED_BILLING_RECONCILIATION'
    with pytest.raises(ValueError, match='verification is incomplete'):
        window(data)


def test_exhausted_budget_raises():
    """When allowance minus reserve is zero or less, window() must raise ValueError."""
    with pytest.raises(ValueError, match='exhausted'):
        window(ledger(reported_usd=28.5, hourly_usd=0.50))


def test_stale_observation_is_rejected():
    """Observations older than 4 hours must be rejected."""
    with pytest.raises(ValueError, match='budget timestamps|refresh|stale'):
        window(ledger(age_seconds=14401))


def test_wrong_resource_group_is_rejected():
    """Ledgers not scoped to the approved group must be rejected."""
    data = ledger()
    data['resource_group'] = 'some-other-group'
    with pytest.raises(ValueError, match='pratirodh-validation'):
        window(data)


def test_wrong_basis_is_rejected():
    """Ledgers without approved cost basis must be rejected."""
    data = ledger()
    data['basis'] = 'SELF_REPORTED'
    with pytest.raises(ValueError, match='recorded billing|basis'):
        window(data)


def test_wrong_approved_usd_is_rejected():
    """Ledgers with a different approved limit must be rejected."""
    data = ledger()
    data['approved_usd'] = 50
    with pytest.raises(ValueError, match=r'\$30|approved'):
        window(data)


@pytest.mark.parametrize('approved', [36, float('nan'), float('inf'), True, 0, -1])
def test_allowance_ceiling_and_numeric_type_cannot_be_bypassed(approved):
    data = ledger()
    data['approved_usd'] = approved
    with pytest.raises(ValueError, match='approved allowance'):
        window(data)


def test_approved_35_preserves_all_prior_consumption_and_reserve():
    now = datetime.now(timezone.utc)
    data = ledger()
    data.update(approved_usd=35, basis='RETAIL_ALLOCATION_RECONCILIATION',
                verification_status='VERIFIED_RETAIL_BOUND',
                observed_at=(now - timedelta(hours=1)).isoformat(),
                resource_creation_utc=(now - timedelta(days=5)).isoformat(),
                cost_anchor_upper_bound_usd=31.39, hourly_upper_bound_usd=.6)
    result = window(data, now)
    assert result['approved_usd'] == 35
    assert result['accrued_upper_bound_usd'] == 31.99
    assert result['available_usd'] == 1.01
    assert result['seconds'] <= 6060
    data['approved_usd'] = 30
    with pytest.raises(ValueError, match='exhausted'):
        window(data, now)


def test_allowance_increase_does_not_remove_shutdown_reserve():
    data = ledger()
    data.update(approved_usd=35, shutdown_reserve_usd=.01,
                verification_status='VERIFIED_RETAIL_BOUND',
                basis='RETAIL_ALLOCATION_RECONCILIATION', cost_anchor_upper_bound_usd=5)
    with pytest.raises(ValueError, match='shutdown reserve'):
        window(data)


def test_legacy_billing_ledger_cannot_claim_new_35_allowance():
    data = ledger()
    data['approved_usd'] = 35
    with pytest.raises(ValueError, match='evidence-bound'):
        window(data)


def test_unverified_anchor_cannot_claim_new_35_allowance():
    data = ledger()
    data.update(approved_usd=35, basis='RETAIL_ALLOCATION_RECONCILIATION', cost_anchor_upper_bound_usd=5)
    with pytest.raises(ValueError, match='evidence-bound'):
        window(data)


def test_campaign_runner_blocks_without_qualification(tmp_path):
    """Campaign runner blocks with BLOCKED_INTAKE when cases are not qualified."""
    import subprocess, sys
    manifest = {'version': 1, 'cases': [{'id': 'x', 'split': 'evaluation'}]}
    mpath = tmp_path / 'manifest.json'
    mpath.write_text(json.dumps(manifest))
    result = subprocess.run(
        [sys.executable, 'tools/run_upstream_campaign.py',
         '--manifest', str(mpath), '--output', str(tmp_path / 'out.json')],
        capture_output=True, text=True,
        cwd=WDIR,
        timeout=15,
    )
    assert result.returncode == 2
    assert 'BLOCKED_INTAKE' in result.stdout


def test_qualify_tool_blocks_with_exhausted_ledger(tmp_path):
    """qualify_upstream_case.py must reject execution when allowance is exhausted."""
    import subprocess, sys
    data = ledger(reported_usd=28.5, hourly_usd=0.50)
    ledger_path = tmp_path / 'ledger.json'
    ledger_path.write_text(json.dumps(data))
    recipe = {
        'approved': True, 'adaptations': 'test',
        'target': '.', 'manifest': '.', 'audit': '.', 'source_map': {},
    }
    recipe_path = tmp_path / 'recipe.json'
    recipe_path.write_text(json.dumps(recipe))
    result = subprocess.run(
        [sys.executable, 'tools/qualify_upstream_case.py',
         '--case', 'python-cve-2021-21330',
         '--recipe', str(recipe_path),
         '--usage-ledger', str(ledger_path)],
        capture_output=True, text=True,
        cwd=WDIR,
        timeout=15,
    )
    # Should exit with error (budget exhausted raises ValueError => parser.error => exit 2)
    assert result.returncode != 0
