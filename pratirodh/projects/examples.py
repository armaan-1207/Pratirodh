"""MIT synthetic demonstrations, explicitly outside external acceptance cohorts."""
import json
from pathlib import Path
import subprocess
from ..evidence import Store
from .engine import run_project
from .manifest import inspect
from .patching import make_diff


def create_example(root, language, image, context='default'):
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise ValueError('synthetic example requires a fresh directory; prior source is preserved')
    root.mkdir(parents=True, exist_ok=True)
    if language == 'python':
        files = {
            'requirements.txt': 'pytest==9.1.1\n',
            'policy.py': 'from users import normalize\n\ndef allowed(owner, user):\n    return True\n',
            'users.py': 'def normalize(user):\n    return "admin" if user == "guest" else user\n',
            'portal.py': 'import sys\nfrom policy import allowed\nprint("GRANTED" if allowed(sys.argv[1], sys.argv[2]) else "DENIED")\n',
            'tests/test_portal.py': 'from policy import allowed\n\ndef test_legitimate():\n    assert allowed("admin", "admin")\n',
        }
        fixed = {'policy.py': 'from users import normalize\n\ndef allowed(owner, user):\n    return owner == normalize(user)\n',
                 'users.py': 'def normalize(user):\n    return user\n'}
        command = ['python', 'portal.py']
        policy_file, users_file = 'policy.py', 'users.py'
        policy_find, policy_replace = 'return owner == normalize(user)', 'return True'
        users_find, users_replace = 'return user', 'return "admin" if user == "guest" else user'
    elif language == 'node':
        files = {
            'package.json': json.dumps({'name': 'pratirodh-synthetic-portal', 'version': '1.0.0', 'scripts': {'test': 'node test.js'}}) + '\n',
            'package-lock.json': json.dumps({'name': 'pratirodh-synthetic-portal', 'version': '1.0.0', 'lockfileVersion': 3,
                'requires': True, 'packages': {'': {'name': 'pratirodh-synthetic-portal', 'version': '1.0.0'}}}) + '\n',
            'policy.js': 'const {normalize} = require("./users");\nexports.allowed = (owner, user) => true;\n',
            'users.js': 'exports.normalize = user => user === "guest" ? "admin" : user;\n',
            'portal.js': 'const {allowed} = require("./policy");\nconsole.log(allowed(process.argv[2], process.argv[3]) ? "GRANTED" : "DENIED");\n',
            'test.js': 'const assert = require("node:assert/strict");\nassert.equal(require("./policy").allowed("admin", "admin"), true);\n',
        }
        fixed = {'policy.js': 'const {normalize} = require("./users");\nexports.allowed = (owner, user) => owner === normalize(user);\n',
                 'users.js': 'exports.normalize = user => user;\n'}
        command = ['node', 'portal.js']
        policy_file, users_file = 'policy.js', 'users.js'
        policy_find, policy_replace = 'owner === normalize(user)', 'true'
        users_find, users_replace = 'user => user;', 'user => user === "guest" ? "admin" : user;'
    elif language == 'cpp':
        files = {
            'CMakeLists.txt': 'cmake_minimum_required(VERSION 3.16)\nproject(portal LANGUAGES CXX)\nset(CMAKE_CXX_STANDARD 17)\nadd_executable(portal portal.cpp policy.cpp users.cpp)\ntarget_compile_options(portal PRIVATE -fsanitize=address,undefined -fno-pie)\ntarget_link_options(portal PRIVATE -fsanitize=address,undefined -no-pie)\nenable_testing()\nadd_test(NAME legitimate COMMAND portal admin admin)\n',
            'policy.hpp': '#pragma once\n#include <string>\nbool allowed(const std::string& owner, const std::string& user);\nstd::string normalize(const std::string& user);\n',
            'policy.cpp': '#include "policy.hpp"\nbool allowed(const std::string& owner, const std::string& user) { return true; }\n',
            'users.cpp': '#include "policy.hpp"\nstd::string normalize(const std::string& user) { return user == "guest" ? "admin" : user; }\n',
            'portal.cpp': '#include "policy.hpp"\n#include <iostream>\nint main(int argc, char** argv) { if(argc != 3) return 2; std::cout << (allowed(argv[1], argv[2]) ? "GRANTED\\n" : "DENIED\\n"); }\n',
        }
        fixed = {'policy.cpp': '#include "policy.hpp"\nbool allowed(const std::string& owner, const std::string& user) { return owner == normalize(user); }\n',
                 'users.cpp': '#include "policy.hpp"\nstd::string normalize(const std::string& user) { return user; }\n'}
        command = ['/work/build/portal']
        policy_file, users_file = 'policy.cpp', 'users.cpp'
        policy_find, policy_replace = 'return owner == normalize(user);', 'return true;'
        users_find, users_replace = 'return user;', 'return user == "guest" ? "admin" : user;'
    else:
        raise ValueError('unsupported synthetic language')
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8', newline='\n')
    manifest = inspect(root)
    manifest.update(status='OPERATOR_APPROVED_SYNTHETIC_DEMO', image=image,
                    worker={'mode': 'demo' if context in {'default', 'desktop-linux'} else 'dedicated', 'context': context},
                    dependencies={'prepared': True, 'image_digest': image, 'resolved': {'fixture': 'no external project dependencies'}})
    manifest['properties'] = [{'id': 'tenant-isolation', 'kind': 'authorization',
        'description': 'Only the synthetic owner may access their synthetic account',
        'provenance': {'kind': 'operator', 'reference': 'PRATIRODH MIT synthetic portal specification v1', 'approved': True},
        'target_files': [policy_file, users_file],
        'harness_review': {'approved': True, 'reference': 'portal calls allowed and normalize directly; CLI stdout originates in portal'},
        'control': {'command': command + ['admin', 'admin'], 'exit': 0, 'stdout': 'GRANTED\n'},
        'reproducer': {'command': command + ['admin', 'guest'], 'exit': 0, 'stdout': 'DENIED\n',
                       'violation': {'exit': 0, 'stdout': 'GRANTED\n'}},
        'variations': [{'command': command + ['alice', 'bob'], 'exit': 0, 'stdout': 'DENIED\n'},
                       {'command': command + ['admin', 'GUEST'], 'exit': 0, 'stdout': 'DENIED\n'}]}]
    manifest['mutations'] = [
        {'family': 'owner-check-removed', 'file': policy_file, 'property': 'tenant-isolation', 'find': policy_find, 'replace': policy_replace},
        {'family': 'identity-confusion', 'file': users_file, 'property': 'tenant-isolation', 'find': users_find, 'replace': users_replace},
    ]
    manifest_path = root / 'pratirodh-project.json'
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    patch = make_diff(files, dict(files, **fixed))
    return manifest_path, patch


