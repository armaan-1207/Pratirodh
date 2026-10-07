# Local operations tooling and activation gates

This tooling is opt-in. It does not activate external alerting, replace an
existing signing key, configure off-host storage, grant Windows permissions,
start cloud resources, or make the application production-ready by itself.
The publication base is 8b3d772; these later changes are prepared for one
consolidated follow-up commit. Exact-revision publication results are recorded
separately after verification.

## Encrypted evidence backup

Use a protected operator terminal and a fresh destination outside the evidence
store. Stop jobs or let the evidence writer lease finish. Backup holds the same
lease as Store.save, verifies every indexed signed record, requires index/disk
agreement, and takes a consistent SQLite backup. Unexpected files, links,
unverifiable signatures and oversized snapshots are rejected.

```powershell
python tools/manage_operations.py backup --store run_output/pratirodh --output X:/protected-backups/evidence-YYYYMMDD.backup
```

The example X: destination is a placeholder, not configured storage. The CLI
prompts twice for a passphrase; never put it on the command line or in logs.
The CLI refuses getpass fallback when a non-echoing terminal is unavailable.
Backups use Scrypt (N=32768, r=8, p=1) and AES-256-GCM with fresh random salt and
nonce. Authentication covers the format identifier and contents. The current
bounded local implementation accepts at most 64 MiB expanded content; larger
stores require reviewed streaming backup support rather than relaxing limits.

The signing key is excluded by default. A separate, explicitly requested
`--include-signer` encrypted operator backup can support recovery. It is not an
evidence export and must never be published or placed in the release tree.
Do not store its passphrase beside the backup. Protect the backup directory and
passphrase recovery through separately controlled identities.

## Restore drill

Supply a historical public key from independently retained trusted material,
not from the same backup. Choose a nonexistent directory.

```powershell
python tools/manage_operations.py restore --backup X:/protected-backups/evidence-YYYYMMDD.backup --output run_output/restore-YYYYMMDD --trusted-public X:/trusted-anchors/trust.pub
```

Wrong passwords, tampering, unexpected paths and wrong anchors fail before the
destination is created. All records and SQLite inventory are validated in
private staging. Duplicate object keys, unsafe portable filenames, excessive
member counts and signed-record/index metadata mismatches are rejected.
Restore never overwrites an existing store. Keep destination parent directories
under operator control; preflight link checks are not a race-free filesystem
sandbox against concurrent hostile changes. Files are created
exclusively with restrictive POSIX modes; Windows ACL enforcement and service
identity access still require an operator-host proof. A failed disk write can
leave a partial fresh destination: retain it for diagnosis and choose a new
destination for the next attempt. Do not activate partial restores.

Production acceptance still requires encrypted off-host placement, seven daily
recovery points, measured RPO <=24 hours, and RTO <=60 minutes. The tool does not
claim those controls from a successful local restore or implement unattended
retention/deletion.

## Separate signing epoch

```powershell
python tools/manage_operations.py new-key-epoch --output run_output/next-signing-epoch
```

This creates a fresh Ed25519 signer and anchor in a new store and refuses an
existing destination. It never edits the old store. Preserve old evidence and
its trusted public anchor together. Verify a synthetic signed record in the
new store before an explicitly approved cutover. The current Store supports
one anchor per store; combining key epochs or transparent in-place rotation is
not implemented. No verification policy is relaxed.

For a compromised key, stop new signing, retain historical evidence, record the
compromised fingerprint, incident time and affected records, and isolate its
store from active review until an operator adjudicates affected evidence.
Mathematically valid signatures do not prove a compromised signer was trusted.
Automated revocation lookup, production account provisioning and cross-store
dashboard activation remain unimplemented. Never silently replace trust.pub
to make historical signatures pass.

## HTTPS alert adapter

`pratirodh.operations.HTTPSAlertDelivery(endpoint, token)` is an explicit adapter
for an operator-selected receiver. No destination is configured by default.
Set both PRATIRODH_ALERT_ENDPOINT and PRATIRODH_ALERT_TOKEN in the protected
service environment and restart to connect application threshold alerts to
this adapter. A partial configuration refuses startup. Never place the token
in a command line, release file or log. Unset both variables to leave delivery
disabled.

The application records sanitized delivery failures and delivered/failed
counters without exposing the endpoint, token or exception text. Access denials
remain enforced when delivery fails. Delivery makes one synchronous attempt;
the bounded transport timeout can add request latency. There is no durable
queue, automatic retry or recipient-acknowledgement guarantee.

Only HTTPS endpoints without URL credentials, query or fragment are accepted.
Default transport validates certificates and hostnames, disables proxy-env
routing, refuses redirects, and makes one bounded attempt. Only type, controller
event code, generated request ID and count are transmitted; source, arbitrary
logs and exception text are excluded. The bearer token stays in the header and
is not returned in failure messages. Delivery failure raises an explicit error;
there is no silent retry, queue or guaranteed-delivery claim. Callers must
surface that error to operator monitoring and handle outages deliberately.

Local tests exercise certificate rejection and authenticated delivery to an
ephemeral loopback HTTPS receiver. This is not an actual recipient notification.
Before unattended service, configure the chosen collector or select Azure
Monitor, exercise a real application event, and confirm delivery
within five minutes and named-recipient acknowledgement within 15 minutes.

## Remaining independent gates

The candidate's push and PR CI passed 312 Docker-enabled Python tests each.
The historical Requests failure is still unexplained and its sanitized
diagnostics are preserved for future failures. New operations changes have
local verification only until explicitly reviewed and published.

