"""Candidate proposals are untrusted; only the independent gate decides readiness."""
from dataclasses import dataclass, asdict
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
from typing import Protocol
from . import repair_templates as templates
from .patches import apply_diff

TEMPLATE_REVISION = 'edffe24'
REGISTRY = {'CWE-22': templates.patch_path_traversal, 'CWE-89': templates.patch_sqli,
            'CWE-78': templates.patch_cmdinj, 'CWE-798': templates.patch_hardcoded_cred}


@dataclass
class Proposal:
    generator: str
    origin: str
    source_revision: str
    finding: dict | None
    outcome: str
    patch: str = ''
    detail: str = ''

    def record(self):
        return asdict(self)


class CandidateGenerator(Protocol):
    def generate(self, source, entrypoint, finding, prompt, budget) -> Proposal: ...


class TemplateGenerator:
    def __init__(self, isolated=False):
        self.isolated = isolated

    def specification(self, source, finding, budget):
        if not self.isolated:
            return REGISTRY[finding['cwe']](source.splitlines(True), finding)
        from .execution import IMAGE
        root = Path(__file__).parent.resolve()
        name = 'template-' + uuid.uuid4().hex
        command = ['docker','run','--rm','--name',name,'--network','none','--read-only',
                   '--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','32',
                   '--memory','256m','--user','65534:65534','--entrypoint','python']
        for filename in ('template_worker.py','repair_templates.py'):
            command += ['--mount',f'type=bind,source={root/filename},target=/generator/{filename},readonly']
        command += ['-i',IMAGE,'-B','/generator/template_worker.py']
        try:
            output = subprocess.run(command,input=json.dumps({'source':source,'finding':finding}),
                capture_output=True,text=True,encoding='utf-8',timeout=min(20,budget.remaining()))
            if output.returncode: raise RuntimeError('isolated template generation unavailable')
            return json.loads(output.stdout)
        finally:
            subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=10)

    def generate(self, source, entrypoint, finding, prompt, budget):
        budget.remaining()
        result = Proposal('historical-template', 'template', TEMPLATE_REVISION, finding, 'UNAVAILABLE')
        function = REGISTRY.get((finding or {}).get('cwe'))
        lines = source.splitlines(True)
        if function is None or not isinstance((finding or {}).get('line'), int) or not 1 <= finding.get('line', 0) <= len(lines):
            result.detail = 'No supported template at the declared finding.'
            return result
        spec = self.specification(source, finding, budget)
        if spec is None:
            result.detail = 'Source does not match the template syntax.'
            return result
        old, new = ''.join(spec['old_lines']), ''.join(spec['new_lines'])
        start = finding['line'] - 1
        if not old or source.count(old) != 1 or ''.join(lines[start:start + len(spec['old_lines'])]) != old:
            result.outcome, result.detail = 'INVALID', 'Replacement is not an exact unambiguous finding match.'
            return result
        updated = source.replace(old, new, 1)
        result.patch = ''.join(difflib.unified_diff(lines, updated.splitlines(True),
                            fromfile='a/' + entrypoint, tofile='b/' + entrypoint))
        try:
            apply_diff(source, result.patch, entrypoint)
        except (ValueError, SyntaxError) as exc:
            result.outcome, result.detail = 'INVALID', str(exc)
            return result
        result.outcome, result.detail = 'GENERATED', spec['rationale']
        return result


class ModelGenerator:
    def __init__(self, provider):
        self.provider = provider

    def generate(self, source, entrypoint, finding, prompt, budget):
        if self.provider is None:
            raise RuntimeError('local provider unavailable')
        answer = self.provider.suggest(prompt, budget)
        if 'source' in answer:
            if not isinstance(answer['source'], str) or len(answer['source'].encode()) > 262144:
                raise ValueError('invalid generated source')
            patch = ''.join(difflib.unified_diff(source.splitlines(True),
                (answer['source'].rstrip() + '\n').splitlines(True),
                fromfile='a/' + entrypoint, tofile='b/' + entrypoint))
        else:
            patch = answer.get('patch')
            if not isinstance(patch, str):
                raise ValueError('model response requires source or patch text')
        return Proposal('model', self.provider.origin, hashlib.sha256(source.encode()).hexdigest(),
                        finding, 'GENERATED', patch)
