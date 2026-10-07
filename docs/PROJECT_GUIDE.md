# PRATIRODH Project Guide

## Purpose and release scope

PRATIRODH helps a developer decide whether a proposed security repair has enough executed evidence to enter human review. It checks the repair against independent requirements, deliberately weakens copies of the repair, and tests whether the verification suite catches those confirmed weaknesses. It keeps request results and source snapshots in signed evidence bundles and refuses to replay a recommendation when its relevant inputs have changed.

This guide is the main technical and presentation reference for the Derby University Cyber AI Hackathon project. It covers the problem, product, implementation, installation, security controls, deployment, evaluation, live demo, recording script, and planned slide content. The release is a working prototype for controlled single-file Python Flask applications with SQLite and fixture files. It supports SQL injection (CWE-89), path traversal (CWE-22), controlled command injection (CWE-78), and embedded credential repair (CWE-798). It does not certify arbitrary applications or automatically deploy repairs.

The working product name is PRATIRODH. Historical source is supplied separately as the pinned archive described in the root README; it is not included in the public release. Historic claims about autonomous merging, military deployment, air gaps, and universal proof are not claims about this release. The active verifier and CLI live in the pratirodh package. Unused earlier application modules and launchers are excluded from the public release.

## Offline repair release and operating choices

Release 0.2 adds a complete local workflow: static detection identifies suspicious source patterns; Ollama proposes a repair; Docker executes independent security and functionality checks; a human records a review of fresh signed evidence. Detection is evidence of a candidate issue, not an executed exploit. A disappearing scanner finding does not establish a successful repair.

The release branch is `codex/pratirodh-offline-pipeline`. Use the project directory for commands below.

Docker isolates target execution on the laptop. Docker Compose starts the review service. Kubernetes manages deployments across clusters and is deliberately outside this laptop release. Native Ollama avoids adding a second inference container and uses the downloaded qwen2.5-coder:3b model. Its download is about 1.9 GB; runtime memory is higher. The local model uses a Qwen research license, retained in docs/OLLAMA_MODEL_LICENSE.txt after setup. Do not substitute licenses from another model size.

## Offline setup and runtime

Run setup-offline.ps1 once while online to install native Ollama, disable cloud features in its configuration, and download qwen2.5-coder:3b. The server binds to 127.0.0.1:11434. Restart an already running Ollama server after configuration changes. The adapter uses a fixed loopback endpoint, disables HTTP proxies, prohibits redirects, and refuses missing or cloud model tags. There is no automatic cloud fallback.

Use start-demo.ps1 to prepare pinned Python dependencies and the runner image. Dependency installation and model downloads require connectivity; repair and verification runtime use the prepared local resources. Doctor checks the image, tools, native server version, and model digest. Setup failure does not invalidate the separately labeled curated demonstration.

```powershell
./setup-offline.ps1
./start-demo.ps1
python -m pratirodh doctor
python -m pratirodh scan benchmark/scenarios/cwe-78-development-01
python -m pratirodh pipeline benchmark/scenarios/cwe-78-development-01 --contract benchmark/scenarios/cwe-78-development-01/contract.json
```

The pipeline command requires an unchanged registered contract. Unsupported findings are displayed as UNVERIFIED with verification_supported=false. The CLI scan does not execute target code. The dashboard permits execution only for catalogue fixtures and rejects arbitrary target paths or uploads. Local execution stays behind host and CSRF controls; hosted review rejects all execution POST requests.

## Model boundaries and failure handling

The common provider interface supplies bounded JSON suggestions. New repair commands default to Ollama; --provider gemini or --provider openai-compatible deliberately selects a cloud adapter. Model output may contain the complete repaired source or a unified diff. Complete source is converted to a diff and subjected to the same single-entrypoint policy, syntax validation, static checks, and isolated execution.

One generation runs at a time. Temperature and seed are zero, context is 8192 tokens, output is capped at 2048 tokens, and the conservative input allowance is 16000 UTF-8 bytes. Oversized context is rejected, never silently truncated. Each generation is capped at 180 seconds. Two repair attempts and a ten-minute overall workflow budget bound local repair. Token counts, parameters, provider, model digest, server version, durations, and failed call status appear in signed evidence.

Repair prompts receive source and compact public requirements. They do not receive held-out requests, probe dictionaries, mutation transformations, or expected security witnesses. Retry feedback describes failed property categories, not detailed held-out inputs. The model does not author trusted contracts or modify fixtures and assertions. Alternative correct coding styles may produce unavailable mutation patterns and therefore insufficient evidence; this is an explicit limitation of pattern-based qualification.

## Property-based security fuzzing

Full mode executes mandatory cases and reviewed probes, qualifies declared weakened copies, and spends the remainder of a 64-request additional budget on seeded input variations. Qualification requests count against that budget. Unguided mode spends the same 64 requests on variations without mutation qualification. Both arms share mandatory checks and candidate patches. Static and fixed modes remain weaker baseline comparisons.

The generator combines trusted attack seeds with percent encoding, repeated encoding, leading and trailing spaces, altered separators present in the seeds, suffixes, shortened inputs, and bounded lengths. Seed and generator version make requests reproducible. Every variation references a trusted security assertion. Requests run in restricted Docker containers and their observations are interpreted in the controller. This is seeded property-based security fuzzing, not coverage-guided fuzzing.

Errors, timeouts, missing effects, and server failures do not count as protection. Unavailable observations cause incomplete evidence. Failed requests and observations are retained and replayable while evidence is fresh. The minimizer tries at most eight reductions and retains only observed security violations; it does not claim global minimality.

## Command injection and credential verification

CWE-78 fixtures execute harmless printf commands in a disposable Linux container. Legitimate allowed input must return the declared string. Attack seeds attempt to create marker.txt using shell separators or substitution. For version-2 cases, a supervisor creates a private fixture root and starts a separate target process per side-effect case. Credential requests are batched only within an isolated environment profile. After the side-effect target process exits, the supervisor inspects the forbidden file; target-produced response fields cannot replace this observation. Network access, host targets, signing keys, and privileged mounts are absent from the runner.

Command repair examples include disabling the endpoint, blocking one separator, retaining shell evaluation, and a correct fixed command argument list with input validation. A crash alone is not a security witness. The supervisor is stronger than trusting target-returned effect metadata, but this trusted-fixture system is not intended to contain arbitrary hostile uploaded programs or operating-system sandbox escapes.

CWE-798 fixtures contain synthetic credentials only. Configured and rotated profiles must authorize their exact current secret. Wrong, old, prefix-extended, and missing-configuration requests must deny access. The repair must remove declared embedded credential values from source and fail closed without a configured secret. A prefix comparison is a misleading repair because it accepts additional incorrect input.

Six scenarios per new class are divided into three development and three held-out variants. Each has correct, incomplete, insecure-alternative, and functionality-breaking patch labels. The full catalogue contains 36 scenarios and 144 curated candidates. These are related constructed families; public labels and shared structure constrain generalization. CWE-94 and CWE-502 detection remains informational, with verified repair deferred.

