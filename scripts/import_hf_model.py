"""Verify and import the reviewed Qwen Hugging Face GGUF, without downloading.

This creates a local Ollama model entry. It does not train or modify weights.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

MODEL = 'pratirodh-qwen:7b-hf'
SOURCE = 'https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF'
REVISION = '13fb94bfda8c8cf22497dc57b78f391a9acb426a'
SHA256 = '509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c'


def verify_weights(path, expected=SHA256):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('select a downloaded regular GGUF file')
    if not 4 <= path.stat().st_size <= 8 * 1024**3:
        raise ValueError('GGUF size is outside the reviewed import limit')
    with path.open('rb') as stream:
        if stream.read(4) != b'GGUF':
            raise ValueError('file is not GGUF weights')
        stream.seek(0)
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != expected:
        raise ValueError('GGUF checksum mismatch: download is incomplete or differs from the reviewed artifact')
    return path.resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gguf', type=Path, required=True)
    args = parser.parse_args()
    try:
        path = verify_weights(args.gguf)
        if any(c in str(path) for c in ('\n', '\r', '"')):
            raise ValueError('model path contains unsupported Modelfile characters')
        binary = shutil.which('ollama')
        if binary is None and os.name == 'nt' and os.getenv('LOCALAPPDATA'):
            installed = Path(os.environ['LOCALAPPDATA']) / 'Programs/Ollama/ollama.exe'
            if installed.is_file():
                binary = str(installed)
        if binary is None:
            raise ValueError('install Ollama from its official source and start its local service')
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from pratirodh.provider import OllamaModel
        provider = OllamaModel(MODEL, assistant='off')
        tags = provider.request('/api/tags')['models']
        if any(m['name'] == MODEL for m in tags):
            raise ValueError('model entry already exists; preserve it and inspect its recorded identity before any replacement')
        output = Path(__file__).resolve().parents[1] / 'run_output/hf-model-import'
        output.mkdir(parents=True, exist_ok=True)
        modelfile = output / 'Modelfile'
        content = f'FROM "{path.as_posix()}"\nPARAMETER num_ctx 8192\nPARAMETER temperature 0\nPARAMETER num_predict 2048\n'
        if modelfile.exists() and modelfile.read_text(encoding='utf-8') != content:
            raise ValueError('existing import preparation differs; preserve it for review')
        modelfile.write_text(content, encoding='utf-8')
        environment = dict(os.environ, OLLAMA_HOST='127.0.0.1:11434', OLLAMA_NO_CLOUD='1')
        subprocess.run([binary, 'create', MODEL, '-f', str(modelfile)],
                       env=environment, check=True, timeout=600)
        identity = provider.identity()
        receipt = {'source': SOURCE, 'revision': REVISION, 'file_sha256': SHA256,
                   'license': 'Apache-2.0', 'identity': identity,
                   'trained': False, 'repair_acceptance': 'not yet tested'}
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(receipt, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'Model import failed: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
