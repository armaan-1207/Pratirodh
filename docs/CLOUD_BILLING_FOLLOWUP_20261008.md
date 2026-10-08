# Cloud billing follow-up — 8 October 2026 (Asia/Calcutta)

## Current execution gate

At 2026-10-08T06:18:05Z, the unchanged evidence-bound ledger projected
**$41.385162 plus the $2 reserve: $43.385162**, exceeding the $35 approval.
This is the controller's conservative planning accrual, **not an observed bill**:
its existing contract charges every hour after the recorded anchor even when
VMs are deallocated. `window()` also rejected the stale observation, so there
is no authorized execution window. The local receipt is
`run_output/final-followup-review-20261008/budget-contract-review.json`.
No ledger reset, alternative ledger, allowance increase or resource start was
performed. Metered reconciliation remains necessary before any reviewed
accounting migration; a lower partial bill cannot authorize spending by itself.

A later read-only power-state observation at 2026-10-08T05:27:47Z again found
all three approved VMs deallocated. The existing ledger hash remained
unchanged. This power-state observation does not refresh cost evidence, arm a
guard or authorize a qualification window. Its ignored receipt is
`run_output/current-cloud-deallocation-20261008.json`.

## Appendix — fresh capture and actual-cost review (8 October 2026)

The subsequent read-only capture completed at **2026-10-07T19:55:46Z** with
all three approved VMs deallocated. Its allocation and retail reconciliation
produced a **$31.99** modeled upper bound. Adding the mandatory **$2.00**
shutdown reserve gives **$33.99** against the approved **$35.00** ceiling.
This is a planning result, not an invoice or spending authorization; the
capture status is `REVIEWED_LEDGER_REQUIRED` and it did not create or update
the ledger.

The earlier resource-group Cost Management response returned six daily
`ActualCost` rows in **INR**. It proves that the query returned data, but does
not prove complete allocation history, a final invoice, an accepted USD
conversion, or current-day completeness. Azure ingestion delay and rerating
remain applicable. A lower fresh retail estimate cannot reset the earlier
ledger anchor: the controller preserves prior consumption and charges the
reconciled anchor forward at its recorded rate. Deallocated VMs also retain
disk, public-IP and storage charges.

The safe refresh path is read-only until review: run
`tools/collect_azure_budget.py` into a new directory with `--approved-usd 35`,
then run `tools/reconcile_azure_budget.py --evidence <capture>
--approved-usd 35` without `--write-ledger`. Independently bind complete
metered costs, currency conversion evidence, allocation intervals,
noncompute charges and ingestion headroom while preserving the old anchor and
reserve. The current CLI refuses to overwrite an existing ledger and
`window()` refuses stale observations, so no command safely or silently lowers,
replaces or resets `usage_ledger.json`. Only an explicitly reviewed ledger
migration could proceed after that evidence review.

The authoritative ledger remains unchanged at SHA-256
`9226a05075fc447943f3a42b980fdef343fdd23493a9141d6f0219f7767c8fc6`.
Qualification and the campaign remain blocked pending that reconciliation.

The read-only capture observed the three approved VMs deallocated at
2026-10-07T19:02:46.616266Z. Its new retail modeled upper bound is $31.89,
including the existing 15% contingency. No resource was started, guard armed,
ledger replaced or qualification signed.

A separate resource-group-scoped [Azure Cost Management Query API](https://learn.microsoft.com/en-us/rest/api/cost-management/query/usage?view=rest-cost-management-2025-03-01)
request successfully returned six daily ActualCost rows for 2–7 October, in INR,
with no continuation page. The raw response, resource identities and capture
inputs remain in ignored local output. This closes the question of whether
metered cost data can be retrieved; it does not establish a final invoice,
complete current-day usage or a USD spending authorization.

[Microsoft documents ingestion delay and possible rerating](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/understand-cost-mgt-data).
The response provides no independent completeness watermark or accepted
billing-currency conversion evidence. An assumed exchange rate, lower partial
bill or fresh retail estimate cannot erase prior consumption.

At 2026-10-07T19:05:18.216313Z, the original ledger projected $34.657247 before
the $2 shutdown reserve: $36.657247 total, exceeding the $35 allowance.
It also failed the four-hour observation freshness check. The authoritative
ledger SHA-256 remained
`9226a05075fc447943f3a42b980fdef343fdd23493a9141d6f0219f7767c8fc6`.
Neither a new ledger path nor refreshed observations were used to bypass that
contract. Qualification and campaign remain 0/24 and 0/216.

To unblock cloud execution within the existing approval, a reviewed
reconciliation must bind complete allocation history, reported metered costs,
the billing/pricing currency conversion evidence and conservative ingestion
headroom, explicitly preserving prior consumption. If its bound plus reserve
does not fit $35, retain deallocation and partial results. No such reviewed
replacement was manufactured in this batch.

Local operations/cloud regression tests passed **119 tests in 23.48 seconds**.
These cover backup/restore, external activation preflight, sanitized alerting,
budget and capture contracts; they do not activate external operations or
prove cloud runtime qualification. Ignored receipts are
`run_output/parallel-operations-cloud-20261008.xml` and
`run_output/parallel-cloud-20261008/`. Public deployment and operator activation
remain deferred by the user's instruction.
