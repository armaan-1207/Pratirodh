"""Display helpers: explanations never authorize or change a gate decision."""
TITLES = {'CWE-22': 'Secure file downloads', 'CWE-89': 'Safe database queries',
          'CWE-78': 'Safe command execution', 'CWE-798': 'Protect application credentials'}


def scenario_name(identifier, cwe=None):
    cwe = cwe or next((key for key in TITLES if identifier.lower().startswith(key.lower())), None)
    title = TITLES.get(cwe, identifier)
    if '-development-' in identifier or '-heldout-' in identifier:
        title += ' · example ' + identifier.rsplit('-', 1)[-1].lstrip('0')
    return title


def explanation(report):
    candidates = report.get('candidates', [])
    selected = next((c for c in candidates if c.get('decision') == report.get('decision')), {})
    checks = selected.get('checks', [])
    attacks = [c for c in checks if c.get('case', {}).get('kind') == 'attack']
    benign = [c for c in checks if c.get('case', {}).get('kind') == 'benign']
    failed = [c for c in checks if c.get('status') == 'FAIL']
    gaps = list(dict.fromkeys(report.get('gaps', []) + selected.get('gaps', [])))
    outcome = report.get('decision')
    headline = {'READY_FOR_REVIEW': 'Required checks passed. Human review comes next.',
                'REJECT': 'This repair failed a required check.',
                'INSUFFICIENT_EVIDENCE': 'There is not enough evidence to recommend this repair.'}.get(outcome, 'Inspect the recorded decision.')
    actions = {'READY_FOR_REVIEW': 'Review the patch and request evidence before recording approval.',
               'REJECT': 'Open the failing request or patch-policy check, then propose a new repair.',
               'INSUFFICIENT_EVIDENCE': 'Inspect missing checks and local setup, then rerun verification.'}
    return dict(headline=headline, next_action=actions.get(outcome, 'Inspect the signed evidence.'),
                attacks_passed=sum(c.get('status') == 'PASS' for c in attacks), attacks_total=len(attacks),
                benign_passed=sum(c.get('status') == 'PASS' for c in benign), benign_total=len(benign),
                failed=len(failed), gaps=len(gaps))
