"""Run installed 7B generation on three synthetic projects; no upstream accuracy claim."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pratirodh.evidence import Store
from pratirodh.projects.engine import run_project
from pratirodh.projects.examples import create_example


def available_memory_gb():
    if sys.platform == 'win32':
        class Memory(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in
                ('total', 'available', 'page_total', 'page_available', 'virtual_total', 'virtual_available', 'extended')]
        state = Memory()
        state.length = ctypes.sizeof(state)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
            raise OSError('Cannot measure available physical memory')
        return state.available / 2**30
    values = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    return int(values['MemAvailable'].split()[0]) / 2**20


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('run_output/generated-prototype-7b'))
    parser.add_argument('--image', default='pratirodh-project-worker:0.2')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--context', default='default', help='Docker context for target execution; inference remains local')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error('Choose a fresh output directory; prior evidence is preserved')
    measured_memory = available_memory_gb()
    if measured_memory < 8:
        output.mkdir(parents=True)
        summary = {'cohort': 'Synthetic local-model smoke checks; not upstream release evaluation',
                   'status': 'MEMORY_PREFLIGHT_BLOCKED', 'runs': [],
                   'available_memory_gb': measured_memory, 'required_memory_gb': 8}
        (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(f'Only {measured_memory:.2f} GiB physical RAM available; 8 GiB required before generation')
        return 2
    binary = shutil.which('ollama')
    if not binary:
        parser.error('Start an installed Ollama runtime with the prepared 7B model')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open('http://127.0.0.1:11434/api/tags', timeout=10) as response:
            models = json.load(response)['models']
    except (OSError, ValueError, KeyError):
        output.mkdir(parents=True)
        summary = {'cohort': 'Synthetic local-model smoke checks; not upstream release evaluation',
                   'status': 'MODEL_RUNTIME_UNAVAILABLE', 'runs': [],
                   'available_memory_gb': measured_memory}
        (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print('Local model runtime is unavailable or returned invalid metadata; no generation ran')
        return 2
    model = next((item for item in models if item['name'] == 'qwen2.5-coder:7b'), None)
    if model is None:
        parser.error('Prepare qwen2.5-coder:7b first; this evaluator downloads no weights')
    image = subprocess.check_output(['docker', '--context', args.context, 'image', 'inspect', args.image,
                                     '--format', '{{.Id}}'], text=True, timeout=15).strip()
    measured_memory = available_memory_gb()
    config = {
        'profile': 'laptop', 'runtime': 'ollama', 'endpoint': 'http://127.0.0.1:11434',
        'name': model['name'], 'weights_digest': 'sha256:' + model['digest'].removeprefix('sha256:'),
        'runtime_binary': str(Path(binary).resolve()),
        'runtime_digest': 'sha256:' + hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
        'quantization': model['details']['quantization_level'],
        'available_memory_gb': measured_memory,
    }
    output.mkdir(parents=True)
    for language in ('python', 'node', 'cpp'):
        manifest_path, _ = create_example(output / language, language, image, context=args.context)
        manifest = json.loads(manifest_path.read_text())
        manifest['model'] = config
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    summary = {'cohort': 'Synthetic local-model smoke checks; not upstream release evaluation',
               'model': config, 'status': 'PREPARED', 'runs': []}
    def save():
        (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    save()
    if args.prepare_only:
        print('Prepared pinned manifests at', output)
        return 0
    if measured_memory < 8:
        summary['status'] = 'MEMORY_PREFLIGHT_BLOCKED'
        save()
        print(f'Only {measured_memory:.2f} GiB physical RAM available; 8 GiB required before generation')
        return 2
    store = Store(output / 'evidence')
    summary['status'] = 'RUNNING'
    save()
    for language in ('python', 'node', 'cpp'):
        print('Generating and verifying', language, flush=True)
        root = output / language
        result = run_project(root, root / 'pratirodh-project.json', 'repair',
                             problem={'property': 'tenant-isolation'}, store=store, allow_demo=True,
                             progress=lambda stage: print('  ', stage, flush=True))
        (output / (language + '-result.json')).write_text(json.dumps(result, indent=2) + '\n')
        summary['runs'].append({'language': language, 'id': result['id'], 'decision': result['decision'],
                                'reason': result['reason'], 'model_calls': result['model_calls']})
        save()
    summary['status'] = 'COMPLETED'
    save()
    print(json.dumps(summary['runs'], indent=2))
    return 0 if all(item['decision'] == 'READY_FOR_REVIEW' for item in summary['runs']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
