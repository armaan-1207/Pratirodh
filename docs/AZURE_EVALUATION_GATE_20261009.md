# Azure evaluation execution gate — 9 October 2026 (Asia/Calcutta)

The requested completion target is 24 current signed qualifications and 216
verified campaign attempts with independent audit evidence. Neither milestone
was executed in this batch. CI-verified commit `984359d` remains the baseline.

## Fresh observations and mandatory stop

Read-only capture at 2026-10-08T18:40:27Z (9 October locally) found the model,
execution and audit VMs deallocated. All required capture inputs passed the
existing allocation/retail reconciliation. It calculated $34.28 in conservative
historical costs; adding the $2 reserve gives $36.28, exceeding the $35 cap by
$1.28 before further execution. This independent fresh estimate does not
replace the authoritative ledger. That ledger separately projects $48.816970
before reserve at 18:41:16Z and rejects stale observations.

Resource-group ActualCost returned seven daily rows in INR without a continuation
page. This is not complete USD cost evidence or a final invoice. Currency
conversion, current-day ingestion completeness and component reconciliation
remain unproven. Microsoft's [cost-data documentation](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/understand-cost-mgt-data)
describes delayed ingestion and rerating; do not assume every account has the
same ingestion interval. No conversion rate or missing cost was invented.

Under the agreed stop-at-cap rule, no execution window is available. No VM was
started, guard armed, ledger replaced or signing qualification fabricated.
Original ledger SHA-256 remains
`9226a05075fc447943f3a42b980fdef343fdd23493a9141d6f0219f7767c8fc6`.
Raw resource identities, captures and billing rows remain ignored locally in
`run_output/cloud-evaluation-capture-20261009/` and
`run_output/cloud-evaluation-billing-20261009/`.

## Remaining funding estimate

The cohort config sets a 172,800-second campaign envelope (48 hours), including
28,800 seconds of audit reserve, and 600 seconds per arm. The evaluation split
has 18 cases; two arms, two workflows and three repetitions produce 216 attempts.
The existing $0.60/hour full-group planning ceiling gives $28.80 for the 48-hour
envelope. Adding the fresh historical bound and shutdown reserve gives **$65.08**,
or **$30.08 above the approved cap**, before additional qualification/preflight
time, future noncompute charges or contingency on new work.

This is an illustrative planning subtotal, not a budget authorization, measured
runtime forecast, guaranteed minimum spend or complete funding request. Actual
execution may use less than the envelope. A complete request must add measured
qualification/pilot durations and separately priced future ancillary charges.
Even a single 600-second group window adds $0.10 at the planning ceiling and
does not fit the current fresh bound. The cap remains $35; no uplift is requested
or applied automatically.

## Verification and handoff

Budget, capture, reconciliation and preparation regressions: **65 passed in
5.88 seconds**. Preservation checked 1,264 original files and all 24 nested
repository heads with no differences. No executable controller changes were
made, so this batch does not claim a new combined Docker suite result.

The accompanying migration and input-contract design is not implemented or
approved execution support. Actual counters remain 0/24 qualifications and
0/216 attempts; 19 preparation cases remain blocked. Public deployment and
external operations activation stay deferred. Changes remain uncommitted.