Removing a credential from source does not revoke a previously exposed value, remove Git history, or rotate other deployed copies. Operators must separately rotate real credentials and review exposure. All credentials used by this evaluation are synthetic fixture values and must never be replaced with real secrets.

## Human review and freshness

```powershell
python -m pratirodh review RUN_ID --action approve --reviewer TeamReviewer --rationale "Reviewed fresh fixture evidence"
python -m pratirodh review RUN_ID --action reject --reviewer TeamReviewer --rationale "Needs additional validation"
```

Approval requires READY_FOR_REVIEW, valid signatures, and current bindings. A review is a separate signed immutable record linking the original inventory digest. It records an operator label and rationale, with identity_verified=false. There is no source promotion or deployment action. Reject records can document a concern about earlier evidence without implying that it remains current.

The dashboard shows generation origin, detector candidates, stages, proposed changes, individual failures, fuzzing budgets, and qualified weakened repairs in Challenge the fix. Freshness identifies changed target, contract, runner, image, Python, or tools. Model provenance is captured in the signed report; it is not a claim that future generation will return the same patch.

## Offline verification and its exact scope

The real local-generation cohort can be run with ./.venv/Scripts/offline-python.exe tools/offline_guard.py. A Python audit hook denies external socket connections while permitting loopback and Docker CLI subprocesses. The script verifies a denied external connection and records all eight local attempts. Native Ollama has cloud features disabled and the selected model is present locally.

The session itself is not elevated. The operator applied the supplied rules in an administrator PowerShell. A dedicated CPython executable was required because the standard Windows virtual-environment launcher forwards execution to its base interpreter. The dedicated executable successfully connected to loopback and its external TCP attempt was denied, while the control interpreter retained connectivity. deploy/offline-firewall.ps1 provides reversible program-specific rules for a dedicated Python executable and Ollama. Use an elevated PowerShell for an additional offline rehearsal, then remove only those named rules. Avoid applying the Python rule to an interpreter used by unrelated sessions. Do not describe process-local guarding as an operating-system firewall or make an unverified air-gap claim.

## Windows offline rehearsal commands

Create the project virtual environment with start-demo.ps1, then prepare the dedicated native executable. The helper copies the CPython executable and required DLLs into the ignored virtual environment; it does not replace the standard launcher or alter the Desktop checkout.

```powershell
python tools/prepare_offline_interpreter.py
```

In an administrator PowerShell, change to this worktree and run the following command. ExecutionPolicy Bypass applies to this invocation only; it does not change the system policy. Use the real worktree path when changing directories.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./deploy/offline-firewall.ps1 -PythonPath ./.venv/Scripts/offline-python.exe
```

Run the genuine local cohort from the normal project terminal. It records every attempt and an external-denial check while preserving loopback inference and local Docker access.

```powershell
./.venv/Scripts/offline-python.exe tools/offline_guard.py
```

The two named rules remain enabled after the rehearsal. To remove only those rules, use the administrator terminal again. Remove them before requesting a new model download; setup skips downloads when the selected model is already present.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./deploy/offline-firewall.ps1 -PythonPath ./.venv/Scripts/offline-python.exe -Remove
```

## Expanded demo and slide changes

Keep the original three-run curated demo to explain verification clearly. Add a genuine local pipeline run or its previously captured signed evidence, labeling whether the model repair was rejected, insufficient, or ready. Then demonstrate command-effect checks, configured/missing/rotated credentials, a fresh review record, and refusal after relevant inputs change. A failed model repair is useful evidence of the gate when explained accurately.

Update the existing video storyboard with a short offline generation segment and the two new classes. The PPT architecture slide should show native Ollama, the controller, the Docker runner, and the read-only review deployment. The AI slide must state actual model outcomes and budgets; the evaluation slide must compare equal additional request budgets and disclose synthetic families. Retain the organizer's template and manually assemble the PPT according to its rules.

## The problem we are solving

AI tools can generate a patch quickly. A successful scanner result or one passing security test does not establish that the repair is complete. A patch can block one particular input while leaving another path to private data. It can also stop an attack by disabling the feature that legitimate users need.

PRATIRODH addresses the evidence behind a repair recommendation. Its intended users are developer teams reviewing security changes in small Python web applications. A developer supplies trusted requirements that define permitted behavior and protected records or documents. The verifier executes the actual application with synthetic fixtures and compares observed results with those requirements.

The campus demonstration uses course notes and fictional student records. Protected data contains a unique canary marker, rather than real personal information. A response containing that marker demonstrates a violation of the declared confidentiality requirement. A changed response alone is not treated as a successful repair. Legitimate responses must match the expected status and body, and server errors cannot satisfy the contract.

## Product contribution and AI role

The central contribution is the connected review workflow: reproduce the original violation, evaluate a candidate, qualify deliberately weakened variants, challenge the tests, strengthen the checks, preserve the observed evidence, and bind it to the version and environment tested.

Mutation testing is established research. Automatic repair and AI-assisted test generation are also established. We should describe PRATIRODH as an implementation and evaluation contribution combining these ideas for a narrow Python web-security workflow. We should not claim that we invented security mutation testing or that the system is globally unique.

The optional cloud adapter can generate up to two candidate unified diffs and structured request cases. Model output cannot modify the contract, expected results, fixture definitions, runner code, or trusted assertion library. Model-generated requests must reference existing security assertions. They are data interpreted by the trusted runner, not arbitrary generated test scripts.

The repeatable dashboard demo uses deliberately curated patches and synthetic data. It makes zero model calls. This makes the verification story reliable without implying a live AI call happened. A separate real local-generation cohort records Ollama attempts. Cloud adapters require explicit provider selection and configured credentials. Report the model, call outcomes, and token metadata for those runs separately. No accuracy claim about AI patch generation follows from the curated benchmark.

## Repository and architecture

The controller and dashboard run on the operator machine. Target source runs in restricted Docker containers. Assertions run in the controller against structured responses, outside the target process. The deployed review service is a separate, read-only dashboard without Docker access.

The principal modules are:

- pratirodh/contracts.py validates the manifest and evaluates exact and security assertions.
- pratirodh/patches.py validates a unified diff, applies it to a temporary copy, compiles the result, and runs Bandit.
- pratirodh/execution.py launches restricted containers and enforces execution budgets.
- pratirodh/worker.py constructs temporary fixtures and executes Flask test-client requests in child processes.
- pratirodh/engine.py coordinates baseline reproduction, candidate verification, qualified mutations, stronger checks, and decisions.
- pratirodh/provider.py implements loopback-only Ollama and explicit cloud adapters with bounded calls.
- pratirodh/evidence.py hashes artifacts, signs inventories, verifies integrity, and checks freshness.
- pratirodh/minimize.py performs a bounded reduction of an already recorded failure request.
- pratirodh/benchmark.py compares the supplied patch cohort across verification modes.
- pratirodh/cli.py and __main__.py provide commands and exit statuses.
- pratirodh/web.py, templates, and static assets provide the local and deployed dashboards.
- benchmark/catalogue.json registers 36 scenarios and their curated candidate labels.
- tests/test_pratirodh.py and tests/test_security.py cover verification and deployment controls.

