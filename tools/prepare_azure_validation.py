"""Write a reviewable ARM deployment; this command never creates Azure resources."""
from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path


def template() -> dict:
    resources = []
    roles = [('model', 'eastasia', 'Standard_D4s_v4'),
             ('execution', 'centralindia', 'Standard_B2als_v2'),
             ('audit', 'centralindia', 'Standard_B2als_v2')]
    for role, location, size in roles:
        name = f'pratirodh-{role}'
        def rid(kind, suffix=''):
            return f"[resourceId('Microsoft.Network/{kind}', '{name}{suffix}')]"
        resources.extend([
            {'type': 'Microsoft.Network/networkSecurityGroups', 'apiVersion': '2023-11-01',
             'name': name, 'location': location, 'properties': {'securityRules': [
                 {'name': 'operator-ssh', 'properties': {'priority': 100, 'protocol': 'Tcp',
                  'access': 'Allow', 'direction': 'Inbound', 'sourceAddressPrefix': "[parameters('operatorCidr')]",
                  'sourcePortRange': '*', 'destinationAddressPrefix': '*', 'destinationPortRange': '22'}},
                 {'name': 'deny-other-inbound', 'properties': {'priority': 200, 'protocol': '*',
                  'access': 'Deny', 'direction': 'Inbound', 'sourceAddressPrefix': '*',
                  'sourcePortRange': '*', 'destinationAddressPrefix': '*', 'destinationPortRange': '*'}}]}},
            {'type': 'Microsoft.Network/virtualNetworks', 'apiVersion': '2023-11-01',
             'name': name, 'location': location, 'dependsOn': [rid('networkSecurityGroups')],
             'properties': {'addressSpace': {'addressPrefixes': ['10.30.0.0/24']},
                            'subnets': [{'name': 'worker', 'properties': {'addressPrefix': '10.30.0.0/24',
                            'networkSecurityGroup': {'id': rid('networkSecurityGroups')}}}]}},
            {'type': 'Microsoft.Network/publicIPAddresses', 'apiVersion': '2023-11-01',
             'name': name, 'location': location, 'sku': {'name': 'Standard'},
             'properties': {'publicIPAllocationMethod': 'Static'}},
            {'type': 'Microsoft.Network/networkInterfaces', 'apiVersion': '2023-11-01',
             'name': name, 'location': location,
             'dependsOn': [rid('virtualNetworks'), rid('publicIPAddresses')],
             'properties': {'ipConfigurations': [{'name': 'primary', 'properties': {
                 'privateIPAllocationMethod': 'Dynamic',
                 'subnet': {'id': f"[resourceId('Microsoft.Network/virtualNetworks/subnets', '{name}', 'worker')]"},
                 'publicIPAddress': {'id': rid('publicIPAddresses')}}}]}},
            {'type': 'Microsoft.Compute/virtualMachines', 'apiVersion': '2024-03-01',
             'name': name, 'location': location, 'dependsOn': [rid('networkInterfaces')],
             'tags': {'project': 'Pratirodh', 'purpose': 'upstream-validation', 'role': role},
             'properties': {'hardwareProfile': {'vmSize': size},
                 'storageProfile': {'imageReference': {'publisher': 'Canonical', 'offer': 'ubuntu-24_04-lts',
                    'sku': 'server', 'version': 'latest'},
                    'osDisk': {'createOption': 'FromImage', 'diskSizeGB': 64,
                               'managedDisk': {'storageAccountType': 'StandardSSD_LRS'}, 'deleteOption': 'Delete'}},
                 'osProfile': {'computerName': name, 'adminUsername': 'pratirodh',
                    'linuxConfiguration': {'disablePasswordAuthentication': True,
                        'ssh': {'publicKeys': [{'path': '/home/pratirodh/.ssh/authorized_keys',
                                               'keyData': "[parameters('sshPublicKey')]"}]}}},
                 'securityProfile': {'securityType': 'TrustedLaunch',
                     'uefiSettings': {'secureBootEnabled': True, 'vTpmEnabled': True}},
                 'networkProfile': {'networkInterfaces': [{'id': rid('networkInterfaces'),
                                                          'properties': {'deleteOption': 'Delete'}}]},
                 'diagnosticsProfile': {'bootDiagnostics': {'enabled': True}}}},
            {'type': 'Microsoft.DevTestLab/schedules', 'apiVersion': '2018-09-15',
             'name': f'shutdown-computevm-{name}', 'location': location,
             'dependsOn': [f"[resourceId('Microsoft.Compute/virtualMachines', '{name}')]"],
             'properties': {'status': 'Enabled', 'taskType': 'ComputeVmShutdownTask',
                'dailyRecurrence': {'time': '2330'}, 'timeZoneId': 'India Standard Time',
                'notificationSettings': {'status': 'Disabled'},
                'targetResourceId': f"[resourceId('Microsoft.Compute/virtualMachines', '{name}')]"}}
        ])
    return {'$schema': 'https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#',
            'contentVersion': '1.0.0.0', 'parameters': {
                'operatorCidr': {'type': 'string'}, 'sshPublicKey': {'type': 'string'}},
            'resources': resources}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operator-ip', required=True)
    parser.add_argument('--public-key', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('run_output/azure-validation'))
    args = parser.parse_args()
    address = ipaddress.ip_address(args.operator_ip)
    key = args.public_key.read_text().strip()
    if not key.startswith('ssh-ed25519 ') or 'PRIVATE KEY' in key:
        parser.error('Supply an Ed25519 PUBLIC key only.')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'template.json').write_text(json.dumps(template(), indent=2), encoding='utf-8')
    deployment = {'$schema': 'https://schema.management.azure.com/schemas/2018-05-01/subscriptionDeploymentTemplate.json#',
        'contentVersion': '1.0.0.0', 'parameters': template()['parameters'], 'resources': [
            {'type': 'Microsoft.Resources/resourceGroups', 'apiVersion': '2022-09-01',
             'name': 'pratirodh-validation', 'location': 'eastasia'},
            {'type': 'Microsoft.Resources/deployments', 'apiVersion': '2022-09-01',
             'name': 'pratirodh-validation', 'resourceGroup': 'pratirodh-validation',
             'dependsOn': ["[subscriptionResourceId('Microsoft.Resources/resourceGroups', 'pratirodh-validation')]"],
             'properties': {'mode': 'Incremental', 'expressionEvaluationOptions': {'scope': 'inner'},
                'parameters': {k: {'value': "[parameters('" + k + "')]"} for k in template()['parameters']},
                'template': template()}}]}
    (args.output / 'subscription-template.json').write_text(json.dumps(deployment, indent=2), encoding='utf-8')
    params = {'operatorCidr': {'value': f'{address}/{address.max_prefixlen}'},
              'sshPublicKey': {'value': key}}
    (args.output / 'parameters.json').write_text(json.dumps({'parameters': params}, indent=2), encoding='utf-8')
    print(f'Prepared {args.output}; no Azure resources created.')


if __name__ == '__main__':
    main()
