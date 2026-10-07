"""Sanitized security events and bounded local alert aggregation.

Events use the application's configured log sink. An HTTPS adapter may be
explicitly configured; actual routing and recipient response remain operator work.
"""
from collections import deque
from datetime import datetime, timezone
import json
import re
import threading
import time


class SecurityEvents:
    def __init__(self, logger, clock=time.monotonic, threshold=5, window=60, delivery=None):
        self.logger, self.clock = logger, clock
        self.threshold, self.window = threshold, window
        self.recent = deque(maxlen=1000)
        self.alerted = {}
        self.lock = threading.Lock()
        self.delivery = delivery
        self.delivery_counts = {'delivered': 0, 'failed': 0}

    def emit(self, code, request_id, authenticated=False, record_id=None):
        # Only controller-owned codes and generated correlation IDs are logged.
        if not re.fullmatch(r'[a-z_]{1,64}', code) or not re.fullmatch(r'[a-f0-9]{32}', request_id):
            raise ValueError('invalid security event identity')
        event = {'type': 'security_event', 'code': code,
                 'timestamp': datetime.now(timezone.utc).isoformat(),
                 'request_id': request_id, 'actor': 'operator' if authenticated else 'anonymous'}
        if record_id is not None:
            event['record_id'] = record_id if re.fullmatch(r'[a-f0-9]{32}', record_id) else 'invalid'
        self.logger.warning('%s', json.dumps(event, separators=(',', ':')))
        with self.lock:
            now = self.clock()
            while self.recent and now - self.recent[0][0] >= self.window:
                self.recent.popleft()
            self.recent.append((now, code))
            count = sum(item[1] == code for item in self.recent)
            alert = count >= self.threshold and now - self.alerted.get(code, -self.window) >= self.window
            if alert:
                self.alerted[code] = now
        if alert:
            notification = dict(event, type='security_alert', count=count,
                                window_seconds=self.window)
            self.logger.error('%s', json.dumps(notification, separators=(',', ':')))
            if self.delivery is not None:
                try:
                    receipt = self.delivery.deliver(notification)
                    if not isinstance(receipt, dict) or receipt.get('delivered') is not True:
                        raise RuntimeError('alert receiver did not acknowledge delivery')
                except (OSError, ValueError, RuntimeError):
                    with self.lock:
                        self.delivery_counts['failed'] += 1
                    # Never log endpoint URLs, tokens, response bodies or exception messages.
                    self.logger.error('%s', json.dumps({
                        'type': 'security_alert_delivery_failed', 'code': code,
                        'request_id': request_id, 'operator_action_required': True},
                        separators=(',', ':')))
                else:
                    with self.lock:
                        self.delivery_counts['delivered'] += 1
