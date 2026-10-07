"""Allowlisted CI diagnostics: never export source, output text or store keys."""
import math
import re

DECISIONS = {'REJECT', 'READY_FOR_REVIEW', 'INSUFFICIENT_EVIDENCE'}
REASONS = {'UNRESOLVED', 'TESTED_REPAIR', 'REPAIR_REJECTED', 'BUDGET_EXHAUSTION',
           'CANCELLED', 'EXECUTION_FAILURE', 'PROVIDER_FAILURE', 'INVALID_PROJECT_OR_MANIFEST'}
STATUSES = {'PASS', 'FAIL', 'ERROR', 'COMPLETE', 'TIMEOUT', 'OUTPUT_LIMIT',
            'MISSING_DEPENDENCY', 'STARTUP_FAILURE', 'QUALIFIED', 'UNCONFIRMED',
            'CONFIRMED_UNSAFE', 'UNRESOLVED', 'INVALID', 'SURVIVED'}

WORKER_PHASES = {'SLOT_WAIT', 'CONTAINER_LAUNCH', 'CONTAINER_WAIT', 'PROTOCOL_VALIDATION'}
WORKER_OUTCOMES = {'WORKER_SLOT_UNAVAILABLE', 'SLOT_ACQUISITION_FAILURE', 'CANCELLED',
                   'WORKFLOW_BUDGET_EXHAUSTED', 'CONTAINER_DEADLINE_EXPIRED',
                   'TRANSPORT_FAILURE', 'TRANSPORT_TIMEOUT', 'INVALID_WORKER_PROTOCOL',
                   'CONTAINER_EXIT_NONZERO', 'COMPLETE'}


def worker_diagnostics(rows):
    """Only controller timing/categories; never Docker errors or target output."""
    result = []
    if not isinstance(rows, list):
        return result
    for value in rows[:1000]:
        if not isinstance(value, dict) or value.get('phase') not in WORKER_PHASES or value.get('outcome') not in WORKER_OUTCOMES:
            continue
        row = {'phase': value['phase'], 'outcome': value['outcome']}
        for key in ('sequence', 'command_count', 'container_exit'):
            if type(value.get(key)) is int and abs(value[key]) <= 1000000:
                row[key] = value[key]
        for key in ('slot_wait_seconds', 'elapsed_seconds', 'container_seconds',
                    'workflow_remaining_seconds', 'applied_timeout_seconds', 'command_limit_seconds'):
            number = value.get(key)
            if type(number) in {float, int} and math.isfinite(number) and 0 <= number <= 86400:
                row[key] = number
        if value.get('deadline_source') in {'WORKFLOW_BUDGET', 'COMMAND_WINDOW'}:
            row['deadline_source'] = value['deadline_source']
        counts = value.get('observation_status_counts')
        if isinstance(counts, dict):
            row['observation_status_counts'] = {key: number for key, number in counts.items()
                if key in STATUSES and type(number) is int and 0 <= number <= 1000000}
        failures = value.get('cleanup_failures')
        if isinstance(failures, list):
            row['cleanup_failures'] = [value for value in failures[:2]
                if value in {'CONTAINER_REMOVAL_FAILED', 'CLIENT_CLEANUP_FAILED'}]
        result.append(row)
    return result


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
        diagnostics = worker_diagnostics(report.get('worker_execution_diagnostics'))
        if diagnostics:
            row['worker_execution_diagnostics'] = diagnostics
        rows.append(row)
    return {'scope': 'SANITIZED_EXECUTION_SUMMARY', 'reports': rows}
