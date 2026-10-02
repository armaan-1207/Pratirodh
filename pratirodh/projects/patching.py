"""Apply exact multi-file diffs to copies, with protected inputs immutable."""
import ast
import difflib
import re
import subprocess
import tempfile
from pathlib import Path
from ..contracts import safe_relative


def make_diff(original, updated):
    parts = []
    for name in sorted(original):
        if original[name] == updated[name]:
            continue
        for line in difflib.unified_diff(original[name].splitlines(True), updated[name].splitlines(True),
                                         fromfile='a/' + name, tofile='b/' + name):
            parts.append(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n')
    return ''.join(parts)


def proposal_diff(answer, files, editable):
    """Normalize supported model proposals before the common immutable edit gate."""
    if not isinstance(answer, dict):
        raise ValueError('model proposal must be an object')
    if isinstance(answer.get('files'), dict):
        replacements = answer['files']
        import json
        if (not replacements or any(n not in editable or not isinstance(body, str)
                                    for n, body in replacements.items())
                or len(json.dumps(replacements).encode()) > 131072):
            raise ValueError('model proposed protected, invalid or oversized source files')
        patch = make_diff(files, dict(files, **replacements))
    else:
        patch = answer.get('patch')
    if not isinstance(patch, str) or not patch or len(patch.encode()) > 131072:
        raise ValueError('empty/oversized model patch')
    return patch


def apply(files, patch, editable):
    if not isinstance(patch, str) or not patch or len(patch.encode()) > 131072:
        raise ValueError('empty/oversized patch')
    if any(line.startswith(('rename ', 'copy ', 'GIT binary', 'new file', 'deleted file', 'old mode', 'new mode'))
           for line in patch.splitlines()):
        raise ValueError('only edits to existing text source files allowed')
    result = subprocess.run(['git', 'apply', '--numstat', '-'], input=patch.encode(), capture_output=True, timeout=10)
    changed = [line.split('\t')[-1] for line in result.stdout.decode().splitlines()]
    if result.returncode or not changed or len(changed) != len(set(changed)):
        raise ValueError('invalid multi-file diff')
    for name in changed:
        safe_relative(name)
        if name not in editable or name not in files:
            raise ValueError('patch escapes editable source: ' + name)
    with tempfile.TemporaryDirectory() as directory:
        for name in changed:
            path = Path(directory) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(files[name], encoding='utf-8', newline='\n')
        process = subprocess.run(['git', 'apply', '--whitespace=nowarn', '-'], input=patch.encode(),
                                 cwd=directory, capture_output=True, timeout=10)
        if process.returncode:
            raise ValueError('patch does not apply to exact source')
        updated = dict(files)
        for name in changed:
            body = (Path(directory) / name).read_text(encoding='utf-8')
            if name.endswith('.py'):
                ast.parse(body)
            # Suppression/removal heuristics are extra gates, never proof of semantic safety.
            for line in difflib.ndiff(files[name].splitlines(), body.splitlines()):
                if line.startswith('+ ') and re.search(r'noqa|nosec|ts-ignore|skip\(|skipif|process\.exit\(0\)|pytest\.skip|except\s*(?:Exception|BaseException)?\s*:|catch\s*\(\s*\.\.\.\s*\)|#\s*define\s+NDEBUG', line, re.I):
                    raise ValueError('patch attempts to suppress verification')
            if not body.strip():
                raise ValueError('patch removes required source')
            updated[name] = body
    return updated