def incomplete_patch(root, manifest, patch):
    """Fix the owner check but retain the guest-to-admin identity confusion."""
    from .manifest import load
    from .patching import apply
    config, files = load(root, manifest)
    updated = apply(files, patch, config['editable'])
    identity = config['mutations'][1]['file']
    updated[identity] = files[identity]
    return make_diff(files, updated)


def demo(output, image, challenge=False, context='default'):
    image_id = subprocess.check_output(['docker', '--context', context, 'image', 'inspect', image, '--format', '{{.Id}}'],
                                       text=True, timeout=15).strip()
    output = Path(output)
    if output.exists():
        raise ValueError('choose a fresh demo output directory; prior evidence is preserved')
    store = Store(output / 'evidence')
    result = {'cohort': 'MIT synthetic multi-file supplied repairs, not external/model release acceptance', 'runs': []}
    for language in ('python', 'node', 'cpp'):
        root = output / language
        manifest, patch = create_example(root, language, image_id, context=context)
        (output / (language + '.diff')).write_text(patch, encoding='utf-8')
        attempts = [('repair', 'incomplete', incomplete_patch(root, manifest, patch))] if challenge else []
        attempts += [(workflow, 'correct', patch) for workflow in ('repair', 'discover')]
        for workflow, label, proposal in attempts:
            print('Executing', language, workflow, flush=True)
            report = run_project(root, manifest, workflow, problem={'property': 'tenant-isolation'}, patch=proposal,
                                 store=store, allow_demo=True, progress=lambda stage: print('  ', stage, flush=True))
            expected = 'REJECT' if label == 'incomplete' else 'READY_FOR_REVIEW'
            result['runs'].append({'language': language, 'workflow': workflow, 'patch': label, 'expected': expected,
                                   'matched_expectation': report['decision'] == expected, 'id': report['id'],
                                   'decision': report['decision'], 'reason': report['reason'], 'gaps': report['gaps']})
            (output / 'summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result
