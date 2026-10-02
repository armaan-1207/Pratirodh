import threading
import time


class WorkflowBudget:
    def __init__(self, limits, cancelled=None, deadline=None):
        self.start = time.monotonic()
        self.deadline = self.start + limits['seconds']
        if deadline is not None:
            self.deadline = min(self.deadline, deadline)
        self.reserve = limits['reserve_seconds']
        self.max_calls = limits['model_calls']
        self.max_candidates = limits['candidates']
        self.model_calls = 0
        self.cancelled = cancelled or threading.Event()

    def remaining(self):
        if self.cancelled.is_set():
            raise InterruptedError('workflow cancelled')
        result = self.deadline - time.monotonic()
        if result <= 0:
            raise TimeoutError('workflow budget exhausted')
        return result

    def proposing(self):
        return self.remaining() > self.reserve and self.model_calls < self.max_calls

    def model_call(self):
        if not self.proposing():
            raise TimeoutError('model budget exhausted or verification reserve reached')
        self.model_calls += 1
        return min(300, self.remaining() - self.reserve)
