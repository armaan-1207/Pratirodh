> Historical demonstration notes from 6 October 2026. Prior run identifiers and timings do not establish current integration freshness or upstream qualification. See [local reconciliation](RECONCILIATION.md) for current verification.

# PRATIRODH — Updated Demo and Presenter Guide

Reviewed on 6 October 2026. This document is written for a reader who has never seen the project, its folders, or earlier conversations. You can understand the demonstration from this guide alone. The setup section is for the presenter operating the prepared machine.

## Project introduction: start here

**PRATIRODH is a security-repair verification lab.** Its purpose is to help a human reviewer decide whether a proposed code change fixes a specific security problem without breaking legitimate behavior.

A security patch can look convincing while leaving a second route to the same bug open. PRATIRODH turns the intended behavior into executable checks, runs the original and changed code separately, and reports the evidence. The demonstration compares an incomplete repair with a corrected repair so the audience can see that distinction.

**What goes in:** application source code, a stated security requirement, test inputs, and a proposed patch. **What comes out:** a decision, the proposed code changes, test observations, deliberately weakened-repair results, and a downloadable signed evidence package.

The audience sees a browser interface with a workspace, live workflow progress, and evidence pages. Code runs in local Docker workers: isolated execution environments used to keep each check separate. The original application source is preserved. A person remains responsible for reviewing and applying any proposed change.

### The two examples in plain language

1. **Account access:** an administrator should be able to access their account; a guest should not. The incomplete repair adds an access check but still confuses the guest with the administrator. The corrected repair fixes both mistakes. Equivalent small applications demonstrate this in Python, JavaScript, and C++.
2. **Credentials during redirects:** Requests is a Python library used to send HTTP requests. A redirect tells it to continue at another address. In the vulnerable version, an Authorization header can follow a redirect from HTTPS to HTTP or to another port on the same host. The corrected upstream patch removes those credentials at those boundaries while preserving the demonstrated legitimate redirects. CVE-2018-18074 is the public identifier for this vulnerability.

### How to read the results

- **Control:** a legitimate action that must continue to work after the repair.
- **Reproducer:** an executable example that demonstrates the original security failure.
- **Variation:** another input that challenges the same security requirement.
- **Mutation:** a deliberately weakened copy of a repair. If the security failure returns, the checks should detect it.
- **REJECT:** the proposed repair fails a required check.
- **READY FOR REVIEW:** the proposed repair passed the declared checks and can be reviewed by a human. This is not a guarantee that the entire application is secure.
- **INSUFFICIENT EVIDENCE:** execution or available evidence was inadequate for a supported decision.
- **Signed evidence:** files whose integrity can be checked using a public key. A signature shows that the recorded files have not changed; it does not establish that every test assertion is correct.

### What has actually been demonstrated

The rehearsal verified **11 expected paths: four rejected repairs and seven repairs ready for review**. Nine paths cover the three-language account examples; two cover Requests. Both live browser workflows were also exercised successfully, and a downloaded evidence package passed signature and file-integrity checks.

The demo uses prepared, supplied patches and makes zero AI model calls. It demonstrates executable verification of those patches. A separate evaluation of 24 upstream vulnerability cases is still unfinished, including cloud qualification and independent final audits. An independent audit means a separate evaluation using its own checks, rather than simply repeating the demo's checks.

**For a judge or new reader:** sections 1, 3–8 explain the demonstration and its evidence. Section 2 and section 9 contain operating instructions. The personal machine paths identify where the presenter can launch the prepared version; you do not need access to those folders to understand the demo. Running it on another machine requires the software and prepared inputs listed in section 2.

## 1. What the demo demonstrates

PRATIRODH takes a declared security problem and a proposed repair, reproduces the original violation, checks legitimate behavior, challenges the patch with additional inputs, deliberately weakens the corrected repair, and saves signed evidence for a human decision.

The presentation now includes both the established three-language synthetic account example and a **local demonstration using pinned Requests source for CVE-2018-18074**. The real upstream source is an addition to the demo; it does not complete the separate Azure qualification campaign.

