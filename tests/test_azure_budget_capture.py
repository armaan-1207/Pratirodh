import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
from urllib.error import HTTPError

import pytest

from tools.collect_azure_budget import collect
from tools import collect_azure_budget
from tools.reconcile_azure_budget import reconcile, ledger_from_report
from tools import reconcile_azure_budget
from pratirodh.projects.cloud_budget import load_ledger, window


NOW = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)


def observations(executable, *args):
    assert executable == 'mock-az'
    assert args[:2] in {('vm', 'list'), ('vm', 'show'), ('disk', 'list'), ('resource', 'list'),
                       ('monitor', 'activity-log'), ('monitor', 'metrics')}
    names = ['pratirodh-model', 'pratirodh-execution', 'pratirodh-audit']
    created = (NOW - timedelta(hours=3)).isoformat()
    regions = {'pratirodh-model': 'eastasia', 'pratirodh-execution': 'centralindia', 'pratirodh-audit': 'centralindia'}
    if args[:2] == ('vm', 'list'):
        return [{'name': name, 'id': '/virtualMachines/' + name, 'location': regions[name],
                 'powerState': 'VM deallocated'} for name in names]
    if args[:2] == ('vm', 'show'):
        name = args[args.index('--name') + 1]
        return {'timeCreated': created, 'hardwareProfile': {'vmSize': 'Standard_D4s_v4' if name == 'pratirodh-model' else 'Standard_B2als_v2'}}
    if args[:2] == ('disk', 'list'):
        return [{'sku': {'name': 'StandardSSD_LRS'}, 'diskSizeGB': 64, 'timeCreated': created,
                 'location': regions[name]} for name in names]
    if args[:2] == ('resource', 'list'):
        return ([{'name': name, 'type': 'Microsoft.Network/publicIPAddresses', 'location': regions[name]} for name in names]
                + [{'name': 'pratirodhstore2873', 'type': 'Microsoft.Storage/storageAccounts', 'id': '/storageAccounts/pratirodhstore2873'}])
    if args[:2] == ('monitor', 'activity-log'):
        return [{'resourceId': '/virtualMachines/' + name, 'eventTimestamp': (NOW - timedelta(hours=1)).isoformat(),
                 'operationName': {'value': 'Microsoft.Compute/virtualMachines/deallocate/action'},
                 'status': {'value': 'Succeeded'}} for name in names]
    metric_names = args[args.index('--metric') + 1:args.index('--aggregation')]
    field = args[args.index('--aggregation') + 1].lower()
    return {'value': [{'name': {'value': name}, 'timeseries': [{'data': [{field: 1000}]}]} for name in metric_names]}


def quotes(query):
    meters = [('D4s v4', '1 Hour'), ('B2als v2', '1 Hour'), ('E6 LRS Disk', '1/Month'),
              ('E6 LRS Disk Operations', '10K'), ('Standard IPv4 Static Public IP', '1 Hour'),
              ('Hot LRS Data Stored', '1 GB/Month'), ('Hot LRS Write Operations', '10K')]
    return {'response': {'Items': [{'meterName': meter, 'unitOfMeasure': unit, 'currencyCode': 'USD',
                                    'type': 'Consumption', 'productName': 'Linux', 'retailPrice': 0.05}
                                   for meter, unit in meters]}}


def test_capture_is_reconcilable_and_does_not_create_execution_authority(tmp_path):
    output = tmp_path / 'new-capture'
    assert collect(output, 'mock-az', read=observations, prices=quotes, now=NOW) == 0
    capture = json.loads((output / 'capture.json').read_text())
    assert capture['observed_at'] == NOW.isoformat()
    assert len(capture['inputs_sha256']) == 16
    assert reconcile(output, NOW)['modeled_upper_bound_usd'] > 0
    status = json.loads((output / 'collection-status.json').read_text())
    assert status['status'] == 'CAPTURED'
    assert status['resources_started'] is False and status['ledger_created'] is False
    assert not (output / 'guard.json').exists()
    assert not (output / 'usage_ledger.json').exists()


def test_existing_capture_is_never_overwritten(tmp_path):
    marker = tmp_path / 'capture.json'
    marker.write_text('original')
    with pytest.raises(FileExistsError):
        collect(tmp_path, 'mock-az', read=observations, now=NOW)
    assert marker.read_text() == 'original'


def test_incomplete_capture_cannot_be_reconciled_and_error_output_is_sanitized(tmp_path):
    def failing_read(executable, *args):
        raise subprocess.CalledProcessError(1, ['az'], stderr='SECRET_TOKEN')
    output = tmp_path / 'failed'
    assert collect(output, 'mock-az', read=failing_read, now=NOW) == 2
    assert not (output / 'capture.json').exists()
    status = (output / 'collection-status.json').read_text()
    assert 'SECRET_TOKEN' not in status
    assert 'BLOCKED_INCOMPLETE_CAPTURE' in status


def test_truncated_allocation_logs_fail_closed(tmp_path):
    def read(executable, *args):
        rows = observations(executable, *args)
        return [rows[0]] * 10000 if args[:2] == ('monitor', 'activity-log') else rows
    output = tmp_path / 'truncated'
    assert collect(output, 'mock-az', read=read, prices=quotes, now=NOW) == 2
    assert not (output / 'capture.json').exists()


