"""Tests for cloud budget validation and runner integration."""
import json
from datetime import datetime, timezone, timedelta
import pytest

from pratirodh.projects.cloud_budget import window

WDIR = r'C:\Users\armaa\.codex\worktrees\pratirodh-upstream-validation\Derby University Hackathon'


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
