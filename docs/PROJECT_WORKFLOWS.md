# PRATIRODH project workflows

The version 2 manifest extends the historical single-file demo contract. The new workflows are experimental until the external release acceptance cohort passes. A successful synthetic run is a working prototype demonstration, not an external evaluation result.

## Controller and worker boundary

`projects/manifest.py` inventories UTF-8 projects, excludes generated/dependency directories, rejects source symlinks and obvious credential files, and binds every included file to SHA-256. The supported build layouts are Python with pytest, npm with package-lock.json and a declared test script, and CMake/CTest with Clang. Other layouts produce an unsupported intake result. The prototype intake limit is 1,000 files, 1 MiB per file and 10 MiB total.

The operator reviews the manifest outside target code. `commands` contains argument arrays rather than shell strings. `editable` enumerates existing source files. Tests, specifications, fixtures, harnesses, dependency locks, build configuration and other non-source files are protected. Commands, properties and resources cannot be authorized by repository text or model output.

Configure an operator-provided disposable Linux VM or dedicated worker with a Docker context. The controller uses that context to inspect and run an already-prepared image. Neither the Docker socket nor controller directories are mounted into target containers. The execution worker gets a source snapshot and approved commands over standard input. The private signing key stays in the controller.

Every execution uses a read-only container root, no external network, an unprivileged target UID, no added target privileges, PID/CPU/memory limits, bounded output, per-command timeouts, and bounded scratch filesystems. A trusted supervisor creates root-owned immutable source/tests, then permanently changes to UID/GID 65534 before running any target command. C/C++ builds use a separate executable scratch directory. Target descendants and containers are removed on completion/cancellation. OS file locks enforce two worker slots and one model generation across controller processes.

`--demo-worker` explicitly allows the shared local Docker VM for controlled synthetic examples. It records `DEMO_ONLY` assurance. A context name is operator configuration, not proof that its host is isolated. Dedicated infrastructure placement, firewall rules, host administration and image provenance remain operator responsibilities. No readiness claim certifies containment against kernel or runtime vulnerabilities.

## Dependency preparation

Prepare dependencies separately on the dedicated worker. Start with `pratirodh project build-worker --context pratirodh-worker`, then build a derived image containing the project's reviewed dependencies. Python dependencies belong in the image's Python environment. Locked Node dependencies belong at `/opt/dependencies/node_modules`; the worker exposes that immutable directory to the project. C/C++ development libraries also belong in the image. Record resolved versions and the actual image ID in `dependencies.resolved`, `dependencies.image_digest` and `image`.

Dependency fetching needs an operator-enforced restricted preparation network or offline package cache. PRATIRODH does not install project dependencies during target execution, download models during repairs, or run build scripts on the controller. The bundled Dockerfile prepares prototype tools using package repositories; it is not a locked application dependency image or a substitute for an operator's restricted production preparation process. Missing packages produce incomplete evidence. No automatic host or cloud fallback exists.

## Security properties and harnesses

Each property has an ID, a separate violation kind, an optional CWE, a description, provenance and approval. Required provenance fields are `kind` (`operator` or `trusted-specification`), `reference` and `approved: true`. A model-authored property remains a proposal until approved.

The current executable oracle is exact command exit and stdout. It is useful for libraries, CLI applications and reviewed HTTP test scripts, including Flask/FastAPI TestClient harnesses. More complex security assertions should be implemented in protected, operator-reviewed scripts. A property contains:

```json
{
  "id": "tenant-isolation",
  "kind": "authorization",
  "description": "Only the synthetic account owner can access that account",
  "provenance": {"kind": "operator", "reference": "reviewed specification v1", "approved": true},
  "target_files": ["policy.py", "users.py"],
  "harness_review": {"approved": true, "reference": "reviewed direct calls to application functions"},
  "control": {"command": ["python", "portal.py", "admin", "admin"], "exit": 0, "stdout": "GRANTED\n"},
  "reproducer": {
    "command": ["python", "portal.py", "admin", "guest"], "exit": 0, "stdout": "DENIED\n",
    "violation": {"exit": 0, "stdout": "GRANTED\n"}
  },
  "variations": [{"command": ["python", "portal.py", "alice", "bob"], "exit": 0, "stdout": "DENIED\n"}]
}
```

The violation oracle must differ from the safe oracle. A crash from a broken harness is not a reproduced authorization failure. Qualification requires all controls and violation observations to match in three clean worker executions, along with an operator review confirming target invocation and failure origin. This review is essential: stdout alone cannot mechanically establish that arbitrary harness code actually reaches the intended application.

Use `pratirodh project harness --language python --module package.parser --function parse_bytes` to propose a callable fuzz target. Python proposals use Atheris, Node proposals use Jazzer.js, and C/C++ proposals use a libFuzzer entrypoint. Proposals require adaptation to the target signature, compilation, execution, control-input review and approval before adding them to the manifest. Add approved fuzz actions to `fuzz` with `tool`, `command`, `approved: true` and `reference`. Fuzz crashes are observations until an approved property reproduces them; this prototype does not infer authorization invariants from crashes or claim coverage measurements it did not collect.

HTTP services may use `commands.startup` plus `service_ready_url` (worker-loopback HTTP, returning 200). The worker starts services only after build commands, waits for readiness, runs the approved check, bounds service log output, and terminates services. Schemathesis can be prepared in the image and invoked as an approved fuzz action. A schema-conformance result is not an authorization or business-property result. Multi-container database service networks are not yet implemented; a project needing one remains unsupported until an appropriate service arrangement is supplied.

## Investigation and verification

