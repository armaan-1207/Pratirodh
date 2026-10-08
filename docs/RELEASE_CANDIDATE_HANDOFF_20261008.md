# Local release candidate handoff — 8 October 2026

This follow-up to `93b713e845f8f368232ae031a13f08af83ef592d` packages the
local findings for one commit on `codex/readiness-followup`, published only to
`armaan-1207/Pratirodh`. Its exact revision is the commit containing this
document, not the earlier candidate `2f973b8`. GitHub main and original source
checkouts are outside this publication batch. No new PR or merge is authorized.

## Evidence and release contents

The default-worker combined local suite passed 430 Python tests with Docker
enabled, zero skips, in 729.73 seconds; frontend tests passed all seven cases.
Sanitized diagnostic plumbing passed 21 focused tests, and the affected C++
repair check passed in 92.50 seconds. These are local results, not a substitute
for this revision's remote CI. The dated CI, cloud, native and upstream
follow-up records preserve historical observations and their limitations.

The commit includes diagnostic tests, failure-only sanitized artifact collection,
worker/revision identity logging, security-status data and the inactive
experimental worker recipe. Existing security-acceptance tests and operations
tooling remain inherited from the base history. It excludes raw logs, private
billing captures, signing keys, databases, environments, upstream acquisitions,
prepared snapshots and generated evidence. The local release-file inspection
covered 1,013 intended files including this handoff document and found
no exclusion violations; the final inspection is retained privately with
per-file SHA-256 values. Original preservation checked 1,264 files and 24
source repository heads without differences.

## External CI gate and infrastructure contingency

The push and existing PR workflows must bind the candidate SHA to checkout
logs, runner image/version, dependency versions and immutable worker image IDs.
Docker tests must execute without skips; all security/build/advisory checks
must complete. Any differing test count must be explained. Failure artifacts
contain only allowlisted IDs, decisions, statuses, categories and timings, with
seven-day retention. No artifact is expected on success. An exception before
report creation can legitimately lack a report artifact and remains a failure.

A failed push must first be checked against the remote SHA. Infrastructure
failure records retain UTC time, candidate SHA, exit status, sanitized error,
remote SHA and available request identifier in ignored local output. Do not
repeat a push already accepted. At most two additional infrastructure-only
attempts, separated by approximately 30 minutes, are allowed. Persistent
failure is `BLOCKED_GITHUB_INFRASTRUCTURE`, not local-test acceptance or a
permanent root-cause conclusion. A README note does not replace CI. Subsequent
run results and log hashes belong in the private handoff receipt, avoiding an
extra result-only commit. Historical Requests and C++ causes remain unexplained.

## Frozen and unfinished milestones

Azure execution stays frozen under the $35 cap including the $2 reserve. The
ledger's last reviewed conservative projection was $43.385162 including reserve
at 2026-10-08T06:18:05Z; this is not an observed bill. No ledger reset or
resource start is authorized. Qualification remains 0/24 and campaign 0/216;
19 upstream preparation cases remain blocked. The Ubuntu worker remains
experimental with 175 open header findings and unverified host-kernel exposure.
External backup, signing and alert activation and public deployment remain
deferred. Safety-rejected harness and cleanup operations were not retried.
