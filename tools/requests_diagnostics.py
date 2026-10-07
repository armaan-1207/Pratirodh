"""Allowlisted CI diagnostics: never export source, output text or store keys."""
import math
import re

DECISIONS = {'REJECT', 'READY_FOR_REVIEW', 'INSUFFICIENT_EVIDENCE'}
REASONS = {'UNRESOLVED', 'TESTED_REPAIR', 'REPAIR_REJECTED', 'BUDGET_EXHAUSTION',
           'CANCELLED', 'EXECUTION_FAILURE', 'PROVIDER_FAILURE', 'INVALID_PROJECT_OR_MANIFEST'}
STATUSES = {'PASS', 'FAIL', 'ERROR', 'COMPLETE', 'TIMEOUT', 'OUTPUT_LIMIT',
            'MISSING_DEPENDENCY', 'STARTUP_FAILURE', 'QUALIFIED', 'UNCONFIRMED',
            'CONFIRMED_UNSAFE', 'UNRESOLVED', 'INVALID', 'SURVIVED'}


def summarize(reports):
    rows = []
    for report in reports:
        row = {'id': report.get('id') if re.fullmatch(r'[a-f0-9]{32}', str(report.get('id'))) else None,
               'decision': report.get('decision') if report.get('decision') in DECISIONS else 'UNKNOWN',
               'reason': report.get('reason') if report.get('reason') in REASONS else 'UNKNOWN',
               'execution': []}
        elapsed = report.get('elapsed_seconds')
        if type(elapsed) in {int, float} and math.isfinite(elapsed) and elapsed >= 0:
            row['elapsed_seconds'] = elapsed

        def visit(value):
            if isinstance(value, list):
                for item in value:
                    visit(item)
            elif isinstance(value, dict):
                if value.get('status') in STATUSES:
                    entry = {'status': value['status']}
                    if type(value.get('exit')) is int:
                        entry['exit'] = value['exit']
                    if type(value.get('caught')) is bool:
                        entry['caught'] = value['caught']
                    row['execution'].append(entry)
                # No arbitrary strings, commands, patches, exception messages or output.
                for key in ('candidates', 'checks', 'actual', 'observations', 'controls',
                            'reproductions', 'original_reproduction', 'mutations', 'findings'):
                    if key in value:
                        visit(value[key])
        visit(report)
        rows.append(row)
    return {'scope': 'SANITIZED_EXECUTION_SUMMARY', 'reports': rows}
