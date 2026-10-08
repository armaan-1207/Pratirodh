# Upstream blocker decisions — 8 October 2026

The read-only metadata review found no demonstrated mapping or overlay defect
that would safely remove the 19 preparation blockers. All 24 source-index entries
match their per-case metadata and recipe revisions; all 49 captured overlay
hashes match the original bytes. There are 34 declared source mappings and 24
approved license metadata records. This checks metadata consistency, not a new
independent license approval or runtime behavior. The development/evaluation
split remains 6/18.

The existing reconstruction receipt remains the source for the case-specific
intake conflicts below: `run_output/upstream-parallel-20261007/result.json`,
SHA-256 `8e588a0349b18ae2fbe5a715a0e8c8f9885fc8b85f25d90fd9a5500b385589f7`.
It records 5 prepared, 19 blocked, and qualification `NOT_RUN` for every case.
This review did not reconstruct another snapshot, execute a harness, alter an
acquisition, contact cloud workers or change controller limits.

## Case disposition and required decision

Every row remains **BLOCKED**. Asset means an independently reviewed, bounded,
hash-bound immutable fixture channel; quota means a reviewed source-selection
contract or controller resource contract, with reproducibility and security
tests. Neither decision is implemented by this review. Private-material fixtures
need their own explicit policy and cannot enter the present intake contract.

| Case | Existing intake conflicts | Required decision before another preparation attempt |
| --- | --- | --- |
| cpp-cve-2018-25032 | 11 non-UTF-8 inputs | Asset channel |
| cpp-cve-2019-1000019 | Non-UTF-8 input, oversized input, 1,018 files, 14,380,114 bytes | Asset channel and quota contract |
| cpp-cve-2020-12762 | 20 upstream links, non-UTF-8 expected result | Explicit link representation and asset channel |
| cpp-cve-2022-43680 | README link, 4 oversized inputs, 86,643,516 bytes | Link representation and quota contract |
| cpp-cve-2023-4863 | 4 non-UTF-8 inputs, 2 oversized inputs | Asset channel and quota contract |
| cpp-cve-2023-50472 | Non-UTF-8 Unity PDF | Asset channel |
| cpp-cve-2024-25062 | 2 links, 140 non-UTF-8 inputs, 4 oversized inputs, 4,068 files, 27,817,926 bytes | Link representation, asset channel and quota contract |
| javascript-cve-2018-6835 | 11 non-UTF-8 inputs | Asset channel |
| javascript-cve-2019-10767 | Credential/private-key fixtures, 20 non-UTF-8 inputs | Private-fixture policy and asset channel |
| javascript-cve-2021-37712 | 5 links, 2 non-UTF-8 inputs, 2 oversized inputs, 23,160,729 bytes | Link representation, asset channel and quota contract |
| javascript-cve-2024-56334 | 39 non-UTF-8 assets | Asset channel |
| python-cve-2018-18074 | 2 non-UTF-8 assets, oversized input | Asset channel and quota contract; reduced Requests demo does not qualify this case |
| python-cve-2018-7750 | Credential/private-key fixtures, 3 non-UTF-8 inputs | Private-fixture policy and asset channel |
| python-cve-2020-25459 | Credential fixture, 154 non-UTF-8 inputs, 15 oversized inputs, 2,096 files, 72,113,310 bytes | Private-fixture policy, asset channel and quota contract |
| python-cve-2021-21330 | Credential fixtures, 6 non-UTF-8 inputs | Private-fixture policy and asset channel |
| python-cve-2021-32633 | 205 non-UTF-8 inputs, 15,180,615 bytes | Asset channel and quota contract |
| python-cve-2021-33203 | 4 links, 1,321 non-UTF-8 inputs, 6,385 files, 39,345,378 bytes | Link representation, asset channel and quota contract |
| python-cve-2022-0767 | 265 non-UTF-8 inputs, oversized input, 18,658,255 bytes | Asset channel and quota contract |
| python-cve-2025-43859 | 2 non-UTF-8 assets | Asset channel |

Links must not be followed implicitly or replaced by arbitrary external content.
Removing binaries, interpreting private keys as ordinary source, increasing
limits merely to obtain a passing result, or silently dropping upstream assets
would invalidate the present source contract. Acquisition contents stay intact.

The 5 structurally prepared cases remain libyaml (`cpp-cve-2014-9130`), tree-kill
(`javascript-cve-2019-15599`), handlebars (`javascript-cve-2021-23369`),
cors-anywhere (`javascript-cve-2021-23664`) and opened
(`javascript-cve-2021-29300`). Previously rejected additional harness edits for
these projects remain deferred: automatic safety review cited possible
cybersecurity risk. They were not retried or attempted through another route.
Structural preparation does not make those edits authorized or those cases
runtime-qualified. Current signed qualifications remain 0/24; campaign 0/216.

## Verification in this review

`tests/test_reconstruct_targets.py`, `tests/test_preparation.py` and
`tests/test_requests_preparation.py`: **29 passed in 15.84 seconds**. These include
temporary-directory preservation, overwrite refusal, binary retention, quota
diagnostics and link non-traversal checks. The tests do not execute the rejected
upstream harness work. Current read-only audit receipt:
`run_output/upstream-resolution-final-20261008.json` (generated and excluded from
release files).

The first metadata audit incorrectly normalized CRLF before comparing raw-byte
hashes, yielding two false mismatches; its receipt is retained for history. The
corrected review uses original bytes and reports zero mismatches. No overlay or
expected hash was changed to obtain that result.

For the agreed local candidate, keep the full upstream evaluation milestone
unfinished and retain these blockers. Public production readiness cannot be
inferred from local example or static preparation results.
