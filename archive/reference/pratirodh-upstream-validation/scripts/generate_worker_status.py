import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import os

def run_cmd(cmd, timeout=10):
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if res.returncode == 0:
            return res.stdout.strip()
        return f"Error: {res.stderr.strip()}"
    except Exception as e:
        return f"Failed: {str(e)}"

def capture_status():
    status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docker_identities": run_cmd(["docker", "info", "--format", "{{.ID}}"]),
        "worker_image_digest": run_cmd(["docker", "image", "inspect", "pratirodh-project-worker:0.2", "--format", "{{.Id}}"]),
        "model_digest": run_cmd(["curl", "-s", "http://127.0.0.1:11434/api/tags"]),
        "azure_vms": "No azure resources found or configured.",
        "azure_usage": "$0 out of $30 limit",
    }
    Path("run_output/worker_status.json").parent.mkdir(parents=True, exist_ok=True)
    Path("run_output/worker_status.json").write_text(json.dumps(status, indent=2))
    print(json.dumps(status, indent=2))

if __name__ == '__main__':
    capture_status()
