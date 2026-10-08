# Azure validation deployment

Historical setup record, prepared against the Azure for Students subscription on
2026-10-02. The recorded disposable deployment was created in resource group
`pratirodh-validation` and later deallocated. These records and price observations
are not current readiness or billing evidence. On 2026-10-07, a read-only Azure
inventory query confirmed all three named VMs are deallocated. Bounded strict
SSH probes could not reach the configured model or worker guests. The integrated
checkout has no current usage ledger, signed qualification index or frozen
execution manifest, so qualification and campaign execution remain blocked.
No Azure resources were started by these checks.

## Fresh budget evidence before another window

Capture current observations into a new ignored directory, from the integrated
repository root. This command only reads Azure and public retail quotes; it does
not start resources, arm a shutdown guard, create an allowance ledger or grant
execution authority:

```powershell
python tools/collect_azure_budget.py --output run_output/cloud-budget-capture-NEW
```

If Azure CLI is installed outside `PATH`, add `--az PATH_TO_INSTALLED_AZ_LAUNCHER`.
The collector refuses an existing output directory, unexpected VM/storage
inventory, potentially truncated allocation logs and allocation histories outside
the supported 89-day retention window. Each Azure request has a 120-second
timeout and at most one retry on timeout. Retail requests have 30-second timeouts,
bounded transient-error retries and at most 20 pages. Missing metrics or quotes
produce `BLOCKED_INCOMPLETE_CAPTURE`; partial files remain for diagnosis, and
`capture.json` is created only after the existing reconciliation checks pass.
Raw resource identifiers remain local and must stay outside release files.

For a completed capture, generate the dated conservative reconciliation report:

```powershell
python tools/reconcile_azure_budget.py --evidence run_output/cloud-budget-capture-NEW
```

This remains a retail estimate rather than an invoice. Before execution, the
operator must supply a reviewed `usage_ledger.json` for the explicitly approved allowance,
with current evidence bindings, recorded compute rates and shutdown reserve.
Do not initialize missing costs to zero or raise the allowance to make a window
fit. `execution_window` must load that ledger and acknowledge the independently
running guard before qualification or campaign work. A capture directory is not
an acknowledgement of the guard.

The smallest remaining sequence is: completed budget capture and reviewed ledger;
an explicitly authorized bounded VM start; current strict-SSH model and distinct
worker attestations; signed qualification of all 24 cases; frozen execution
manifest; then the equal-budget campaign. The previously recorded deallocated
inventory cannot satisfy current worker or qualification evidence.

On 2026-10-07 at 13:38 UTC, a fresh read-only capture completed all 16 inputs and
passed reconciliation. Its conservative retail upper bound was **$31.39**, plus
the required **$2 shutdown reserve**, exceeding the existing **$30 allowance**.
This is not an actual invoice. The current cloud lane is therefore blocked by
the former allowance as well as missing signed qualifications at that checkpoint. The complete raw
observations and hashes remain in the ignored operator directory
`run_output/cloud-budget-capture-20261007-followup/`. No ledger or guard was
created and no VMs were started. Review current metered billing and documented
conservative assumptions before considering a future execution window; do not
silently reset historical consumption or increase the approved limit.

Later on 2026-10-07, the operator explicitly approved a **$35 total ceiling**.
Tool defaults remain $30, existing $30 ledger caps stay $30, and values above
$35 or non-finite amounts are rejected. An uplift above $30 requires a verified,
evidence-bound allocation reconciliation; a legacy billing ledger cannot claim
the new allowance. The $2 shutdown reserve remains mandatory and hash-bound to
the reconciliation report.

The approved $35 ledger was initialized from the actual captured historical
upper bound of $31.39, the actual earliest VM creation time, all three recorded
compute rates and current evidence hashes. No consumption was reset to zero.
Elapsed time after the observation accrues at the existing $0.60/hour planning
ceiling even while VMs remain deallocated. The observation-time allowance was
$1.61 after the reserve (at most 9,660 seconds); inspect `window(load_ledger(...))`
again immediately before any guarded work because the remaining window shrinks.
No VM start follows automatically from collecting or reconciling this evidence.

Reproduce initialization from the retained capture into new output paths:

```powershell
python tools/reconcile_azure_budget.py --evidence run_output/cloud-budget-capture-20261007-followup --approved-usd 35 --report run_output/cloud-budget-capture-20261007-followup/reconciliation-approved35.json --write-ledger
```

Initialization refuses existing ledger/report output; it does not replace or
discard previous ledgers. The current local `usage_ledger.json` and raw evidence
remain ignored and excluded from publication. A future refresh requires review
of preserved prior consumption before replacing an existing ledger.

