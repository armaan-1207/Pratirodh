# PRATIRODH demo narration

## Prepare

Start Docker Desktop, then run `./start-demo.ps1`. For a fresh evidence set, run `python tools/prepare_demo.py`; it checks replay, reduction, and stale-evidence refusal. Open http://127.0.0.1:8765/workspace. Local and combined generation also require the configured Ollama model. Keep the curated demonstration available if generation is slow or unresolved.

## Presenter flow

1. Introduce PRATIRODH as a repair lab that produces evidence for a human decision. A readiness decision covers the recorded checks; it never applies a patch automatically.
2. Select **Start guided demo** above the mode tabs to run the three supplied verifications. Watch actual execution stages and elapsed time; Docker/model availability is shown in the workspace. The fixed-test gate accepts an incomplete path repair; the full gate rejects that same repair; a correct repair becomes ready for review. These are disclosed development examples.
3. Open the rejected full run. Read the verdict summary and next action, then show its verified signature, current freshness, patch, and failed security requests. In **Requests**, filter to failures, expand `probe-symlink`, and replay the exact request. The synthetic private canary remains visible, demonstrating why the patch was rejected.
4. Open the correct full run. Inspect **Challenge the Fix**: qualified unsafe mutations, missed initial tests, and additional catching tests. Unavailable mutations remain visible. Show request evidence and provenance rather than presenting a confidence score as authorization.
5. Show **Combined repair** and **Local AI**. Combined tries one untrusted template, then at most two local model proposals if readiness is not established. Every proposal uses the same verification gate and is retained. A failure or timeout is an honest unresolved outcome. Source files remain unchanged.
6. Filter evidence by `template` or `local-model` to inspect candidate origins. A signed human approval is a separate review record. Current evidence is shown first; the stale-evidence toggle reveals retained history. Old or modified evidence cannot be replayed or approved as current evidence.
7. Open **Comparison**, switch between **Repair** and **Verification**, and expand costs or raw records when needed. Explain the separate curated and real-world-derived cohorts, frozen manifest, quota shortfall, native historical review referrals, and independent final audit. Use the measured Markdown report for conclusions. Four evaluation cases and related projects cannot establish market-wide superiority.

## Local generation example

The registered external command fixture exercises a template without requiring a model call:

```powershell
python -m pratirodh pipeline benchmark/external-v1/cases/external-ghsa-j5h9-9r39-43q5 --contract benchmark/external-v1/cases/external-ghsa-j5h9-9r39-43q5/contract.json --strategy combined
```

Its result remains subject to ordinary verification and freshness. The fixture reproduces a documented mechanism with harmless synthetic command effects; it is not an assessment of the upstream application.

## Read-only review deployment

Export fresh signed bundles with `python tools/export_review.py`, then build the authenticated dashboard with `docker compose up -d --build`. The review dashboard can display evidence and comparison results but cannot generate repairs, replay targets, or sign approvals. Run `python tools/check_deployment.py` to check authentication and read-only enforcement. Keep deployment credentials and signing material local.

## Workspace preview

[View the guided workspace](screenshots/ui-workspace.jpg). Use the live demo for verdicts, replay, and comparison screens; duplicate presentation captures are not shipped.

The Word document, recording, slide assembly, and public hosting are outside this release.

The interface refresh does not retune verification decisions or change the frozen v1 comparison. Those results describe the measured implementation before this presentation update; fresh demo evidence is regenerated after relevant code changes.
