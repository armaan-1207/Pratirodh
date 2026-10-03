"""Read Azure retail rates and inventory; never starts or creates resources."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import shutil
import urllib.parse
import urllib.request


def retail(region, sku):
    query = "armRegionName eq '" + region + "' and armSkuName eq '" + sku + "' and priceType eq 'Consumption'"
    url = 'https://prices.azure.com/api/retail/prices?' + urllib.parse.urlencode({'$filter': query})
    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.load(response)
    choices = [r for r in data['Items'] if r.get('serviceName') == 'Virtual Machines'
               and r.get('productName', '').startswith('Virtual Machines ')
               and r.get('isPrimaryMeterRegion') is True and r.get('unitOfMeasure') == '1 Hour'
               and not any(x in (r.get('productName', '') + r.get('skuName', '')).lower()
                           for x in ('windows', 'spot', 'low priority'))]
    if len(choices) != 1:
        raise ValueError('ambiguous or unavailable current Linux retail rate')
    row = choices[0]
    return {'region': region, 'sku': sku, 'usd_per_hour': row['retailPrice'],
            'meter_id': row['meterId'], 'effective_start': row['effectiveStartDate'], 'source': url}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hours', type=int, default=48)
    parser.add_argument('--output', type=Path, default=Path('run_output/upstream-validation/cloud-cost-plan.json'))
    args = parser.parse_args()
    if not 1 <= args.hours <= 168:
        parser.error('choose between 1 and 168 hours')
    az = shutil.which('az')
    if not az:
        parser.error('Azure CLI is unavailable')
    inventory = subprocess.run([az, 'vm', 'list', '-g', 'pratirodh-validation', '-d',
        '--query', '[].{name:name,state:powerState,size:hardwareProfile.vmSize,location:location}', '-o', 'json'],
        check=True, capture_output=True, text=True, timeout=90)
    rates = [dict(retail('eastasia', 'Standard_D4s_v4'), count=1),
             dict(retail('centralindia', 'Standard_B2als_v2'), count=2)]
    compute = sum(r['usd_per_hour'] * r['count'] for r in rates) * args.hours
    # This explicitly estimated allowance is not a metered disk/IP/transfer quote.
    ancillary_allowance = 5.0
    estimate = compute + ancillary_allowance
    suggested_cap = math.ceil(estimate * 1.25 / 5) * 5
    result = {'updated': datetime.now(timezone.utc).isoformat(), 'inventory': json.loads(inventory.stdout),
              'hours': args.hours, 'rates': rates, 'compute_estimate_usd': round(compute, 2),
              'unpriced_storage_ip_transfer_allowance_usd': ancillary_allowance,
              'suggested_total_cap_usd': suggested_cap, 'approved_total_cap_usd': None,
              'actual_spend': 'UNCONFIRMED', 'execution_authorized': False,
              'shutdown': 'Independent fixed-deadline deallocation guard required before any VM restart',
              'limitations': 'Retail estimate, not actual billing. Credits, taxes, storage and transfer are not verified. Storage/IP charges persist while VMs are deallocated.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in {'rates', 'inventory'}}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