The presenter story is:

> “We do not accept a patch because one test passes. We reproduce the original problem, preserve legitimate use, challenge the repair, test whether weakened repairs are caught, and let a reviewer inspect signed evidence.”

All demonstrated repairs are supplied patches. The demonstration makes **zero model calls**. It does not apply patches to the original repository, deploy a repair, or claim whole-application security.

## 2. Start the correct version

The updated source is here:

```text
C:\Users\armaa\.codex\worktrees\pratirodh-upstream-validation\Derby University Hackathon
```

The Desktop project remains an older checkout. Use the Desktop launcher to run the updated version:

```powershell
cd 'C:\Users\armaa\Desktop\Derby University Hackathon'
.\Start-Updated-Demo.ps1
```

It selects the newest complete recording of the updated demonstration, verifies signed records, and serves the current interface at **http://127.0.0.1:8767**. Reopening a recording does not rerun its checks. Keep the terminal open; Ctrl+C stops the server and preserves evidence.

To regenerate all demonstration paths before presenting:

```powershell
.\Start-Updated-Demo.ps1 -Fresh
```

To show recorded evidence with live execution disabled:

```powershell
.\Start-Updated-Demo.ps1 -ReadOnly
```

If the port is occupied, select another one, for example `-Port 8769`, and use that port in the browser.

From the final checkout, the equivalent fresh command is:

```powershell
python scripts/start_demo.py --port 8767
```

### Requirements and preparation

- Python 3.11+ with project dependencies installed, and Docker Desktop using Linux containers.
- The final checkout, prepared Requests target, and acquired Git objects containing the pinned vulnerable and reference-fixed revisions.
- The launcher prepares the general project worker image and the pinned Requests dependency image if missing. First-time preparation downloads packages; target execution itself has no external network access.
- Frontend assets are already built locally. After changing frontend source or preparing a new checkout, use `npm ci` followed by `npm run build`.
- A fresh run performs nine synthetic checks plus two Requests repair runs before serving the dashboard. Allow several minutes; C++ checks rebuild their small application repeatedly.
- Run one rehearsal/workflow at a time. Do not start another launcher while browser execution is in progress. Cross-process worker limits retain failures as insufficient evidence when slots cannot be acquired.

## 3. Demonstration A: one account, two repairs

Open **Workspace** (`/workspace`). Choose **Python / pytest** and **Repair a reported problem**, then click **Challenge both repairs**.

The synthetic application has an admin account. A guest incorrectly receives access because the access policy and user normalization are both flawed.

### First candidate: incomplete repair

The patch adds an owner check, but the guest is still normalized into the admin identity. A legitimate admin request works while the forbidden guest request remains allowed.

Expected decision: **REJECT**. The evidence shows which required security checks fail. Rejection is an executable result, not a static guess.

### Second candidate: corrected repair

The patch repairs the owner check and identity normalization across two files. Legitimate owner access must still work; guest and unrelated-user requests must be denied.

Expected decision: **READY FOR REVIEW**. Open the record and show:

1. The proposed two-file diff.
2. Three clean original reproductions and their legitimate controls.
3. Security and regression checks on the candidate.
4. Additional attack variations.
5. Two deliberately weakened repairs: removing the owner check and restoring identity confusion. Their unsafe behavior is confirmed and the verifier catches them.
6. The timeline, elapsed time, pinned worker image, resource limits, and zero observed model calls.

Repeat with **JavaScript / Node.js** or **C++ / CMake** if time permits. All three languages implement the same synthetic behavioral contract. C++ uses a CMake build and sanitizer-enabled instrumentation; this is not a general proof of memory safety.

The **Discover and repair an approved violation** option searches the approved executable property and verifies supplied candidates. It is bounded discovery with declared checks, not unconstrained AI vulnerability discovery.

The startup verification exercises three paths per language: incomplete repair rejected, corrected repair ready for review, and corrected discovery workflow ready for review. That produces **nine expected synthetic decisions: three rejected and six ready for review**.

## 4. Demonstration B: Requests redirect-security repair