The engine records intake, baseline, static inspection, harness qualification, reproduced findings, bounded minimization, proposals, verification, mutation challenges and evidence. Python static inspection uses Bandit when available. C/C++ inspection creates ASan/UBSan compiler settings. Node syntax/build checks use the project's approved commands and TypeScript compiler when configured. Static allegations remain separate from confirmed executable findings.

Discovery searches approved executable properties and approved fuzz harnesses. Optional manifest flags `model_analysis: true` and `generate_harnesses: true` request bounded local-model allegations and harness source proposals. These consume the same call budget, are retained as unconfirmed/proposed artifacts, and never authorize new execution or readiness. The operator must review and approve a new manifest before proposed harnesses become executable inputs. The system does not autonomously establish a trusted security specification. If no approved violation reproduces, the result is `No violation found within this search` or an unresolved/missing-property reason, never a secure-project certificate. Broad coverage-guided search and general delta debugging are not complete in this prototype. Minimization currently tries only operator-approved argument reductions and never claims global minimality.

Candidates come from supplied diffs, report-supplied exact replacement templates or the local model. Model context excludes test source, fixture contents, formal assertions and final audits. It contains selected editable source, property descriptions and reproducer commands. The current context selection is file-scoped; a full semantic cross-language call graph is future work. Models propose complete file contents or unified diffs; the controller generates exact reviewable diffs and applies them to copies. Attempts to edit protected inputs, add/delete files, change modes, escape paths or introduce common check suppressions are rejected. Suppression heuristics do not replace behavioral verification.

A candidate must pass its build, existing tests, every approved control, the original reproducer and all approved variations. The original violation is requalified for each candidate. Every declared mutation family must be available, demonstrate the relevant violation while preserving its control, and be caught by the security verifier. Equivalent, invalid and unconfirmed mutations are retained and do not count as caught. A correct repair can remain unresolved when its source does not match an approved mutation pattern; this is a disclosed verifier limitation.

Formal actions are optional required checks once declared. CrossHair and CBMC must already be installed in the prepared image. Each action records its property, assumptions, bounds, arguments and raw observations. CBMC needs `--unwind` and `--unwinding-assertions`; successful explicit output is reported only as `BOUNDED_PROPERTY_VERIFIED`. CrossHair searches and inconclusive tool outputs do not authorize a proof. Timeouts, missing tools and empty/inconclusive success output stay unresolved. No result proves the whole application secure.

## Models and budgets

The default is `laptop`: Qwen2.5-Coder 7B, 8,192 context tokens. `alternative` (Qwen3.5 9B) stays experimental. `linux-large` (Qwen3-Coder 30B A3B) requires memory and measured latency preflight. `prototype-small` is a separately labeled experimental Qwen2.5-Coder 3B profile for machines with only that model installed; it does not satisfy the planned default-model release evaluation.

The controller supports Ollama and a local llama.cpp server. Endpoints must be loopback HTTP without credentials or redirect paths. Model and runtime identifiers, SHA-256 digests, quantization and declared available memory are required. Ollama preflight checks the installed model digest and quantization; local binary hashes are checked for both runtimes. llama.cpp also checks a local GGUF hash and server health. These checks do not attest which binary a separately managed live server process is executing; operate that process from the recorded immutable artifacts. No paid-provider fallback is used by version 2 workflows.

Limits are 30 minutes, eight calls, three candidate attempts, a five-minute per-call ceiling, one concurrent generation and a final ten-minute verification reserve. Failed calls count. Generation stops at the reserve. Cancellation retains signed partial evidence. Resume makes a new signed record, requires unchanged source/manifest, reexecutes checks and carries forward time/call/candidate consumption. Model cancellation may wait until the bounded HTTP call returns.

## External evaluation

`pratirodh project-benchmark --manifest campaign.json --freeze-only` validates case provenance and freezes source, manifest and audit hashes. A complete cohort requires two development and six evaluation cases per language (24 total), with licensed upstream advisory/fix URLs and disclosed adaptations. The tool validates metadata; operators must independently check licenses and reproduce upstream behavior. No synthetic fixture should be relabeled as an upstream case.

Each evaluation case is scheduled round-robin for three repetitions of repair/discovery in expanded/model-only arms. Both arms use the same independent verifier and final audit; the model-only arm proposes without discovery feedback. The campaign has a twelve-hour total cap and final-audit reserve, writes checkpoints atomically, and retains unstarted, failed and unresolved rows. The final audit resides outside the source tree and uses a separate dedicated Docker context. It receives only signed candidate artifacts and its own protected assertions. Audit inputs are not passed back to generation/development verification or model prompts.

Release completeness requires the complete cohort, all scheduled runs/audits, repair and discovery generated successes in every language, and passing separate audits for every ready row. Partial campaigns remain partial. Language status remains experimental until acceptance is demonstrated. Case-level raw repetitions are retained; confidence intervals, gold-fix correctness analysis, measured peak memory and a completed 24-case upstream corpus remain external evaluation work. Any tuning following evaluation requires a new versioned manifest and label.

## Evidence and compatibility

Version 1 demo evidence remains readable. Version 2 reports include source revision/inventory, adapter, manifest, provenance, reproductions, multi-file patches, candidate snapshots, mutation/formal results, model usage, limits, elapsed time and explicit unknown measurements. The controller signs the artifact inventory with Ed25519. The external public trust fingerprint must be preserved separately. Signatures establish integrity, not correctness of assertions or identity certification.

`pratirodh export RUN_ID --output evidence.zip` validates the record and exports artifacts plus `trust.pub`; it excludes the private key. The original project is never modified by a repair. Approval, applying a patch, committing and publishing are separate actions.

Set `PRATIRODH_READ_ONLY=1` for read-only evidence deployments. All POST actions then fail closed. This implementation request makes no commits and performs no publication.
