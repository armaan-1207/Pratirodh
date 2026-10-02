"""Create two independent VirtualBox guests; does not install or boot an OS.

Default prints a reviewable plan. --apply creates only the named new guests.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, help='Optional verified Ubuntu Server ISO; can attach after creation')
    parser.add_argument('--directory', type=Path, default=Path('run_output/linux-workers'))
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    iso = args.iso.resolve(strict=True) if args.iso else None
    if iso and (not iso.is_file() or iso.suffix.lower() != '.iso'):
        parser.error('--iso must be an existing Ubuntu Server ISO')
    executable = shutil.which('VBoxManage')
    fallback = Path('C:/Program Files/Oracle/VirtualBox/VBoxManage.exe')
    if executable is None and fallback.is_file():
        executable = str(fallback)
    if args.apply and executable is None:
        parser.error('Install VirtualBox first; administrator approval is required by its installer')
    root = args.directory.resolve()
    plans = []
    for name, port in [('pratirodh-worker', 2222), ('pratirodh-audit', 2223)]:
        disk = root / name / (name + '.vdi')
        commands = [
            ['createvm', '--name', name, '--ostype', 'Ubuntu_64', '--basefolder', str(root), '--register'],
            ['modifyvm', name, '--memory', '3072', '--cpus', '1', '--paravirt-provider', 'none', '--ioapic', 'off', '--nic1', 'nat',
             '--natpf1', f'ssh,tcp,127.0.0.1,{port},,22', '--clipboard-mode', 'disabled',
             '--drag-and-drop', 'disabled', '--graphicscontroller', 'vmsvga', '--vram', '32'],
            ['createmedium', 'disk', '--filename', str(disk), '--size', '40960', '--format', 'VDI'],
            ['storagectl', name, '--name', 'SATA', '--add', 'sata', '--controller', 'IntelAhci'],
            ['storageattach', name, '--storagectl', 'SATA', '--port', '0', '--device', '0',
             '--type', 'hdd', '--medium', str(disk)],
        ]
        if iso:
            commands.append(['storageattach', name, '--storagectl', 'SATA', '--port', '1', '--device', '0',
                             '--type', 'dvddrive', '--medium', str(iso)])
        plans.append({'name': name, 'ssh_port': port, 'commands': commands})
    print(json.dumps({'executable': executable or 'VBoxManage', 'machines': plans}, indent=2))
    if not args.apply:
        return
    # Check BOTH names before creating anything. Never modify an existing guest.
    for plan in plans:
        probe = subprocess.run([executable, 'showvminfo', plan['name']], capture_output=True)
        if probe.returncode == 0 or (root / plan['name']).exists():
            parser.error(f"Guest or directory already exists: {plan['name']}; inspect it manually")
    root.mkdir(parents=True, exist_ok=True)
    for plan in plans:
        for command in plan['commands']:
            subprocess.run([executable, *command], check=True)
    print('Guests created. Install Ubuntu Server in each using the VirtualBox interface.')


if __name__ == '__main__':
    main()
