# Two Linux workers on Windows

The full evaluation needs two independent Linux guests and Docker daemons. Docker
Desktop aliases and two distributions sharing a WSL kernel do not establish this
separation. Both guests can run in VirtualBox on the same physical laptop; this
separates guest kernels but does not provide two independent physical hosts.

The selected names are `pratirodh-worker` and `pratirodh-audit`. Neither guest
receives Windows shared folders, the controller SSH private key, the evidence
signing key, clipboard sharing or the controller Docker socket. SSH forwarding
is bound to Windows loopback ports 2222 and 2223. Network access is used for OS
and dependency preparation; target containers execute with no network.

Current laptop setup status: the execution guest has Ubuntu installed, but
VirtualBox 7.2.4 over the Windows Hyper-V backend still shows repeated clock
delays and SSH command timeouts. Switching between the observed single-CPU
clock configurations has not established a reliable worker. Its state is saved;
the audit guest remains uninstalled. Neither is ready for release evaluation.
Do not treat the workaround configuration below as a verified solution. See
[cloud workers](CLOUD_WORKERS.md) for an alternative that preserves separate
guest kernels without relying on this laptop's VirtualBox backend.

## Prepare the machines

Install [VirtualBox](https://www.virtualbox.org/wiki/Downloads) if it is absent.
Its Windows installer requires administrator approval. Download an Ubuntu 24.04
Server ISO from [Ubuntu](https://releases.ubuntu.com/24.04/) and verify its SHA256
against the publisher's checksum file before use. Keep installation media and
guest disks under the ignored `run_output/linux-workers` directory.

`python scripts/prepare_worker_media.py` downloads the pinned Ubuntu 24.04.5
Server ISO, checkpoints completed transfer ranges, and verifies the complete
publisher SHA256 before making the ISO available. It executes no downloaded code.

From the project directory, review the proposed commands, then create the guests:

```powershell
python scripts/create_worker_vms.py --iso run_output/linux-workers/media/ubuntu-24.04.5-live-server-amd64.iso
python scripts/create_worker_vms.py --iso run_output/linux-workers/media/ubuntu-24.04.5-live-server-amd64.iso --apply
python scripts/install_worker_vms.py --iso run_output/linux-workers/media/ubuntu-24.04.5-live-server-amd64.iso
```

Each guest has 1 CPU, 3 GB RAM and a dynamically allocated 40 GB disk. One CPU
and disabled guest paravirtualized clocks avoid the CPU timing lockup observed
with VirtualBox 7.2.4 running over this laptop's Windows Hyper-V compatibility
backend. The installer uses `nomodeset` for a text console. This changes guest
configuration without disabling Windows virtualization or existing Docker.
IO-APIC is disabled for these single-CPU guests after the installed Ubuntu kernel
reported an IO-APIC timer panic on this compatibility backend.
The setup
refuses to overwrite existing guests or SSH credentials. Unattended preparation
creates a dedicated Windows SSH key and appends the two aliases to `.ssh/config`.
It generates a random installation password without printing or persisting the
plaintext. SSH accepts the controller public key and disables password login.
The installation uses original cloud-init configuration; Guest Additions are not
installed. Provisioning failures remain failures and require inspection.

Start **one guest at a time** through VirtualBox's normal interface to install
Ubuntu. Free at least 4 GB host RAM before starting one guest. The installer
powers off after installation. Start the installed guest again and wait for
cloud-init to install Docker from its signed official Ubuntu repository. This
can take several minutes. Open its console to inspect boot/provisioning errors.
For both guests together plus local model generation, reserve sufficient host
memory; 16 GB laptops may require sequential execution and reduced model context.
Do not stop unrelated containers or VMs to reclaim memory automatically.

## Verify host keys and connect

In each guest's console, obtain the SSH host fingerprint using:

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

From a Windows terminal, make the initial connections:

```powershell
ssh -o StrictHostKeyChecking=ask pratirodh-worker
ssh -o StrictHostKeyChecking=ask pratirodh-audit
```

Compare the displayed fingerprints with the corresponding console fingerprints
before accepting them. The setup deliberately does not automatically trust a
host-key scan. After boot, `docker info` must work as the `pratirodh` guest user;
Docker group membership grants administrative access inside that dedicated VM.
If required, log out and back in after provisioning finishes.

Register and verify the separate daemons without changing the active context:

```powershell
powershell -File scripts/connect_workers.ps1
pratirodh project build-worker --context pratirodh-worker
pratirodh project build-worker --context pratirodh-audit
```

Record the actual image IDs and prepared dependencies in project/audit manifests.
The connection script rejects matching daemon IDs and the local shared daemon.
This is connection verification; an operator still needs to attest the guest
isolation and provenance. Build upstream dependencies in controlled preparation,
then freeze their images. Do not mount upstream benchmark images containing
developer fixes into generation. The final audit files remain controller-side
until they are sent to the independent audit worker.

## If automatic provisioning fails

Install Ubuntu Server manually in each **new** guest using the matching hostname,
a `pratirodh` login, and OpenSSH Server. Add only the generated public key to that
user's `~/.ssh/authorized_keys`. Copy `scripts/bootstrap_ubuntu_worker.sh` into
the guest, then run `sudo bash bootstrap_ubuntu_worker.sh pratirodh`. Preserve
existing machines and inspect partial guests rather than deleting them silently.

Docker installation follows its [official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/).
SSH Docker contexts follow [Docker's SSH connection documentation](https://docs.docker.com/engine/security/protect-access/).
