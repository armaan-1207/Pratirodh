# Security and operations acceptance follow-up

Date: 2026-10-07. Base candidate: `2f973b85eeee7f6dcf0d101b5cdeb02ccea79ab2`.
This supplement adds local tests and acceptance decisions without changing
application behavior, evidence signatures, worker policy or frontend assets.
Prepared for the single authorized final follow-up commit. Public deployment
remains deferred. Publication results are recorded separately against the final
commit SHA; this document does not predeclare passing CI.

## Native execution boundary

The controller executes native programs inside a disposable worker; this is not
a claim that an opaque native library is memory-safe. The trusted test uses a
small C program with an intentional `abort()`, not a CVE reproducer or an
upstream qualification harness. No rejected upstream work is repeated.

`tests/test_worker_boundary.py` verifies malformed protocol rejection,
nonzero-container exit rejection despite purported success output, cleanup,
UID 65534, zero effective capabilities, no-new-privileges, read-only root,
loopback-only networking, absent Docker socket, and absent host environment
canary. It compiles and runs a valid native program, deliberately aborts it,
checks timeout and output limits, rejects traversal and oversized intake,
then successfully runs the native program again. Containers must be absent
after execution, including failed execution.
Controller-level tests additionally verify that crash, timeout, output-limit,
missing-dependency and startup-failure observations produce signed
INSUFFICIENT_EVIDENCE reports, never READY_FOR_REVIEW.

Local worker image under test:
`sha256:3c9d4d79d83fa2ff38a71971376f7a00c027bc492487d4092601e8209e2014a4`.
The explicit local-demo mode is used. This is not an Azure host-isolation proof,
24-case qualification, an independent audit, or validation of every native
library. Memory/PID/disk configuration and other worker behavior retain the
existing real Docker regression coverage; this test does not exhaust memory.

Acceptance for the tested boundary requires the focused tests and existing
real worker regressions to pass with Docker enabled and no skips. Changed worker
images require fresh proofs. Native advisories remain open, and native workers
remain restricted to dedicated, offline, disposable environments for unfamiliar
inputs. Sensitive or shared public workloads are outside the verified scope.

## Key management decision

- **A: locally operated control.** Recommended first operational gate. Require
  a dedicated signer identity, verified host access restrictions, no private keys
  in workers/exports/logs, and a rehearsed rotation/revocation procedure.
- **B: managed service.** A vault may store the current Ed25519 key as a secret
  with restricted identity access and audited retrieval. This is not equivalent
  to non-exportable managed signing. Azure Key Vault's documented signing-key
  types do not include Ed25519; any signature-format migration requires a
  separate compatibility and trust review.
- **C: documented limitation.** Current attended-local scope only. No production
  key-management acceptance is recorded.

`tests/test_key_recovery_boundary.py` proves public-only recovery can verify
historical records but cannot silently regenerate a signer; a mismatched private
key cannot save new evidence; and a different key epoch cannot verify records
under the wrong trust anchor. Separate synthetic stores demonstrate trust
separation, not automatic rotation or revocation support. Windows production
ACLs and service identities are unverified. No operator keys were read or changed.

## Backup decision

- **A: locally operated control.** Recommended first operational gate. Require
  consistent encrypted off-host backups of databases, evidence and trust
  metadata, with separately protected signing-key recovery.
- **B: managed service.** Managed retention/deletion protection is acceptable
  only with application-consistent capture and a successful recovery drill.
- **C: documented limitation.** Disposable demonstration data only; not
  irreplaceable qualification or campaign evidence.

Proposed targets, awaiting operational adoption: RPO at most 24 hours, RTO at
most 60 minutes, seven daily recovery points. A real isolated restore must
check complete record inventory, historical signatures, trust fingerprints,
tamper rejection and recovered key permissions. Current synthetic staging
restore proofs do not establish off-host backups, encryption, retention, RPO
or RTO. Backups therefore remain an operational blocker for persistent service.

## Alerting decision

- **A: locally operated control.** Authenticated external receiver, sanitized
  events, bounded delivery handling and observable receiver outages.
- **B: managed service.** Recommended before unattended service: Azure Monitor
  and an Action Group with a named recipient and both notification-test and
  actual application-event delivery proofs.
- **C: documented limitation.** Current attended-local scope, active log review;
  no external delivery or round-the-clock response claim.

Proposed acceptance: a synthetic security event reaches its named recipient
within five minutes, is acknowledged within 15 minutes, and delivery failure
is observable. Current local collector delivery passes, but an external
destination and recipient have not been configured. No outbound notifications
were sent. Public activation remains pending.

## Evidence and release gate

Generated receipts remain ignored under `run_output/`:

