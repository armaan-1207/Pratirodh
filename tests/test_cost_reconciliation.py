from datetime import datetime, timezone, timedelta
import hashlib
import json
import pytest
from pratirodh.projects.cost_reconciliation import allocated_intervals, metric_values
from pratirodh.projects.cloud_budget import window, load_ledger


def test_deallocated_interval_is_excluded_and_failed_start_is_charged():
    start = datetime(2026,10,2,tzinfo=timezone.utc)
    vm = {'name':'pratirodh-model','timeCreated':start.isoformat(),'state':'VM running'}
    def event(hour,operation,status):
        return {'resource':'/virtualMachines/pratirodh-model','time':(start+timedelta(hours=hour)).isoformat(),
                'operation':'Microsoft.Compute/virtualMachines/'+operation,'status':status}
    events = [event(1,'deallocate/action','Succeeded'),event(10,'start/action','Started'),event(11,'start/action','Failed')]
    intervals = allocated_intervals(vm,events,start+timedelta(hours=12))
    assert sum(i['charged_hours_upper_bound'] for i in intervals)==3


def test_missing_shutdown_receipt_cannot_discount_running_hours():
    start = datetime(2026,10,2,tzinfo=timezone.utc)
    vm={'name':'pratirodh-model','timeCreated':start.isoformat(),'state':'VM deallocated'}
    with pytest.raises(ValueError,match='shutdown'):
        allocated_intervals(vm,[],start+timedelta(hours=2))


def test_empty_metrics_do_not_mean_zero_spend():
    with pytest.raises(ValueError,match='missing'):
        metric_values({'value':[]},'total')


def test_anchor_preserves_incurred_cost_and_charges_since_observation():
    now=datetime(2026,10,6,tzinfo=timezone.utc)
    ledger={'resource_group':'pratirodh-validation','approved_usd':30,'verification_status':'VERIFIED',
            'basis':'RETAIL_ALLOCATION_RECONCILIATION','resource_creation_utc':(now-timedelta(days=4)).isoformat(),
            'observed_at':(now-timedelta(hours=1)).isoformat(),'hourly_upper_bound_usd':.6,
            'cost_anchor_upper_bound_usd':20,'shutdown_reserve_usd':2}
    assert window(ledger,now)['accrued_upper_bound_usd']==20.6
    assert window(ledger,now)['available_usd']==7.4


def test_altered_receipt_is_rejected(tmp_path):
    report={'basis':'RETAIL_ALLOCATION_RECONCILIATION','observed_at':'2026-10-06T00:00:00+00:00',
            'modeled_upper_bound_usd':20,'hourly_upper_bound_usd':.6,'approved_usd':30,'evidence_sha256':{}}
    path=tmp_path/'receipt.json';path.write_text(json.dumps(report))
    ledger=dict(report,reconciliation_evidence='receipt.json',cost_anchor_upper_bound_usd=20,
                reconciliation_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    p=tmp_path/'ledger.json';p.write_text(json.dumps(ledger))
    assert load_ledger(p)['cost_anchor_upper_bound_usd']==20
    path.write_text('{}')
    with pytest.raises(ValueError,match='changed'):
        load_ledger(p)
