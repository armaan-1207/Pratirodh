"""Explicit, resumable Ubuntu installer preparation with a pinned SHA256.

Downloads official media only. Never boots a VM or runs installer contents.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time
import urllib.request

NAME = 'ubuntu-24.04.5-live-server-amd64.iso'
URL = 'https://releases.ubuntu.com/24.04/' + NAME
SHA256 = '97f3d7ffb032c3eb3b23d2c8be9cc76e60c2c1f2c0146ba5ba9fe01cafae0fd8'
SIZE = 4080486400


def main():
    folder = Path('run_output/linux-workers/media').resolve()
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / NAME
    partial = target.with_suffix('.iso.partial')
    checkpoint = target.with_suffix('.iso.ranges.json')
    for path in (target, partial, checkpoint):
        if path.is_symlink():
            raise ValueError('Refusing symbolic link media paths')
    if target.exists():
        with target.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != SHA256:
            raise ValueError('Existing ISO digest mismatch')
        print('Verified existing Ubuntu ISO:', target, flush=True)
        return
    if checkpoint.exists():
        state = json.loads(checkpoint.read_text())
        if state['url'] != URL or state['sha256'] != SHA256 or state['size'] != SIZE:
            raise ValueError('Download checkpoint does not match pinned media')
        if not partial.exists():
            raise ValueError('Checkpoint has no partial media')
    else:
        # An earlier serial download is a contiguous prefix. Once parallel
        # transfer begins, ONLY this checkpoint determines resumable ranges.
        prefix = partial.stat().st_size if partial.exists() else 0
        if not 0 <= prefix <= SIZE:
            raise ValueError('Unexpected partial media size')
        state = {'url': URL, 'sha256': SHA256, 'size': SIZE, 'prefix': prefix, 'complete': []}
        if not partial.exists():
            partial.touch()
    def save():
        temporary = checkpoint.with_suffix('.json.new')
        temporary.write_text(json.dumps(state))
        temporary.replace(checkpoint)
    save()
    block = 16 * 1024**2
    ranges = [(start, min(start + block, SIZE) - 1) for start in range(state['prefix'], SIZE, block)]
    completed = set(state['complete'])
    if not completed.issubset({start for start, _ in ranges}):
        raise ValueError('Invalid checkpoint ranges')
    def transfer(pair):
        start, end = pair
        for attempt in range(4):
            try:
                request = urllib.request.Request(URL, headers={'Range': f'bytes={start}-{end}'})
                with urllib.request.urlopen(request, timeout=45) as response, partial.open('r+b') as output:
                    if response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{SIZE}':
                        raise ValueError('Server did not honor exact range')
                    output.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        chunk = response.read(min(1024**2, remaining))
                        if not chunk:
                            raise ValueError('Truncated download range')
                        output.write(chunk)
                        remaining -= len(chunk)
                    output.flush()
                return start
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(attempt + 1)
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(transfer, pair) for pair in ranges if pair[0] not in completed]
        for future in as_completed(futures):
            completed.add(future.result())
            state['complete'] = sorted(completed)
            save()
            size = state['prefix'] + sum(end-start+1 for start, end in ranges if start in completed)
            print('Ubuntu installer transferred:', round(size * 100 / SIZE, 1), '%', flush=True)
    with partial.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if partial.stat().st_size != SIZE or actual != SHA256:
        raise ValueError('ISO SHA256/size verification failed; refusing installation')
    partial.replace(target)
    checkpoint.unlink()
    print('Verified Ubuntu ISO:', target, flush=True)


if __name__ == '__main__':
    main()
