"""Process-local Python egress guard for the offline evaluation; not an OS firewall."""
import ipaddress
import json
from pathlib import Path
import runpy
import sys


def guard(event, args):
    if event == 'socket.connect':
        address = args[1]
        if isinstance(address, tuple):
            try:
                local = ipaddress.ip_address(address[0]).is_loopback
            except ValueError:
                local = address[0] == 'localhost'
            if not local:
                raise PermissionError('offline evaluation denies external Python connections')


if __name__ == '__main__':
    sys.addaudithook(guard)
    import socket
    denied = False
    try:
        socket.create_connection(('1.1.1.1', 443), timeout=1)
    except PermissionError:
        denied = True
    assert denied
    Path('run_output/offline-check.json').write_text(json.dumps({'python_external_connection_denied': denied,
        'scope': 'Python audit policy plus operator-applied program firewall rules. Independent OS connection checks in firewall-python-check.json.',
        'local_generation_cohort': 'local-evaluation.json'}, indent=2))
    runpy.run_path(str(Path(__file__).with_name('local_evaluation.py')), run_name='__main__')
