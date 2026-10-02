# Azure validation deployment

Prepared against the Azure for Students subscription on 2026-10-02. The approved disposable validation deployment was created in resource group `pratirodh-validation`.

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

Live Azure Retail Prices API quotes: East Asia D4s_v4 Linux $0.264/hour; Central India B2als_v2 Linux $0.0246/hour each. Combined VM compute is $0.3132/hour ($3.7584 for 12 hours). Disks, three public IPs, and inter-region transfers are additional. Use a $10 operating allowance for setup and pilot; do not upgrade the subscription. Azure budget alerts are not spending caps. Daily 23:30 India-time auto-shutdown is included; deallocate promptly after work because OS shutdown alone does not stop Azure compute billing. Storage/IP charges persist until resources are removed.

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
