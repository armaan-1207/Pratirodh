# Cloud budget review — 7 October 2026

Read-only Azure capture at 2026-10-07T17:58:36.107618+00:00 produced a **$31.79 retail modeled upper bound**, including the existing 15% contingency. This is not invoiced billing, a new allowance, or authorization to start resources.

At 2026-10-07T18:00:46.172511+00:00, the existing evidence-bound $35 ledger projected **$34.0119** under its unchanged full-rate accrual contract. Preserving the greater bound and the $2 shutdown reserve requires **$36.0119**, above the approved $35 total. The ledger also fails freshness validation: `refresh Azure cost and resource observations before another window`.

The difference is explained by the existing ledger charging every hour after its earlier observation at $0.60/hour, including deallocated time. The new allocation-based estimate is lower; it cannot automatically reset prior accrual or replace the authoritative ledger. Deallocation also retains disk, IP and storage charges. No ledger field, cost anchor, allowance, reserve or resource was changed.

Execution remains **BLOCKED**. A reviewed authoritative billing/allocation reconciliation preserving prior consumption is required; if that cannot satisfy the existing cap, retain deallocation and report partial progress. Do not use a new path, a fresh ledger, a retail estimate or a stale qualification as a bypass. No resource start, signing of qualification or campaign execution occurred.

The source catalogue still records 24 cases, five structurally prepared and 19 intake blockers. Runtime qualification remains 0/24 and the independent campaign 0/216. Earlier automatically rejected harness work remains outside this batch.

Ignored receipts: `run_output/final-cloud-readonly-20261007/`, `run_output/final-cloud-budget-review-20261007.json`. The read-only review binds the existing ledger SHA-256 `9226a05075fc447943f3a42b980fdef343fdd23493a9141d6f0219f7767c8fc6`. Raw resource identifiers and billing captures stay outside release files.

At the capture timestamp, all three observed VM states were `VM deallocated`. This is a dated read-only observation, not continuous monitoring.
