#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io python3-venv git curl ca-certificates cmake clang nodejs npm
systemctl enable --now docker
systemctl enable --now ssh.socket
usermod -aG docker pratirodh
install -d -o pratirodh -g pratirodh /home/pratirodh/validation
printf '%s\n' 'WORKER_RUNTIME_READY' >/home/pratirodh/validation/bootstrap-status
