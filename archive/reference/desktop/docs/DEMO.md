# Present PRATIRODH

Use Python 3.11+ and Docker Desktop in Linux-container mode. From the project
folder, install dependencies once, then start the demo:

```powershell
python -m pip install -e .
python scripts/start_demo.py
```

The launcher checks prerequisites, prepares the worker image if missing, verifies
nine fresh Docker runs and starts the dashboard at http://127.0.0.1:8767.
Six corrected repair/discovery runs must be ready for review and three incomplete
repairs must be rejected. Evidence is retained in a new timestamped directory.
Allow several minutes for verification; a first image build can take longer.
The launcher never overwrites previous runs or stops existing servers.

To reopen an existing store without regenerating evidence:

```powershell
python scripts/start_demo.py --store C:/path/to/demo-output/evidence
```

Use `--port 8768` if the default port is occupied. Ctrl+C stops the server.
Do not edit controller code during presentation: that makes existing evidence
stale, and fresh verification is required to restore its current status.

## Three-minute presenter walkthrough

1. Open the dashboard. Explain: “PRATIRODH challenges security repairs and saves
   the evidence supporting human review.” Identify the supplied-patch label.
2. Choose Python and “Repair a reported problem.” Click “Challenge both repairs.”
   The guest-to-admin identity mapping survives the incomplete owner-check fix.
   Show that this patch is rejected even though legitimate admin access works.
3. Open the corrected repair. Show the two-file diff, three original violation
   reproductions, legitimate-use checks, attack variations and both qualified
   unsafe mutations being caught.
4. Download signed evidence. The ZIP includes observations, source snapshots,
   patches, an artifact inventory, signature and public trust key. The controller
   signing key is excluded. A valid signature protects integrity, not correctness.
5. Return to history and show JavaScript and C++ repair/discovery evidence.
   Run another language live if time permits.

The browser refreshes while a workflow runs. Cancellation preserves partial
evidence; it never marks an unfinished run successful. If Docker is unavailable,
use the previously collected evidence for the walkthrough. Do not describe a
recorded run as a new live execution.

## What the demo establishes

These are synthetic examples with supplied patches, not autonomous AI results,
independent upstream audits or an accuracy benchmark. They demonstrate actual
container execution, protected source, attack reproduction, repair rejection,
mutation challenges and signed review artifacts. Original source stays unchanged.

The local Qwen 7B model is installed. Its separate smoke evaluator requires 8 GiB
of available RAM and records a blocked preflight if that requirement is unmet:

```powershell
python scripts/evaluate_local_prototype.py --output run_output/model-smoke-new
```

For approved dedicated workers add `--context pratirodh-worker`. Inference stays
on the laptop. Cloud provisioning and the 24-case upstream evaluation are separate
milestones; neither is needed to present this supplied-patch demo.

## Verified on 2 October 2026

The demo-ready verification passed all nine expected decisions: six corrected
repair/discovery runs ready for review and three incomplete repairs rejected.
The browser-triggered Python demonstration also completed with the expected
rejection and acceptance. Its downloaded ZIP passed signature and artifact-hash
validation and excluded the private signing key. All original source stayed
unchanged. Software tests: 58 passed; opt-in Docker integration tests: 9 passed.

Saved demonstration: `run_output/demo-ready-20261002/evidence`. Reopen it with:

```powershell
python scripts/start_demo.py --store run_output/demo-ready-20261002/evidence
```

The separate 7B smoke check recorded `MEMORY_PREFLIGHT_BLOCKED` with 2.19 GiB
available RAM. It produced no generated repair results. No Azure resource was
provisioned for this demo.
