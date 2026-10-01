"""Append a separately signed review record, without promoting source."""
from datetime import datetime, timezone
from .evidence import Store, fresh, digest, new_id
from .execution import DockerExecutor


def review(run_id, action, reviewer, rationale, store=None, executor=None):
    store = store or Store()
    report = store.load(run_id)
    if action not in {'approve', 'reject'} or not reviewer.strip() or not rationale.strip():
        raise ValueError('review needs action, operator label and rationale')
    if len(reviewer) > 100 or len(rationale) > 2000:
        raise ValueError('review metadata exceeds limit')
    if action == 'approve' and (report['decision'] != 'READY_FOR_REVIEW' or not fresh(report, executor or DockerExecutor())):
        raise ValueError('approval requires fresh, valid evidence ready for review')
    record = {'id': new_id(), 'created': datetime.now(timezone.utc).isoformat(), 'scenario': report['scenario'],
              'decision': 'HUMAN_' + action.upper(), 'kind': 'review', 'run_id': run_id,
              'evidence_digest': digest((store.run_path(run_id) / 'inventory.json').read_bytes()),
              'reviewer_label': reviewer, 'identity_verified': False, 'rationale': rationale}
    store.save(record, {})
    return record
