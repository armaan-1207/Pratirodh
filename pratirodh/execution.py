import json
from pathlib import Path
import subprocess
import time
import uuid
import threading

IMAGE = "pratirodh-runner:0.1"
SLOTS = threading.BoundedSemaphore(2)


class Budget:
    def __init__(self, seconds=300, max_model_calls=4):
        self.start = time.monotonic()
        self.deadline = self.start + seconds
        self.model_calls = 0
        self.max_model_calls = max_model_calls

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("run time budget exhausted")
        return remaining

    def model_call(self):
        self.remaining()
        if self.model_calls >= self.max_model_calls:
            raise TimeoutError("model call budget exhausted")
        self.model_calls += 1


class DockerExecutor:
    def __init__(self, image=IMAGE):
        self.image = image
        self._identity = None

    def identity(self):
        if self._identity:
            return self._identity
        result = subprocess.run(["docker", "image", "inspect", self.image, "--format", "{{.Id}}"],
                                capture_output=True, text=True, timeout=10, check=True)
        self._identity = result.stdout.strip()
        return self._identity

    def batch(self, sources, contract, cases, budget):
        name = "pratirodh-" + uuid.uuid4().hex
        runner = Path(__file__).parent.resolve()
        # Private ephemeral container tmpfs; this is not a host temporary path.
        tmpfs_mount = '/tmp:rw,noexec,nosuid,size=128m,mode=1777'  # nosec B108
        command = ["docker", "run", "--rm", "--name", name, "--network", "none",
                   "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                   "--pids-limit", "64", "--cpus", "2", "--memory", "2g", "--user", "65534:65534",
                   "--tmpfs", tmpfs_mount,
                   "--mount", f"type=bind,source={runner},target=/runner,readonly", "-i", self.image]
        payload = dict(sources=sources, cases=cases, fixtures=contract["fixtures"],
                       symlinks=contract.get("symlinks", {}), version=contract['version'],
                       profiles=contract.get('profiles', {'default': {}}),
                       observed_files=sorted({n for a in contract['assertions'].values() for n in a.get('absent_files', [])}))
        timeout = min(budget.remaining(), (10 * len(cases) if contract['version'] == 2 else 20) * len(sources) + 10)
        try:
            if not SLOTS.acquire(timeout=budget.remaining()):
                raise TimeoutError('container capacity unavailable')
            try:
                result = subprocess.run(command, input=json.dumps(payload), text=True,
                                        encoding="utf-8", capture_output=True,
                                        timeout=min(timeout, budget.remaining()))
            finally:
                SLOTS.release()
            if result.returncode:
                raise RuntimeError("Docker execution failed (exit " + str(result.returncode) + "): " + result.stderr[-1000:])
            outputs = json.loads(result.stdout)
            if not isinstance(outputs, list) or len(outputs) != len(sources):
                raise RuntimeError("executor result count mismatch")
            return outputs
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("container execution timeout") from exc
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=10)

