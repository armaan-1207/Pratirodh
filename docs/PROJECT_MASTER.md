# PRATIRODH Technical Team Handover

**Local integration update — 7 October 2026:** current work is on `codex/main-integrated-demo`, combining main controller protections with later improvements. See [reconciliation](RECONCILIATION.md) and [pinned preparation](UPSTREAM_PREPARATION.md). The current strict preparation result is 5 prepared / 19 blocked, not 24 qualified. Azure execution is excluded from this stage. Operational observations below are dated history; they do not authorize a new cloud window. The original historical document is retained in the inactive reference archive.


**Project master document · Version 0.2.0 · Status reviewed 6 October 2026**

PRATIRODH investigates security problems, challenges proposed repairs, and saves signed evidence for human review. We have a recorded three-language supplied-patch demonstration. The real upstream evaluation remains blocked and requires additional validation work.

This document gives teammates the project context, architecture, source map, setup, commands, evaluation plan, known limitations, and remaining work. It is designed to be shared with someone who has only the main repository. No previous chats or access to the project lead's computer are needed to understand it.

**Start here:** confirm the team's shared repository and commit, create a Python environment, install the package, and run the software tests. Use the controlled Docker demo to learn the workflow before attempting the upstream campaign. Section 4 explains what a normal clone contains; section 12 covers setup; section 18 gives the completion plan.

**Availability matters:** this document is sufficient for understanding and onboarding. Running every workflow additionally requires the dependencies and assets listed in section 4. A normal clone does not include ignored evidence, model weights, prepared worker images, or cloud access. Recorded results below are dated evidence summaries, not claims that your checkout has already reproduced them.

The labels **Desktop** and **final** refer to the project lead's prototype and validation development lines at the review snapshot. They are not folders you must create. All source paths are repository-relative, and example command paths should be adapted to your machine.

## Contents

