# CI causal review — 8 October 2026

This review distinguishes a passing release candidate from an explained historical
failure. Read-only GitHub API collection reconfirmed both historical logs and the
absence of retained Actions artifacts. No workflow was dispatched, publication
performed, timeout increased, expectation relaxed, or automatic retry introduced.

## Historical Requests failure

The failed push run [37632194569](https://github.com/armaan-1207/Pratirodh/actions/runs/37632194569)
and passing PR run [37632202872](https://github.com/armaan-1207/Pratirodh/actions/runs/37632202872)
both identify candidate `65a0e9210b577af767425b0df7abdcd4ac4fa9ed`, runner
image **20261004.327.1**, Ubuntu **24.04.5**, runner **2.337.0**, and Python
**3.11.17**. The push's 292 passes / one failure took 447.59 seconds; the PR's
293 passes took 156.58 seconds. The provisioned hosts were in different regions,
but these logs do not prove host contention, network conditions, or geography
caused the mismatch. Pinning a runner-image label alone cannot be claimed to fix
this incident: the recorded image version already matched.

The failing assertion proves that the reference-fix result was
`INSUFFICIENT_EVIDENCE` instead of `READY_FOR_REVIEW`. The log contains no report
reason, failed command category, worker timing, immutable runtime image ID, or
decision artifact. The historical result therefore cannot be classified as a
specific timeout or missing configuration. Its root cause remains **UNEXPLAINED**.

Retained log SHA-256 values, reconfirmed by download:

- Failure: `ce95e7c58aa54cee528176ec9a499a3382bf704720cdc9d1c227febf94c33f7e`.
- Success: `495c2217d122f9eac9c1d403fdbe6b66a868d98c9151597d8e7283bf873d83d3`.

Raw logs stay in ignored local acquisition storage. Release documentation contains
only allowlisted observations, never raw target sources or credentials.

## Historical local C++ failure

The retained JUnit record for `test_real_multi_file_end_to_end[repair-cpp]`
records 463.843 seconds for the test and 463.656 seconds for the report.
The report classifies the failure as `BUDGET_EXHAUSTION` with a worker-container
timeout. Its last execution stage, "Independently verify", began at 18.671
seconds; signed insufficient evidence was produced at 463.656 seconds.
This narrows the observed delay to independent verification, without proving
whether launch, compilation, host scheduling, or deadline enforcement caused it.
The historical report has no per-dispatch timing to resolve that ambiguity.
This was a **local Docker suite incident**, not an observed GitHub C++ failure.

## Closing the measurement gap

The Requests test already exports sanitized signed-report decisions, reasons,
check statuses, and controller worker timing. The multi-language end-to-end test
now exports the same allowlisted summary for each workflow/language before its
readiness assertion. Its assertion no longer dumps the raw report into CI logs.
The failure-only Actions upload includes all JSON files in this dedicated
diagnostic directory, using seven-day retention. No generic evidence store,
JUnit tracebacks, command output, project source, signing keys, or arbitrary
exception text is uploaded.

Focused tests prove a sanitized artifact exists on both success and failing
readiness decisions; the failed assertion retains the worker deadline category
without private strings. A controller exception before a report is returned
still lacks a report artifact. Such exceptions remain CI failures; this change
does not invent successful evidence or replace an exception with a decision.

Acceptance of the current candidate and causal closure are separate:
`93b713e845f8f368232ae031a13f08af83ef592d` passed both GitHub CI runs with 428
Python tests and seven frontend tests, while these older incident causes remain
unexplained. The next failing dispatch must supply the newly available timing
and category evidence before a concrete remediation is claimed.

Local verification of this follow-up: **21 focused diagnostic tests passed in
4.32 seconds**. The affected real Docker C++ repair test passed once in **92.50
seconds**, with zero skips and a sanitized `project-repair-cpp.json` artifact.
This is verification of artifact plumbing and the current successful execution;
it is not a retry policy or an explanation of the older timeout.
