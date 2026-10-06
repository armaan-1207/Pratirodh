"""Reconcile saved Azure inventory, allocation events, retail prices and metrics.

This generates a conservative retail estimate, not an Azure invoice. It starts
no resources. --write-ledger is allowed only when the estimated bound supports
the existing $30 allowance. All evidence remains hash-bound in the report.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pratirodh.projects.cost_reconciliation import allocated_intervals, metric_values, timestamp


def reconcile(folder, observed):
    evidence = {}
    def read(name):
        path = folder / name
        body = path.read_bytes()
        evidence[name] = hashlib.sha256(body).hexdigest()
        return json.loads(body.decode('utf-8-sig'))
    def price(name, meter, unit):
        rows = [r for r in read(name)['response']['Items'] if r['meterName'] == meter
                and r['unitOfMeasure'] == unit and r['currencyCode'] == 'USD'
                and r.get('type') == 'Consumption']
        if not rows:
            raise ValueError('required USD retail meter missing: ' + meter)
        return max(r['retailPrice'] for r in rows)
    vms, events, disks = read('vms-current.json'), read('allocation-events-current.json'), read('disks-current.json')
    resources = read('resources-current.json')
    names = {'pratirodh-model', 'pratirodh-execution', 'pratirodh-audit'}
    if {v['name'] for v in vms} != names or len(vms) != 3:
        raise ValueError('approved three-VM inventory required')
    allowed = {'Microsoft.Compute/virtualMachines', 'Microsoft.Compute/disks', 'Microsoft.Network/publicIPAddresses',
               'Microsoft.Network/networkSecurityGroups', 'Microsoft.Network/networkInterfaces',
               'Microsoft.Network/virtualNetworks', 'Microsoft.DevTestLab/schedules', 'Microsoft.Storage/storageAccounts'}
    if any(r['type'] not in allowed for r in resources):
        raise ValueError('unpriced resource type present')
    components, allocations = {}, []
    compute = 0
    for vm in vms:
        expected = ('Standard_D4s_v4', 'eastasia', 'D4s v4') if vm['name'] == 'pratirodh-model' else ('Standard_B2als_v2', 'centralindia', 'B2als v2')
        if (vm['size'], vm['location']) != expected[:2]:
            raise ValueError('VM SKU or region changed')
        rate = price(expected[0]+'.json', expected[2], '1 Hour')
        # VM price files include Windows rows with the same meter: exclude them.
        rows = [r for r in read(expected[0]+'.json')['response']['Items'] if r['meterName'] == expected[2]
                and 'Windows' not in r['productName'] and r['type'] == 'Consumption' and r['currencyCode'] == 'USD']
        if not rows:
            raise ValueError('Linux compute retail meter missing')
        rate = max(r['retailPrice'] for r in rows)
        intervals = allocated_intervals(vm, events, observed)
        hours = sum(i['charged_hours_upper_bound'] for i in intervals)
        compute += hours * rate
        allocations.append({'name': vm['name'], 'intervals': intervals, 'hours_upper_bound': hours, 'usd_per_hour': rate})
    components['compute'] = compute
    disk_total = io_total = 0
    if len(disks) != 3:
        raise ValueError('expected three OS disks')
    for disk in disks:
        if disk['sku']['name'] != 'StandardSSD_LRS' or disk['diskSizeGB'] != 64:
            raise ValueError('unpriced disk tier')
        name = 'disks-'+disk['location']+'.json'
        hours = math.ceil((observed-timestamp(disk['timeCreated'])).total_seconds()/3600)
        if hours < 0:
            raise ValueError('disk creation follows observation')
        # Divide by the shortest calendar month, not the usual 730-hour quote.
        disk_total += hours * price(name, 'E6 LRS Disk', '1/Month') / 672
        # Charge the published LRS maximum even during deallocated hours.
        io_total += hours * 81200 / 10000 * price(name, 'E6 LRS Disk Operations', '10K')
    components.update(disk_capacity=disk_total, disk_transactions=io_total)
    earliest = min(timestamp(v['timeCreated']) for v in vms)
    hours = math.ceil((observed-earliest).total_seconds()/3600)
    ips = [r for r in resources if r['type'] == 'Microsoft.Network/publicIPAddresses']
    if len(ips) != 3:
        raise ValueError('unexpected public-IP count')
    components['public_ips'] = sum(hours*price('ips-'+r['location']+'.json', 'Standard IPv4 Static Public IP', '1 Hour') for r in ips)
    accounts = [r for r in resources if r['type'] == 'Microsoft.Storage/storageAccounts']
    if len(accounts) != 1 or accounts[0]['name'] != 'pratirodhstore2873':
        raise ValueError('unpriced storage account')
    capacity = max(metric_values(read('storage-capacity.json'), 'average'))
    operations = read('storage-transactions-egress.json')
    total_operations = sum(metric_values({'value':[m for m in operations['value'] if m['name']['value']=='Transactions']}, 'total'))
    storage_egress = sum(metric_values({'value':[m for m in operations['value'] if m['name']['value']=='Egress']}, 'total'))
    # Bill at least two GB for a full month, including metric sampling headroom.
    components['blob_capacity'] = max(2, math.ceil(capacity*2/1e9))*price('blob-eastasia.json','Hot LRS Data Stored','1 GB/Month')
    components['blob_operations'] = max(10000,total_operations*2)/10000*price('blob-eastasia.json','Hot LRS Write Operations','10K')
    vm_egress = sum(sum(metric_values(read('network-'+role+'.json'),'total')) for role in ['model','execution','audit'])
    # Do not assume free transfer tiers: use twice the bytes, whole GB rounding,
    # and an explicit $1/GB planning ceiling for regional/internet transfer.
    components['network_planning_ceiling'] = math.ceil((vm_egress+storage_egress)*2/1e9)*1.0
    total = sum(components.values())
    return {'observed_at': observed.isoformat(), 'basis': 'RETAIL_ALLOCATION_RECONCILIATION',
            'actual_invoice_status': 'UNAVAILABLE', 'components_usd': components,
            'allocated_compute': allocations, 'modeled_upper_bound_usd': math.ceil(total*1.15*100)/100,
            'contingency_percent':15, 'hourly_upper_bound_usd':0.60, 'shutdown_reserve_usd':2,
            'approved_usd':30, 'evidence_sha256':evidence,
            'limitations':['Retail planning bound, not actual metered billing.',
                          'Metric sampling and ingestion lag covered by headroom; not a monetary Azure spending cap.',
                          'Transfer uses an explicit $1/GB planning ceiling, not a metered quote.',
                          'Refresh snapshots before another run; inventory and workload must remain bounded.'],
            'disk_io_cap_source':'https://azure.microsoft.com/en-us/pricing/details/managed-disks/'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence', type=Path, default=ROOT/'run_output/upstream-validation/budget-check')
    p.add_argument('--write-ledger', action='store_true')
    args = p.parse_args()
    capture_path = args.evidence/'capture.json'
    capture = json.loads(capture_path.read_text(encoding='utf-8'))
    observed = timestamp(capture['observed_at'])
    age = (datetime.now(timezone.utc)-observed).total_seconds()
    if not 0 <= age <= 14400:
        p.error('refresh Azure observations; capture is future-dated or older than four hours')
    if hashlib.sha256((args.evidence/'vms-current.json').read_bytes()).hexdigest() != capture['inventory_sha256']:
        p.error('captured VM inventory changed')
    report = reconcile(args.evidence, observed)
    report['evidence_sha256']['capture.json'] = hashlib.sha256(capture_path.read_bytes()).hexdigest()
    report_path = args.evidence/'reconciliation.json'
    report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if args.write_ledger:
        if report['modeled_upper_bound_usd']+report['shutdown_reserve_usd']>=30:
            p.error('conservative bound exhausts the approved allowance')
        path = ROOT/'usage_ledger.json'
        ledger = json.loads(path.read_text(encoding='utf-8'))
        ledger.update(basis=report['basis'], verification_status='VERIFIED_RETAIL_BOUND', observed_at=report['observed_at'],
                      cost_anchor_upper_bound_usd=report['modeled_upper_bound_usd'],
                      hourly_upper_bound_usd=report['hourly_upper_bound_usd'],
                      reconciliation_evidence=str(report_path.relative_to(ROOT)).replace('\\','/'),
                      reconciliation_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
                      actual_invoice_status='UNAVAILABLE')
        path.write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