- [1. Purpose and product scope](#1-purpose-and-product-scope)
- [2. History and terminology](#2-history-and-terminology)
- [3. Current state and evidence](#3-current-state-and-evidence)
- [4. Working from the main repository](#4-working-from-the-main-repository)
- [5. Architecture and execution flow](#5-architecture-and-execution-flow)
- [6. Codebase map and technology stack](#6-codebase-map-and-technology-stack)
- [7. Supported projects and intake](#7-supported-projects-and-intake)
- [8. Manifest, properties, and test contracts](#8-manifest-properties-and-test-contracts)
- [9. Repair verification and decisions](#9-repair-verification-and-decisions)
- [10. Models, resources, and budgets](#10-models-resources-and-budgets)
- [11. Worker isolation and infrastructure](#11-worker-isolation-and-infrastructure)
- [12. Installation and first run](#12-installation-and-first-run)
- [13. Operator command reference](#13-operator-command-reference)
- [14. Demo and presentation](#14-demo-and-presentation)
- [15. Evidence, signatures, and reproducibility](#15-evidence-signatures-and-reproducibility)
- [16. Testing and quality checks](#16-testing-and-quality-checks)
- [17. Upstream evaluation protocol and cohort](#17-upstream-evaluation-protocol-and-cohort)
- [18. Known gaps and completion roadmap](#18-known-gaps-and-completion-roadmap)
- [19. Troubleshooting](#19-troubleshooting)
- [20. Team workflow, licensing, and handover](#20-team-workflow-licensing-and-handover)
- [21. Glossary and source index](#21-glossary-and-source-index)

## 1. Purpose and product scope

PRATIRODH investigates security problems in source projects, proposes candidate repairs, challenges those repairs with executable checks, and exports signed evidence for human review. Its central question is whether the available evidence supports accepting a particular repair while preserving legitimate behavior.

The intended users are developers, security engineers, and reviewers who need a reproducible explanation of what a repair changed and how it was tested. The hackathon demonstration presents that workflow through a local dashboard.

The current product has three related paths:

| Path | Purpose | Current boundary |
|---|---|---|
| Historical single-file workflow | Flask-oriented security contracts and repair demonstrations | Separate engine and benchmark; historical results remain labeled |
| Version 2 project workflows | Experimental multi-file Python, JavaScript/TypeScript, and C/C++ repair/discovery | Reviewed manifests, supported build layouts, isolated workers |
| Upstream evaluation | Measure generated repairs on licensed real upstream cases with separate audits | Acquired/prepared material exists; qualification and campaign completion remain outstanding |

Repair can use an operator-supplied diff, a report-supplied replacement template, or a local model proposal. The supplied-patch demo exercises verification without depending on live model generation.

The output is a review decision plus artifacts. Automatic deployment, publication, universal vulnerability discovery, whole-application security proofs, and production containment certification are outside the demonstrated scope.

## 2. History and terminology

The repository retains **Kavach-CRS**, an earlier Python-oriented cyber reasoning prototype with detect, triage, reason, patch, prove, gate, and signed-ledger stages. Historical modules remain at the root, and `docs/KAVACH_README.md` preserves their original documentation.

PRATIRODH adds a clearer evidence-oriented repair workflow, a dashboard, explicit decision states, and the experimental version 2 project engine. The historical Kavach descriptions of automatic merging, broad proof, timings, or infrastructure capabilities should not be carried into current PRATIRODH claims without corresponding current evidence.

Use the installed **`pratirodh`** command for current workflows. The root **`cli.py`** is historical and exposes a different interface. Likewise, the old signed ledger and the current evidence store are related concepts with different formats and commands.

There are multiple kinds of “24 cases”: the related synthetic Flask scenarios in the historical benchmark and the planned 24 upstream cases are separate cohorts. A passing synthetic benchmark does not satisfy upstream acceptance.

## 3. Current state and evidence

The current implementation is on `codex/pratirodh-final`, based on consolidation commit `736df98` (24-case overlays, manifests, qualification, and cloud guard). The published frontend design has been integrated into the validation checkout. Desktop and older worktrees remain separate; run the server from the final checkout.

Fresh read-only checks on 6 October found all 24 recipes structurally ready and both `pratirodh-execution` and `pratirodh-audit` Docker contexts reachable. Azure reported model, execution, and audit VMs running. Power and connectivity observations are time-limited setup evidence, not proof of successful inference, isolation, qualification, or audits.

The generated campaign contains 24 cases and declares `qualification: NOT_CHECKED`, `release_complete: false`. Saved campaign progress remains zero qualified, zero completed, zero audited, and 216 scheduled attempts. Do not promote structural preparation to runtime qualification.

The focused preparation, campaign-generation, and FATE contract suite passed 36 tests. Full current-code Docker verification with zero skipped tests remains outstanding. The updated dashboard suite also passed four tests and the two new status regressions passed, giving 42 focused backend tests; frontend tests passed 3/3 and the build succeeded. Seven required browser routes returned HTTP 200. Earlier totals and blocked-worker records are historical evidence, not current failure diagnoses.

The earlier placeholder/hash-only audit-delivery and missing-harness findings are superseded by the consolidated preparation tooling and the current 24/24 structural check. Executable behavior still needs qualification on vulnerable and reference-fixed revisions.

### Generated status and browser routes

Run `python tools/update_validation_status.py --refresh` for read-only Azure power observations and bounded Docker preparation probes. It does not start VMs, invoke models, run target code, or verify billing. Status is generated from the consolidated cohort, stored acquisition (including the two corrected-revision provenance records), preparation, signed qualifications, campaign, and worker artifacts. Saved runner failure state is labeled separately from current preparation/worker observations. Observation timestamps and stale flags remain visible.

Overview displays generated upstream progress. Workspace provides controlled supplied-patch synthetic demonstrations. Comparison separates those fixtures and historical records from upstream outcomes. Validation exposes provenance, qualification, workers, and audit counts. Walkthrough lists signature-verified records; signature validity alone does not establish current freshness or independent audit acceptance.

### Current infrastructure and spending boundary

The model VM is `Standard_D4s_v4`; execution and audit are `Standard_B2als_v2`. Both worker contexts use restricted SSH and pinned project-worker images. Current spending must be supported by billing/pricing evidence and allocation history. A ledger timestamp update or old student-credit screenshot is insufficient. Arm and verify the bounded shutdown guard before further cloud execution.


### Azure allowance check — 6 October 2026

Step 1 identified and corrected the ledger's Low Priority model rate and Windows worker rates. Official Linux on-demand compute is $0.264/hour for the model plus $0.0246/hour for each worker, $0.3132/hour total before other resources. Retail API response snapshots and the complete allocation history are saved under `run_output/upstream-validation/budget-check`.

The authenticated Education portal showed ₹1,184.20 October costs and ₹8,414 credit remaining out of ₹9,599. These INR observations are not asserted to be a verified USD spending bound. The Cost Management scope selector explicitly marked Azure for Students unsupported, and REST queries returned HTTP 429. The previous $5 ledger entry has been retained only as an unverified historical value.

The ledger blocks cloud execution until billing, actual allocation intervals, and noncompute costs are reconciled. The guard's Windows Azure CLI batch invocation is corrected; 11 budget/CLI regression tests pass. The independent execution guard has not been armed. Azure confirmed all three VMs deallocated while this gate remains unresolved. Disks and prepared environments are retained; noncompute charges can persist. No campaign execution was started during this check.


### Reconciliation and guard update — 6 October 2026

The saved allocation history, live inventory, official USD retail receipts, and Azure Monitor storage/network metrics now produce an evidence-bound retail planning estimate. Rounded-up VM intervals cost $11.0104; disk capacity $2.24; the maximum disk transaction allowance $4.77456; IPs $1.47; blob capacity/operations $0.098; and the transfer planning ceiling $3.00. A 15% contingency yields a $25.99 historical planning bound. This is not an Azure invoice. No INR-to-USD conversion is assumed. The documented sponsorship portal also reports no active sponsorship for this account.

`python tools/reconcile_azure_budget.py --write-ledger` now preserves the capture-time cost anchor and binds the ledger to report/input hashes. It requires current captures; later time is charged at $0.60/hour even while VMs are off. The $30 approval and $2 shutdown reserve remain unchanged. Approximately $1.95 remained available at guard arming. Inventory changes and later execution require refreshed captures.

The independent guard is ARMED until **2026-10-06 07:22:18 UTC (12:52:18 IST)**. Its PID is recorded in `run_output/upstream-validation/guard-reconciled/guard.json`. The VMs remain deallocated; this update does not start models or execute target code. Guard deadlines are operational backstops, not monetary Azure caps. Sixteen accounting/CLI tests pass. The next step is fresh worker/model readiness under a valid guard; previous blocked-billing notes are historical and superseded by this explicitly estimated retail basis.


### Worker/model readiness — 6 October 2026, 06:44 UTC

The three Azure guests were started under the bounded guard. The operator SSH rule now allows only the observed public IP `the then-observed operator address (/32)`. SSH from the laptop remains intermittent; the controller reached the workers successfully.

`tools/check_campaign_workers.py` captured PASS for distinct execution/audit guest boot IDs, machine IDs and Docker daemons, and verified their pinned image IDs. Transport failures remain in the receipt. Bounded retries apply only to transport failures; identity/digest errors block without retry. `tools/check_model_worker.py` verified Ollama 0.35.0, Qwen2.5-Coder 7B Q4_K_M, runtime digest `sha256:0b0650a962dda61ec0598141ea11e3b688d225e926c9c00bc2c299d0ed34c4f8`, model digest `sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`, and valid structured inference. The saved warm inference took 1.78 seconds; available memory after loading was 10.03 GiB. This is readiness evidence, not repair accuracy.

The laptop sandbox probes timed out. The separately saved controller probes passed on both worker images using the current worker code: unprivileged target process, read-only root, loopback-only interface, no Docker socket, zero effective capabilities and no-new-privileges. Their receipt is `run_output/upstream-validation/worker-sandbox-probe-controller.json`; the Azure response and exact staged probe script are retained beside it. The older installed controller code differed from the current worker module; current source was staged separately without replacing that installation. Full controller deployment still needs synchronization before qualification.

A real invocation exposed a Windows batch-path quoting failure in the Azure CLI helper. It now invokes the MSI's bundled Python directly, avoiding `cmd /c`. A live Azure query succeeded. The corrected independent guard is PID 21312, receipt `guard-msi-fixed/guard.json`, with the unchanged deadline 07:22:18 UTC (12:52:18 IST); the old guard was superseded only after the new guard acknowledged arming. Twenty-two focused accounting, CLI, transport and UI status tests pass; seven project routes return HTTP 200. This is not the full suite. Azure confirmed all three VMs deallocated at 06:46:31 UTC after readiness capture. Disks/IPs remain and can incur noncompute charges; verify generated power observations before restarting.

**Next step:** synchronize the controller with this final checkout, repair the qualification tool's removed default manifest path and configure the recipe worker/model pins. Qualify `python-cve-2018-18074` first, checking vulnerable reproduction, reference fix, legitimate controls and independent audit. Then qualify the remaining 23 cases before freezing or running the 216-attempt comparison. Qualified/completed/audited counts remain 0. A running VM or a successful sandbox probe must not increase those counts. Refresh spending evidence and establish a valid shutdown guard before the next execution window.

## 4. Working from the main repository

Start in the repository you received from the team. All code paths in this document are relative to that repository root. You do not need the project lead's Desktop folders, Codex worktrees, or previous chat history to understand this handover.

The main repository alone may not include the newest upstream-validation work or recorded demo results. A branch named main is not proof that every development change has been integrated. Check your checkout before following a workflow:

```powershell
git branch --show-current
git log -1 --oneline
git status --short
git remote -v
Test-Path pyproject.toml
Test-Path scripts/start_demo.py
Test-Path benchmark/recipes
```

The inspected machine had remotes for armaan-1207/Pratirodh, armaan-1207/Kavach-CRS, and peterparker2107/Pratirodh on GitHub. Confirm the team's chosen shared repository and branch with the project lead; these configured remotes do not establish which has the newest published code.

| Development line | Inspected commit | What teammates need to know |
|---|---|---|
| Desktop prototype | 86e614d | Established demo and current package; upstream recipes absent in this checkout |
| Final validation branch | 736df98 | Consolidated 24-case tooling and overlays; current documentation/frontend integration is a working change |
| Offline pipeline branch | 5df8e81 | Earlier UI and documentation work; not the final validation line |
| Historical baseline | edffe24 | Retained original baseline |

These commit references identify the review snapshot. They may not be available in your clone until the project lead publishes or merges the relevant work. Do not invent missing local paths or assume that a Git checkout recreates ignored evidence, installed models, worker images, credentials, or cloud resources.

### What is available and what requires a separate handover

| Item | Usually in the repository | Action if missing |
|---|---|---|
| Controller code, tests, docs, and setup scripts | Yes, depending on branch | Obtain the agreed current branch |
| Upstream recipes and nested targets | Branch dependent | Obtain the reviewed validation branch and its documented source initialization or archives |
| Demo evidence and campaign logs under run_output | No, ignored | Request a sanitized evidence export or regenerate the controlled demo |
| Presentation package | No, ignored | Request the approved package only if presenting |
| Local model weights and runtime | No | Prepare the selected model separately and pin its identity |
| Worker images and application dependencies | No | Build or obtain the approved images and record digests |
| Azure access, SSH configuration, tokens, and signing keys | No | Arrange appropriate access privately; do not commit secrets |

For a first contribution, the controller code, a Python environment, and the software tests are sufficient to start reviewing implementation. Docker with Linux containers is additionally required for fresh demo execution. Full upstream validation also needs the prepared sources, real harnesses, isolated workers, and model resources described later.

## 5. Architecture and execution flow

```text
Operator / local browser / CLI
             |
             v
Controller: intake -> reviewed manifest -> project engine -> decision
                |                 |                      |
                |                 v                      v
                |          Local model server      Signed evidence store
                |          (proposal generation)   -> dashboard / ZIP
                v
Dedicated execution worker -> bounded disposable target containers
                |
                v
Candidate artifacts -> separate audit worker -> campaign results
```

The controller inventories source, enforces editable/protected boundaries, manages budgets, asks for proposals, dispatches checks, and signs reports. Imported project commands execute on workers. The model suggests changes; it does not grant execution permission or determine acceptance by itself.

A typical version 2 run proceeds through:

1. **Intake:** identify adapter, snapshot files, validate source/manifest identity and policy.
2. **Baseline:** build and run approved existing tests and legitimate controls.
3. **Inspection:** collect static observations and approved executable findings.
4. **Qualification:** show that the original violation reproduces consistently and controls work.
5. **Search/minimization:** run approved properties or fuzz actions and bounded argument reductions.
6. **Proposal:** obtain a supplied patch, a template candidate, or bounded model output.
7. **Candidate checks:** apply to a copy; enforce edit policy; build, test, replay, and vary inputs.
8. **Mutation challenges:** weaken copies of the repair and check whether the verifier detects the unsafe behavior.
9. **Evidence:** retain failures and uncertainty, record usage/resources, sign artifacts, issue the decision.
10. **External campaign audit:** independently check candidate artifacts on the separate audit worker.

Repair starts from a reported problem. Discovery searches approved properties and harnesses. Generated allegations or harness proposals remain unconfirmed until reviewed and executed through an approved manifest.

## 6. Codebase map and technology stack

| Path | Responsibility |
|---|---|
| `pyproject.toml` | Package version, installation dependencies, `pratirodh` entry point, pytest discovery |
| `pratirodh/cli.py` | Current CLI dispatch and flags |
| `pratirodh/web.py`, `templates/`, `static/` | Flask dashboard, project forms, jobs, history, evidence views |
| `pratirodh/engine.py`, `contracts.py`, `execution.py` | Historical single-file PRATIRODH engine and contracts |
| `pratirodh/evidence.py` | Artifact hashing, signing, integrity verification, store support |
| `pratirodh/projects/manifest.py` | Intake inventory, adapters' initial commands, profiles, manifest policy |
| `pratirodh/projects/engine.py` | Multi-file discovery and repair orchestration |
| `pratirodh/projects/worker.py`, `worker_entry.py`, `Dockerfile` | Container dispatch, trusted supervisor, worker image |
| `pratirodh/projects/adapters.py` | Language-specific inspection/check support |
| `pratirodh/projects/model.py` | Pinned local model client and preflight |
| `pratirodh/projects/patching.py` | Multi-file patch policy and application to copies |
| `pratirodh/projects/budget.py`, `leases.py` | Run accounting and concurrency locks |
| `pratirodh/projects/harnesses.py`, `templates.py` | Harness proposals and candidate templates |
| `pratirodh/projects/evaluation.py` | Frozen cohort, scheduling, separate audit, completion accounting |
| `pratirodh/projects/examples.py`, `export.py` | Synthetic examples and project evidence exports |
| `scripts/start_demo.py` | Demo prerequisites, fresh verification, dashboard launch |
| `scripts/evaluate_local_prototype.py` | Separate local-model smoke evaluation |
| `scripts/prepare_local_model.py` | Explicit model preparation; separate from repair execution |
| `scripts/author_upstream_manifests.py` | Upstream manifest/audit authoring; generated output still needs review |
| `scripts/*worker*`, `scripts/connect_workers.ps1` | Worker setup/status utilities |
| `benchmark/scenarios/` | Historical synthetic scenarios |
| `benchmark/recipes/` in final | Upstream case recipes, manifests, audits, nested source targets |
| `detect/`, `reason/`, `patch/`, `prove/`, `gate/`, `ledger/` | Retained Kavach pipeline |
| `tests/` | Unit, protocol, policy, evidence, dashboard, and opt-in container tests |
| `run_output/` | Ignored local generated evidence and operational records |
| `presentation/` | Ignored generated presentation assets |

Controller dependencies in `pyproject.toml` are Python 3.11+, Flask, cryptography, Bandit, and Waitress. The older root `requirements.txt` contains additional/pinned historical tools; do not assume it is identical to current package metadata.

The prototype project worker starts from Python 3.11 on Debian Bookworm and installs Node/npm, Clang, CMake, Make, pytest, Bandit, Flask, FastAPI, and HTTPX. Application-specific dependencies require derived prepared images. The bundled image is a prototype tool environment, not a universal dependency bundle.

## 7. Supported projects and intake

| Adapter | Recognized layout | Execution notes |
|---|---|---|
| Python | Python files plus `pyproject.toml`, `requirements.txt`, or `setup.cfg` | AST syntax baseline and pytest-oriented tests |
| Node | `package.json`, `package-lock.json`, declared test script | Uses approved npm test command; dependencies prepared separately |
| TypeScript | Node layout plus `tsconfig.json` | Prepared TypeScript compiler used for no-emit checking |
| C/C++ | `CMakeLists.txt` | CMake/CTest, Clang, sanitizer-oriented compiler settings |

Unsupported layouts return an explicit unsupported result. Arbitrary build systems and multi-container service networks are not generally supported.

Intake skips common generated/dependency directories such as `.git`, `.venv`, `node_modules`, `run_output`, `build`, and `dist`. Included files are decoded as UTF-8 and hashed. Symlinks/junctions and obvious credential/private-key filenames are rejected. This is not a complete secret scanner.

**Current checkout differences:**

| Setting | Desktop | Final worktree |
|---|---:|---:|
| Maximum individual file | 1 MiB | 15 MiB |
| Maximum total inventory | 10 MiB | 200 MiB |
| Maximum file count | 1,000 | 15,000 |

Larger limits do not solve binary fixture handling. Preserve original upstream artifacts and record adaptations explicitly. Removing fixtures or rewriting sources solely to pass intake can invalidate the qualification experiment.

The manifest `revision` produced by intake is an inventory digest. Record the upstream Git commit separately; those identifiers serve different purposes.

## 8. Manifest, properties, and test contracts

`project inspect` produces a version 2 proposal with `NEEDS_APPROVAL`. The inspection result is not a runnable, fully qualified security specification.

| Manifest field | Meaning |
|---|---|
| `version`, `revision`, `inventory` | Schema and exact source identity |
| `adapter` | `python`, `node`, or `cpp` |
| `worker`, `image` | Approved worker context and pinned prepared image |
| `commands` | Build/test/startup commands as argument arrays |
| `editable` | Existing source files candidates may modify |
| `properties` | Reviewed behavior, controls, violation observations, variations |
| `mutations` | Reviewed weakened-repair challenges |
| `formal`, `fuzz` | Optional prepared-tool checks, approvals, assumptions, and bounds |
| `dependencies` | Preparation state, resolved versions, image digest |
| `model`, `limits` | Pinned generation configuration and resource budget |
| `model_analysis`, `generate_harnesses` | Optional proposal-generation features; no automatic authorization |

Tests, specifications, fixtures, harnesses, locks, configuration, and other protected files cannot be edited as a candidate repair. Command arrays must be explicit; repository text or model output cannot approve them.

Each security property needs an identifier, violation kind, description, target files, approved provenance, and harness review. A **control** demonstrates legitimate use. A **reproducer** distinguishes the original violation from the expected safe result. **Variations** challenge additional reviewed inputs. A generic exception, missing test, or unrelated failure is not evidence of the intended violation.

The current oracle compares command exit status and stdout. The harness must actually invoke the relevant target behavior. Operator review remains necessary because a script can print expected text without exercising the application.

A minimal problem-report shape for the synthetic portal is:

```json
{
  "property": "tenant-isolation",
  "files": ["policy.py", "users.py"],
  "description": "A synthetic guest can access the admin account. Preserve owner access."
}
```

Consult `docs/PROJECT_WORKFLOWS.md`, `docs/audit.example.json`, and the current validators for full schemas. Upstream `recipe.json`, execution `manifest.json`, external `audit.json`, and the campaign manifest are distinct records; changing one does not automatically regenerate or validate the others.

## 9. Repair verification and decisions

| Decision | Meaning |
|---|---|
| `READY_FOR_REVIEW` | Required development checks support reviewing this candidate under the recorded assumptions |
| `REJECT` | Candidate violates edit policy or fails a required behavior/security check |
| `INSUFFICIENT_EVIDENCE` | Missing, inconsistent, unavailable, stale, or incomplete evidence prevents readiness |

A ready candidate must pass the build, existing tests, legitimate controls, original security reproducer under the safe expectation, and approved variations. Original violations are qualified through three clean reproductions. Declared mutations must preserve their control, demonstrate unsafe behavior, and be detected; equivalent, invalid, or unconfirmed mutations are retained without counting as successes.

Candidate changes are applied to source copies. Attempts to escape paths, edit protected inputs, add/delete files, change modes, or introduce recognized check suppressions are rejected. Heuristic suppression detection supplements behavior checks; it does not replace them.

CrossHair/CBMC checks require prepared tools and explicit assumptions and bounds. Successful CBMC evidence is scoped to a bounded property. Missing tools, timeouts, and inconclusive output remain unresolved. Discovery finding no approved violation means only that none was found within that search.

Human approval, applying the patch to the original project, committing, and publishing are separate actions. Development readiness also does not replace the separate final audit required by the upstream campaign.

## 10. Models, resources, and budgets

Version 2 uses Ollama or a local llama.cpp server. No automatic paid-provider fallback or model download occurs during repair. Legacy provider options in the older workflow are separate.

| Profile | Model identity in code | Required declared memory | Status |
|---|---|---:|---|
| `laptop` | Qwen2.5-Coder 7B / Ollama `qwen2.5-coder:7b` | 8 GiB | Default; saved smoke run blocked |
| `alternative` | Qwen3.5 9B / `qwen3.5:9b` | 12 GiB | Experimental configuration |
| `linux-large` | Qwen3-Coder 30B A3B / `qwen3-coder:30b` | 24 GiB | Requires measured latency preflight |
| `prototype-small` | Qwen2.5-Coder 3B / `qwen2.5-coder:3b` | 4 GiB | Historical experimental profile; docs record local weights removed |

All listed profiles use an 8,192-token context setting. These are repository configurations, not comparative accuracy claims or a guarantee that a machine can serve them efficiently.

Preflight requires weight/runtime SHA-256 digests, quantization, memory information, and an approved loopback HTTP endpoint. Ollama checks the installed model identity; llama.cpp additionally checks its GGUF file and server health. A binary hash alone does not attest which executable a separately managed server process is running.

Prompts contain scoped editable source, descriptions, and reproducer arguments. Test contents, fixtures, formal assertions, and final audits are excluded. Context selection is file-scoped; a complete semantic cross-language call graph remains future work.

### Budget discrepancies to resolve before freezing a campaign

| Configuration | Desktop | Final / other evidence |
|---|---|---|
| Newly inspected project run | 600 s; 180 s reserve; 2 model calls; 3 candidates | Final: 1,800 s; 600 s reserve; 8 calls; 3 candidates |
| Shared initial resource defaults | 120 s/command, 2,048 MiB, 2 CPUs, 64 PIDs, 256 MiB disk, 65,536 output bytes | Check approved manifests for overrides |
| Campaign function inspected | 172,800 s total; 28,800 s audit reserve | 48 h total; 8 h reserve |
| Older workflow documentation | Describes 12 h total | Stale relative to inspected function defaults |
| Saved campaign status | 345,600 s total; 172,800 s reserve | Historical configuration: 96 h / 48 h; not the current function default |

There is no single reliable “default budget” across all saved material. Freeze the exact selected values in a new campaign and ensure docs, manifests, CLI behavior, and implementation agree. Concurrency controls target two execution slots and one model generation across controller processes. Cancellation retains partial evidence; resume records a new run, rechecks inputs, and carries forward consumed budgets.

## 11. Worker isolation and infrastructure

Imported targets belong on dedicated disposable Linux workers. Execution and final audit must use separate workers with independently verified identities. Context names alone do not prove separate infrastructure.

The implemented boundary uses no external target network, a read-only container root, bounded scratch space, resource/output/time limits, and target UID/GID 65534. The trusted supervisor prepares immutable source/tests before dropping privileges. Controller directories, Docker sockets, host credentials, and signing keys are not intended to be mounted into targets. Worker/container descendants are cleaned up after completion or cancellation.

Dependencies are prepared separately in an approved image, using a restricted preparation network or offline cache. The controller does not install arbitrary target dependencies on the host as a repair fallback.

Context naming currently needs reconciliation:

| Name | Where used |
|---|---|
| `default` | Controlled local demo/image commands |
| `pratirodh-worker` | General manifest proposals and worker setup docs |
| `pratirodh-execution` | Upstream authoring and latest failed qualification report |
| `pratirodh-audit` | Separate final audit |

Local VirtualBox setup scripts and cloud-worker documentation exist. Older docs record VM stability issues and Azure student-account/quota preparation. Live Azure inventory, current costs, quota, worker connectivity, and billing were not checked for this master document. Historical credits, quotes, or hardcoded status strings must not be treated as live account state.

A remote model over a private tunnel additionally needs accurate remote runtime/weight provenance. The current local-runtime assumptions do not by themselves establish that integration.

## 12. Installation and first run

Use Python 3.11+, Git, and Docker with Linux containers for the controlled demo. Use a separate virtual environment per checkout to avoid accidentally importing another worktree's editable install.

```powershell
Set-Location '<your-repository-folder>'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pratirodh --help
.\.venv\Scripts\python.exe -c "import pratirodh; print(pratirodh.__file__)"
docker version
```

On Linux or macOS, use the corresponding environment paths:

```bash
cd /path/to/your/repository
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install pytest
.venv/bin/python -m pratirodh --help
.venv/bin/python -m pytest -q
.venv/bin/python scripts/start_demo.py
```

The remaining examples use PowerShell syntax. Repository commands are the same on other shells; adapt environment-variable assignments, executable paths, and worker setup instructions to the host operating system.

The import path should point into the checkout being tested. Package installation may require network access; target execution remains a separate concern.

Run the established demonstration:

```powershell
.\.venv\Scripts\python.exe scripts/start_demo.py
```

The launcher verifies prerequisites, prepares the image when required, runs nine fresh demo checks, and starts the dashboard at `http://127.0.0.1:8767`. Give a fresh output location to commands that refuse overwriting earlier evidence. Building/preparing the image is separate from executing target checks.

## 13. Operator command reference

The examples below assume the correct environment's `pratirodh` command is on PATH; otherwise use `.\.venv\Scripts\python.exe -m pratirodh`.

| Task | Command |
|---|---|
| Help | `pratirodh --help` |
| Historical runner image | `pratirodh build-runner` |
| Default dashboard | `pratirodh serve --port 8765` |
| Project worker image | `pratirodh project build-worker --context pratirodh-worker` |
| Three-language synthetic project demo | `pratirodh project demo --challenge --output run_output/project-demo-new` |
| Inspect source without executing it | `pratirodh project inspect C:/source/my-project --output C:/source/my-project/pratirodh-project.json` |
| Discover | `pratirodh discover C:/source/my-project --manifest C:/source/my-project/pratirodh-project.json --profile laptop` |
| Repair a reported issue | `pratirodh repair C:/source/my-project --manifest C:/source/my-project/pratirodh-project.json --report C:/reports/problem.json --profile laptop` |
| Supplied candidate | Add `--patch C:/patches/candidate.diff` to the approved project workflow |
| Resume | Add `--resume RUN_ID`; source/manifest must match |
| Verify saved integrity | `pratirodh verify-evidence RUN_ID --store C:/evidence/store` |
| Export | `pratirodh export RUN_ID --store C:/evidence/store --output C:/exports/review-evidence.zip` |
| Freeze evaluation | `pratirodh project-benchmark --manifest C:/evaluation/campaign.json --freeze-only` |
| Run evaluation | `pratirodh project-benchmark --manifest C:/evaluation/campaign.json --output run_output/project-campaign-new.json` |
| Historical synthetic benchmark | `pratirodh benchmark --split all --output run_output/benchmark-new.json` |

`C:/source`, `C:/reports`, and `C:/evaluation` above are illustrative operator paths, not promises that those files exist. Complete and review manifests before execution. `--demo-worker` is an explicit exception for controlled synthetic examples and records demo-only assurance.

For read-only evidence serving:

```powershell
$env:PRATIRODH_READ_ONLY = '1'
pratirodh serve --store C:/evidence/store --port 8766
```

All POST actions are then blocked. Keep write-enabled control interfaces local and use the existing host/CSRF restrictions.

## 14. Demo and presentation

The saved demonstration uses synthetic account-isolation projects in Python, Node, and C++. Correct repairs change two files. An incomplete owner-check repair fails to fix an identity-mapping path, so the verifier rejects it while accepting the corrected candidate under its declared checks.

Presentation sequence:

1. Explain the security property and distinguish legitimate use from the violation.
2. Select Python and challenge both supplied repairs.
3. Show the incomplete repair's rejection and its evidence.
4. Open the corrected repair, two-file diff, original reproductions, controls, variations, and mutation results.
5. Download evidence and explain signature/inventory verification.
6. Show equivalent JavaScript and C++ repair/discovery records.

If the team has supplied this evidence directory, reopen it from your repository root:

```powershell
python scripts/start_demo.py --store run_output/demo-ready-20261002/evidence
```

Use `--port 8768` if required. A recorded walkthrough is usable when Docker is unavailable, but it should be described as recorded. Code changes can make evidence stale; prepare fresh verification before presenting a current live result.

The saved demo establishes the supplied-patch verification flow. It does not establish model accuracy, autonomous upstream repair success, or completion of independent final audits. The separately shared ZIP presentation package should be refreshed after the technical story and evidence are frozen.

## 15. Evidence, signatures, and reproducibility

Version 2 records include source/manifest identity, adapter, reproductions, diffs, candidate snapshots, verification/mutation/formal observations, model usage, limits, elapsed time, and explicit unknown measurements. Historical version 1 evidence remains readable.

Ed25519 signatures and SHA-256 inventories protect artifact integrity. Preserve the public trust-key fingerprint through a separate trusted channel. A valid signature establishes that the stored bytes match the signed inventory; it does not establish correctness of the security assertions or certify the signer's identity.

Exports validate integrity, include the public key, and exclude the private signing key. Preserve complete stores and context rather than copying only a summary. Unknown peak memory or missing measurements must remain unknown.

For reproducible results retain:

- Controller commit plus any local modifications, dependency/runtime versions, and selected checkout.
- Upstream Git revision, original archive/source hashes, adaptation record, and source inventory digest.
- Approved execution and audit manifests, worker image IDs, resolved dependencies, and worker identities.
- Model/runtime/weight digests, quantization, resources, latency preflight, and budgets.
- Raw command outputs, candidate attempts, failed/unstarted rows, signed artifacts, and audit results.

`run_output/`, `presentation/`, virtual environments, model weights, VM disks, and other generated material are ignored by Git. Committing code alone does not back up those artifacts. Untracked operational archives and token-related files in final should be reviewed separately before staging; they are not document source material to publish.

## 16. Testing and quality checks

```powershell
python -m pytest -q
```

For the separately opted-in Docker integration checks:

```powershell
$env:PRATIRODH_DOCKER_TESTS = '1'
python -m pytest -q
Remove-Item Env:PRATIRODH_DOCKER_TESTS
```

Use the selected checkout's environment. The tests cover patch protection, project workflows, local model protocols, budgets, evidence, dashboard behavior, independent evaluation, and opt-in container execution. Passing software tests and passing upstream qualification are different milestones.

Recorded results must retain their dates and scope:

- Demo guide, 2 October: 58 software tests and nine opt-in Docker integration tests reported passing.
- Final-worktree log, 4 October: 145 passed and one failure in `tests/test_combined.py::test_combined_template_then_model_history_and_replay`, with `ValueError: evidence is stale; create a new verification run`.
- Qualification index, 5 October: 24 blocked entries.
- Focused check during the 5 October change review, 5 October: `python -m pytest -q tests/test_projects.py::test_model_failure_retained_no_cloud_fallback` in final — **1 passed in 0.12 s**. A pytest-asyncio default-loop-scope deprecation warning was emitted.
- Static syntax checks during the same review: both FATE data-leak test files failed parsing after Python encoding detection; this check did not import or execute upstream target code.

These are different snapshots/suites. The stored failure may change after current edits, and its referenced test file is not part of the inspected Desktop test listing. Run the relevant current checkout before reporting a clean test result.

For documentation-only changes, check file identity, repository references, and command names. The full evaluation campaign remains a separate validation milestone.

## 17. Upstream evaluation protocol and cohort

The intended cohort is **24 licensed cases**, eight per language group: two development and six evaluation cases. Development cases establish the process; the 18 evaluation cases feed the comparison campaign.

The inspected scheduler produces **216 rows**: 18 evaluation cases × two workflows (repair/discover) × two arms (expanded/model-only) × three repetitions. Both arms use the same verifier and separate final audit. Preserve failed, unresolved, and unstarted rows rather than counting only successful attempts.

Freeze source, manifests, audit hashes, case provenance, licenses, adaptations, and budgets before comparison. Developer fixes and final audit assertions must stay outside generation inputs. Evaluation-driven tuning requires a new versioned evaluation, and model training exposure to public cases cannot be ruled out.

### Candidate cohort recorded in the saved campaign status

The following mapping is project metadata from the saved status, not a claim that each case has qualified. All 24 are blocked in the inspected qualification index.

| Language | Case | Upstream project | Split |
|---|---|---|---|
| Python | CVE-2021-21330 | aio-libs/aiohttp | Development |
| Python | CVE-2022-0767 | janeczku/calibre-web | Development |
| Python | CVE-2020-25459 | FederatedAI/FATE | Evaluation |
| Python | CVE-2021-32633 | zopefoundation/Zope | Evaluation |
| Python | CVE-2021-33203 | django/django | Evaluation |
| Python | CVE-2025-43859 | python-hyper/h11 | Evaluation |
| Python | CVE-2018-7750 | paramiko/paramiko | Evaluation |
| Python | CVE-2018-18074 | requests/requests | Evaluation |
| JavaScript | CVE-2021-37712 | isaacs/node-tar | Development |
| JavaScript | CVE-2021-23369 | handlebars-lang/handlebars.js | Development |
| JavaScript | CVE-2021-29300 | ronomon/opened | Evaluation |
| JavaScript | CVE-2021-23664 | isomorphic-git/cors-proxy | Evaluation |
| JavaScript | CVE-2019-10767 | ioBroker/ioBroker.js-controller | Evaluation |
| JavaScript | CVE-2018-6835 | ether/etherpad-lite | Evaluation |
| JavaScript | CVE-2019-15599 | pkrumins/node-tree-kill | Evaluation |
| JavaScript | CVE-2024-56334 | sebhildebrandt/systeminformation | Evaluation |
| C/C++ | CVE-2023-50472 | DaveGamble/cJSON | Development |
| C/C++ | CVE-2018-25032 | madler/zlib | Development |
| C/C++ | CVE-2022-43680 | libexpat/libexpat | Evaluation |
| C/C++ | CVE-2019-1000019 | libarchive/libarchive | Evaluation |
| C/C++ | CVE-2023-4863 | webmproject/libwebp | Evaluation |
| C/C++ | CVE-2024-25062 | GNOME/libxml2 | Evaluation |
| C/C++ | CVE-2014-9130 | yaml/libyaml | Evaluation |
| C/C++ | CVE-2020-12762 | json-c/json-c | Evaluation |

Each case still needs demonstrable legitimate behavior, original violation, known-fixed behavior, reviewed variations/mutations, working dependencies, preserved provenance, and separate audit execution. Source acquisition or a generated manifest is not qualification.

Release completeness requires the whole cohort, all required scheduled work/audits, generated repair and discovery successes across all language groups, and successful separate audits for every ready row. Executable rejected candidates also need audit analysis to expose false rejection or unresolved-correct cases. Statistical uncertainty analysis and measured performance should accompany completed results rather than inferred percentages.

## 18. Known gaps and completion roadmap

1. **Reproducibility:** validate tracked overlays and target reconstruction from a fresh clone. Parent commits do not include arbitrary untracked edits inside submodules. Preserve exact upstream provenance and document adaptations.
2. **Allowance and shutdown:** verify current spending, actual VM rates, allocation intervals, storage, and shutdown reserve. Verify the bounded guard before executing qualification or models.
3. **Runtime readiness:** record fresh worker identities, pinned image digests, isolation checks, model digest, memory, and inference preflight. Running VMs and reachable Docker daemons are only setup checks.
4. **24 runtime qualifications:** Review exact per-case license identifiers and reconcile qualification/campaign tool manifest defaults with the consolidated `benchmark/upstream-cohort.json` and `benchmark/campaign.json`; removed `upstream-v2/manifest.json` paths must not be required.  reproduce each vulnerability; preserve legitimate behavior; demonstrate the upstream reference fix; execute independent audit inputs; retain signed qualification evidence. Keep blocked/failed cases visible.
5. **Freeze:** bind licenses, revisions, source maps, source hashes, execution and audit definitions, worker/model/controller digests, cohort split, and equal declared budgets. Keep held-out audits inaccessible to generation.
6. **216 comparison attempts:** execute both arms with resumable accounting. Record unsuccessful repairs, provider failures, unresolved runs, and unstarted attempts without resetting consumed budgets.
7. **Independent audits and export:** audit retained candidates on the separate worker. Accept only independently audited outcomes. Verify signed exports and artifact bindings from the exported bundle.
8. **Frontend walkthrough:** validate generated counts and timestamps, intake, evidence details, exports, and empty/error/stale states. Complete the browser path without manual JSON edits and verify recorded evidence after Azure shutdown.
9. **Final checks:** run the complete backend suite with Docker and zero skips, frontend tests/build, and route/browser checks against the exact release commit.
10. **Publication and teardown:** publish the tested implementation with reproducible setup, evidence bundles, SSH/public host-key documentation, model/image digests, and teardown instructions. Exclude private keys and credentials. Remove campaign resources after evidence and offline walkthrough verification.

PPT and video production remain deferred. A successful synthetic demo or structurally ready cohort does not complete upstream acceptance.

## 19. Troubleshooting

| Symptom | Interpretation and next check |
|---|---|
| `docker context inspect pratirodh-execution` fails | Check actual context inventory and worker configuration; reconcile manifest names with verified endpoints |
| Docker cannot connect | Check Docker Desktop/Linux engine or dedicated-worker reachability before rerunning targets |
| `MEMORY_PREFLIGHT_BLOCKED` | Saved available RAM is below the model requirement; establish capacity and repeat measured preflight |
| Evidence is stale | Source, manifest, controller, or relevant execution identity changed; create fresh verification and preserve old records |
| Intake rejects UTF-8 or size | Check selected checkout's limits and original fixtures; design/record a valid adaptation rather than silently discarding data |
| Missing dependencies | Prepare a derived image and update its digest/resolved versions; do not install on the controller as a fallback |
| Harness passes but case remains blocked | Inspect actual target invocation, violation origin, control, variation, mutation, and audit requirements |
| Correct patch has unavailable mutations | Literal mutation patterns may not match an alternative fix; review challenges and rerun without hiding uncertainty |
| Port 8767 occupied | Choose another port, such as 8768; do not terminate unrelated services |
| Changes appear ignored by tests | Print `pratirodh.__file__` and confirm the environment points to this checkout |
| Campaign summary contradicts code | Compare timestamps/configuration hashes; old status is not regenerated by editing source |
| Signature verifies but outcome looks wrong | Integrity and behavioral correctness are separate; inspect the commands and assertions |

## 20. Team workflow, licensing, and handover

Use a dedicated environment and clear branch per task. Before work, inspect parent and nested Git status and record the selected evidence store. Keep case fixtures and tests protected from repair candidates. Preserve raw failures and avoid editing evidence to manufacture a success.

Before a technical handover:

- Record the selected branch/commit and all remaining local changes.
- Run relevant current software/container checks and save their logs with scope/date.
- Recreate evidence affected by implementation or manifest changes.
- Verify exported signatures/artifact hashes and preserve the public trust fingerprint.
- Confirm execution and audit identities, dependencies, model provenance, and frozen budgets.
- Review upstream licenses, attribution, source revisions, and adaptations individually.
- Preserve ignored evidence and operational assets securely; exclude private keys, tokens, and signed access URLs from shared packages.
- Update this master file and publish the updated handover alongside the agreed repository version.

`docs/THIRD_PARTY_NOTICES.md` is the starting point for attribution. Upstream sources and model weights have their own licenses. A project-level license or an earlier branch's license commit does not settle redistribution rights for every acquired case, fixture, dependency, or model.

No team owners, service-level commitments, or release date are assigned by this document. Assign them in the team's actual tracker when planning implementation. The open priorities above are based on inspected blockers rather than invented completion percentages.

## 21. Glossary and source index

| Term | Meaning here |
|---|---|
| Control | Legitimate-use check that should keep working |
| Reproducer | Executable observation distinguishing a specific original violation from safe behavior |
| Variation | Additional reviewed security input/check |
| Mutation | Deliberately weakened repair used to challenge the verifier |
| Qualification | Evidence that a case/harness behaves correctly before using it to judge repairs |
| Candidate | Proposed source change under evaluation |
| Audit | Separate final assessment with protected inputs outside development generation |
| Frozen campaign | Versioned case/configuration set with preserved hashes and comparison rules |
| Inventory revision | Digest of included source content; distinct from an upstream Git SHA |
| Readiness | Evidence supports human review under declared checks; not automatic deployment |
| Stale evidence | Historical evidence no longer bound to the current relevant inputs/controller |

### Primary repository references

- [README.md](README.md): product overview and current-entry commands; some limits/status prose is older than final code.
- [docs/PROJECT_WORKFLOWS.md](docs/PROJECT_WORKFLOWS.md): manifest, worker, verification, evaluation, and evidence details.
- [docs/DEMO.md](docs/DEMO.md): presenter steps and dated demo verification.
- [docs/LINUX_WORKERS.md](docs/LINUX_WORKERS.md): dedicated local-worker setup.
- [docs/CLOUD_WORKERS.md](docs/CLOUD_WORKERS.md): historical cloud preparation, worker plan, and integration gaps; recheck live provider state separately.
- [docs/THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md): attribution and licensing boundaries.
- [docs/KAVACH_README.md](docs/KAVACH_README.md): historical origin and architecture; not current acceptance evidence.
- [pyproject.toml](pyproject.toml): package metadata and entry point.
- [pratirodh/cli.py](pratirodh/cli.py): authoritative available CLI flags for this checkout.
- [pratirodh/projects/manifest.py](pratirodh/projects/manifest.py): authoritative intake and initial manifest defaults for this checkout.
- [pratirodh/projects/evaluation.py](pratirodh/projects/evaluation.py): scheduler and campaign requirements.

### Evidence to request or regenerate

These files are provenance references. Unless the project lead shares them separately, teammates should expect to regenerate evidence in their own environment. The dated summaries above explain the current results without requiring access to these files.

| Location relative to the specified checkout | Source |
|---|---|
| Desktop `run_output/demo-ready-20261002/summary.json` and `evidence/` | Nine recorded synthetic demo decisions |
| Desktop `run_output/model-smoke-demo-ready-20261002/summary.json` | Blocked default-model smoke preflight |
| Desktop `presentation/PRATIRODH-Presentation-Package.zip` | Existing presentation package |
| Final `run_output/upstream-validation/qualification-index.json` | Latest inspected case qualification index |
| Final `run_output/upstream-validation/status.json` | Older saved campaign counters/configuration |
| Final `run_output/pratirodh/runs/<run_id>/report.json` | Reports referenced by qualification records |
| Final `run_output/implementation-tests.log` | Saved 145-pass/one-failure suite result |
| Final `benchmark/recipes/<case>/` | Upstream preparation and current audit files |

**Maintenance rule:** when code, evidence, worktrees, or infrastructure changes, update the snapshot date and the affected claims together. Preserve the distinction between inspected implementation, saved results, live verification, and future plans.
