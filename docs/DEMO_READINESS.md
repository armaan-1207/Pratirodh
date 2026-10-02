# Demo readiness — 2 October 2026

The redesigned Pratirodh checkout is the application being extended. The older
Desktop Kavach checkout is preserved. PPT and video production are deferred.

## Available now

- Redesigned Overview, Workspace, Comparison, Upstream Validation, project intake,
  project evidence, and recorded walkthrough routes.
- Multi-file Python, Node, and C/C++ synthetic demonstrations in restricted Docker
  workers, with signed reports and verified exports.
- Resumable comparison runner with separate execution/audit contexts, explicit
  audit image digests, controller/input hashes, and equal declared budgets.
- All 24 upstream source revisions acquired, with vulnerable/fixed revisions,
  license-file hashes, full source inventories, and reference-fix hashes.

Source acquisition does **not** establish qualification or repair success. The
generated `/validation/status.json` is the current count authority.

## Outstanding acceptance gates

1. Review the licenses and prepare runnable manifests for all 24 upstream cases.
   Establish vulnerable, fixed, legitimate, and held-out audit controls. No case
   is currently qualified.
2. Confirm remaining Azure spending allowance. Cost Management returned an error;
   the consumption endpoint returned no usage. Neither establishes zero cost.
   All three VMs are deallocated; disks and reserved public IPs remain.
3. Prepare each case's dependencies in pinned worker images and capture current
   model/execution/audit attestations. Historical worker attestations remain
   distinguishable from the current deallocated power state.
4. Freeze the qualified 24-case cohort (two development and six evaluation cases
   per language). Run 216 scheduled attempts: 18 evaluation cases, two workflows,
   two arms, and three repetitions. Retain failures and unresolved outcomes.
5. Independently audit executable retained candidates. Capture and verify signed
   campaign evidence, including referenced per-attempt reports.
6. Verify the complete browser flow and offline evidence replay, finish tests,
   document final host/image/model identities, and remove Azure resources after
   evidence capture. The full upstream acceptance criteria remain unfulfilled.

## Start the synthetic browser demonstration

From the redesigned checkout:

```powershell
python scripts/start_demo.py --port 8767
```

This creates new signed **synthetic** records before serving the browser. To
reopen a previously captured store without recomputing:

```powershell
python scripts/start_demo.py --port 8767 --store PATH_TO_EVIDENCE_STORE
```

Select a verified record at `/walkthrough`, inspect its evidence, and export it.
Keep the trust public key independently from the ZIP when handing evidence over:

```powershell
python -m pratirodh export RUN_ID --store PATH_TO_EVIDENCE_STORE --output result.zip
python -m pratirodh verify-bundle result.zip --trust PATH_TO_TRUST_PUBLIC_KEY
```

The ZIP contains public trust material and signed artifacts, never signing keys.
Do not present the synthetic walkthrough as a completed upstream experiment.
