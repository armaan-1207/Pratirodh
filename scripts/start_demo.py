"""Verify the synthetic demonstration and serve its signed evidence locally."""
import argparse
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
import socket
import subprocess
import sys


def verified_store(path):
    """Check all records, including those outside the UI's recent-record limit."""
    from pratirodh.evidence import Store
    from cryptography.exceptions import InvalidSignature
    path = Path(path).resolve()
    if not path.is_dir() or not (path / 'index.sqlite').is_file():
        raise ValueError('selected evidence store is missing; choose an existing --store or use --fresh')
    try:
        with sqlite3.connect((path / 'index.sqlite').as_uri() + '?mode=ro', uri=True) as database:
            ids = [row[0] for row in database.execute('SELECT id FROM runs')]
        if not ids:
            raise ValueError('selected evidence store has no signed records')
        if not (path / 'runs').is_dir() or {p.name for p in (path / 'runs').iterdir()} != set(ids):
            raise ValueError('evidence index and retained records disagree')
        store = Store(path)
        for run_id in ids:
            store.load(run_id)
    except (OSError, sqlite3.Error, InvalidSignature, ValueError, KeyError) as exc:
        raise ValueError('evidence verification failed; preserve this store and restore a verified backup or select another --store') from exc
    return store, len(ids)


def selected_store(root, explicit=None, fresh=False):
    if explicit is not None:
        return Path(explicit)
    state = root / 'run_output' / 'launcher-state.json'
    if fresh or not state.exists():
        return None
    try:
        data = json.loads(state.read_text(encoding='utf-8'))
        path = Path(data['store'])
        if data.get('version') != 1 or not path.is_absolute():
            raise ValueError('invalid saved path')
        return path
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError('saved launcher state is invalid; select --store explicitly or use --fresh') from exc


def remember_store(root, store, model=None):
    from uuid import uuid4
    state = root / 'run_output' / 'launcher-state.json'
    # Preparing supplied demonstrations must not erase the installed model choice.
    if model is None and state.exists():
        try:
            previous = json.loads(state.read_text(encoding='utf-8'))
            if previous.get('version') == 1 and isinstance(previous.get('model'), str):
                model = previous['model']
        except (ValueError, TypeError, AttributeError):
            pass  # An explicitly selected verified store can replace broken state.
    state.parent.mkdir(parents=True, exist_ok=True)
    temporary = state.with_name('launcher-state-' + uuid4().hex + '.tmp')
    temporary.write_text(json.dumps({'version': 1, 'store': str(store.root), 'model': model}) + '\n', encoding='utf-8')
    temporary.replace(state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--store', type=Path, help='reopen signed evidence without preparing new runs')
    parser.add_argument('--requests', action='store_true', help='also verify the prepared Requests reference-fix demonstration')
    parser.add_argument('--model', help='installed local Ollama model for browser generation, e.g. qwen2.5-coder:7b')
    parser.add_argument('--fresh', action='store_true', help='prepare new demonstrations while preserving previous stores')
    parser.add_argument('--check', action='store_true', help='check local dependencies and selected evidence without starting the dashboard')
    args = parser.parse_args()
    if args.fresh and args.store:
        parser.error('--fresh and --store cannot be combined')
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
        store_path = selected_store(root, args.store, args.fresh)
        # Validate before any image build or demo execution; failed stores stay intact.
        if store_path is not None:
            store, count = verified_store(store_path)
        read_only = os.getenv('PRATIRODH_READ_ONLY') == '1'
        if not read_only or store_path is None:
            try:
                docker = subprocess.run(['docker', '--context', 'default', 'info', '--format', '{{.OSType}}'],
                                        cwd=root, check=True, capture_output=True, text=True, timeout=20)
                if docker.stdout.strip() != 'linux':
                    raise ValueError('Docker must use Linux containers; switch Docker Desktop to Linux containers and retry')
            except (OSError, subprocess.SubprocessError) as exc:
                raise ValueError('Docker is unavailable. Start Docker Desktop with Linux containers, then retry; use --store with PRATIRODH_READ_ONLY=1 for saved review') from exc
        if not args.model and store_path is not None and args.store is None:
            saved = json.loads((root / 'run_output/launcher-state.json').read_text(encoding='utf-8'))
            args.model = saved.get('model')
            if args.model is not None and not isinstance(args.model, str):
                raise ValueError('saved model setting is invalid; select --store explicitly')
            if args.model:
                os.environ['PRATIRODH_LOCAL_MODEL'] = args.model
        if args.model and not read_only:
            from pratirodh.provider import OllamaModel
            try:
                identity = OllamaModel(args.model).identity()
                print(f"Local model available: {identity['model']} ({identity['digest']}); generation is verified only after an actual run", flush=True)
            except Exception as exc:
                raise ValueError('local model unavailable. Start Ollama on 127.0.0.1:11434 with cloud disabled and install the requested model; omit --model for supplied-patch workflows') from exc
        if args.check:
            print('Local setup checks passed.' + (f' Verified {count} saved records.' if store_path is not None else ' First launch will prepare demonstrations.'), flush=True)
            return 0
        if store_path is None:
            # Both workflow families must be available from the browser.
            runner = subprocess.run(['docker', '--context', 'default', 'image', 'inspect',
                                     'pratirodh-runner:0.1'], cwd=root, capture_output=True, timeout=15)
            if runner.returncode:
                run(sys.executable, '-m', 'pratirodh', 'build-runner')
            image = subprocess.run(['docker', '--context', 'default', 'image', 'inspect',
                                    'pratirodh-project-worker:0.2', '--format', '{{.Id}}'],
                                   cwd=root, capture_output=True, text=True, timeout=15)
            if image.returncode:
                run(sys.executable, '-m', 'pratirodh', 'project', 'build-worker')
            output = root / 'run_output' / ('demo-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            run(sys.executable, '-m', 'pratirodh', 'project', 'demo', '--challenge', '--output', str(output))
            if args.requests:
                run(sys.executable, str(root / 'scripts/prepare_requests_demo.py'))
                run(sys.executable, str(root / 'scripts/run_requests_demo.py'), '--output', str(output))
            store_path = output / 'evidence'
            store, count = verified_store(store_path)
        elif args.requests:
            print('Reusing saved evidence; use --fresh --requests to prepare new Requests results.', flush=True)
        remember_store(root, store, args.model)
        print(f'Verified {count} signed records. Store: {store.root}', flush=True)
        print(f'Open http://127.0.0.1:{args.port}', flush=True)
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
