import argparse
import json
from pathlib import Path
import subprocess
import sys
from .engine import run, replay
from .evidence import Store, fresh, digest
from .execution import DockerExecutor, IMAGE
from .provider import model_provider, OllamaModel


def main():
    parser = argparse.ArgumentParser(description='PRATIRODH security repair evidence')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('build-runner')
    commands.add_parser('doctor')
    serve = commands.add_parser('serve')
    serve.add_argument('--port', type=int, default=8765)
    serve.add_argument('--host', default='127.0.0.1')
    scan_parser = commands.add_parser('scan')
    scan_parser.add_argument('target')
    review_parser = commands.add_parser('review')
    review_parser.add_argument('run_id')
    review_parser.add_argument('--action', choices=['approve', 'reject'], required=True)
    review_parser.add_argument('--reviewer', required=True)
    review_parser.add_argument('--rationale', required=True)
    for name in ('verify-patch', 'run', 'pipeline'):
        command = commands.add_parser(name)
        command.add_argument('target')
        command.add_argument('--contract', required=True)
        if name == 'verify-patch':
            command.add_argument('--patch', required=True)
        command.add_argument('--mode', choices=['static', 'fixed', 'ai', 'full', 'unguided'], default='full')
        command.add_argument('--provider', choices=['ollama', 'gemini', 'openai-compatible'], default='ollama')
        command.add_argument('--model')
        if name == 'pipeline':
            command.add_argument('--strategy', choices=['combined', 'ollama', 'template'], default='ollama')
    check = commands.add_parser('verify-evidence')
    check.add_argument('run_id')
    repeat = commands.add_parser('replay')
    repeat.add_argument('run_id')
    repeat.add_argument('--case', required=True)
    repeat.add_argument('--candidate', type=int, default=0)
    reduce = commands.add_parser('minimize')
    reduce.add_argument('run_id')
    reduce.add_argument('--case', required=True)
    reduce.add_argument('--candidate', type=int, default=0)
    comparison = commands.add_parser('benchmark')
    comparison.add_argument('--split', choices=['all', 'development', 'held-out'], default='all')
    comparison.add_argument('--output', default='run_output/benchmark.json')
    comparison.add_argument('--cloud', action='store_true')
    comparison.add_argument('--model')
    paired = commands.add_parser('compare', help='Frozen external cohort, historical gate and repeated repairs')
    paired.add_argument('--prepare', action='store_true', help='Calibrate and freeze before measurement')
    paired.add_argument('--hours', type=float, default=12, help='Hard execution cap, at most twelve hours')
    paired.add_argument('--resume', action='store_true')
    paired.add_argument('--output', default='docs/COMPARISON_RESULTS_V1.json')
    args = parser.parse_args()
    if args.command == 'compare':
        from .comparison import prepare, compare
        result = prepare() if args.prepare else compare(args.output,args.hours,args.resume)
        print(json.dumps(result.get('metrics', {'frozen': result.get('version')}), indent=2))
        return 0
    if args.command == 'scan':
        from .detection import scan
        print(json.dumps({'findings': scan(args.target)}, indent=2))
        return 0
    if args.command == 'review':
        from .review import review
        print(json.dumps(review(args.run_id, args.action, args.reviewer, args.rationale), indent=2))
        return 0
    if args.command == 'build-runner':
        subprocess.run(['docker', 'build', '-t', IMAGE, '-f', str(Path(__file__).parent / 'Dockerfile'),
                        str(Path(__file__).parent)], check=True)
        return 0
    if args.command == 'doctor':
        try:
            print('Runner image:', DockerExecutor().identity())
            subprocess.run(['git', '--version'], check=True)
            subprocess.run([sys.executable, '-m', 'bandit', '--version'], check=True)
            print('Local model:', json.dumps(OllamaModel().identity()))
            print('Ready. Dashboard: python -m pratirodh serve')
            return 0
        except Exception as exc:
            print('Setup incomplete:', exc)
            return 2
    if args.command == 'serve':
        from .web import create_app
        from waitress import serve
        serve(create_app(), host=args.host, port=args.port, threads=4,
              max_request_body_size=8192, expose_tracebacks=False)
        return 0
    if args.command == 'verify-evidence':
        store = Store()
        report = store.load(args.run_id)
        print(json.dumps(dict(integrity='VALID', fresh=fresh(report, DockerExecutor()),
                             trust_fingerprint=digest((store.root / 'trust.pub').read_bytes())), indent=2))
        return 0
    if args.command == 'replay':
        print(json.dumps(replay(args.run_id, args.case, candidate=args.candidate), indent=2))
        return 0
    if args.command == 'minimize':
        from .minimize import minimize
        print(json.dumps(minimize(args.run_id, args.case, candidate=args.candidate), indent=2))
        return 0
    if args.command == 'benchmark':
        from .benchmark import benchmark
        result = benchmark(args.split, args.cloud, args.model, args.output)
        print(json.dumps(result['metrics'], indent=2))
        return 0
    model = model_provider(args.provider, args.model) if args.command in {'run', 'pipeline'} or args.mode == 'ai' else None
    findings = None
    if args.command == 'pipeline':
        from .detection import scan
        from .contracts import load_contract
        findings = scan(args.target)
        contract = load_contract(args.contract)
        root = Path(__file__).resolve().parents[1]
        registered = root / 'benchmark/scenarios' / contract['id'] / 'contract.json'
        if not registered.exists():
            manifest = json.loads((root / 'benchmark/external-v1/manifest.json').read_text())
            row = next((r for r in manifest['cases'] if r['id'] == contract['id']), None)
            if row: registered = root / row['path'] / 'contract.json'
        if not registered.exists() or registered.read_bytes() != Path(args.contract).read_bytes():
            raise ValueError('pipeline requires an unchanged registered trusted contract')
        if not any(f['file'] == str((Path(args.target) / contract['entrypoint']).resolve()) and f['cwe'] == contract['cwe'] for f in findings):
            print(json.dumps({'decision': 'INSUFFICIENT_EVIDENCE', 'findings': findings, 'gap': 'no matching detector candidate'}))
            return 2
    patch = Path(args.patch).read_text(encoding='utf-8') if args.command == 'verify-patch' else None
    result = run(args.target, args.contract, patch, mode=args.mode, model=model, findings=findings, strategy=getattr(args, 'strategy', 'ollama'))
    print(json.dumps(result, indent=2))
    return 0 if result['decision'] == 'READY_FOR_REVIEW' else 2
