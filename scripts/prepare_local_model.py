"""Explicit setup helper for official Ollama weights; never called by repairs.

Streams artifacts, verifies sizes/digests, then atomically installs the manifest.
Useful when an operator's Ollama downloader cannot access the registry.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def download_blob(url, temporary, descriptor):
    if descriptor['size'] < 64 * 1024**2:
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open('wb') as stream:
            shutil.copyfileobj(response, stream, 1024**2)
        return
    # Disjoint, validated byte ranges improve explicit preparation throughput.
    checkpoint = temporary.with_suffix('.ranges.json')
    if checkpoint.exists():
        state = json.loads(checkpoint.read_text())
        if state['url'] != url or state['descriptor'] != descriptor or not temporary.exists():
            raise ValueError('download checkpoint does not match model artifact')
    else:
        # An old parallel partial can contain holes. Its file size does NOT
        # establish a completed prefix; retransfer every untracked range.
        state = {'url': url, 'descriptor': descriptor, 'complete': []}
    chunk_size = 32 * 1024**2
    ranges = [(start, min(start + chunk_size, descriptor['size']) - 1)
              for start in range(0, descriptor['size'], chunk_size)]
    completed = set(state['complete'])
    if not completed.issubset({start for start, _ in ranges}):
        raise ValueError('invalid model checkpoint ranges')
    if not temporary.exists():
        temporary.touch()
    def fetch(pair):
        start, end = pair
        for attempt in range(4):
            try:
                request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}'})
                with urllib.request.urlopen(request, timeout=60) as response, temporary.open('r+b') as stream:
                    if response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{descriptor["size"]}':
                        raise ValueError('registry did not honor the requested byte range')
                    stream.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        data = response.read(min(1024**2, remaining))
                        if not data:
                            raise ValueError('truncated model range')
                        stream.write(data)
                        remaining -= len(data)
                    stream.flush()
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(attempt + 1)
        return end - start + 1
    complete = sum(end-start+1 for start, end in ranges if start in completed)
    failures = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch, pair): pair[0] for pair in ranges if pair[0] not in completed}
        for future in as_completed(futures):
            try:
                complete += future.result()
            except Exception as exc:
                failures.append(exc)
                continue
            completed.add(futures[future])
            state['complete'] = sorted(completed)
            checkpoint_new = checkpoint.with_suffix('.json.new')
            checkpoint_new.write_text(json.dumps(state))
            checkpoint_new.replace(checkpoint)
            print('Transferred model ranges', round(100 * complete / descriptor['size'], 1), '%', flush=True)
    if failures:
        raise RuntimeError(f'{len(failures)} model ranges failed; successful ranges were checkpointed. Retry preparation.') from failures[0]


def prepare(root, model):
    root = Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    registry = 'https://registry.ollama.ai/v2/library/'
    family, tag = model.split(':')
    with urllib.request.urlopen(registry + family + '/manifests/' + tag, timeout=30) as response:
        manifest_bytes = response.read(65537)
    if len(manifest_bytes) > 65536:
        raise ValueError('oversized model manifest')
    manifest = json.loads(manifest_bytes)
    descriptors = [manifest['config']] + manifest['layers']
    if len(descriptors) > 20:
        raise ValueError('too many model layers')
    if any(not re.fullmatch(r'sha256:[a-f0-9]{64}', d['digest']) or type(d['size']) is not int or not 0 <= d['size'] <= 8 * 1024**3 for d in descriptors):
        raise ValueError('invalid model descriptor')
    blob_dir = root / 'blobs'
    blob_dir.mkdir(exist_ok=True)
    needed = sum(d['size'] for d in descriptors if not (blob_dir / d['digest'].replace(':', '-')).exists())
    if shutil.disk_usage(root).free < needed + 512 * 1024**2:
        raise ValueError('insufficient disk for explicit model preparation')
    for descriptor in descriptors:
        path = blob_dir / descriptor['digest'].replace(':', '-')
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('model artifact path escapes installation directory')
        if path.exists():
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if 'sha256:' + actual == descriptor['digest'] and path.stat().st_size == descriptor['size']:
                continue
            raise ValueError('existing model blob does not match official digest')
        temporary = path.with_suffix('.partial')
        if temporary.is_symlink():
            raise ValueError('temporary model blob path is a symlink')
        print('Preparing', descriptor['digest'], descriptor['size'], 'bytes', flush=True)
        download_blob(registry + family + '/blobs/' + descriptor['digest'], temporary, descriptor)
        with temporary.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if temporary.stat().st_size != descriptor['size'] or 'sha256:' + actual != descriptor['digest']:
            raise ValueError('downloaded model blob digest/size mismatch')
        temporary.replace(path)
        checkpoint = temporary.with_suffix('.ranges.json')
        if checkpoint.exists():
            checkpoint.unlink()
    destination = root / 'manifests' / 'registry.ollama.ai' / 'library' / family / tag
    if not destination.resolve().is_relative_to(root):
        raise ValueError('model manifest path escapes installation directory')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() != manifest_bytes:
            raise ValueError('existing model manifest differs; use a separate prepared root')
    else:
        destination.write_bytes(manifest_bytes)
    print('Prepared', model, 'manifest digest sha256:' + hashlib.sha256(manifest_bytes).hexdigest(), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=['qwen2.5-coder:7b'], required=True)
    parser.add_argument('--root', default=str(Path.home() / '.ollama' / 'models'))
    args = parser.parse_args()
    prepare(args.root, args.model)
