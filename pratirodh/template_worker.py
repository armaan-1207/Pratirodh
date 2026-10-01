"""Container-only template execution. No cohort, audit, evidence or host mounts."""
import json
import sys
import repair_templates as templates

REGISTRY = {'CWE-22': templates.patch_path_traversal, 'CWE-89': templates.patch_sqli,
            'CWE-78': templates.patch_cmdinj, 'CWE-798': templates.patch_hardcoded_cred}

if __name__ == '__main__':
    job = json.load(sys.stdin)
    function = REGISTRY.get(job['finding']['cwe'])
    print(json.dumps(function(job['source'].splitlines(True), job['finding']) if function else None))
