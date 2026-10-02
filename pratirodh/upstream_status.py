"""Derive UI status from source acquisition and campaign artifacts."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from .evidence import Store, canonical
from cryptography.exceptions import InvalidSignature


def read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except FileNotFoundError:
        return {}, None
    except (OSError, ValueError) as error:
        return {}, f"{path.name}: {type(error).__name__}"


def load_status(root: Path) -> dict:
    errors = []
    def artifact(relative):
        value, error = read(root / relative)
        if error:
            errors.append(error)
        return value
    manifest_path = root / "benchmark/upstream-v1/manifest.json"
    manifest = artifact("benchmark/upstream-v1/manifest.json")
    campaign = artifact("run_output/upstream-validation/campaign.json")
    acquisition = artifact("run_output/upstream-acquisition/acquisition.json")
    attestations = artifact("run_output/azure-validation/attestations.json")
    power = artifact("run_output/azure-validation/power-state.json")
    acquired_by_id = {row["id"]: row for row in acquisition.get("cases", [])}
    cases = []
    for item in manifest.get("cases", []):
        case = dict(item)
        row = acquired_by_id.get(item["id"], {})
        provenance = row.get("provenance", {})
        if row.get("status"):
            case["status"] = row["status"]
        case.update(project=item.get("project", "unknown"), advisory=item.get("cve", "unknown"),
                    source_url=item.get("fix_url") or item.get("repository_url", ""))
        case["source_revision"] = provenance.get("vulnerable_revision", item.get("source_revision"))
        case["license_evidence"] = provenance.get("license_files", item.get("license_evidence", []))
        cases.append(case)
    rows = campaign.get("rows", [])
    signed = False
    if campaign.get('signed_run_id'):
        try:
            store = Store(root / 'run_output/pratirodh')
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
    for worker in attestations.get("workers", []):
        worker = dict(worker)
        worker["attestation_status"] = worker.get("status")
        worker["status"] = power.get("status", "CURRENT_STATE_UNKNOWN")
        workers.append(worker)
    return {
        "target": manifest.get("target_count", 24),
        "acquired": sum(c.get("status") in {"SOURCE_ACQUIRED", "QUALIFIED", "AUDITED"} for c in cases),
        "qualified": sum(c.get("status") in {"QUALIFIED", "AUDITED"} for c in cases),
        "completed": len(rows),
        "audited": sum(bool(r.get("audit_observations")) for r in rows),
        "accepted": sum(r.get("decision") == "READY_FOR_REVIEW" and r.get("audit") == "PASS" for r in rows) if signed else 0,
        "status": "EVIDENCE_UNAVAILABLE" if errors else campaign.get("status", "INTAKE_PENDING_QUALIFICATION"),
        "workers": workers, "cases": cases, "errors": errors,
        "updated": campaign.get("updated") or power.get("updated") or "No campaign timestamp recorded",
        "manifest_digest": "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest() if manifest_path.exists() else "",
        "arms": manifest.get("comparison", {}).get("arms", []),
        "comparison": manifest.get("comparison", {}),
        "release_complete": bool(campaign.get("release_complete")) and signed and not errors,
        "signature_verified": signed,
    }