- `security-operations-focused-20261007.xml`: focused boundary, recovery,
  authentication and deployment-verifier checks.
- `security-operations-regression-20261007.xml`: existing real Docker worker,
  signed-export and concurrent-evidence regression checks.
- `security-operations-deployment-20261007.json`: repeated synthetic local HTTPS,
  authenticated/read-only behavior, proxy/backend host rejection, signed
  restore, tamper rejection and sanitized threshold-alert delivery.
- `security-operations-source-bindings-20261007.json`: hashes binding the tested
  implementation, tests and report to this local follow-up.

Focused result: 25 passed, zero skips, 14.44 seconds with Docker enabled.
Existing real worker, export and evidence-concurrency regressions: 19 passed,
zero skips, 243.90 seconds. Total for this batch: 44 passing tests.

The deployment receipt is PASS for dashboard image
`sha256:fbf8f9591e68217886e7af71bce2644a0eb8ac2eb82704ef12bc0e84a3b16cf1`.
It explicitly records public activation as NOT_CONFIGURED, backups as synthetic,
and alert delivery as local. Historical 295-test verification is preserved;
it is not presented as a newly repeated complete suite for these additions.

At the end of the local security-verification batch, CI engagement was blocked
by recorded GitHub push Internal Server Errors; the historical Requests
inconsistency remained unexplained. Neither issue is closed by local tests.
The subsequent authorized publication may push this branch, but does not merge,
create a PR, change branch protection, start Azure resources or deploy publicly.
The total cloud cap stays $35 including the $2 shutdown reserve.
Read-only remote verification still shows main at
`c164369e952e0b954f3f3e5199459121fd11d2fe` and the remote readiness branch at
`65a0e9210b577af767425b0df7abdcd4ac4fa9ed`. The original desktop checkout's
reported status is unchanged from the start of this batch.

Production acceptance requires actual host key permissions and key lifecycle,
recoverable off-host backups, external alert delivery and CI evidence.
Risk acceptance needs an owner, reason, expiry and review trigger, and cannot
override automatic rejection. No production exception is silently approved.

## Reproduction and submission

Use an isolated checkout with the locked deployment dependencies and pytest
9.1.1, and build the existing project-worker image through the controller.
Never execute imported native source on the host. These tests use only trusted
synthetic fixtures and isolated containers.

```powershell
python -m pratirodh project build-worker
$env:PRATIRODH_DOCKER_TESTS = '1'
python -m pytest -q tests/test_worker_boundary.py tests/test_key_recovery_boundary.py tests/test_local_deployment_verification.py tests/test_security.py
python -m pytest -q tests/test_projects_docker.py tests/test_project_export.py tests/test_evidence_concurrency.py
python tools/verify_local_deployment.py --image pratirodh-dashboard:local-release --output run_output/security-operations-deployment-fresh.json
```

The deployment verifier additionally requires a locally available dashboard
image built from the candidate and `caddy:2`; it refuses missing images and
existing receipt destinations. Its result covers synthetic local HTTPS and
recovery, not production operators or off-host services.

`CI_CANDIDATE_HANDOFF_20261007.json` preserves sanitized test totals, source/image
hashes, receipt checksums, historical push request IDs, CI acceptance criteria
and unresolved gates. Raw reports, signing keys, databases and acquisition
trees remain outside this follow-up commit. The earlier complete Python suite
passed 295 tests; this follow-up adds 17 tests and reports only its actually
executed 44-test subset, not an assumed 312-test complete-suite pass.

The historical push attempts were at 2026-10-07 15:12:40Z, 15:12:52Z and
15:14:31Z. Each returned Internal Server Error and left the remote branch at
65a0e92. This is a documented external publication blocker with unknown root
cause, not proof of a permanent outage. Historical push run 37632194569 failed
the Requests reference-fix expectation (READY_FOR_REVIEW versus observed
INSUFFICIENT_EVIDENCE); PR run 37632202872 passed. The old failure lacks the
reason/runner diagnostics needed to explain the discrepancy. The existing
candidate diagnostics and failure-artifact step are retained without weakened
assertions or verification retries.

The final commit must be tested by exact SHA. A repeated push failure permits
local handoff of a verified Git bundle and checksums, but cannot replace passing
CI, satisfy main's required checks or authorize public deployment. New push and
CI receipts are kept under ignored `run_output/` to avoid repeated commits solely
for recording attempts.

References: [Azure Key Vault key types](https://learn.microsoft.com/en-us/azure/key-vault/keys/about-keys),
[Azure Backup protections](https://learn.microsoft.com/en-us/azure/backup/secure-by-default),
[Azure Monitor Action Group testing](https://learn.microsoft.com/en-us/azure/azure-monitor/alerts/action-groups).
