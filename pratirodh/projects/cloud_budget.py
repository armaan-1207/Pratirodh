"""Conservative allowance accounting for the disposable Azure validation group."""
from datetime import datetime, timezone, timedelta
import math
import hashlib
import json
from pathlib import Path

# Explicit operator approval raised the ceiling to $35 on 2026-10-07. Existing
# lower ledger caps remain authoritative; tools default to the previous $30.
MAX_APPROVED_USD = 35


def approved_allowance(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= MAX_APPROVED_USD:
        raise ValueError('approved allowance must be finite, positive and at most $35')
    return value


def load_ledger(path):
    path = Path(path).resolve()
    ledger = json.loads(path.read_text(encoding='utf-8'))
    if ledger.get('basis') == 'RETAIL_ALLOCATION_RECONCILIATION':
        relative = Path(ledger['reconciliation_evidence'])
        report_path = (path.parent / relative).resolve()
        if relative.is_absolute() or not report_path.is_relative_to(path.parent):
            raise ValueError('reconciliation evidence escapes ledger directory')
        body = report_path.read_bytes()
        if hashlib.sha256(body).hexdigest() != ledger['reconciliation_sha256']:
            raise ValueError('reconciliation evidence changed')
        report = json.loads(body)
        if any(report.get(key) != ledger.get(field) for key, field in [
                ('basis','basis'), ('observed_at','observed_at'),
                ('modeled_upper_bound_usd','cost_anchor_upper_bound_usd'),
                ('hourly_upper_bound_usd','hourly_upper_bound_usd'), ('approved_usd','approved_usd'),
                ('shutdown_reserve_usd','shutdown_reserve_usd')]):
            raise ValueError('ledger does not match reconciliation evidence')
        if ledger.get('approved_usd', 0) > 30 and report.get('resource_creation_utc') != ledger.get('resource_creation_utc'):
            raise ValueError('resource creation time does not match reconciliation evidence')
        for name, expected in report['evidence_sha256'].items():
            evidence = (report_path.parent / name).resolve()
            if evidence.parent != report_path.parent or hashlib.sha256(evidence.read_bytes()).hexdigest() != expected:
                raise ValueError('reconciliation input changed')
    return ledger


def window(ledger, now=None):
    now = now or datetime.now(timezone.utc)
    if ledger.get('resource_group') != 'pratirodh-validation':
        raise ValueError('the approved allowance applies only to pratirodh-validation')
    approved = approved_allowance(ledger.get('approved_usd'))
    if ledger.get('verification_status') not in (None, 'VERIFIED', 'VERIFIED_RETAIL_BOUND'):
        raise ValueError('Azure allowance verification is incomplete; reconcile recorded billing and allocation history')
    anchored = ledger.get('basis') == 'RETAIL_ALLOCATION_RECONCILIATION'
    if approved > 30 and (not anchored or ledger.get('verification_status') != 'VERIFIED_RETAIL_BOUND'):
        raise ValueError('allowance above $30 requires evidence-bound allocation reconciliation')
    if ledger.get('basis') not in {'RETAIL_UPPER_BOUND_WITH_RECORDED_BILLING', 'RETAIL_ALLOCATION_RECONCILIATION'}:
        raise ValueError('recorded billing and a conservative usage bound are required')
    start = datetime.fromisoformat(ledger['resource_creation_utc'])
    observed = datetime.fromisoformat(ledger['observed_at'])
    if start.tzinfo is None or observed.tzinfo is None or not start <= observed <= now:
        raise ValueError('budget timestamps must be ordered UTC-aware observations')
    if (now - observed).total_seconds() > 14400:
        raise ValueError('refresh Azure cost and resource observations before another window')
    cost_field = 'cost_anchor_upper_bound_usd' if anchored else 'reported_cost_usd_upper_bound'
    values = [ledger[k] for k in ('hourly_upper_bound_usd', cost_field, 'shutdown_reserve_usd')]
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('finite positive cost bounds are required')
    rate, reported, reserve = values
    if reserve < 2:
        raise ValueError('retain at least the $2 shutdown reserve')
    rates = ledger.get('compute_rates', [])
    if rates:
        if not isinstance(rates, list) or any(type(r.get('count')) is not int or r['count'] <= 0
                or type(r.get('usd_per_hour')) not in (int, float)
                or not math.isfinite(r['usd_per_hour']) or r['usd_per_hour'] <= 0 for r in rates):
            raise ValueError('invalid recorded compute rates')
        if rate < sum(r['usd_per_hour'] * r['count'] for r in rates):
            raise ValueError('hourly bound understates recorded VM compute rates')
    # Legacy ledgers charge all time since creation. Reconciled ledgers preserve
    # the evidence-bound historical estimate and charge every later hour at the
    # full planning rate, even if the VMs remain deallocated.
    accrued = (reported + (now - observed).total_seconds()/3600*rate if anchored else
               max(reported, (now - start).total_seconds() / 3600 * rate))
    available = max(0, approved - accrued - reserve)
    seconds = min(14400, math.floor(available / rate * 3600))
    if seconds < 60:
        raise ValueError('approved usage allowance is exhausted')
    return {'approved_usd': approved, 'accrued_upper_bound_usd': round(accrued, 6), 'available_usd': round(available, 6),
            'hourly_upper_bound_usd': rate, 'seconds': seconds,
            'deadline': (now + timedelta(seconds=seconds)).isoformat(),
            'remaining_total_seconds': math.floor(available / rate * 3600)}
