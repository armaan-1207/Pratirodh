#!/usr/bin/env bash
# Run ONLY inside a new dedicated Ubuntu VM, after OS installation.
set -euo pipefail
if [[ $EUID -ne 0 || $# -ne 1 ]]; then
  echo 'Usage inside the dedicated VM: sudo bash bootstrap_ubuntu_worker.sh LOGIN_USER' >&2
  exit 2
fi
worker_user="$1"
id "$worker_user" >/dev/null
case "$(hostname -s)" in
  pratirodh-worker|pratirodh-audit) ;;
  *) echo 'Refusing: hostname must be pratirodh-worker or pratirodh-audit' >&2; exit 2 ;;
esac
. /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != 24.04 ]]; then
  echo 'This bootstrap targets a fresh Ubuntu 24.04 guest.' >&2; exit 2
fi
if command -v docker >/dev/null; then
  echo 'Docker already exists; preserving installation. Verify it manually.' >&2; exit 2
fi
apt-get update
apt-get install -y ca-certificates curl openssh-server
install -m 0755 -d /etc/apt/keyrings
curl --fail --show-error --silent --location --proto '=https' --tlsv1.2 \
  https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/pratirodh-docker.asc
chmod a+r /etc/apt/keyrings/pratirodh-docker.asc
if [[ -e /etc/apt/sources.list.d/pratirodh-docker.sources ]]; then
  echo 'Repository configuration already exists; inspect it manually.' >&2; exit 2
fi
cat > /etc/apt/sources.list.d/pratirodh-docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/pratirodh-docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
usermod -aG docker "$worker_user"
systemctl enable --now docker ssh
docker version
echo 'Bootstrap complete. Log out and back in to activate Docker group membership.'
echo 'Docker group membership grants administrative access INSIDE this dedicated VM.'
