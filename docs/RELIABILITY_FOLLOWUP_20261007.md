# Reliability follow-up — 7 October 2026

Scope: additive, sanitized controller diagnostics and a demonstrated cleanup fault.
This follow-up does not identify either historical timeout's cause. Local results
are distinct from signed upstream qualification and Azure execution.

## Retained observations and open diagnoses

The first combined 389-case run had 388 passes and one failure in
`test_real_multi_file_end_to_end[repair-cpp]`, taking 995.176 seconds overall.
The failed report returned `INSUFFICIENT_EVIDENCE` / `BUDGET_EXHAUSTION`, with
`worker container timeout`. The unchanged C++ case passed in isolation in
63.83 seconds; an unchanged full repeat subsequently passed 389 tests without
skips in 517.26 seconds. Neither passing rerun establishes whether the original
cause was startup, compilation, host contention, or a workflow deadline.
No execution limits, assertions, decision requirements or verification reserves
were increased or relaxed.

The historical Requests push run 37632194569 on revision
65a0e9210b577af767425b0df7abdcd4ac4fa9ed had 292 passes and one failure in
447.59 seconds: the reference fix returned `INSUFFICIENT_EVIDENCE` rather than
`READY_FOR_REVIEW`. Its retained runner log identifies Ubuntu 24.04 and Python
3.11.17, but contains no decision reason or execution-category artifact. The
same-revision PR run passed in 156.58 seconds. Subsequent exact-revision CI
runs on 8b3d772 also passed. Those successes establish successful executions,
not an explanation of the earlier failure; its diagnosis remains open.

## New evidence for the next failure

Each worker execution now records controller-generated sequence, command count,
slot wait, container elapsed time, applied timeout, command limit, workflow
remaining allowance, and which deadline bounded dispatch. Categories distinguish
slot acquisition failure, exhausted workflow budget, container deadline expiry,
cancellation, invalid protocol, nonzero container exit and transport failure.
Validated observation status counts are recorded after successful protocol
validation. These records are additive to signed reports; they do not grant
readiness and cannot replace actual worker observations.

Requests CI diagnostic export explicitly allowlists those enums and finite,
bounded numbers. It excludes commands, filenames, source, stdout/stderr,
exception text, Docker context, credentials and arbitrary diagnostic fields.
Timing measures controller execution before cleanup; cleanup failures have
separate categories. Slot and container measurements cannot attribute elapsed
time to individual compile commands inside the worker. That remains a stated
measurement limitation rather than an inferred root cause.

## Demonstrated cleanup fault and fix

A synthetic fault-injection regression reproduced a separate controller issue:
if the bounded Docker removal call raised `TimeoutExpired`, the old sequential
`finally` skipped client termination and worker lease release, and replaced the
original execution exception with the cleanup exception. This is demonstrated
locally; it is not claimed as the cause of the historical C++ or Requests event.

Cleanup now makes one bounded removal attempt, always attempts client
termination/collection with a ten-second bound, and releases the lease in a
nested `finally`. It preserves an existing execution exception and records
sanitized cleanup failure categories. A cleanup failure after otherwise valid
execution raises instead of returning successful verification.

Because containers use Docker `--rm`, a nonzero removal exit can mean Docker
already removed a completed container. In that case one bounded, read-only,
exact-name listing must succeed and return no matching containers before cleanup
is accepted. Missing/malformed return codes, failed listings and retained
containers fail closed. This is an absence check, not a removal retry.
The worker object refuses further execution after any cleanup failure.

Operational disposition: quarantine the affected worker and inspect its Docker
context and matching container before operator reuse. Container absence remains
unverified if removal or listing fails. The in-process guard is not a persistent
cross-controller quarantine registry; operators must enforce that boundary
across restarts. No stronger persistent guarantee is claimed.

## Verification and publication boundary

Focused Docker-enabled verification passed **33 tests, no skips, in 8.08 seconds**:
worker telemetry, cleanup fault injection, malformed protocol, native fault
containment/recovery, signed insufficient reports and sanitizer behavior.
The new cleanup fault test was observed failing before the fix. Bandit found
no medium/high findings in the two changed worker/diagnostic modules.
An earlier Requests-only run in this batch passed two tests in 39.80 seconds;
that run preceded the final cleanup hardening and is not final-source acceptance.
The complete final-source suite is recorded separately by the coordinating
release verification. Passing final checks still do not close the historical
causal diagnoses. These changes are prepared for the single consolidated follow-up commit; external CI results are recorded separately against its exact revision.

The first follow-up combined run had 427 passes and one deterministic intake-order regression. Quarantine was inspected before input validation, breaking the existing secret-rejection boundary test. Validation was restored as the first step before state inspection and Docker contact; the original test and rejection policy were preserved. The corrected full-suite result is recorded separately. This regression is explained and distinct from the unexplained historical timeouts.

Corrected final-source verification: **428 Python tests passed with Docker enabled, zero skips, in 611.23 seconds**; the explained intake-order regression is resolved. Seven frontend tests and bundle consistency also passed. Current Bandit results retain 84 low findings and zero medium/high. Exact-revision GitHub CI and final artifact receipts are recorded separately after preparation; no external qualification or production acceptance is inferred. These dated receipts use 7 October UTC (8 October local time for the final handoff).
