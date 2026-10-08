"""Explicit local backup, recovery and separate-key-epoch operations.

Passphrases are requested interactively, never command arguments. No cloud or
external notification is activated by this CLI. Existing destinations are refused.
"""
import argparse
import getpass
import json
from pathlib import Path
import sys
import warnings

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pratirodh.evidence import Store
from pratirodh.operations import encrypted_backup, restore_backup, create_signing_epoch


def secret_prompt(message):
    # getpass otherwise falls back to echoed stdin when no secure terminal is
    # available. Refuse that fallback rather than disclose a backup passphrase.
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        try:
            return getpass.getpass(message).encode('utf-8')
        except (getpass.GetPassWarning, EOFError):
            raise ValueError('a non-echoing interactive terminal is required for the passphrase') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    backup = commands.add_parser('backup')
    backup.add_argument('--store', type=Path, required=True)
    backup.add_argument('--output', type=Path, required=True)
    backup.add_argument('--include-signer', action='store_true',
                        help='Include signer only in this encrypted operator backup, never an evidence export')
    restore = commands.add_parser('restore')
    restore.add_argument('--backup', type=Path, required=True)
    restore.add_argument('--output', type=Path, required=True)
    restore.add_argument('--trusted-public', type=Path, required=True,
                         help='Independent historical trust.pub, not a key recovered from the backup')
    epoch = commands.add_parser('new-key-epoch')
    epoch.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'new-key-epoch':
        receipt = create_signing_epoch(args.output)
    else:
        password = secret_prompt('Backup passphrase (at least 16 UTF-8 bytes): ')
        if args.command == 'backup':
            confirmation = secret_prompt('Confirm backup passphrase: ')
            if password != confirmation:
                raise ValueError('passphrases differ')
            receipt = encrypted_backup(Store(args.store), args.output, password, args.include_signer)
        else:
            receipt = restore_backup(args.backup, args.output, password, args.trusted_public.read_bytes())
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