The execution flow is: trusted contract and original source, baseline execution, candidate diff validation, disposable candidate copy, request assertions and static scan, mutation qualification, stronger request assertions, decision, signed evidence, human review.

## Verification procedure in detail

First, validate the manifest. Contracts versions 1 and 2 are supported for four declared CWE classes. Version 2 adds independently observed fixture effects and synthetic environment profiles. The only editable file must be the Python entrypoint. Fixture paths must be relative and remain within their fixture tree. Symlink fixtures may resolve to another fixture, but cannot escape the temporary fixture root. Case IDs must be unique. Requests are GET or POST with query, form, or JSON objects. Security cases must reference security assertions; legitimate cases must reference exact assertions.

Second, execute the original program. All legitimate baseline cases must pass. At least one initial attack must reproduce a declared violation: disclosure, forbidden fixture creation, or unauthorized access. Startup failure, mismatched output, timeout, or an unreproduced original issue leads to insufficient evidence. The verifier does not assume a labelled target is vulnerable merely because its scenario says so.

Third, stage a candidate. Diff metadata is inspected by Git. Only textual changes to the allowlisted entrypoint are accepted. Renames, copies, binary changes, new files, deletion, and mode changes are prohibited. Git applies the patch in a temporary directory, and Python parses the result. The live source file is never replaced. A prohibited or invalid supplied patch is rejected and its diff retained.

Fourth, run the initial cases and Bandit on the candidate. Legitimate cases compare exact body and status. Security cases require an allowed HTTP status and exclusion of every protected marker. A 500 error is a failure, not successful protection. Missing or malformed results are execution errors. Responses larger than the evidence limit are errors rather than silently truncated successes. Medium or high Bandit findings reject the candidate; low findings are recorded for review.

Fifth, in full mode, execute all registered reviewed probes against the real candidate. These deterministic probes are added immediately; no discovered witness is hidden to make the result look favorable. The current release strengthens the suite using trusted scenario probes and mutation witnesses. It does not autonomously invent a new security property.

Sixth, apply each declared weakening transformation to a copy of the candidate. A transformation must match exactly once and produce valid Python. The mutant must preserve all declared benign behavior and demonstrate a declared security violation through one of its witness requests. Only then is it labelled CONFIRMED_UNSAFE. Invalid, unavailable, and unconfirmed variants are evidence gaps. They do not count as caught weaknesses.

Seventh, compare qualified mutant results with the initial and strengthened suites. A mutant missed by the initial suite exposes weak verification. A confirmed unsafe mutant surviving the strengthened suite means insufficient evidence. A surviving mutant does not, by itself, prove the real candidate is vulnerable. Conversely, an actual candidate security failure rejects the candidate even if some mutation families cannot be instantiated.

Finally, seal the report and artifacts. For model repairs, a rejected first candidate can inform one additional request using only summarized property failures; held-out requests and mutation witnesses are withheld. All candidate attempts remain in the report. Human review remains the final release boundary.

## Decision meanings

REJECT means a mandatory candidate check failed: a protected-data requirement, legitimate behavior, static security scan, or patch-edit policy. Passing checks never compensate for a failed mandatory check.

INSUFFICIENT_EVIDENCE means the required evidence is incomplete. Examples include unavailable Docker, failed execution, unreproduced baseline, missing mutation patterns, unconfirmed variants, surviving variants, malformed model output, or exhausted budgets. Empty checks and zero usable challenges cannot produce readiness.

READY_FOR_REVIEW means every required check for the selected verification mode passed and no recorded gap remains. The mode matters: static and fixed modes are intentionally weaker experimental baselines. A full-mode recommendation also requires successful qualification and detection of every declared challenge family. The dashboard displays the mode beside the outcome. Use full mode for the product demonstration and developer decisions.

Readiness is a review recommendation within the declared scope. It is not deployment authorization, a mathematical proof, or a guarantee that undiscovered vulnerabilities do not exist.

## Installation and local startup

Use Python 3.11 or newer, Git, and Docker Desktop configured for Linux containers. Start Docker Desktop before building the runner. No GPU or cloud account is needed for the curated demo. Internet access is needed for initial dependency and image installation; subsequent curated runs can execute locally with their prepared dependencies.

