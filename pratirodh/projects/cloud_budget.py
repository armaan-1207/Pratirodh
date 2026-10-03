"""Conservative allowance accounting for the disposable Azure validation group."""
from datetime import datetime, timezone, timedelta
import math


def window(ledger, now=None):
    now = now or datetime.now(timezone.utc)
    if ledger.get('resource_group') != 'pratirodh-validation' or ledger.get('approved_usd') != 30:
        raise ValueError('the approved allowance is $30 for pratirodh-validation')
    if ledger.get('basis') != 'RETAIL_UPPER_BOUND_WITH_RECORDED_BILLING':
        raise ValueError('recorded billing and a conservative usage bound are required')
    start = datetime.fromisoformat(ledger['resource_creation_utc'])
    observed = datetime.fromisoformat(ledger['observed_at'])
    if start.tzinfo is None or observed.tzinfo is None or not start <= observed <= now:
        raise ValueError('budget timestamps must be ordered UTC-aware observations')
    if (now - observed).total_seconds() > 14400:
        raise ValueError('refresh Azure cost and resource observations before another window')
    values = [ledger[k] for k in ('hourly_upper_bound_usd', 'reported_cost_usd_upper_bound', 'shutdown_reserve_usd')]
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('finite positive cost bounds are required')
    rate, reported, reserve = values
    # Charge every hour since resource creation as if all VMs were running.
    # This includes qualification, downtime, storage/IP and billing lag.
    accrued = max(reported, (now - start).total_seconds() / 3600 * rate)
    available = max(0, 30 - accrued - reserve)
    seconds = min(14400, math.floor(available / rate * 3600))
    if seconds < 60:
        raise ValueError('approved usage allowance is exhausted')
    return {'accrued_upper_bound_usd': round(accrued, 6), 'available_usd': round(available, 6),
            'hourly_upper_bound_usd': rate, 'seconds': seconds,
            'deadline': (now + timedelta(seconds=seconds)).isoformat(),
            'remaining_total_seconds': math.floor(available / rate * 3600)}