In Workspace, find **Credentials must stop at the redirect boundary** and click **Challenge the redirect repair**.

This demonstration uses the pinned upstream Requests library rather than the synthetic account application. It copies a reduced source snapshot into a separate demo directory and applies supplied diffs there. Acquired originals are preserved. Source and fix revisions, hashes, license, and adaptations are recorded in the manifest and signed source artifacts.

### The behavioral contract

- **Same-origin redirect:** Authorization remains present. Exact result: `CONTROL_PASS`, exit 0.
- **Standard HTTP → HTTPS upgrade on the same host:** Authorization remains present for the upstream compatibility contract. Included in the control.
- **Same-host HTTPS → HTTP downgrade:** the vulnerable revision forwards credentials; the reference fix strips them. Result: `VIOLATION`, exit 1, before repair; `SAFE`, exit 0, after repair.
- **Same-host port change:** the vulnerable revision forwards credentials; the reference fix strips them. The safe result must also pass as an independent variation.

The reviewed adapter supplies HTTP responses entirely in memory. It exercises actual Requests redirect logic and inspects the resulting requests. No external servers receive credentials; the demonstration does not test real TLS connections.

### Two candidates and a mutation

The incomplete redirect repair restores the reference fix's scheme/port decision to `return False`. It must be **REJECTED** because downgrade and port-change checks still observe credential forwarding.

The complete upstream reference fix must reach **READY FOR REVIEW** with the legitimate controls and both security paths passing. PRATIRODH then weakens a copy of the corrected scheme/port check, confirms that unsafe behavior returns, and verifies that the checks catch it. The corrected candidate shows **one confirmed unsafe mutation caught**.

Import failures, wrong target imports, missing redirects, and setup failures produce errors rather than a valid violation. The demo requires real pinned dependencies; it does not use the harness's optional dependency stubs. Sessions ignore host proxy/netrc settings, and the worker's network is disabled.

The prepared Python 3.11 image uses urllib3 1.26.20, chardet 3.0.4, idna 2.10, and certifi 2024.8.30. This compatibility adaptation is recorded; the run is not presented as the original maintainer build environment.

**Scope:** this is a local supplied-reference-fix demonstration, with `DEMO_ONLY` assurance. The separate audit harness is prepared, but this button does not run the independent Azure audit worker or grant upstream qualification. The upstream count remains zero until actual qualification succeeds.

## 5. Signed evidence and browser screens

Every demonstrated repair record includes a decision and supporting observations. **READY FOR REVIEW** is a human-review state, not automatic approval or deployment.

- **Overview:** introduces the workflow and displays generated upstream progress. Its university-file example and animation are illustrative; they are not outputs from the Requests case.
- **Workspace:** launches both live demonstrations and lists evidence history. Language/workflow selectors belong to the synthetic example; Requests has its own button.
- **Run detail:** shows decisions, supplied patch, clean reproductions, checks, mutation witnesses, provenance, timeline, and resources.
- **Walkthrough:** selects stored signature-verified evidence for a recorded presentation.
- **Comparison:** separates historical/synthetic results from the unfinished upstream comparison campaign.
- **Validation:** shows provenance, preparation, qualifications, worker observations, campaign attempts, and audit counts. Old observations remain visibly stale; VM readiness is not repair success.
- **Projects:** exposes advanced intake and manifest review. Unfamiliar projects require reviewed contracts and dedicated workers. It is not the recommended main presenter path.

Click **Download signed evidence** from a run detail page. The ZIP contains the report, source snapshots, manifest, proposed diff, observations, SHA-256 artifact inventory, Ed25519 signature, and public trust key. It excludes the private signing key.

Signatures protect artifact integrity. They do not prove the test assertions are correct, certify the signer, or establish independent audit acceptance. Changed source, manifest, controller code, or relevant inputs can make a signed record stale. A valid but stale recording must be described as recorded evidence.

Cancellation retains partial evidence. Failed, cancelled, resource-blocked, or unresolved runs must not be presented as successful repairs.

## 6. Suggested 5–7 minute presenter sequence