Cloud execution must still pass current budget evidence, worker/model identity,
readiness and shutdown-guard acknowledgement. Prior consumption is retained;
the $35 total cap includes the $2 reserve. Previously rejected upstream harness
work is not retried. Nineteen preparation blockers, 0/24 signed qualifications
and 0/216 campaign runs are not upgraded by local tooling tests.

## Recorded local verification — 7 October 2026

- Combined Docker-enabled suite: 334 passed, zero skips, 690.42 seconds.
- Final operations suite: 23 passed, zero skips, including the real loopback
  HTTPS test added after the combined suite was collected. The two receipts
  cover all 335 currently collected cases; no single 335-test run is claimed.
- Frontend: 7 passed; rebuilt assets match committed assets. No frontend design
  or verification policy changed in this operations follow-up.
- Locked deployment Python and production npm audits: no known vulnerabilities.
  Bandit: zero medium/high findings; 83 existing low findings remain.
- Clean-source wheel: 106 members, including operations.py, with no private or
  generated acquisition/evidence paths. Deployment-image build and isolated
  encrypted-backup/restore/key-epoch drill passed; synthetic Linux signer files
  had mode 0600. Production account/ACL enforcement remains unverified.
- Final image local HTTPS, authenticated/read-only, host rejection, signed
  restore, tamper rejection and local sanitized threshold-alert checks passed.
- All four image advisory reports passed the existing review policy: 249
  reviewed high/critical residual candidates remain (46 dashboard, 44 runner,
  115 general worker, 44 Requests). No unreviewed high/critical findings were
  found using the database updated 2026-10-07T07:38:55Z. This does not mean zero
  vulnerabilities or remediation of the reviewed native-library risks.

A read-only Azure observation at 2026-10-07T16:39:49Z records a $31.69 modeled
upper bound, not an invoice or new allowance.
At that observation, all three VMs were deallocated; this is a dated observation,
not continuous monitoring. The existing conservative execution ledger subsequently refused a new window
with "approved usage allowance is exhausted". The prior ledger was not reset,
and the $35 ceiling with $2 reserve was not increased. Current qualification
and campaign execution therefore remains blocked; no resources were started.

Generated evidence is retained under ignored run_output paths, including
operations-combined-20261007.xml, operations-tooling-final-20261007.xml,
operations-test-coverage-final-20261007.json,
operations-local-deployment-release-20261007.json,
operations-cloud-execution-gate-20261007.json and operations-wheel-20261007/.
The final handoff binds release source hashes and the image-advisory gate
receipt separately. These later changes remain uncommitted and unpushed.

## Parallel follow-up acceptance — 7 October 2026

Focused hardening checks passed without skips: 59 operations cases, 59
Docker-enabled application/security cases, 19 scanner-binding/policy cases and
80 preparation/readiness cases. These overlap and are not a combined count.
The frontend's seven tests, bundle consistency, deployment Python and production
npm audits passed. Four installed/vendored image dependency audits found no
applicable advisories; two partial-component candidates remain explicitly
reviewed. The current local deployment image passed HTTPS, authentication,
read-only access, unexpected-host rejection, signed restore and tamper checks.
The clean wheel contains 106 members and excludes private/generated paths.

Fresh scans with the existing database passed the dated advisory gate with the
same 249 residual candidates. Four image bindings validate ordered filesystem
layers and archive/report hashes; differing Docker and scanner config IDs are
reported explicitly. This improves provenance, not native-library remediation.

The first 389-case complete run had 388 passes and one C++ repair worker timeout
(no skips). It returned INSUFFICIENT_EVIDENCE / BUDGET_EXHAUSTION. The same case
passed unchanged in isolation in 63.83 seconds. The timeout cause is unexplained;
a later passing run must not be represented as its diagnosis or fix. Initial
and repeat suite receipts remain separate under ignored run_output paths.
No worker limits, assertion or decision policy was weakened.

The complete unchanged-source repeat passed **389 tests with Docker enabled,
zero skips, in 517.26 seconds**. The initial failure receipt is retained and
its cause remains unexplained; this passing repeat does not close that finding.

## Reliability and activation-review follow-up — 7 October 2026

A demonstrated cleanup transport fault was fixed without changing worker
limits, expected decisions or verification reserves. Signed reports and CI
diagnostics now distinguish deadline/slot/cleanup categories. Historical
C++ and Requests causal diagnoses remain open. The operator acceptance preflight
fails missing, stale, wrong-anchor or changed drill evidence; valid attestations
only permit review and do not independently prove external service operation.
No operator account, off-host destination, recipient or public service was activated.

See RELIABILITY_FOLLOWUP_20261007.md, OPERATIONS_ACTIVATION_20261007.md,
NATIVE_MIGRATION_ACCEPTANCE_20261007.md and CLOUD_BUDGET_REVIEW_20261007.md.
Separate dated source hashes are in SECURITY_STATUS.json under release_followup.
The authoritative ledger and $35 cap with $2 reserve are preserved. No earlier
automatically rejected harness operation or cleanup deletion was retried.

Corrected final-source verification: **428 Python tests passed with Docker enabled, zero skips, in 611.23 seconds**; the explained intake-order regression is resolved. Seven frontend tests and bundle consistency also passed. Current Bandit results retain 84 low findings and zero medium/high. Exact-revision GitHub CI and final artifact receipts are recorded separately after preparation; no external qualification or production acceptance is inferred. These dated receipts use 7 October UTC (8 October local time for the final handoff).
