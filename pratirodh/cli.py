import argparse
import json
from pathlib import Path
import subprocess
import sys
import signal
import threading
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
    serve.add_argument('--store')
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
    check.add_argument('--store', help='evidence store containing this run')
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
    upstream = commands.add_parser('upstream-status', help='Show the generated real-upstream validation status')
    project = commands.add_parser('project')
    project_commands = project.add_subparsers(dest='project_command', required=True)
    inspect_command = project_commands.add_parser('inspect')
    inspect_command.add_argument('path')
    inspect_command.add_argument('--output')
    build_project = project_commands.add_parser('build-worker')
    build_project.add_argument('--tag', default='pratirodh-project-worker:0.2')
    build_project.add_argument('--context', default='default')
    example = project_commands.add_parser('demo')
    example.add_argument('--output', default='run_output/project-demo')
    example.add_argument('--image', default='pratirodh-project-worker:0.2')
    example.add_argument('--context', default='default')
    example.add_argument('--challenge', action='store_true', help='also demonstrate rejection of incomplete repairs')
    harness = project_commands.add_parser('harness')
    harness.add_argument('--language', choices=['python', 'node', 'cpp'], required=True)
    harness.add_argument('--module', required=True)
    harness.add_argument('--function', required=True)
    for name in ('discover', 'repair'):
        command = commands.add_parser(name)
        command.add_argument('path')
        command.add_argument('--manifest', required=True)
        command.add_argument('--profile', choices=['laptop', 'alternative', 'linux-large', 'prototype-small'])
        command.add_argument('--patch')
        command.add_argument('--report', required=name == 'repair')
        command.add_argument('--demo-worker', action='store_true')
        command.add_argument('--resume')
    campaign_command = commands.add_parser('project-benchmark')
    campaign_command.add_argument('--manifest', required=True)
    campaign_command.add_argument('--output', default='run_output/project-campaign.json')
    campaign_command.add_argument('--freeze-only', action='store_true')
    campaign_command.add_argument('--resume', action='store_true')
    campaign_command.add_argument('--seconds', type=int, help='campaign-wide allowance; frozen and preserved on resume')
    campaign_command.add_argument('--audit-reserve', type=int, help='campaign-wide final audit reserve in seconds')
    export = commands.add_parser('export')
    export.add_argument('run_id')
    export.add_argument('--output', required=True)
    export.add_argument('--store', help='evidence store containing this run')
    bundle_check = commands.add_parser('verify-bundle')
    bundle_check.add_argument('path')
    bundle_check.add_argument('--trust', required=True, help='previously trusted public key file')
    args = parser.parse_args()
    if args.command == 'project':
        if args.project_command == 'harness':
            from .projects.harnesses import callable_harness
            print(json.dumps(callable_harness(args.language, args.module, args.function), indent=2))
            return 0
        if args.project_command == 'build-worker':
            directory = Path(__file__).parent / 'projects'
            subprocess.run(['docker', '--context', args.context, 'build', '-t', args.tag,
                            '-f', str(directory / 'Dockerfile'), str(directory)], check=True)
            print('Pin this image ID in your manifest:')
            subprocess.run(['docker', '--context', args.context, 'image', 'inspect', args.tag, '--format', '{{.Id}}'], check=True)
            return 0
        if args.project_command == 'demo':
            from .projects.examples import demo
            result = demo(args.output, args.image, challenge=args.challenge, context=args.context)
            print(json.dumps(result, indent=2))
            return 0 if all(r['matched_expectation'] for r in result['runs']) else 2
        from .projects.manifest import inspect
        result = inspect(args.path)
        serialized = json.dumps(result, indent=2)
        if args.output:
            output_path = Path(args.output)
            if output_path.exists():
                raise ValueError('inspect will not overwrite an existing approved manifest')
            output_path.write_text(serialized, encoding='utf-8')
        print(serialized)
        return 2 if result.get('status') == 'UNSUPPORTED_PROJECT' else 0
    if args.command in {'discover', 'repair'}:
        from .projects.engine import run_project
        cancelled = threading.Event()
        previous = signal.signal(signal.SIGINT, lambda *_: cancelled.set())
        try:
            result = run_project(args.path, args.manifest, args.command,
                problem=json.loads(Path(args.report).read_text(encoding='utf-8')) if args.command == 'repair' else None,
                patch=Path(args.patch).read_text(encoding='utf-8') if args.patch else None,
                profile=args.profile, allow_demo=args.demo_worker, cancelled=cancelled, resume=args.resume)
        finally:
            signal.signal(signal.SIGINT, previous)
        print(json.dumps(result, indent=2))
        return 0 if result['decision'] == 'READY_FOR_REVIEW' else 2
    if args.command == 'project-benchmark':
        from .projects.evaluation import campaign, freeze
        if args.freeze_only:
            if args.seconds is not None or args.audit_reserve is not None:
                parser.error('declare campaign_budget in the manifest before freezing')
            result = freeze(args.manifest)
        else:
            cancelled = threading.Event()
            previous = signal.signal(signal.SIGINT, lambda *unused: cancelled.set())
            try:
                result = campaign(args.manifest, args.output, resume=args.resume, seconds=args.seconds,
                                  audit_reserve=args.audit_reserve, cancelled=cancelled,
                                  progress=lambda state: print(json.dumps(state), flush=True))
            finally:
                signal.signal(signal.SIGINT, previous)
        print(json.dumps(result, indent=2))
        return 0 if args.freeze_only or result['release_complete'] else 2
    if args.command == 'verify-bundle':
        from .projects.export import verify_bundle
        print(json.dumps(verify_bundle(args.path, Path(args.trust).read_bytes()), indent=2))
        return 0
    if args.command == 'export':
        from .projects.export import export_bundle
        print(export_bundle(Store(args.store) if args.store else Store(), args.run_id, args.output))
        return 0
    if args.command == 'compare':
        from .comparison import prepare, compare
        result = prepare() if args.prepare else compare(args.output,args.hours,args.resume)
        print(json.dumps(result.get('metrics', {'frozen': result.get('version')}), indent=2))
        return 0
    if args.command == 'upstream-status':
        from .upstream_status import load_status
        print(json.dumps(load_status(Path(__file__).resolve().parents[1]), indent=2))
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
        serve(create_app(Store(args.store) if args.store else None), host=args.host, port=args.port, threads=4,
              max_request_body_size=8192, expose_tracebacks=False)
        return 0
    if args.command == 'verify-evidence':
        store = Store(args.store) if args.store else Store()
        report = store.load(args.run_id)
        if report.get('version') == 2:
            from .projects.engine import project_fresh
            print(json.dumps(dict(integrity='VALID', fresh=project_fresh(report),
                                  trust_fingerprint=digest((store.root / 'trust.pub').read_bytes())), indent=2))
            return 0
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
