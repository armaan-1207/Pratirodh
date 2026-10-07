"""Configured application alerts use controller-owned events; no real recipient."""
import json
import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pratirodh.evidence import Store
from pratirodh.security_events import SecurityEvents
from pratirodh import web


def test_threshold_alert_is_delivered_once_per_window():
    delivered = []
    now = [0]
    def deliver(event):
        delivered.append(event)
        return {'delivered': True}
    events = SecurityEvents(logging.getLogger('alert-bridge-window'),
        clock=lambda: now[0], delivery=SimpleNamespace(deliver=deliver))
    for _ in range(12):
        events.emit('integrity_denied', 'a' * 32, record_id='private-input')
    assert len(delivered) == 1 and delivered[0]['count'] == 5
    assert delivered[0]['record_id'] == 'invalid'
    assert events.delivery_counts == {'delivered': 1, 'failed': 0}
    now[0] = 61
    for _ in range(5):
        events.emit('integrity_denied', 'b' * 32)
    assert len(delivered) == 2


@pytest.mark.parametrize('failure', ['exception', 'missing-ack'])
def test_receiver_failure_is_sanitized_and_does_not_change_access_denial(caplog, failure):
    calls = []
    def deliver(event):
        calls.append(event)
        if failure == 'exception':
            raise RuntimeError('token-private-source')
        return {'delivered': False}
    events = SecurityEvents(logging.getLogger('alert-bridge-failure'),
        delivery=SimpleNamespace(deliver=deliver))
    with caplog.at_level(logging.WARNING):
        for _ in range(5):
            events.emit('authentication_failed', 'a' * 32)
    assert len(calls) == 1
    assert events.delivery_counts == {'delivered': 0, 'failed': 1}
    failure_logs = [json.loads(record.getMessage()) for record in caplog.records
                    if 'security_alert_delivery_failed' in record.getMessage()]
    assert len(failure_logs) == 1 and failure_logs[0]['operator_action_required']
    assert 'token-private' not in caplog.text


@pytest.mark.parametrize('configured', ['endpoint', 'token'])
def test_incomplete_alert_configuration_refuses_startup(tmp_path, monkeypatch, configured):
    monkeypatch.delenv('PRATIRODH_ALERT_ENDPOINT', raising=False)
    monkeypatch.delenv('PRATIRODH_ALERT_TOKEN', raising=False)
    name, value = ('PRATIRODH_ALERT_ENDPOINT', 'https://receiver.invalid/alerts') if configured == 'endpoint' else (
        'PRATIRODH_ALERT_TOKEN', 'synthetic-token-only')
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match='both endpoint and bearer token'):
        web.create_app(Store(tmp_path))


def test_alerts_default_to_no_outbound_transport(tmp_path, monkeypatch):
    monkeypatch.delenv('PRATIRODH_ALERT_ENDPOINT', raising=False)
    monkeypatch.delenv('PRATIRODH_ALERT_TOKEN', raising=False)
    adapter = Mock(side_effect=AssertionError('external transport must not be constructed'))
    monkeypatch.setattr(web, 'HTTPSAlertDelivery', adapter)
    app = web.create_app(Store(tmp_path))
    assert app.extensions['pratirodh_security_events'].delivery is None
    adapter.assert_not_called()


def test_application_denials_reach_explicitly_configured_adapter(tmp_path, monkeypatch):
    monkeypatch.setenv('PRATIRODH_ALERT_ENDPOINT', 'https://receiver.invalid/alerts')
    monkeypatch.setenv('PRATIRODH_ALERT_TOKEN', 'synthetic-token-only')
    monkeypatch.setenv('PRATIRODH_PASSWORD', 'synthetic-auth-password')
    adapter = Mock()
    adapter.deliver.return_value = {'delivered': True}
    factory = Mock(return_value=adapter)
    monkeypatch.setattr(web, 'HTTPSAlertDelivery', factory)
    app = web.create_app(Store(tmp_path))
    client = app.test_client()
    for _ in range(5):
        assert client.get('/validation').status_code == 401
    factory.assert_called_once_with('https://receiver.invalid/alerts', 'synthetic-token-only')
    adapter.deliver.assert_called_once()
    event = adapter.deliver.call_args.args[0]
    assert event['type'] == 'security_alert' and event['code'] == 'authentication_failed'
    assert app.extensions['pratirodh_security_events'].delivery_counts['delivered'] == 1
