# Cloud and local worker setup

The active Azure setup is documented in [Azure validation](../deploy/AZURE_VALIDATION.md).
It has a model/controller VM and separate execution and final-audit VMs. The
recorded setup completed model and image preflight, then deallocated the three
guests. Infrastructure preparation does not qualify the upstream cases or
establish model repair accuracy. Read current power state and runtime evidence
before a campaign instead of treating past attestations as current readiness.

The alternative local VirtualBox setup is documented in [Linux workers](LINUX_WORKERS.md).
Its recorded clock and boot problems remain unresolved. Local and cloud workers
use the same reviewed project manifests and immutable execution policy.

## Worker separation

- Use distinct Linux guests and Docker daemons for execution and final audit.
- Keep audit definitions and upstream reference fixes outside model-visible source.
- Restrict SSH to approved controller addresses. Keep Docker and model APIs local.
- Preserve host fingerprints, pinned images, runtime and weights digests, and
  dependency inventories in the ignored operator evidence directory.
- Prepare dependencies before target execution. Containers receive no external
  network, controller mounts, signing keys or Docker socket.

The cloud model/controller can run the existing loopback Ollama client directly
on Linux. A laptop SSH tunnel alone cannot establish the identity of a remote
runtime. Do not substitute a Windows executable hash for the Linux runtime.

## Local preparation helpers

`scripts/prepare_local_model.py` explicitly prepares pinned local model artifacts.
Repair runs never download weights. The VM/media helpers named in the Linux
worker guide prepare local guests only when explicitly invoked. They are an
alternative to the Azure setup, not prerequisites for it.

## Budget and shutdown

Confirm remaining credit and the authorized total allowance before restarting
billable resources. Budget alerts and operating-system shutdown are not compute
deallocation. `tools/azure_validation_guard.py` provides a timed deallocation
backstop. Disks and reserved public IPs can continue billing while VMs are
deallocated. Preserve signed evidence before separately authorized deletion.
