"""Verify the synthetic demonstration and serve its signed evidence locally."""
import argparse
import os
from datetime import datetime
from pathlib import Path
import socket
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--store', type=Path, help='reopen signed evidence without preparing new runs')
    parser.add_argument('--requests', action='store_true', help='also verify the prepared Requests reference-fix demonstration')
    parser.add_argument('--model', help='installed local Ollama model for browser generation, e.g. qwen2.5-coder:7b')
    args = parser.parse_args()
    if args.model:
        os.environ['PRATIRODH_LOCAL_MODEL'] = args.model
    if not 1024 <= args.port <= 65535:
        parser.error('choose a port between 1024 and 65535')
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', args.port))
        except OSError:
            parser.error(f'port {args.port} is occupied; choose another --port')
    sys.path.insert(0, str(root))
    try:
        import waitress
        from pratirodh.evidence import Store
    except ImportError:
        parser.error('install project dependencies first: python -m pip install -e .')

    def run(*arguments):
        subprocess.run(arguments, cwd=root, check=True)

    try:
        store_path = args.store
        if store_path is None:
            run('docker', '--context', 'default', 'info', '--format', '{{.ID}}')
            image = subprocess.run(['docker', '--context', 'default', 'image', 'inspect',
                                    'pratirodh-project-worker:0.2', '--format', '{{.Id}}'],
                                   cwd=root, capture_output=True, text=True, timeout=15)
            if image.returncode:
                run(sys.executable, '-m', 'pratirodh', 'project', 'build-worker')
            output = root / 'run_output' / ('demo-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            run(sys.executable, '-m', 'pratirodh', 'project', 'demo', '--challenge', '--output', str(output))
            if args.requests:
                run(sys.executable, str(root / 'scripts/run_requests_demo.py'), '--output', str(output))
            store_path = output / 'evidence'
        store_path = store_path.resolve()
        store = Store(store_path)
        ids = store.list()
        if not ids:
            parser.error('no signed evidence found in the selected store')
        for run_id in ids:
            store.load(run_id)
        print(f'Verified {len(ids)} signed records. Open http://127.0.0.1:{args.port}', flush=True)
        print('Keep this terminal open. Ctrl+C stops the dashboard.', flush=True)
        from pratirodh.web import create_app
        waitress.serve(create_app(store), host='127.0.0.1', port=args.port, threads=4,
                       max_request_body_size=8192, expose_tracebacks=False)
        return 0
    except KeyboardInterrupt:
        print('\nDashboard stopped; evidence preserved.')
        return 0
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f'Demo setup failed: {exc}. Previously collected evidence is preserved.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
