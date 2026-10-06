"""Conservative allocation accounting; never infer a zero bill from missing data."""
from datetime import datetime
import math


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('allocation timestamps require timezone offsets')
    return result


def allocated_intervals(vm, events, observed):
    created = timestamp(vm['timeCreated'])
    if created > observed:
        raise ValueError('resource creation follows observation')
    start = created
    intervals = []
    rows = sorted((r for r in events if r['resource'].lower().endswith('/' + vm['name'].lower())),
                  key=lambda r: timestamp(r['time']))
    for row in rows:
        when = timestamp(row['time'])
        if not created <= when <= observed:
            continue
        op = row['operation'].lower()
        if op.endswith('/deallocate/action') and row['status'] == 'Succeeded':
            if start is not None:
                intervals.append((start, when))
                start = None
        elif row['status'] == 'Started' and (op.endswith('/start/action') or op.endswith('/write')):
            # Failed/repeated starts and writes conservatively count as allocated.
            if start is None:
                start = when
        elif op.endswith('/start/action') and row['status'] == 'Succeeded' and start is None:
            raise ValueError('successful start has no recorded start boundary')
    if start is not None:
        intervals.append((start, observed))
    if vm['state'] == 'VM running' and start is None:
        raise ValueError('power observation contradicts allocation history')
    if vm['state'] == 'VM deallocated' and start is not None:
        raise ValueError('deallocated VM lacks completed shutdown in history')
    if vm['state'] not in {'VM running', 'VM deallocated'}:
        raise ValueError('unresolved VM power state')
    return [{'start': a.isoformat(), 'end': b.isoformat(),
             'charged_hours_upper_bound': math.ceil((b-a).total_seconds()/3600)} for a, b in intervals]


def metric_values(document, field):
    values = [r[field] for m in document['value'] for series in m['timeseries']
              for r in series['data'] if r.get(field) is not None]
    if not values or any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('missing or invalid usage metrics')
    return values