The disposable `pratirodh-validation` resource group contains three Ubuntu 24.04 VMs. `pratirodh-model` uses Standard_D4s_v4 (4 CPUs, 16 GiB) in East Asia. `pratirodh-execution` and `pratirodh-audit` each use Standard_B2als_v2 (2 CPUs, 4 GiB) in Central India. This respects the six-CPU per-region quota and subscription allowed-region policy. Southeast Asia was rejected by that policy. B1ms was unavailable.

Each VM has its own unpeered VNet, a 64-GiB Standard SSD, and a Standard static public IP. Password login is disabled. Inbound SSH is restricted to the operator's current public IP. All other inbound traffic is denied, including traffic from other VNet hosts. Model and Docker APIs remain local. Worker SSH additionally admits only the model VM public IP with a separate controller public key. No laptop private key is uploaded.

Resolve current addresses from the operator's Azure resource inventory. Machine-specific addresses, local SSH paths and host-key records remain in the ignored operator evidence directory:

| role | VM | public IP | SSH command |
|---|---|---:|---|
| model controller | `pratirodh-model` | `MODEL_PUBLIC_IP` | `ssh -i PATH_TO_OPERATOR_KEY pratirodh@MODEL_PUBLIC_IP` |
| execution | `pratirodh-execution` | `EXECUTION_PUBLIC_IP` | `ssh -i PATH_TO_OPERATOR_KEY pratirodh@EXECUTION_PUBLIC_IP` |
| final audit | `pratirodh-audit` | `AUDIT_PUBLIC_IP` | `ssh -i PATH_TO_OPERATOR_KEY pratirodh@AUDIT_PUBLIC_IP` |

Preserve the operator key fingerprint separately. The model controller passed Ollama/Qwen2.5-Coder 7B Q4_K_M preflight with runtime digest `sha256:0b0650a962dda61ec0598141ea11e3b688d225e926c9c00bc2c299d0ed34c4f8` and weights digest `sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`. The pinned worker image is `pratirodh-project-worker:0.2`; the execution digest is `sha256:b8386eea9d7bb2898e9e2a342232ddd220bef78c91b1576886b436f2065fa558` and the audit digest is `sha256:24be6e5fdc4850e26b87586e8baf25cabd3e623021b18e2aaa53e4163f1db8e4`. These attestations are copied to `run_output/azure-validation/attestations.json`.

The three VMs were deallocated after the image and runtime attestations were captured; their static IPs and disks remain in the resource group for a later approved campaign run.

Recorded setup quotes (2026-10-02): East Asia D4s_v4 Linux $0.264/hour; Central India B2als_v2 Linux $0.0246/hour each. Combined VM compute was $0.3132/hour ($3.7584 for 12 hours). Disks, three public IPs, and inter-region transfers were additional. The historical setup/pilot allowance was $10; a later $30 total allowance was explicitly raised to $35 by the operator on 2026-10-07 with all prior consumption preserved. These setup prices do not supersede fresh budget evidence. Do not upgrade the subscription. Azure budget alerts are not spending caps. Daily 23:30 India-time auto-shutdown is included; deallocate promptly after work because OS shutdown alone does not stop Azure compute billing. Storage/IP charges persist until resources are removed.

Generate local artifacts (the command performs no Azure write):

```powershell
python tools/prepare_azure_validation.py --operator-ip YOUR_PUBLIC_IP --public-key PATH_TO_OPERATOR_PUBLIC_KEY
```

Subscription validation, also without resource creation:

```powershell
az deployment sub validate --location eastasia --template-file run_output/azure-validation/subscription-template.json --parameters '@run_output/azure-validation/parameters.json'
```

The reviewed deployment was created after approval with:

```powershell
az deployment sub create --name pratirodh-validation --location eastasia --template-file run_output/azure-validation/subscription-template.json --parameters '@run_output/azure-validation/parameters.json'
```

Infrastructure readiness does not mean the upstream corpus is qualified. Case acquisition, pinned licensing, vulnerable/fixed reproduction, equal-budget comparison runs, independent audit evidence, and importing verified results into the published UI remain separate gates. The runner intentionally remains `BLOCKED_INTAKE` until all 24 cases pass those gates.

After evidence is copied out, stop billing with `az vm deallocate --resource-group pratirodh-validation --name <vm>`. Remove the disposable group only when the saved evidence bundle is no longer needed: `az group delete --name pratirodh-validation --yes --no-wait`.