From the repository root on Windows:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-deploy.txt
./.venv/Scripts/python.exe -m pratirodh build-runner
./.venv/Scripts/python.exe -m pratirodh doctor
./.venv/Scripts/python.exe -m pratirodh serve
```

Open http://127.0.0.1:8765. The start-demo.ps1 script performs this setup and starts the same production WSGI server. It does not open the application on an external interface. If that port is busy, use serve --port 8767. The default listener is loopback.

On Linux, use python3 -m venv .venv, activate the environment, install requirements-deploy.txt, build the runner, and run python -m pratirodh serve. Commands below also work with the environment's Python executable on Windows.

Use the pinned deployment requirements for a reproducible environment. Historical dependencies are locked in the baseline record and installed only inside the disposable baseline image. An editable development install is available with python -m pip install -e ., but the fully pinned file is the release reference.

## Command reference

Verify a supplied corrected patch:

```powershell
python -m pratirodh verify-patch benchmark/scenarios/cwe-22-development-01 --contract benchmark/scenarios/cwe-22-development-01/contract.json --patch benchmark/scenarios/cwe-22-development-01/patches/correct.diff
```

Replace correct.diff with incomplete.diff to demonstrate the rejected repair. The command prints the report including its 32-character run ID. Exit code 0 means ready for review; exit code 2 means rejection or insufficient evidence. Automation must read both mode and decision, rather than interpreting any passing baseline as full verification.

Other commands are:

```powershell
python -m pratirodh replay RUN_ID --case probe-symlink
python -m pratirodh verify-evidence RUN_ID
python -m pratirodh minimize RUN_ID --case probe-symlink
python -m pratirodh benchmark --split all --output run_output/benchmark.json
```

Replay re-executes a saved case against the saved candidate after verifying the bundle and its freshness. It returns the new observation and previously recorded status. Replay does not overwrite the signed report. Minimize accepts a recorded failing security case, tests up to eight reduced request variants, and keeps a shorter request only when execution still reproduces an observed security violation. It does not establish global minimality.

build-runner prepares the target image. doctor checks Git, Bandit, and the runner image. serve uses Waitress, with debug mode and tracebacks disabled. --mode static runs legitimate cases and scanning; fixed includes the initial security cases; ai optionally adds model-suggested cases; full adds reviewed probes and qualified mutations. full is the default.

## Optional cloud integration and configuration

Cloud calls happen only when a cloud command or AI benchmark is invoked. Configure GEMINI_API_KEY in the shell and optionally PRATIRODH_MODEL. The current adapter default is gemini-3.8-flash. Availability depends on the provider and account; a provider failure is retained as insufficient evidence rather than fabricated output.

```powershell
$env:PRATIRODH_MODEL = 'gemini-3.8-flash'
python -m pratirodh run benchmark/scenarios/cwe-22-development-01 --contract benchmark/scenarios/cwe-22-development-01/contract.json --provider gemini
```

For an OpenAI-compatible service, configure PRATIRODH_API_URL as an HTTPS chat-completions endpoint and PRATIRODH_API_KEY, then pass --provider openai-compatible --model YOUR_MODEL. The provider URL is operator-controlled. URL credentials and redirects are prohibited. The adapter sends source and contract context to the selected service, so only use material authorized for that destination. Target processes receive neither model credentials nor a Docker socket.

The execution budget is five minutes for supplied-patch verification and ten minutes for generation workflows, two repair candidates, four total model calls including failed calls, at most six declared mutation families, and at most 100 distinct request definitions in a candidate batch. Version-1 target batches time out after 15 seconds; version-2 isolated groups have a ten-second observation timeout. Target source is limited to 256 KB; supplied diffs to 128 KB; cloud model prompt to 64 KB and local prompt to 16000 UTF-8 bytes; request definitions to 8 KB; recorded response bodies to 64 KB. A bounded semaphore allows two concurrent containers inside one controller process. Operate one execution controller per workspace; independent CLI processes do not share that semaphore. The dashboard queues one demo at a time.

The prototype bounds calls and time, rather than enforcing a monetary billing limit. Configure spending controls in the provider account. Token usage is recorded when the provider supplies it; missing metadata is not zero tokens. Do not put API keys into source files, command screenshots, or submission materials.

## Evidence format and lifecycle

The default store is run_output/pratirodh. Each run has an exclusive runs/RUN_ID directory containing original.py, contract.json, candidate diffs and sources, generated mutant sources when available, observed.json, report.json, inventory.json, and signature.hex.

Each inventory maps filenames to SHA-256 hashes. The Ed25519 signature covers the canonical inventory. load verifies the external public key, signature, exact file inventory, and every file hash before returning a report. Added files and changed bytes invalidate the bundle. Read-only file attributes discourage accidental modifications; they are not protection against an administrator or malicious local account.

The trust.pub file is outside the signed run. Preserve its SHA-256 fingerprint in a separate trusted channel before third-party verification. The signing.key file remains private and is not included in the dashboard container. OS file permissions must protect it; Windows deployments should restrict its ACL to the operator. Replacing both a bundle and its trust anchor defeats trust unless the independently saved fingerprint is checked.

Freshness includes relevant target source/config/dependency files, contract bytes, Python runner code, installed Flask/Bandit/cryptography/Waitress versions, Python version, and Docker image identity. A relevant change marks the recommendation stale and prevents replay. It does not automatically establish a new vulnerability. Re-run verification to create a new signed record. Preserve the original record for provenance.

The read-only deployed service verifies artifact integrity but does not have the local execution environment or Docker. It conservatively displays execution freshness as stale or unavailable and disables execution through its POST policy. Local current evidence and deployed archival evidence are distinct states.

## Benchmark and evaluation method

The expanded catalogue has 36 synthetic scenarios: twelve each for SQL injection and path traversal, and six each for command injection and embedded credentials. Eighteen are development cases and eighteen are held-out cases. Each has four curated patches: correct, incomplete, functionality-breaking, and insecure-alternative. This produces 144 labelled candidates and 576 evaluations across static, fixed, full, and unguided modes. The original 0.1 cohort is preserved separately.

The scenarios vary query/form/JSON transport, direct and encoded handling, fixture paths, Unicode, SQL construction, command separators, and synthetic credential profiles. They are related constructed families, not independent real-world vulnerabilities. Labels and files are public. A held-out split describes evaluation partitioning; the repository cannot mechanically guarantee blind human development.

The benchmark saves raw rows after each completed evaluation so interrupted work remains inspectable. A row includes scenario, split, candidate label, mode, decision, evidence run ID, gaps, runtime, candidate check count, mutation misses, model calls, and reported usage. Request execution counts include mutation qualification; the additional_requests field records the equal 64-request allowance for full and unguided modes.

Report correct readiness, incorrect readiness, correct rejection, abstentions, and runtime together. A system abstaining on everything is not successful. Full verification executes more deterministic challenges than fixed checking. The equal-budget comparison charges qualification against full mode and gives unguided mode the same number of additional requests. Both use identical mandatory checks, patches, and partitions. Similar outcomes do not establish a benefit from mutation guidance. Timing includes concurrent evaluation load and is not a controlled latency measurement.

The AI baseline is NOT_RUN unless --cloud is explicitly supplied. Actual model-generated repairs form a separate cohort. The release results section at the end of this guide is generated from measured local outputs, rather than illustrative percentages.

## Security review against OWASP Top 10 2025

The review uses the 2025 awareness categories from https://top10.owasp.org/2025/0x00_2025-Introduction/. It covers the new controller/dashboard/provider/evidence package and deployment configuration. Intentionally vulnerable benchmark fixtures are test inputs and are excluded from the application scanner. Legacy historical baseline modules are retained for provenance and are not the deployed application.

### A01 Broken Access Control

Only registered scenario IDs are accepted by dashboard demo submission. Run IDs are restricted to 32 hexadecimal characters; artifact names are simple filenames. The patch policy allows exactly the declared entrypoint. Dashboard hosts are allowlisted. The deployed application requires authentication and rejects every POST in read-only mode. There is one operator role; per-user RBAC and multi-tenant isolation are not implemented.

### A02 Security Misconfiguration

Waitress replaces Flask's development server. Debugging and exposed tracebacks are disabled. Cookies are HttpOnly and SameSite Strict, and production cookies are Secure. Responses include CSP, framing protection, no-sniff, no-referrer, no-store, and restrictive permissions. Production startup fails when secrets are missing or too short. Docker deployment is non-root, read-only, resource-limited, and loopback-bound behind the HTTPS proxy. External fonts and inline refresh scripts were removed so the dashboard works with a self-only CSP.

### A03 Software Supply Chain Failures

Deployment Python packages are version-pinned and audited. The Python base image is pinned by digest. The target image has explicit framework versions. CI runs tests, dependency audit, scanning, and image build. Refresh dependencies and base-image digests deliberately; pins improve reproducibility but do not make dependencies permanently secure. The current audit found vulnerable Click and cryptography versions, which were upgraded before release checks were repeated.

### A04 Cryptographic Failures

Evidence uses SHA-256 and Ed25519, with an independent public-key fingerprint. Production access must be served through TLS. Credentials and the signing key stay outside source control and target containers. The prototype signing key is not encrypted at rest; secure operator filesystem permissions and backups are required. A signature establishes integrity relative to a trusted key, not universal correctness or certified operator identity.

### A05 Injection

Subprocess calls use argument arrays with shell execution disabled. Git validates patch scope before application. SQLite index operations use parameters. Jinja templates autoescape displayed scenario text and evidence. Model requests are structured data tied to trusted assertions. The provider accepts HTTPS operator endpoints and blocks redirects. The verifier checks SQL and filesystem disclosure, controlled command effects, and unauthorized credential access against synthetic fixtures.

### A06 Insecure Design

Mandatory checks cannot be offset by favorable scores. Missing evidence produces abstention. Original source, contracts, and assertions remain immutable; the model can propose changes only to the candidate entrypoint. Docker execution is limited to controlled targets and separated from the deployed review service. No web endpoint accepts arbitrary uploaded code or executes arbitrary repositories. Contracts remain a trust assumption: a weak requirement can miss a real problem, which is why qualified mutations and honest scope disclosures matter.

### A07 Authentication Failures

Production requires a strong operator password and stable session secret. HTTP Basic authentication is checked with constant-time comparison and must be used over HTTPS. A bounded in-memory failure window rate-limits repeated authentication failures. The service has a single operator account, with no password recovery, MFA, or enterprise SSO. For broader deployment, put an identity-aware gateway with MFA in front of the loopback service.

### A08 Software or Data Integrity Failures

Bundle reads verify signatures and the exact artifact inventory. Replay also requires matching freshness bindings. Tests cover changed artifact bytes, escaped display, and invalid patch scope. The deployed container mounts a published evidence snapshot read-only and receives only the public trust key, never the signing key. Administrative protection of the independent trust fingerprint is essential.

### A09 Security Logging and Alerting Failures

The application logs host-policy denial, authentication failures, CSRF denial, replay failure, and execution exceptions. Signed run evidence records candidate results and model call outcomes. Sensitive authorization headers are not logged. Deployment operators should retain container logs, monitor repeated 401/429 responses and verification failures, and alert on unavailable health checks or inventory tampering. External alert delivery is an operator integration, not an implemented automatic notification feature.

### A10 Mishandling of Exceptional Conditions

Timeouts, absent runners, malformed provider output, invalid executor result counts, oversized responses, stale evidence, and missing challenges produce errors or insufficient evidence. Zero checks cannot produce readiness. An application error response cannot count as preserved normal behavior. The dashboard exposes a generic failure message rather than secrets or raw provider responses. Containers are removed in a finally block. Deploy a single execution controller to respect the current process-local concurrency bound.

This review is supported by automated checks and a focused code review. It is not OWASP certification, a third-party penetration test, or a guarantee against all threats.

## Deployment and operating procedure

The release has two operating modes. Local execution uses the full controller and Docker runner on a trusted developer workstation. Hosted review uses the authenticated read-only container with no Docker socket and no target execution privileges. Both use the same application and templates.

Create production secrets and a public evidence snapshot before starting Compose:

```powershell
./deploy/init-secrets.ps1
python tools/export_review.py
docker compose up -d --build
docker compose ps
```

init-secrets.ps1 refuses to overwrite an existing .env and generates independent random password/session values. Keep .env private, restrict its ACL, and store the password in the operator's password manager. The production dashboard listens through a loopback-only mapping at 127.0.0.1:8766. Health checks use /healthz. This endpoint returns only service availability and read-only state; evidence requires authentication.

For a public HTTPS deployment, copy the project to a controlled Linux server with Docker Compose, generate production secrets, and set PRATIRODH_ALLOWED_HOSTS to the chosen domain as well as any required localhost health-check hosts. Use deploy/Caddyfile with your real domain and DNS. Run Caddy on the host, proxying to 127.0.0.1:8766. Only expose HTTPS through the proxy. Do not publish the execution controller or mount /var/run/docker.sock into the dashboard.

Production Secure cookies require HTTPS. Direct HTTP localhost access is suitable for a health/access smoke test; authenticated browser sessions should use the TLS proxy. The local demo server uses non-production loopback settings for browser convenience.

Publish evidence through tools/export_review.py. It verifies source bundles before copying their signed public artifacts and public trust key to run_output/review. The signing key is excluded. The exporter creates a temporary snapshot, then moves it into place; stop the dashboard while replacing an already mounted snapshot. Preserve the trust fingerprint independently. Republishing does not rewrite any signed run.

For updates, stop the review service with docker compose down, export a new snapshot, re-run tests and audits, rebuild, and start again. Verify health, authentication, and a signed report. Keep the previous image digest and evidence backup for rollback. Never clear keys to fix an integrity error; diagnose whether the trust anchor or artifacts changed.

Back up private execution evidence and the signing key separately from the public review snapshot. Restrict both backups. Restore to a staging machine first and verify integrity against the separately stored fingerprint. Old evidence may remain cryptographically valid while its execution recommendation is stale.

No public hosting account, domain, or certificate has been provisioned by this project task. The supplied deployment is locally exercised and ready for an operator-selected server and TLS domain.

## Tests and release checks

Run the quick and container suites:

```powershell
python -m pytest -q
$env:PRATIRODH_DOCKER_TESTS = '1'
python -m pytest -q
python -m bandit -r pratirodh -ll
python -m pip_audit -r requirements-deploy.txt
```

Tests cover uncompensated failures, empty evidence, changed error responses, unauthorized patch edits, all 144 patch applications, missing execution, signed-artifact tampering, dashboard host/CSRF rules, HTML escaping, strong production configuration, authenticated read-only behavior, rate limiting, real SQL/path container verification, replay, freshness, and source preservation.

The dependency audit is a point-in-time known-advisory check. Re-run it before submission and deployment. The application scanner's low subprocess warnings are reviewed: subprocesses are necessary for Git, Bandit, Docker, and isolated workers, use argument arrays, and never use a shell. The temporary-directory warning corresponds to private container tmpfs, rather than a predictable host temporary file.

The GitHub workflow is included for future pushes. Local commands provide the actual release evidence; an included workflow does not mean GitHub CI has already run.

## Live demonstration runbook

Use the development path-traversal scenario cwe-22-development-01 as the main story. Start Docker and the local dashboard before presenting. Close unrelated applications, hide credential files, and prepare the three report links. The workspace's Run curated demo action executes incomplete/fixed, incomplete/full, and correct/full checks, preserving real reports.

1. Explain the fictional university document portal. Legitimate users should read course notes. A protected record must never appear in a response.
2. Show the original baseline security observation in the report. It contains the synthetic private marker, proving the declared issue was reproduced.
3. Open the incomplete repair under fixed verification. It blocks the obvious traversal request while legitimate use passes. Explain that the baseline recommendation is intentionally weaker and its mode is visible.
4. Open the same repair under full verification. Show the reviewed alternative request and its protected-data disclosure. The candidate is rejected based on executed evidence.
5. Open the corrected repair under full verification. Show legitimate request preservation and successful security checks. Expand the mutation panel: weakened copies are qualified by observed unsafe witnesses and caught by the strengthened suite.
6. Replay a legitimate case from the corrected candidate and a failure from the incomplete candidate. Explain that replay uses the saved source and requirements, not a reconstructed illustration.
7. Demonstrate expiry on a disposable copy of a scenario: change a relevant source/config input, verify that old evidence is stale, then restore the copy and run a new verification. Do not edit the benchmark during the held-out evaluation.
8. End on READY_FOR_REVIEW, its mode, and the human-review boundary. Show the benchmark counts and limits.

Allocate four minutes to this sequence in a ten-minute presentation. Prepare a backup recording using the same actual run IDs. If Docker fails live, label the backup as a prior executed run. Never display a recording as a current live execution.

## Demo video plan and narration

Record a three-to-four-minute video at 1920 by 1080 with readable browser zoom, clean audio, and no credentials or personal data. Keep the cursor near the evidence being explained. Trim waiting time transparently; show a brief elapsed-time caption when a container run is shortened. Keep an unedited original recording for provenance.

### Opening from zero to twenty seconds

Show the dashboard name and university scenario. Narration: We use AI to propose security fixes, but passing tests can create false confidence. PRATIRODH checks both the repair and whether its tests can detect known weaknesses. This demonstration uses synthetic campus data and curated patches.

### Baseline from twenty to fifty seconds

Show the original violation and legitimate course-note response. Narration: The original program exposes this protected marker. Our contract independently states that the notes must remain available and that private records must never appear in responses.

### Incomplete repair from fifty to ninety seconds

Show the diff and fixed-mode passing evidence. Narration: This candidate blocks the original example. The fixed tests pass. We do not treat that as a complete conclusion: the verification mode and scope are visible.

### Stronger evidence from ninety to one hundred forty seconds

Show the full-mode failed request and observed marker. Narration: A reviewed alternative request still exposes private data. Full verification executes it against the candidate and rejects the repair. The result is an actual observation, not an AI confidence score.

### Corrected candidate from one hundred forty to one hundred ninety seconds

Show legitimate/security checks, mutation qualification, and replay. Narration: The corrected candidate preserves normal downloads and blocks the declared disclosures. We deliberately weaken copies of it. Those copies must remain functional and demonstrate a leak before counting as unsafe. The stronger suite catches each required weakness.

### Expiry and conclusion from one hundred ninety to two hundred thirty seconds

Show stale evidence after a disposable input change, then the measured results. Narration: Evidence applies to the tested code, requirements, tools, and image. Relevant changes require fresh verification. Our recommendation is ready for human review within this scope. The benchmark uses synthetic scenarios, and local generation results are separately recorded from curated verification.

Export MP4 using H.264 video and AAC audio, name it PRATIRODH_Demo.mp4, and check audio/video on another device. Add captions for the three decisions, verification mode, and synthetic-data disclosure. The script and shot plan are included here; the team still needs to perform the screen recording and narration.

## Planned PPT content

Prepare the actual submission manually using the organizer's current official template. The earlier participant-plan review recorded a prohibition on AI-generated PPTs. This guide supplies planning notes, evidence, and a suggested speaking sequence; it does not generate a submission deck. Confirm the current organizer instructions and allowed use of writing assistance before submission.

### Slide 1 Project and team

State PRATIRODH, Security repair evidence for human review, team members, institution, and Open Innovation track. Use one clean dashboard screenshot. Say the prototype supports controlled Flask fixtures for four declared vulnerability classes.

### Slide 2 Concrete user problem

Show the developer receiving a patch and green checks while a private document remains exposed through another supported request. Explain the cost of incomplete repairs and functional regressions. Avoid invented market statistics.

### Slide 3 What the product does

Show the three main outputs: actual security observations, qualified challenges to the test suite, and signed version-bound evidence. Explain each decision and the human-review boundary.

### Slide 4 System architecture

Draw the controller, trusted contract, local Ollama adapter and optional explicitly selected cloud adapter, isolated target runner, and evidence store. Make the trust boundary clear: AI suggests data, target code executes in a restricted environment, and assertions stay outside it. Show hosted review as a separate read-only surface.

### Slide 5 Test the tester

Use one worked example with initial cases, a weakened candidate copy, a confirmed unsafe witness, and the stronger suite. State that invalid and unconfirmed variants do not count. Explain why mutant survival means weak verification, rather than automatically proving the actual candidate vulnerable.

### Slide 6 AI integration

Show configurable repair and request suggestions, two candidates/four calls/ten minutes for generation workflows, immutable requirements, and captured provenance. Label the main demo as curated. Show captured genuine Ollama runs and their decisions. Include cloud runs only if explicitly performed.

### Slide 7 Live demo

Reserve this slide for the demonstration sequence: baseline leak, incomplete repair, full rejection, corrected candidate, replay, and stale evidence. Include backup video availability and actual run IDs in presenter notes.

### Slide 8 Comparative results

Use measured raw counts from the release results, separating static, fixed, full, and equal-budget unguided verification. Include denominators for correct and incorrect candidates, held-out results, and runtime. Caption the 36 synthetic scenarios and 144 curated patches. Explicitly state that full mode uses additional cases.

### Slide 9 Security and deployment

Show authenticated read-only hosting, TLS proxy, no Docker socket, pinned/audited dependencies, resource limits, signature checks, and fail-closed outcomes. Describe the OWASP 2025 review as scoped engineering checks, not certification.

### Slide 10 Research and differentiation

Cite security mutation testing, FixCheck, MUTGEN, and the repair-validation literature. Explain that the contribution is their integration into a reproducible operational evidence workflow, with measured synthetic results. Avoid claiming a new theory or universal superiority.

### Slide 11 Limits and next steps

State trusted contracts, single-file Flask scope, four CWE classes, synthetic benchmark, process-local container concurrency, lack of enterprise RBAC/SSO, and no universal proof. Next steps are broader real-world evaluation, richer adaptive test selection, framework adapters, independent contract review, and an execution service designed for stronger isolation.

### Slide 12 Closing and questions

Return to the practical result: developers receive a reviewable repair, its executed evidence, and clear expiry conditions. Show the repository and demo link only after the team chooses the public release destination. Use the remaining time for questions.

For ten minutes, aim for two minutes on the problem and workflow, four minutes on the demo, two minutes on results and AI, and two minutes on limits and deployment. Team members should manually shorten the outline to match the official template and required slide count.

## Common questions and troubleshooting

Why not rely on Bandit alone? A static scan can miss application-specific disclosure behavior. The contract executes the actual requests and compares them with explicit requirements. Static results remain one mandatory signal.

Why not let an LLM judge correctness? The model may share assumptions with the repair generator. Here, execution and trusted assertions determine outcomes. Separate prompts are not evidence of model independence.

Does a signature prove security? No. It detects changed evidence relative to a trusted key. Test coverage, requirement quality, and the execution environment are separate assumptions.

Why did a valid-looking repair abstain? A declared mutation may not match an alternative coding style or may fail to produce a qualified unsafe witness. The tool reports the missing evidence rather than calling the repair wrong solely for style differences.

Docker unavailable or image missing: start Docker Desktop, enable Linux containers, run build-runner, and run doctor. The CLI retains insufficient-evidence reports. A server port conflict can be resolved with serve --port 8767.

Authentication failure: check the current .env and username, use HTTPS for production browser sessions, and wait for the bounded failure window to clear after repeated failed attempts. Do not weaken authentication to work around a deployment error.

Integrity failure: compare the saved trust fingerprint and backups. Do not edit a run report or replace keys to make it pass. Freshness failure: rerun under the current source and image. Provider error: check account/model availability privately, then intentionally retry; never put credentials in logs.

## Research and official references

Official event page and current schedule: https://theamse.org/hackathon/CyberAIHackathon2026. The page currently lists Round I on 3 October 2026 at 11:59 PM and presentations on 10 to 11 October. The deadline timezone is unspecified, so use an earlier submission buffer rather than assuming IST.

Participant guidelines: https://docs.google.com/document/d/1Udi42BiadndF-v4fWSA7qMLIhK7d8PuCN9cEXuMDPbo/edit. Re-check the official template, reuse rules, and presentation restrictions before submitting.

OWASP Top 10 2025: https://top10.owasp.org/2025/0x00_2025-Introduction/. Docker execution controls: https://docs.docker.com/engine/containers/run/. Current Gemini models: https://ai.google.dev/gemini-api/docs/models.

Research references carried forward from the planning review are Security-aware mutation testing, https://orbilu.uni.lu/handle/10993/29780; FixCheck, https://facumolina.github.io/files/MOLINA_ETAL_ICST2024.pdf; MUTGEN, https://arxiv.org/abs/2506.02954; SWE-Mutation, https://arxiv.org/abs/2605.22175; SWExploit, https://arxiv.org/abs/2509.25894; and automated vulnerability repair survey, https://www.usenix.org/conference/usenixsecurity25/presentation/li-ying. Their results are not directly comparable with this constructed Flask benchmark. No quoted paper performance number is used as PRATIRODH performance.

## Redesigned interface and presentation workflow

PRATIRODH checks whether a security repair deserves human approval. It reproduces a declared vulnerability, checks a proposed patch against normal behaviour and security requirements, deliberately weakens repairs to challenge the tests, and preserves signed evidence. The interface separates an explanatory showcase at / from the operational workspace at /workspace.

The university example follows the actual development fixture. A public download accepts ../private/record.txt and exposes a synthetic private file. An incomplete filter blocks ../ but still follows public/link.txt into the private directory. Full verification records that failed request. The correct repair resolves the path and enforces containment, preserving the notes.txt download. Showcase illustrations explain this sequence; they are explicitly labelled and never represent live results.

### Showcase and workspace

Start at http://127.0.0.1:8765/. Read the main claim, then use Explore the example to switch between vulnerable, incomplete, and corrected states. The original Three.js illustration explains successive checks. Use Change diagram angle to rotate it and Pause illustration to stop motion. On small screens, with reduced motion, or without usable WebGL, a static diagram remains available.

Use the live interface to inspect this view; duplicate presentation screenshots are not shipped.

Open workspace to choose a registered development fixture. Curated demonstration executes an incomplete repair under fixed tests, the same repair under full verification, and a correct repair under full verification. It produces three signed records. Local generation instead asks the native Ollama model for a real candidate and subjects it to independent checks. Generation can fail or produce rejected repairs. The interface never substitutes a curated patch for a generated one.

Use the live interface to inspect this view; duplicate presentation screenshots are not shipped.

Jobs now poll a protected, read-only /api/jobs/<job_id> endpoint. The progress panel displays the backend stage and completed result links. It does not invent percentages or completion. A connection failure leaves the result unknown and offers a retry. Another active job returns a conflict. Read-only deployments hide execution controls and reject protected POST actions on the server.

Evidence search and the decision, CWE, and origin selectors filter only the 30 loaded recent records. They are not a search of the entire evidence archive. Clearing filters restores that loaded set. Curated, supplied, local-model, cloud-model and signed review records remain distinct. Empty results, incomplete evidence and invalid signatures are shown explicitly.

### Reading a verification record

The report begins with the decision, signature status, freshness, candidate origin and elapsed time. Overview explains failures and gaps. Patch shows escaped, inert source with unified-diff line numbers and change highlighting. Challenge the Fix shows original mandatory requests, confirmed unsafe mutants, weaknesses missed by initial tests, catching witnesses and the resulting candidate decision. Requests provides a failures-only filter and exact replay when evidence is current and execution is enabled. Provenance exposes evidence bindings and model usage.

Use the live interface to inspect this view; duplicate presentation screenshots are not shipped.

A signature establishes integrity, not universal security. A stale record names changed or unavailable bindings and cannot support a new approval. Historical model runs keep their original outcomes and are labelled stale when the runner changes. A signed human review records an operator label and rationale. That label is metadata, not authenticated personal identity, and approval never applies source changes. Follow its reviewed-evidence link to inspect present freshness.

### Comparison and measured limits

historical baseline also provides detection, repair generation, offline AI, testing, signatures and human review. PRATIRODH emphasizes explicit challenge evidence and review freshness. No direct benchmark establishes overall superiority. Full verification accepted 36 correct curated repairs and rejected 108 incorrect curated repairs in the synthetic release suite. Equal-budget unguided testing made the same decisions. The eight recorded local-generation evaluation runs were all rejected. A separate redesign smoke run also used genuine Ollama generation and was rejected; it is not silently added to that eight-run evaluation cohort.

### Frontend build and operation

Install Node.js for development, run npm ci, then npm run build. The pinned dependency graph and frontend/build.mjs reproduce the browser bundles and self-hosted fonts. Flask/Jinja remains the server stack; Node is not needed for runtime. GSAP controls restrained reveals and diagram transitions. Three.js is lazy loaded. Rendering pauses off-screen and when the tab is hidden; reduced-motion and small-screen users receive the static diagram. Navigation, native forms, visible focus, and report disclosures remain usable without animation or JavaScript.

All browser assets are local. There are no CDN fonts, remote images, remote module imports, or analytics requests. The self-only content security policy, authentication, host allowlist, CSRF and read-only checks remain enforced. Source and model output are escaped by Jinja or inserted with textContent. The hosted container has no Docker socket, execution privileges or private signing key. Source attribution and redistribution notices are in docs/INTERFACE_SOURCES.md and pratirodh/static/licenses.

The redesign was checked at 390, 768 and 1440 pixel viewports, including keyboard tab switching, empty search, failed-request filtering, real generation, curated execution, replay and signed-review navigation. The Python suite passed 30 tests with Docker enabled. Renderer-free JavaScript tests verify reduced-motion, small-screen and unavailable-WebGL entry paths. Browser inspection confirmed the small-screen fallback and recovery after WebGL context loss. This is a focused accessibility check, not a comprehensive accessibility certification.

### Demo video and presentation changes

Open the showcase for the first 20 seconds of the demonstration and state what the product decides. Show the three example states, then enter the workspace. Clearly name the curated mode before presenting its three records. In the correct full-verification record, open Challenge the Fix and show the confirmed containment-weakened mutant that the original tests missed. Switch to the incomplete repair's Requests tab, filter failures, and replay probe-symlink. Finish with the corrected decision, signed human review and deliberately stale record. Show a genuine recorded model run separately and say that it was rejected.

For the PPT, use the showcase screenshot on the opening slide, the university-file story on the problem slide, and the Challenge the Fix screenshot on the differentiator slide. Keep architecture, measured results, historical baseline comparison, security limits and next steps as separate slides following the existing manual outline. State the curated and local-model denominators visibly. Do not imply the 3D illustration is telemetry or that guided testing outperformed the equal-budget comparison.

Next prioritize diagnosing rejected local-model repairs, then rehearse the demo, record the narrated video, and manually assemble the PPT. Public hosting is a separate deployment step. The completed project remains in C:/Users/armaa/.codex/worktrees/08d9/Derby University Hackathon on codex/pratirodh-offline-pipeline; the Desktop checkout is unchanged.

## Measured release results

The expanded comparison recorded 576 evaluations on a catalogue of 144 curated candidates across 36 synthetic scenarios and four modes. These are related constructed families, not production accuracy. Cloud generation was not invoked.

- Fixed verification: 36 of 36 correct patches ready; 30 of 108 incorrect patches incorrectly ready; 0 abstentions; 1059.8 cumulative seconds.
- Full verification: 36 of 36 correct patches ready; 0 of 108 incorrect patches incorrectly ready; 0 abstentions; 2148.08 cumulative seconds.
- Static verification: 36 of 36 correct patches ready; 30 of 108 incorrect patches incorrectly ready; 0 abstentions; 1063.44 cumulative seconds.
- Unguided verification: 36 of 36 correct patches ready; 0 of 108 incorrect patches incorrectly ready; 0 abstentions; 1594.79 cumulative seconds.

Real local Ollama generation is a separate cohort. Every attempted scenario is listed below; unsuccessful outcomes are retained.
- cwe-22-development-01: REJECT; 84.579 seconds; evidence da12737b258f4195aeaa91c3d9bd747d.
- cwe-22-development-02: REJECT; 73.469 seconds; evidence 62e5785101f6495c9f55d2321657feda.
- cwe-89-development-01: REJECT; 84.141 seconds; evidence 35769adb9f9a4f6cab4b0f57acd2d830.
- cwe-89-development-02: REJECT; 89.188 seconds; evidence 9a75968b6c6049dd92710815a2d9892c.
- cwe-78-development-01: REJECT; 71.5 seconds; evidence 5e23df6b5e4a4afeb122fc3e742c7c25.
- cwe-78-development-02: REJECT; 65.704 seconds; evidence 5d5f96d672124d1ba99217bf7b324573.
- cwe-798-development-01: REJECT; 61.75 seconds; evidence 54c78460eb224ba68d4d7c094d91354f.
- cwe-798-development-02: REJECT; 68.281 seconds; evidence fa1333d3672b4307ade16da0da36e655.

Full and unguided modes each spend 64 additional request executions per candidate; qualification counts against the guided budget. This implementation uses a shared trusted input pool, so similar outcomes are possible. No superiority claim follows without measured differences.

The original 0.1 comparison contained 288 evaluations: full mode accepted 24 correct patches and no incorrect patch out of 72. Those historical results are kept separately and must not be substituted for this release.

The final check record is docs/RELEASE_CHECKS.json. The operator applied program-specific Windows firewall rules. The dedicated Python executable retained loopback access and its external connection was denied; a control interpreter retained external access. Ollama has an active outbound rule and disabled cloud features. The real cohort uses the dedicated interpreter and an additional Python audit policy.

A narrated MP4 and organizer-template PPT remain team deliverables; this guide supplies their content and recording sequence.


## Combined repair milestone

The workspace now provides Curated demonstration, Local AI, and Combined repair. Combined repair tries one exact-match template and then up to two local Ollama proposals if the same independent verification gate has not established readiness. Every attempted candidate retains its origin, proposed diff, generation outcome, source revision, checks, and rejection. Templates are untrusted and cannot authorize readiness through confidence scores.

Run `python -m pratirodh pipeline TARGET --contract CONTRACT --strategy combined`. The CLI preserves its `ollama` default; new combined-mode workspace runs explicitly select `combined`. The complete repair budget is ten minutes, with two model calls maximum and 180 seconds per generation. Detection-only classes remain unsupported for automatic repair. Source application is separate from human review and is never automatic.

Seven minimal real-world-derived reproductions are registered in `benchmark/external-v1/manifest.json`. Their original and known repair audit calibration was completed before freezing. Four cases are reserved for evaluation and three for development. The sixteen-case target has a disclosed nine-case shortfall; no synthetic development scenario was relabelled as a newly sourced application. Two projects contribute related cases, so generalization is limited.

Run `python tools/build_baseline.py`, then `python -m pratirodh compare --prepare` and `python -m pratirodh compare --hours 12 --output run_output/reproduced-comparison-v1.json`. Historical source revision `edffe24` and earlier product revision `8f57db6` are pinned. The historical image has its own dependency lock, native gate, native corpus, and disabled promotion. Its native human-review routing label remains separate from automatic approval. Historical transport adaptations and missing native routes are disclosed in the results.

The comparison rotates repair arms across cases and three repetitions, interleaves identical-patch verification tasks, checkpoints results, and reserves time for final auditing. Template and local-model costs are recorded separately. Final requests/assertions live in `benchmark/audit-v1`; neither the template container nor the loopback model adapter receives that directory. Audit results never feed repair generation. A separate supervisor executes the final requests and assertions, and calibrates against originals and known repairs before measurement.

See [the measured comparison report](COMPARISON.md), [machine-readable results](COMPARISON_RESULTS_V1.json), and [updated demo narration](DEMO.md). `/comparison` presents results without enabling execution. Scenario-level paired differences and descriptive bootstrap intervals group repetitions and related patch variants rather than treating them as independent applications.

The earlier curated results, eight local-generation development attempts, and original release checks remain historical evidence. The Word guide is intentionally unchanged. Use the Markdown narration for this milestone; recording, manual slides, and public hosting remain future work.

## Repository scope

The public release keeps the active application, frontend source and built assets, tests, fixture manifests, independent audit inputs, recorded results, deployment helpers, and required licenses. Screenshots are omitted; the live interface presents the current views and evidence. The small patch/ module remains for the existing patch-matching regression test. Unique historical source stays in the inactive archive. Local generated evidence, environments, build output and signing material remain ignored.
