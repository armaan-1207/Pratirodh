import json
from tools.requests_diagnostics import summarize


def test_execution_categories_preserved_without_sensitive_payloads():
    report = {'id': 'a' * 32, 'decision': 'INSUFFICIENT_EVIDENCE', 'reason': 'BUDGET_EXHAUSTION',
              'gaps': ['password-private'], 'patch': 'private-source', 'elapsed_seconds': 123,
              'candidates': [{'checks': [{'status': 'ERROR', 'command': ['secret-command'],
                  'actual': {'status': 'TIMEOUT', 'stdout': 'token-private', 'stderr': 'key-private', 'exit': 9}}]}]}
    result = summarize([report])
    row = result['reports'][0]
    assert row['id'] == 'a' * 32 and row['reason'] == 'BUDGET_EXHAUSTION'
    assert row['execution'] == [{'status': 'ERROR'}, {'status': 'TIMEOUT', 'exit': 9}]
    assert 'private' not in json.dumps(result) and 'secret-command' not in json.dumps(result)


def test_unknown_values_and_nonfinite_elapsed_are_not_exported():
    result = summarize([{'id': 'private', 'decision': 'secret', 'reason': 'secret',
                         'elapsed_seconds': float('nan'), 'checks': [{'status': 'private'}]}])
    assert result['reports'] == [{'id': None, 'decision': 'UNKNOWN', 'reason': 'UNKNOWN', 'execution': []}]
