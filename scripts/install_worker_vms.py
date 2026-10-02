"""Prepare unattended Ubuntu installs in the two NEW PRATIRODH VirtualBox VMs.

Creates a dedicated controller SSH key and appends two SSH aliases. The guests
remain powered off. No existing guest, key or alias is overwritten.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--directory', type=Path, default=Path('run_output/linux-workers'))
    args = parser.parse_args()
    iso = args.iso.resolve(strict=True)
    root = args.directory.resolve(strict=True)
    executable = shutil.which('VBoxManage') or 'C:/Program Files/Oracle/VirtualBox/VBoxManage.exe'
    ssh = Path.home() / '.ssh'
    ssh.mkdir(exist_ok=True)
    key_path = ssh / 'pratirodh_workers_ed25519'
    config = ssh / 'config'
    original = config.read_text() if config.exists() else ''
    # Avoid partially replacing an operator's prior setup.
    if key_path.exists() or any(name in original for name in ('pratirodh-worker', 'pratirodh-audit')):
        parser.error('Dedicated SSH key or aliases already exist. Inspect them before retrying.')
    for name in ('pratirodh-worker', 'pratirodh-audit'):
        machine = subprocess.run([executable, 'showvminfo', name, '--machinereadable'],
                                 capture_output=True, text=True, check=True).stdout
        expected = str(root / name).lower().replace('\\', '/')
        settings = next((line for line in machine.splitlines() if line.startswith('CfgFile=')), '')
        normalized = settings.lower().replace('\\\\', '/').replace('\\', '/')
        if expected not in normalized or 'VMState="poweroff"' not in machine:
            parser.error(f'{name} must be a powered-off guest in the specified directory')
        if list((root / name).glob('Unattended-*')):
            parser.error(f'{name} already has unattended installation media; inspect before retrying')
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.OpenSSH,
                                           serialization.PublicFormat.OpenSSH).decode()
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                          serialization.PrivateFormat.OpenSSH,
                                          serialization.NoEncryption()))
    key_path.with_suffix('.pub').write_text(public + '\n')
    additions = '\n# Dedicated PRATIRODH VirtualBox guests\n'
    for name, port in [('pratirodh-worker', 2222), ('pratirodh-audit', 2223)]:
        additions += (f'Host {name}\n    HostName 127.0.0.1\n    Port {port}\n'
                      f'    User pratirodh\n    IdentityFile "{key_path.as_posix()}"\n'
                      '    IdentitiesOnly yes\n    StrictHostKeyChecking yes\n')
    with config.open('a', encoding='utf-8') as stream:
        stream.write(additions)
    if os.name == 'nt':
        # Windows OpenSSH rejects inherited access by other ordinary accounts.
        identity = subprocess.run(['whoami'], capture_output=True, text=True, check=True).stdout.strip()
        for path in (config, key_path):
            subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r', identity + ':F'],
                           capture_output=True, check=True)
    bootstrap = Path(__file__).with_name('bootstrap_ubuntu_worker.sh').read_bytes()
    encoded = base64.b64encode(bootstrap).decode()
    for name in ('pratirodh-worker', 'pratirodh-audit'):
        template = root / name / 'pratirodh-autoinstall.yaml'
        template.write_text(f'''#cloud-config
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: us
  storage:
    layout:
      name: direct
    swap:
      size: 0
  identity:
    hostname: {name}
    username: pratirodh
    password: '@@VBOX_INSERT_USER_PASSWORD_SHACRYPT512@@'
  ssh:
    install-server: true
    allow-pw: false
    authorized-keys:
      - {json.dumps(public)}
  shutdown: poweroff
  user-data:
    disable_root: true
    write_files:
      - path: /root/pratirodh-bootstrap.sh
        permissions: '0700'
        encoding: b64
        content: {encoded}
    runcmd:
      - [bash, /root/pratirodh-bootstrap.sh, pratirodh]
''', encoding='utf-8')
        result = subprocess.run([executable, 'unattended', 'install', name,
            '--iso=' + str(iso), '--user=pratirodh', '--user-password-file=stdin',
            '--hostname=' + name + '.local', '--script-template=' + str(template),
            '--extra-install-kernel-parameters=nomodeset',
            '--no-install-additions', '--no-install-txs', '--start-vm=none'],
            input=secrets.token_urlsafe(48) + '\n', text=True, capture_output=True)
        if result.returncode:
            # Never echo installer output: it may include credential fields.
            raise RuntimeError(f'Unattended preparation failed for {name}; inspect VirtualBox locally')
        print(f'{name}: unattended installation prepared; guest remains powered off')
    print('SSH aliases configured. Private key stays on this Windows controller.')


if __name__ == '__main__':
    main()