1. **Overview, 30 seconds:** state the security-repair question. Open live demonstrations.
2. **Synthetic Python example, about 2 minutes:** challenge both repairs, show the rejection, then open the corrected two-file repair. Explain preserved admin access and caught mutations.
3. **Requests case, about 2 minutes:** explain downgrade/port-change credential leakage, show the weakened repair rejected and the reference fix ready for review, then show the caught mutation and upstream revisions.
4. **Evidence export, 30 seconds:** download the signed ZIP and explain its contents and human-review boundary.
5. **Other languages, 30 seconds:** show verified JavaScript/C++ records. Run them live only if time permits.
6. **Validation, 30 seconds:** show actual prepared/qualified/completed/audited counts and explain the remaining evaluation work.

Use pre-collected records for a short slot, selecting them in Walkthrough. State clearly when a result is recorded. Live runtime varies; do not promise fixed response times.

## 7. What remains outside the demonstrated result

At this review, 24 recipes are structurally prepared, but saved upstream progress is **0/24 qualified, 0/216 comparison attempts, and zero independent final audits**. Static readiness and local demo results do not increase those counts.

Azure worker/model readiness has been recorded previously. Its freshness and power observations must be checked separately. The last reviewed live query found all three VMs deallocated. The saved $28.58 retail planning estimate plus the $2 shutdown reserve exceeds the $30 gate, and the ledger/report binding needs reconciliation. This is a planning estimate, not an invoice. None of these cloud prerequisites is required to present the local demo.

Do not claim autonomous AI-generated repairs, completed upstream qualification, 216 completed comparisons, independent audit acceptance, measured model accuracy, universal support for arbitrary repositories, or production-certified isolation.

## 8. Verification receipt

The expected presenter paths are nine synthetic runs and two Requests runs: **11 paths**, comprising four rejected repairs and seven ready-for-review results. Rehearsal failures are retained separately in the verification receipt and source evidence store; the history can therefore contain more than 11 records. A Python discovery run initially exhausted its worker-slot wait while other rehearsals were running; a new signed retry produced the expected ready-for-review result. No original failed report was changed.

The agent's rehearsal checks, signed run IDs, route checks, export integrity checks, and any retained failed attempts are recorded in the adjacent `DEMO_VERIFICATION.json`. Use that receipt to distinguish measured outcomes from expected behavior in this guide.

Verification completed: all 11 presenter paths produced their expected decisions with valid signatures, current source/controller bindings, unchanged originals, and zero actual model calls. Both live browser buttons were then exercised successfully: synthetic Python and Requests each rejected the incomplete repair and accepted the corrected repair for review. The corrected Python candidate caught both declared unsafe mutations; Requests caught its declared scheme/port mutation.

Ten backend regression tests and three frontend tests passed, the frontend build passed, and all nine checked page/asset routes returned HTTP 200. Read-only execution returned HTTP 403. The Desktop launcher successfully reopened the verified store. A ZIP downloaded through the browser passed signature and artifact-hash verification and excluded the private signing key. Full release acceptance is a separate milestone.

## 9. Troubleshooting and fallback

- **Port occupied:** use another port; the launcher does not stop another server.
- **Docker unavailable:** use a verified recording with `-ReadOnly`; live buttons are disabled. Fresh Docker checks require Docker Desktop in Linux-container mode.
- **Requests image missing:** run the fresh launcher to build it, then retry. Missing prepared dependencies must remain an error.
- **Worker slots unavailable:** finish/cancel the other local workflow, then start a new run. Preserve the insufficient-evidence record.
- **Upstream source/fix objects missing:** restore the licensed acquisition and target inputs. A normal Git clone does not include ignored acquisition/evidence directories.
- **Stale recording:** regenerate before claiming a current live result. Do not change controller code during the presentation.
- **Unexpected decision or export failure:** inspect the retained evidence and server logs. Show a previously verified recording and describe it honestly; never edit a JSON decision to force success.

The existing PPT/video package is historical. This updated browser demonstration and guide should be the technical source of truth until those presentation artifacts are refreshed.
