"""Capture read-only Azure budget observations; never start resources or arm a guard.

Raw resource identifiers stay in the operator-selected ignored output directory.
A capture is not a ledger, approval, signed qualification or spending guarantee.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from http.client import HTTPSConnection
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pratirodh.projects.azure_cli import azure_command, find_azure_cli
from pratirodh.projects.cost_reconciliation import timestamp
from pratirodh.projects.cloud_budget import approved_allowance

GROUP = 'pratirodh-validation'
NAMES = {'pratirodh-model', 'pratirodh-execution', 'pratirodh-audit'}


def retail_page(url):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.netloc != 'prices.azure.com'
            or parsed.path != '/api/retail/prices' or parsed.fragment):
        raise ValueError('unexpected retail endpoint')
    connection = HTTPSConnection('prices.azure.com', timeout=30)
    try:
        connection.request('GET', parsed.path + '?' + parsed.query)
        response = connection.getresponse()
        # Reject redirects; the trusted host and scheme cannot change.
        if response.status != 200:
            raise HTTPError(url, response.status, 'retail query failed', {}, None)
        body = response.read(8 * 1024 * 1024 + 1)
        if len(body) > 8 * 1024 * 1024:
            raise ValueError('retail page exceeds bounded response size')
        return json.loads(body)
    finally:
        connection.close()


def azure_read(executable, *arguments):
    for attempt in range(2):
        try:
            result = subprocess.run(azure_command(executable, *arguments, '--output', 'json', '--only-show-errors'),
                                    capture_output=True, text=True, timeout=120, check=True)
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            if attempt:
                raise
            time.sleep(1)


def retail(filter_text):
    url = 'https://prices.azure.com/api/retail/prices?' + urlencode({'$filter': filter_text})
    items = []
    for _ in range(20):
        for attempt in range(2):
            try:
                document = retail_page(url)
                break
            except (HTTPError, URLError, TimeoutError) as error:
                if attempt or isinstance(error, HTTPError) and error.code not in {429, 500, 502, 503, 504}:
                    raise
                time.sleep(1)
        items.extend(document['Items'])
        url = document.get('NextPageLink')
        if not url:
            return {'response': {'Items': items}}
        if not url.startswith('https://prices.azure.com/api/retail/prices?'):
            raise ValueError('unexpected retail pagination host')
    raise ValueError('retail quote exceeds bounded pagination')


def collect(output, executable, read=azure_read, prices=retail, now=None, approved_usd=30):
    approved_usd = approved_allowance(approved_usd)
    output = Path(output)
    if output.exists():
        raise FileExistsError('choose a new capture directory; existing observations are never overwritten')
    output.mkdir(parents=True)
    started = now or datetime.now(timezone.utc)
    hashes = {}

    def save(name, value):
        body = (json.dumps(value, indent=2) + '\n').encode('utf-8')
        (output / name).write_bytes(body)
        hashes[name] = hashlib.sha256(body).hexdigest()

    try:
        vms = read(executable, 'vm', 'list', '--resource-group', GROUP, '--show-details')
        if {vm['name'] for vm in vms} != NAMES or len(vms) != 3:
            raise ValueError('expected exactly the three approved VMs')
        inventory = []
        for vm in vms:
            detail = read(executable, 'vm', 'show', '--resource-group', GROUP, '--name', vm['name'])
            inventory.append({'name': vm['name'], 'state': vm['powerState'],
                              'size': detail['hardwareProfile']['vmSize'], 'location': vm['location'],
                              'timeCreated': detail['timeCreated'], 'id': vm['id']})
        save('vms-current.json', inventory)
        earliest = min(timestamp(vm['timeCreated']) for vm in inventory)
        end = started.isoformat()
        begin = earliest.isoformat()
        # Azure Activity Log only exposes the retention window. Refuse to
        # manufacture complete allocation history for older resources.
        if not 0 <= (started - earliest).total_seconds() < 89 * 86400:
            raise ValueError('allocation history requires archived logs for resources older than 89 days')
        events = read(executable, 'monitor', 'activity-log', 'list', '--resource-group', GROUP,
                      '--start-time', begin, '--end-time', end, '--max-events', '10000')
        if len(events) >= 10000:
            raise ValueError('allocation event capture may be truncated')
        save('allocation-events-current.json', [
            {'resource': event['resourceId'], 'time': event['eventTimestamp'],
             'operation': event['operationName']['value'], 'status': event['status']['value']}
            for event in events])
        save('disks-current.json', read(executable, 'disk', 'list', '--resource-group', GROUP))
        resources = read(executable, 'resource', 'list', '--resource-group', GROUP)
        save('resources-current.json', resources)
        accounts = [row for row in resources if row['type'] == 'Microsoft.Storage/storageAccounts']
        if len(accounts) != 1 or accounts[0]['name'] != 'pratirodhstore2873':
            raise ValueError('expected approved storage account')
        storage = accounts[0]['id']

        def metrics(resource, names, aggregation):
            return read(executable, 'monitor', 'metrics', 'list', '--resource', resource,
                        '--metric', *names, '--aggregation', aggregation,
                        '--start-time', begin, '--end-time', end, '--interval', 'PT1H')

        save('storage-capacity.json', metrics(storage, ['UsedCapacity'], 'Average'))
        save('storage-transactions-egress.json', metrics(storage + '/blobServices/default',
                                                       ['Transactions', 'Egress'], 'Total'))
        for vm in inventory:
            save('network-' + vm['name'].removeprefix('pratirodh-') + '.json',
                 metrics(vm['id'], ['Network Out Total'], 'Total'))
        for sku, region in [('Standard_D4s_v4', 'eastasia'), ('Standard_B2als_v2', 'centralindia')]:
            save(sku + '.json', prices("armRegionName eq '" + region + "' and armSkuName eq '" + sku + "'"))
        for region in ['eastasia', 'centralindia']:
            save('disks-' + region + '.json', prices("armRegionName eq '" + region + "' and serviceName eq 'Storage' and contains(productName, 'Standard SSD')"))
            save('ips-' + region + '.json', prices("armRegionName eq '" + region + "' and serviceName eq 'Virtual Network'"))
        save('blob-eastasia.json', prices("armRegionName eq 'eastasia' and serviceName eq 'Storage' and contains(productName, 'Block Blob')"))
        # Require all existing reconciliation checks to pass before marking a
        # capture usable. This command deliberately does not create a ledger.
        from tools.reconcile_azure_budget import reconcile
        report = reconcile(output, started, approved_usd)
        save('capture.json', {'observed_at': end, 'collection_finished_at': datetime.now(timezone.utc).isoformat(),
                              'inventory_sha256': hashes['vms-current.json'], 'inputs_sha256': dict(hashes),
                              'scope': 'READ_ONLY_BUDGET_CAPTURE'})
        save('collection-status.json', {'status': 'CAPTURED', 'resource_group': GROUP,
                                       'observed_at': end, 'modeled_upper_bound_usd': report['modeled_upper_bound_usd'],
                                       'execution_allowance_status': ('BLOCKED_ALLOWANCE_EXHAUSTED'
                                           if report['modeled_upper_bound_usd'] + report['shutdown_reserve_usd'] >= report['approved_usd']
                                           else 'REVIEWED_LEDGER_REQUIRED'),
                                       'resources_started': False, 'ledger_created': False})
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        save('collection-status.json', {'status': 'BLOCKED_INCOMPLETE_CAPTURE', 'error': type(error).__name__,
                                       'observed_at': started.isoformat(), 'captured_files': sorted(hashes),
                                       'resources_started': False, 'ledger_created': False})
        return 2
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--az', default=find_azure_cli())
    parser.add_argument('--approved-usd', type=float, default=30,
                        help='Explicit total allowance; default30, approved ceiling35 USD')
    args = parser.parse_args()
    if not args.az:
        parser.error('Azure CLI unavailable; provide its installed launcher using --az')
    try:
        result = collect(args.output, args.az, approved_usd=args.approved_usd)
    except (FileExistsError, ValueError) as error:
        parser.error(str(error))
    print((args.output / 'collection-status.json').read_text(encoding='utf-8'))
    return result


if __name__ == '__main__':
    raise SystemExit(main())
