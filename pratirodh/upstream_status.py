"""Derive UI status from source acquisition and campaign artifacts."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from .evidence import Store, canonical, digest
from .evidence import tree_hash
from .contracts import safe_relative
from cryptography.exceptions import InvalidSignature


def read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except FileNotFoundError:
        return {}, None
    except (OSError, ValueError) as error:
        return {}, f"{path.name}: {type(error).__name__}"


def observation_age(timestamp):
    try:
        observed = datetime.fromisoformat(timestamp)
        if observed.tzinfo is None:
            return None
        age = (datetime.now(timezone.utc) - observed).total_seconds()
        return age if age >= 0 else None
    except (TypeError, ValueError):
        return None


def load_status(root: Path) -> dict:
    errors = []
    def artifact(relative):
        value, error = read(root / relative)
        if error:
            errors.append(error)
        return value
    active = artifact('benchmark/upstream-current.json')
    relative = active.get('manifest', 'benchmark/upstream-cohort.json' if
                          (root / 'benchmark/upstream-cohort.json').exists() else 'benchmark/upstream-v1/manifest.json')
    safe_relative(relative)
    manifest_path = root / relative
    manifest = artifact(relative)
    manifest_digest = digest(manifest_path.read_bytes()) if manifest_path.exists() else ''
    campaign = artifact("run_output/upstream-validation/campaign.json")
    acquisition = artifact("run_output/upstream-acquisition/acquisition.json")
    attestations = artifact("run_output/azure-validation/attestations.json")
    power = artifact("run_output/azure-validation/power-state.json")
    preparation = artifact('run_output/upstream-validation/preparation.json')
    acquired_by_id = {row["id"]: row for row in acquisition.get("cases", [])}
    review = artifact('run_output/upstream-validation/intake-review.json')
    reviews = {r['id']: r for r in review.get('cases', [])} if review.get('manifest_digest') == manifest_digest else {}
    qualification = artifact('run_output/upstream-validation/qualification-index.json')
    qualification_rows = qualification.get('cases', {}) if qualification.get('manifest_digest') == manifest_digest else {}
    store = Store(root / 'run_output/pratirodh')
    cases = []
    for item in manifest.get("cases", []):
        case = dict(item)
        recipe = artifact('benchmark/recipes/' + safe_relative(item['id']) + '/recipe.json')
        case.setdefault('language', item['id'].split('-')[0])
        case.setdefault('license', recipe.get('license_review', {}).get('identifier', 'License review unavailable'))
        case.setdefault('detail', recipe.get('description', 'Runtime qualification required'))
        row = acquired_by_id.get(item["id"], {})
        provenance = row.get("provenance", {})
        revised = root / 'run_output/upstream-acquisition-v2' / item['id'] / 'provenance.json'
        if not item.get('acquisition') and revised.exists():
            revised_provenance = artifact(str(revised.relative_to(root)).replace('\\', '/'))
            if (revised_provenance.get('repository') == item.get('repository_url') and
                    revised_provenance.get('fixed_revision') == item.get('fix_revision')):
                provenance = revised_provenance
        if item.get('acquisition'):
            safe_relative(item['acquisition'])
            provenance = artifact(item['acquisition'] + '/provenance.json')
        acquired = (provenance.get('repository') == item.get('repository_url')
                    and provenance.get('fixed_revision') == item.get('fix_revision')
                    and bool(provenance.get('source_hashes')))
        case['status'] = 'SOURCE_ACQUIRED' if acquired else 'INTAKE_PENDING_QUALIFICATION'
        if not acquired:
            case['provenance_warning'] = 'Recorded source provenance does not bind the current repository and reference fix.'
        case['source_review'] = reviews.get(item['id'], {}).get('status', 'PENDING')
        case['qualification_errors'] = reviews.get(item['id'], {}).get('errors', [])
        record = qualification_rows.get(item['id'], {})
        if record.get('run_id'):
            try:
                signed_qualification = store.load(record['run_id'])
                if (signed_qualification.get('scenario') == 'upstream-qualification'
                        and signed_qualification.get('status') == 'QUALIFIED'
                        and signed_qualification.get('case') == item['id']
                        and signed_qualification.get('source_review', {}).get('fix_revision') == item['fix_revision']
                        and signed_qualification.get('manifest_digest') == digest(Path(record['execution_manifest']).read_bytes())
                        and signed_qualification.get('audit_digest') == digest(Path(record['audit']).read_bytes())
                        and signed_qualification.get('recipe_digest') == digest(Path(record['recipe']).read_bytes())
                        and signed_qualification.get('controller_digest') == tree_hash(root / 'pratirodh')):
                    case['status'] = 'QUALIFIED'
                    case['qualification_run_id'] = record['run_id']
                else:
                    case['qualification_errors'].append('Qualification is failed or stale against current inputs')
            except (OSError, ValueError, KeyError, InvalidSignature):
                case['qualification_errors'].append('Qualification signature or input binding unavailable')
        case.update(project=item.get("project") or item.get('repository_url', '').removeprefix('https://github.com/'),
                    advisory=item.get("cve") or item['id'].split('-', 1)[-1].upper(),
                    source_url=item.get("fix_url") or item.get("repository_url", ""))
        case["source_revision"] = provenance.get("vulnerable_revision", item.get("source_revision"))
        case["license_evidence"] = provenance.get("license_files", item.get("license_evidence", []))
        cases.append(case)
    rows = campaign.get("rows", [])
    signed = False
    if campaign.get('signed_run_id'):
        try:
            store.load(campaign['signed_run_id'])
            snapshot = json.loads((store.run_path(campaign['signed_run_id']) / 'campaign.json').read_text(encoding='utf-8'))
            actual = {k: v for k, v in campaign.items() if k != 'signed_run_id'}
            expected = {k: v for k, v in snapshot.items() if k != 'signed_run_id'}
            signed = canonical(actual) == canonical(expected)
            if signed:
                for row in rows:
                    if row.get('run_id'):
                        store.load(row['run_id'])
            if not signed:
                errors.append('Campaign differs from signed snapshot')
        except (OSError, ValueError, InvalidSignature):
            signed = False
            errors.append('Campaign signature unavailable or invalid')
    workers = []
    live_preflight = artifact('run_output/upstream-validation/worker-preflight.json')
    power_age = observation_age(power.get('updated'))
    identity_age = observation_age(live_preflight.get('updated'))
    live_workers = {w.get('role'): w for w in live_preflight.get('workers', [])}
    model_preflight = artifact('run_output/upstream-validation/model-preflight.json')
    sandbox_preflight = artifact('run_output/upstream-validation/worker-sandbox-probe-controller.json')
    if model_preflight:
        live_workers['model'] = model_preflight
    for worker in attestations.get("workers", []):
        worker = dict(worker)
        worker["attestation_status"] = worker.get("status")
        worker['power_observed_at'] = power.get('updated')
        worker['power_age_seconds'] = power_age
        worker['power_stale'] = power_age is None or power_age > 300
        role = {'Model controller': 'model', 'Execution': 'execution', 'Final audit': 'audit'}.get(worker.get('role'))
        live = live_workers.get(role, {})
        worker['identity'] = live
        worker['identity_observed_at'] = live.get('observed_at') or live_preflight.get('updated')
        worker_age = observation_age(worker['identity_observed_at'])
        worker['identity_stale'] = not live or worker_age is None or worker_age > 300
        name = {'Model controller': 'pratirodh-model', 'Execution': 'pratirodh-execution',
                'Final audit': 'pratirodh-audit'}.get(worker.get('role'))
        observed = next((row.get('state') for row in power.get('observations', [])
                         if row.get('name') == name), None)
        worker["status"] = ('STALE_OBSERVATION' if worker['power_stale'] else
                            observed or power.get("status", "CURRENT_STATE_UNKNOWN"))
        if worker['identity_stale']:
            worker['attestation_status'] = 'HISTORICAL_IDENTITY'
        else:
            worker['attestation_status'] = live.get('status', 'UNKNOWN')
        workers.append(worker)
    scheduled = sum(c.get('split') == 'evaluation' for c in cases) * 12
    keys = [(r.get('case'), r.get('workflow'), r.get('arm'), r.get('repetition')) for r in rows]
    if len(set(keys)) != len(keys):
        errors.append('Duplicate campaign attempts')
        signed = False
    return {
        'cohort': manifest.get('cohort', 'upstream-v1'),
        "target": manifest.get("target_count", 24),
        "acquired": sum(c.get("status") in {"SOURCE_ACQUIRED", "QUALIFIED", "AUDITED"} for c in cases),
        "qualified": sum(c.get("status") in {"QUALIFIED", "AUDITED"} for c in cases),
        "completed": len(rows),
        'scheduled': scheduled,
        'source_reviewed': sum(c['source_review'] == 'SOURCE_REVIEWED' for c in cases),
        'pending_audits': len(campaign.get('pending', [])),
        'unstarted': len(campaign.get('unstarted', [])) if campaign.get('freeze') else scheduled,
        'active_attempt': campaign.get('active'),
        'worker_preflight': live_preflight,
        'sandbox_preflight': sandbox_preflight,
        "audited": sum(bool(r.get("audit_observations")) for r in rows),
        "accepted": sum(r.get("decision") == "READY_FOR_REVIEW" and r.get("audit") == "PASS" for r in rows) if signed else 0,
        "status": ("EVIDENCE_UNAVAILABLE" if errors else 'PENDING_RUNTIME_QUALIFICATION'
                   if not rows and campaign.get('status') in {'BLOCKED_INFRASTRUCTURE', 'BLOCKED_INTAKE'}
                   else campaign.get("status", "INTAKE_PENDING_QUALIFICATION")),
        "recorded_campaign_status": campaign.get('status', 'NOT_STARTED'),
        "workers": workers, "cases": cases, "errors": errors,
        "preparation": preparation,
        "preparation_stale": (observation_age(preparation.get('updated')) is None or
                              observation_age(preparation.get('updated')) > 300),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "updated": campaign.get("updated") or "No campaign timestamp recorded",
        "manifest_digest": 'sha256:' + manifest_digest if manifest_digest else '',
        "arms": manifest.get("comparison", {}).get("arms", []),
        "comparison": manifest.get("comparison", {}),
        "release_complete": bool(campaign.get("release_complete")) and signed and not errors,
        "signature_verified": signed,
    }
