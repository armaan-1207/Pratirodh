# PRATIRODH

A Derby University hackathon project exploring evidence-based security repair with local AI. This is a research prototype for trusted, registered fixtures and human review.

PRATIRODH proposes security repairs and produces signed evidence for human review. It detects candidate findings, reproduces a declared violation, challenges each proposed repair with legitimate requests and security checks, and records failures and missing evidence. Approval is a separate human action; source files are never replaced automatically.

## Setup on Windows, macOS, and Linux

Install Git, Python 3.11 (the measured environment used 3.11.9), and Docker. On Windows use [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) with Linux containers; on macOS use the [installer matching your Mac](https://docs.docker.com/desktop/setup/install/mac-install/). On Linux use [Docker Engine](https://docs.docker.com/engine/install/) or Docker Desktop. Start Docker and confirm `docker info` succeeds with your user account.

```sh
git clone https://github.com/armaan-1207/Pratirodh.git
cd Pratirodh
```

### Windows — PowerShell

```powershell
py -3.11 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-deploy.txt
./.venv/Scripts/python.exe -m pratirodh build-runner
./.venv/Scripts/python.exe -m pratirodh doctor
./.venv/Scripts/python.exe -m pratirodh serve --port 8765
```

These commands use the virtual environment directly, so PowerShell activation-policy changes are unnecessary. The optional `./start-demo.ps1` helper starts the existing Windows demo setup. If Windows requests firewall access, the demo only needs local access.

### macOS and Linux — Terminal

```sh
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements-deploy.txt
./.venv/bin/python -m pratirodh build-runner
./.venv/bin/python -m pratirodh doctor
./.venv/bin/python -m pratirodh serve --port 8765
```

Use a Python 3.11 interpreter for the virtual environment. Some Linux distributions require their `python3-venv` package. Docker must be running and accessible to your account. Windows has been exercised locally; the macOS/Linux commands describe the portable Python/Docker workflow and have not been separately validated on those hosts.

### Open and use the demo

Open [the workspace](http://127.0.0.1:8765/workspace) and select **Start guided demo**. It runs the supplied example through basic checks, stronger verification, and a corrected repair. Follow the recorded stages, open each signed result, inspect failing requests, and replay a request. The result summary explains the next action. Current evidence appears first; enable **Include stale evidence** to inspect retained older runs.

The workspace offers three modes:

- **Curated demonstration:** supplied examples; no model installation or model calls required.
- **Local AI:** local Ollama proposes up to two repairs, each independently verified.
- **Combined repair:** one template first, then up to two local Ollama attempts if readiness is not established. The complete repair workflow has a ten-minute limit.

Combined repair is the default workspace tab. Candidate history retains every rejection. `/comparison` provides separate Repair and Verification tabs with recorded outcomes, costs, and expandable raw evidence. Stop the server with Ctrl+C. Source files are never replaced automatically.

### Optional local AI — all three platforms

Install [Ollama](https://docs.ollama.com/quickstart) for your OS and download the configured model while online:

```sh
ollama pull qwen2.5-coder:3b
ollama list
```

Keep the Ollama application/service running at `127.0.0.1:11434`. On Linux, follow [Ollama's installation instructions](https://docs.ollama.com/linux); run `ollama serve` if the service is not already running. Windows users can also use `./setup-offline.ps1`. No cloud API key is required. Local and combined modes use the restricted loopback provider and never invoke a cloud fallback. Missing models and provider timeouts leave unresolved evidence.

If Docker or the runner is unavailable, start Docker and repeat `build-runner` and `doctor`. If the model is unavailable, check `ollama list` and the local service. If port 8765 is occupied, use `serve --port 8767` and open that port. After relevant source changes, regenerate presentation evidence with the virtual-environment interpreter and `tools/prepare_demo.py`; old evidence remains stale by design.

The CLI examples below use `python` as shorthand for the virtual-environment interpreter: `./.venv/Scripts/python.exe` on Windows, `./.venv/bin/python` on macOS/Linux. Node.js is only needed to rebuild the frontend; prebuilt local assets are included.

## Generate, verify, and replay

```powershell
python -m pratirodh pipeline benchmark/scenarios/cwe-22-development-01 --contract benchmark/scenarios/cwe-22-development-01/contract.json --strategy combined
python -m pratirodh verify-patch benchmark/scenarios/cwe-22-development-01 --contract benchmark/scenarios/cwe-22-development-01/contract.json --patch benchmark/scenarios/cwe-22-development-01/patches/correct.diff
python -m pratirodh replay RUN_ID --case legitimate
python -m pratirodh verify-evidence RUN_ID
python -m pratirodh review RUN_ID --action approve --reviewer "Local reviewer" --rationale "Reviewed current evidence"
```

The pipeline supports `--strategy combined|ollama|template`. Its CLI default remains `ollama` for compatibility. A required failure returns `REJECT`; missing observations or unqualified checks return `INSUFFICIENT_EVIDENCE`; passing the required checks returns `READY_FOR_REVIEW`. Readiness applies only to the run's bounded scope. Approval and replay require current evidence.

Templates generate diffs in memory from an exact, unambiguous source match. They use the same patch policy and independent gate as model repairs. Supported repair classes are CWE-22, CWE-89, CWE-78, and CWE-798. Other detected classes remain detection-only. The supported targets are trusted, registered, single-file Flask fixtures.

## Reproduce the comparison

The previously inspected development/regression cohort contains 36 synthetic scenarios and 144 curated patches. Its recorded results are in [the curated results](docs/BENCHMARK_RESULTS.json). It is separate from the external cohort.

The versioned external cohort contains seven **real-world-derived reproductions**, including four evaluation cases and three development cases. Each adapts a documented public vulnerability mechanism into a minimal Flask fixture with synthetic data and harmless effects. These are not tests of complete upstream applications. The target was sixteen cases; the nine-case shortfall and source exclusions are disclosed in [the manifest](benchmark/external-v1/manifest.json).

```powershell
python tools/build_baseline.py --archive /path/to/historical-edffe24.tar
python -m pratirodh compare --prepare
python -m pratirodh compare --hours 12 --output run_output/reproduced-comparison-v1.json
```

This public release uses clean Git history and excludes earlier branding, database snapshots, and the Word document. Historical source is not redistributed here. To rebuild the historical arm, separately provide the original `git archive edffe24` tar (SHA256 `a64f6a440083aecc0e770ca5be1df0f9aec391ce33267273e8459cf2e83097b1`); the builder refuses any other archive. On Windows, replace the example archive path with your local path. Without that archive, the recorded comparison can be reviewed, but a fresh historical comparison cannot be reproduced from this repository alone.

The historical baseline is pinned to source revision `edffe24`; the earlier product revision is pinned to `8f57db6`. Baseline dependencies run only in a disposable Docker image. Its native `AUTO_MERGE`, `HUMAN_REVIEW`, and `REJECT` labels are retained. A review referral is never counted as an approved repair.

The comparison uses identical patch variants for verification, plus three repair repetitions per evaluation case for the historical, local AI, and combined workflows. Runs rotate across cases and systems, use one concurrent model request, and checkpoint results. Each repair allows at most two model calls, 180 seconds per generation, and ten minutes total. A final budget reserve audits already-generated candidates.

The final audit is calibrated against vulnerable originals and known repairs before measurement, runs in a separate supervisor process, and is not included in generator prompts or repair feedback. Template workers have only two read-only code mounts; model workers receive source and public requirements through the loopback adapter. Neither receives the audit directory. This is a team-authored evaluation, not third-party certification.

Results are published in `docs/COMPARISON_RESULTS_V1.json` and explained in [the comparison report](docs/COMPARISON.md). Open `/comparison` for the read-only view. Costs, failed attempts, compatibility gaps, and abstentions remain visible. Repetitions and patch variants are grouped by scenario for uncertainty estimates. No overall market superiority is claimed.

To resume an interrupted comparison within its original cap, add `--resume`. Resumption refuses changed cohort or implementation hashes. Changed implementations require a new versioned evaluation; avoid tuning on evaluation outcomes.

## Checks and deployment

```powershell
python -m pip install pytest==8.1.1
$env:PRATIRODH_DOCKER_TESTS = '1'
python -m pytest -q
npm ci
npm run build
npm test
python -m bandit -r pratirodh -ll
```

On macOS/Linux, use `PRATIRODH_DOCKER_TESTS=1 python -m pytest -q` instead of the PowerShell environment assignment.

Use the pinned `requirements-deploy.txt` for the active application. Historical dependencies must not be installed into that environment.

The dashboard includes authentication, CSRF protection, host restrictions, escaped evidence, signed inventories, and freshness checks. Container execution has no network access and uses read-only mounts. Deployment can be configured for authenticated read-only evidence review; it has no target execution privileges or signing key.

```powershell
./deploy/init-secrets.ps1
python tools/export_review.py
docker compose up -d --build
```

Keep `.env`, signing keys, local databases, and generated private evidence out of Git. The repository includes synthetic fixture credentials only. Review the exact staged files before publishing.

See [the project guide](docs/PROJECT_GUIDE.md), [demo narration](docs/DEMO.md), [interface attribution](docs/INTERFACE_SOURCES.md), and [security policy](SECURITY.md). The Word document, video, manual presentation assembly, and public hosting are outside this milestone.

## License and hackathon scope

PRATIRODH is released under the [MIT License](LICENSE). This repository was built for the Derby University hackathon to demonstrate bounded security repair and evidence review. It is a prototype, not a certification service or an automatic production patching tool.

Third-party packages and adapted public fixtures retain their own licenses and attribution. See the [external case manifest](benchmark/external-v1/manifest.json) and [interface attribution](docs/INTERFACE_SOURCES.md); the project license does not replace those terms.
