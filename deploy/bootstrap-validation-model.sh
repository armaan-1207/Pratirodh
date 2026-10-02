#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
export HOME=/root
apt-get update
apt-get install -y python3-venv git curl ca-certificates zstd openssh-client
systemctl enable --now ssh.socket
install -d -o pratirodh -g pratirodh /home/pratirodh/validation
if ! command -v ollama >/dev/null; then
    curl -fsSL https://ollama.com/install.sh -o /home/pratirodh/validation/install-ollama.sh
    sha256sum /home/pratirodh/validation/install-ollama.sh >/home/pratirodh/validation/install-ollama.sha256
    bash /home/pratirodh/validation/install-ollama.sh
fi
systemctl enable --now ollama
ollama pull qwen2.5-coder:7b
ollama --version >/home/pratirodh/validation/ollama-version.txt
sha256sum "$(command -v ollama)" >/home/pratirodh/validation/ollama-runtime.sha256
ollama list >/home/pratirodh/validation/models.txt
free -m >/home/pratirodh/validation/memory.txt
printf '%s\n' 'MODEL_INSTALLED_PREFLIGHT_PENDING' >/home/pratirodh/validation/bootstrap-status
