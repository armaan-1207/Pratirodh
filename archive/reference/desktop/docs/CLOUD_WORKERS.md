# Cloud execution and model hosting

Cloud VMs can replace the two local VirtualBox guests. This setup has not yet
been provisioned or evaluated. A rented model server also changes the deployment
from laptop-local inference to self-hosted cloud inference; record that distinction
in reports rather than describing it as offline laptop execution.

Use two separate Ubuntu 24.04 VMs and Docker daemons, named `pratirodh-worker`
and `pratirodh-audit`. For x86 workers, start with at least 2 vCPUs, 4 GB RAM and
40 GB disk each. They can share a cloud provider but must remain separate guests.
The final audit files and developer fixes must remain outside the execution
worker and model prompts. Do not use a GPU Pod container as a substitute for
the two independent worker VMs.

## Provider choices and account setup

As checked on 2026-10-02, [Oracle's Always Free documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
lists 2 Ampere A1 OCPUs and 12 GB RAM total for Always Free tenancies. This can
be split into two 1-OCPU guests. These are Arm machines, so rebuild all worker
images and project dependencies for Arm, set each manifest's CPU limit to one,
and verify each case's architecture compatibility. It supplies no free GPU;
capacity, account eligibility and successful case execution are not guaranteed.

A paid alternative is two small x86 cloud VMs and a separately rented model GPU.
[Runpod's current pricing](https://www.runpod.io/pricing) lists an RTX A5000 with
24 GB VRAM at $0.27/hour and an RTX A6000 with 48 GB VRAM at $0.53/hour.
Twelve active hours therefore cost $3.24 or $6.36 for GPU compute alone.
Worker VMs, storage, network and taxes are additional; confirm the selected
instance's actual price and availability before provisioning. These estimates
do not promise completion of the evaluation within twelve hours.

The operator must create the provider account, complete any verification and
approve a total spending cap before billable resources are created. Keep
passwords, payment information, API tokens and private keys out of chat.
University credits can cover the same architecture if available.

### GitHub Student Developer Pack

As checked on 2026-10-02, the [current Student Developer Pack](https://education.github.com/pack)
includes Microsoft Azure's $100 student credit and Camber's Student plan with
40 CPU hours, 5 GPU hours, 50 GB storage and 50 agent messages per month.
[Azure for Students](https://azure.microsoft.com/en-us/free/students/) requires
student verification and no credit card; its $100 credit is valid for twelve
months. Use the account's available VM sizes and quotas to determine whether it
can host the two workers. Credit alone does not guarantee GPU availability.

Camber's GPU allowance is a candidate for model smoke checks, but its job APIs,
hardware, model-serving permissions and runtime provenance still need review
before integration. Five GPU hours cannot guarantee completion of the full
campaign. Azure credit cannot pay for a different provider's GPU rental.

On 2026-10-02, the operator's Azure Education hub showed an active Azure for
Students subscription with all $100 credit available, expiry 2027-10-02, and
$0 usage. Its allowed-region policy listed Central India, East Asia, Korea
Central, India South Central and Malaysia West. These are account observations,
not a promise of regional capacity or GPU quota.

The first worker draft uses Ubuntu 24.04 x64, Trusted Launch, B2als v2 (2 vCPUs,
4 GiB), a 64 GiB Standard SSD LRS disk and East Asia. The public
[Azure retail price API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices)
reported Linux B2als v2 at $0.0526/hour there: two workers for twelve active hours
cost approximately $1.26 in compute alone. This family is burstable; measure
CPU credit throttling and execution latency before using it for the campaign.
The E6 LRS disk meter was $4.80/month
per disk, with separate operations charges. Public IPs and outbound traffic may
also cost credit. D2s v6 failed preflight because East Asia Dsv6 quota was zero;
the quota page showed Basv2 quota 10 and DSv4 quota 4. B2als v2 subsequently
passed the VM quota check. The portal's price/legal-term retrieval failed;
the final firewall draft passed preflight too. Spending/terms authorization and
actual provisioning remain pending. No VM has been created. The draft has an explicit NSG with
no custom inbound allow rules and auto-shutdown at 23:59 India Standard Time.
Keep the two guests on separate unpeered networks and restrict
SSH to the controller IP after authorization; model and Docker services must
not have public inbound ports.

GitHub accepts a current dated student ID or other enrollment evidence, subject
to its academic-email requirements. Apply through [GitHub Education](https://docs.github.com/en/education/about-github-education/github-education-for-students/apply-to-github-education-as-a-student)
and submit proof to GitHub, not to this project or chat. The old DigitalOcean
$200 Student Pack promotion is no longer available after July 31, 2026, according
to [GitHub's partner changelog](https://github.com/github-education-resources/Student-Developer-Pack-Current-Partners-FAQ/blob/main/SDP-changelog.md).

## Worker provisioning and verification

1. Add only the controller's dedicated SSH **public** key to each guest. Restrict
   inbound SSH to the controller's public IP. Do not expose Docker's TCP socket.
2. Verify each SSH host fingerprint through the provider's trusted console before
   recording it locally. Configure the existing `pratirodh-worker` and
   `pratirodh-audit` SSH aliases with their actual addresses. Preserve the previous
   VirtualBox aliases under different names if retaining that setup.
3. Set the matching hostname, create the `pratirodh` user and run
   `scripts/bootstrap_ubuntu_worker.sh pratirodh` as root inside each fresh guest.
   Inspect partial provisioning rather than blindly rerunning the bootstrap.
4. Run `scripts/connect_workers.ps1` to verify distinct daemons and register the
   two Docker contexts. Inspect any existing contexts before updating them; the
   helper deliberately refuses replacement.
5. Build the worker image separately in each context, record its real image ID,
   prepare case dependencies, and freeze the project and audit manifests. Target
   execution retains the existing network and container restrictions.

## Model serving and remaining implementation

The current model client accepts loopback HTTP endpoints and pins local runtime
artifacts. It has no completed cloud provisioning or remote-runtime attestation
adapter. Connecting to a self-hosted model through an SSH tunnel requires a
reviewed extension that records the actual remote runtime, model weights,
quantization, resources and latency; do not reuse the Windows runtime hash to
claim a Linux server's identity. Expose model inference only through an
authenticated private connection, keeping it separate from the audit worker.

Start by comparing the existing 7B baseline with the selected candidate on the
same cases. A larger GPU permits larger models, but it does not establish higher
security-repair accuracy. Only independently audited results can establish that.

Stop GPU compute when it is idle and inspect storage charges. Many cloud VMs
continue billing when powered off; remove rented resources only after preserving
needed evidence and obtaining authorization for that deletion.
