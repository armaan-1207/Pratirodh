"""Write the canonical generated status projection atomically."""
import argparse
import json
from pathlib import Path
import sys
import subprocess
import shutil
import os
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pratirodh.upstream_status import load_status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--refresh', action='store_true', help='Read-only Azure power and bounded Docker preparation probes')
    args = parser.parse_args()
    if args.refresh:
        from scripts.check_preparation import report
        root = args.root.resolve()
        preparation = report(root / 'benchmark/recipes', True, 5)
        preparation['updated'] = datetime.now(timezone.utc).isoformat()
        prepared_path = root / 'run_output/upstream-validation/preparation.json'
        prepared_path.parent.mkdir(parents=True, exist_ok=True)
        prepared_path.write_text(json.dumps(preparation, indent=2) + '\n', encoding='utf-8')
        try:
            from pratirodh.projects.azure_cli import find_azure_cli, azure_command
            az = find_azure_cli()
            if not az:
                raise FileNotFoundError('Azure CLI is not on PATH')
            command = azure_command(az)
            result = subprocess.run(command + ['vm', 'list', '-g', 'pratirodh-validation', '-d',
                                     '--query', '[].{name:name,state:powerState}', '-o', 'json'],
                                    check=True, capture_output=True, text=True, timeout=45)
            observations = json.loads(result.stdout)
            power_path = root / 'run_output/azure-validation/power-state.json'
            power_path.parent.mkdir(parents=True, exist_ok=True)
            power_path.write_text(json.dumps({'status': 'OBSERVED', 'observations': observations,
                                              'updated': datetime.now(timezone.utc).isoformat(),
                                              'source': 'Azure CLI read-only vm list -d'}, indent=2) + '\n', encoding='utf-8')
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            print('Azure power refresh unavailable: ' + type(error).__name__, file=sys.stderr)
    payload = load_status(args.root.resolve())
    output = args.root / 'run_output/upstream-validation/status.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    temporary.replace(output)
    print(json.dumps({key: payload[key] for key in ('status', 'acquired', 'qualified', 'completed', 'audited')}, indent=2))


if __name__ == '__main__':
    main()