@pytest.mark.parametrize('url', [
    'file:///etc/passwd',
    'http://prices.azure.com/api/retail/prices?$filter=test',
    'https://untrusted.example/api/retail/prices?$filter=test',
])
def test_retail_endpoint_rejection_occurs_before_any_network_connection(monkeypatch, url):
    def forbidden_connection(*args, **kwargs):
        raise AssertionError('untrusted endpoint reached the network')
    monkeypatch.setattr(collect_azure_budget, 'HTTPSConnection', forbidden_connection)
    with pytest.raises(ValueError, match='unexpected retail endpoint'):
        collect_azure_budget.retail_page(url)


def mocked_retail_connection(monkeypatch, status, body):
    observations = {'reads': [], 'requests': [], 'closed': False}

    class Response:
        def __init__(self):
            self.status = status

        def read(self, limit):
            observations['reads'].append(limit)
            return body[:limit]

    class Connection:
        def __init__(self, host, timeout):
            observations['host'] = host
            observations['timeout'] = timeout

        def request(self, method, target):
            observations['requests'].append((method, target))

        def getresponse(self):
            return Response()

        def close(self):
            observations['closed'] = True

    monkeypatch.setattr(collect_azure_budget, 'HTTPSConnection', Connection)
    return observations


def test_retail_redirect_is_rejected_without_reading_body_or_following_location(monkeypatch):
    observations = mocked_retail_connection(monkeypatch, 302, b'untrusted redirect payload')
    with pytest.raises(HTTPError) as error:
        collect_azure_budget.retail_page('https://prices.azure.com/api/retail/prices?$filter=test')
    assert error.value.code == 302
    assert observations == {'reads': [], 'requests': [('GET', '/api/retail/prices?$filter=test')],
                            'closed': True, 'host': 'prices.azure.com', 'timeout': 30}


def test_retail_response_size_is_bounded_and_connection_closed_on_rejection(monkeypatch):
    limit = 8 * 1024 * 1024
    observations = mocked_retail_connection(monkeypatch, 200, b'x' * (limit + 1))
    with pytest.raises(ValueError, match='bounded response size'):
        collect_azure_budget.retail_page('https://prices.azure.com/api/retail/prices?$filter=test')
    assert observations['reads'] == [limit + 1]
    assert observations['closed'] is True
    assert observations['host'] == 'prices.azure.com'
    assert observations['timeout'] == 30


def test_initial_35_ledger_uses_captured_history_and_is_bound_to_report(tmp_path):
    output = tmp_path / 'capture'
    assert collect(output, 'mock-az', read=observations, prices=quotes, now=NOW, approved_usd=35) == 0
    report = reconcile(output, NOW, approved_usd=35)
    report_path = output / 'approved-reconciliation.json'
    report_path.write_text(json.dumps(report))
    ledger_path = tmp_path / 'usage_ledger.json'
    data = ledger_from_report(report, report_path, ledger_path, now=NOW)
    assert data['approved_usd'] == 35
    assert data['cost_anchor_upper_bound_usd'] == report['modeled_upper_bound_usd'] > 0
    assert data['resource_creation_utc'] == (NOW - timedelta(hours=3)).isoformat()
    assert len(data['compute_rates']) == 3
    assert data['shutdown_reserve_usd'] == 2
    ledger_path.write_text(json.dumps(data))
    loaded = load_ledger(ledger_path)
    assert window(loaded, NOW)['approved_usd'] == 35
    with pytest.raises(FileExistsError, match='preserved'):
        ledger_from_report(report, report_path, ledger_path, now=NOW)
    data['approved_usd'] = 30
    ledger_path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='does not match'):
        load_ledger(ledger_path)
    data['approved_usd'] = 35
    data['shutdown_reserve_usd'] = 1
    ledger_path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='does not match'):
        load_ledger(ledger_path)


def test_unsafe_capture_allowance_is_rejected_before_output_creation(tmp_path):
    output = tmp_path / 'unsafe'
    with pytest.raises(ValueError, match='approved allowance'):
        collect(output, 'mock-az', approved_usd=36)
    assert not output.exists()


def test_new_ledger_publication_preserves_existing_temp_and_racing_destination(tmp_path, monkeypatch):
    now = datetime.now(timezone.utc)
    data = {'resource_group': 'pratirodh-validation', 'approved_usd': 30,
            'basis': 'RETAIL_UPPER_BOUND_WITH_RECORDED_BILLING',
            'resource_creation_utc': (now - timedelta(hours=1)).isoformat(),
            'observed_at': now.isoformat(), 'reported_cost_usd_upper_bound': 1,
            'hourly_upper_bound_usd': .6, 'shutdown_reserve_usd': 2}
    path = tmp_path / 'usage_ledger.json'
    stale_temp = path.with_suffix('.tmp')
    stale_temp.write_text('original temporary contents')
    reconcile_azure_budget.publish_new_ledger(path, data)
    assert load_ledger(path)['approved_usd'] == 30
    assert stale_temp.read_text() == 'original temporary contents'
    original_link = reconcile_azure_budget.os.link
    race_path = tmp_path / 'racing_ledger.json'

    def racing_link(source, destination):
        Path(destination).write_text('concurrent writer contents')
        original_link(source, destination)

    monkeypatch.setattr(reconcile_azure_budget.os, 'link', racing_link)
    with pytest.raises(FileExistsError):
        reconcile_azure_budget.publish_new_ledger(race_path, data)
    assert race_path.read_text() == 'concurrent writer contents'
    assert stale_temp.read_text() == 'original temporary contents'
    assert not list(tmp_path.glob('*.json.*.tmp'))
