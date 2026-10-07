"""Enforce a cloud deadline and confirm an independently running shutdown guard."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from .cloud_budget import window, load_ledger
from .azure_cli import find_azure_cli


def execution_window(ledger_path, guard_directory, seconds=14400, az=None):
    ledger_path = Path(ledger_path).resolve()
    ledger = load_ledger(ledger_path)
    allowance = window(ledger)
    if not ledger.get('compute_rates'):
        raise ValueError('refresh the ledger with recorded VM compute rates before cloud execution')
    if type(seconds) is not int or not 1 <= seconds <= 14400:
        raise ValueError('cloud window must be between one second and four hours')
    seconds = min(seconds, allowance['seconds'])
    # Leave time for the guard to validate and arm within the same allowance.
    if seconds <= 10:
        raise ValueError('insufficient cloud allowance to arm shutdown guard')
    wall_deadline = datetime.now(timezone.utc) + timedelta(seconds=seconds - 5)
    deadline = time.monotonic() + seconds - 5
    az = az or find_azure_cli()
    if not az:
        raise ValueError('Azure CLI is required on the independent guard host')
    directory = Path(guard_directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve().parents[2] / 'tools/azure_validation_guard.py'
    kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {'start_new_session': True}
    with (directory / 'guard.stdout.log').open('w') as stdout, (directory / 'guard.stderr.log').open('w') as stderr:
        process = subprocess.Popen([sys.executable, str(script), '--deadline', wall_deadline.isoformat(),
            '--az', str(az), '--output', str(directory), '--usage-ledger', str(ledger_path)],
            stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, **kwargs)
    record_path = directory / 'guard.json'
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError('independent shutdown guard failed to arm')
        try:
            record = json.loads(record_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            record = {}
        if (record.get('status') == 'ARMED' and record.get('pid') == process.pid
                and record.get('deadline') == wall_deadline.isoformat()):
            return deadline, record
        time.sleep(.05)
    # Keep a successfully started guard alive even if acknowledgement fails.
    raise RuntimeError('independent shutdown guard acknowledgement unavailable')
