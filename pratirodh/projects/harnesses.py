"""Generated harness proposals. An operator must review and approve before use."""
import json
import re


def callable_harness(language, module, function, tool=None):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', module) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', function):
        raise ValueError('harness needs a valid module/function identifier')
    if language == 'python':
        body = ('import atheris\nimport sys\nwith atheris.instrument_imports():\n'
                '    from ' + module + ' import ' + function + '\n\ndef TestOneInput(data):\n'
                '    ' + function + '(data)\n\natheris.Setup(sys.argv, TestOneInput)\natheris.Fuzz()\n')
        command, name, selected = ['python', 'fuzz/proposed.py', '-max_total_time=30'], 'fuzz/proposed.py', 'atheris'
    elif language == 'node':
        body = ('const target = require(' + json.dumps('./' + module) + ');\n'
                'exports.fuzz = data => target.' + function + '(data);\n')
        command, name, selected = ['node', 'node_modules/@jazzer.js/core/dist/cli.js', 'fuzz/proposed.js', '-f', 'fuzz', '--', '-max_total_time=30'], 'fuzz/proposed.js', 'jazzer.js'
    elif language == 'cpp':
        # Header/function signature must be reviewed; compilation qualification is required.
        body = ('#include <cstddef>\n#include <cstdint>\n#include "' + module + '.h"\n'
                'extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {\n'
                '    ' + function + '(data, size);\n    return 0;\n}\n')
        command, name, selected = ['/work/build/fuzz_target', '-max_total_time=30'], 'fuzz/proposed.cpp', 'libFuzzer'
    else:
        raise ValueError('unsupported callable fuzz language')
    return {'status': 'PROPOSAL_REQUIRES_APPROVAL', 'files': {name: body}, 'tool': selected,
            'command': command, 'approved': False, 'qualification_required': ['build', 'target invocation', 'legitimate control', 'three clean violations'],
            'notes': 'Byte-callable signature assumed; adapt and review the target invocation and expected security property.'}


def http_harness(schema):
    if not schema.startswith(('http://127.0.0.1:', 'http://localhost:')):
        raise ValueError('HTTP harness schema must be served within the worker')
    return {'status': 'PROPOSAL_REQUIRES_APPROVAL', 'tool': 'schemathesis',
            'command': ['schemathesis', 'run', schema, '--max-examples', '50'], 'approved': False,
            'notes': 'Requires an approved service lifecycle. Schema checks alone do not verify authorization/business properties.'}
