> Historical assessment of commit `790f13a946eae01609af8ccd6ab888d5b823cd50`. See [subsequent fixes, verification and residual risks](SECURITY_REMEDIATION_20261007.md). Original findings below are retained as dated evidence.

> Local release follow-up: see [current release dispositions](LOCAL_RELEASE_BLOCKERS_20261007.md) and [verification addendum](LOCAL_RELEASE_VERIFICATION_20261007.md). Three local Requests Docker reruns passed, but the historical GitHub inconsistency remains unexplained. Qualification and public deployment are not inferred from local results.

# PRATIRODH OWASP assessment — 7 October 2026

**Conclusion: all ten OWASP categories were reviewed; security findings remain open. This is not an OWASP certification or a claim that the application is fully secure.** The authenticated, read-only dashboard has useful tested controls. Project execution and the offline export verifier need further hardening before processing sensitive or unfamiliar repositories and untrusted bundles.

Assessed branch: `codex/main-integrated-demo`, commit `790f13a946eae01609af8ccd6ab888d5b823cd50`. [PR #1](https://github.com/armaan-1207/Pratirodh/pull/1) remains unmerged. Assessment work does not change production behavior, original checkouts, GitHub settings or Azure resources. Findings below describe the assessed commit, not completed remediation.

## Scope and method

The assessment uses the current [OWASP Top 10:2025](https://top10.owasp.org/2025/) categories. It covers the Flask dashboard and endpoints, authentication and CSRF, source intake, model transport, Docker workers, controller verification and patch policy, signed evidence and export verification, budget/qualification enforcement, frontend dependencies, packaging, CI and repository governance.

Methods: source and configuration review; existing security regression tests including actual Docker isolation/cancellation tests; bounded local probes; installed Python package inventories from the three local images; fresh package advisory audits; static analysis; read-only GitHub API inspection. All probe credentials were synthetic. Redirect probes contacted only two temporary loopback servers. The ZIP probe decompressed only 128 KiB. No exploit was sent to a public service, no real private key was used, and no cloud resource was started.

Threat model: a trusted single operator controls approved manifests and model configuration; project code, model output, repository text and received evidence bundles may be hostile. The dashboard is not a multi-tenant identity system. The published review container and local writable execution interface have different capabilities. Authentication proves possession of a shared operator password, not independent user identity.

Inactive archives and deliberate benchmark vulnerabilities are excluded from production vulnerability counts. Their exclusion from packaging and deployment remains important. No exhaustive review of every historical archive or upstream project's internals is claimed.

## Findings and remediation

### F01 — High, conditional: source intake admits secret-bearing files

**Categories:** A04, A06. **Evidence:** `pratirodh/projects/manifest.py:30–55`; `pratirodh/projects/engine.py:146–183`; local probe “Secret-bearing intake filenames”.

Intake rejects `.env` and a short list of case-sensitive key suffixes, but accepted synthetic `id_rsa`, `.env.local` and `credentials.json`. It decodes and inventories these contents. The engine serializes the complete inventory into `original-source.json` and passes it to worker execution. Therefore an accidentally included real credential can enter signed artifacts and be read by project code. Restricting editable source files does not prevent this disclosure. This behavior was demonstrated with dummy values; theft of an actual credential was not attempted. Impact is high if an operator imports a repository containing secrets. Worker network isolation does not remove disclosure into stored/exported source artifacts.

**Remediation:** reject common secret filenames case-insensitively, detect private-key material regardless of filename, and use a reviewed source/fixture allowlist with an explicit approval process for necessary non-code files. Apply the same policy before worker input, model context and evidence serialization. Never print suspect contents. Test renamed keys, `.env.*`, uppercase suffixes, nested credentials and legitimate fixtures. If real credentials have already been imported, investigate stored/exported artifacts and rotate affected secrets.

### F02 — Medium: project model transport follows redirects outside its validated origin

**Categories:** A01, A02. **Evidence:** `pratirodh/projects/model.py:19–53`; local probe “Project model follows cross-origin redirects”.

`LocalModel` validates the initial endpoint as loopback HTTP and disables machine proxies, but its urllib opener retains the default redirect handler. A loopback test endpoint returned HTTP 302 to a different loopback origin; the client followed it and returned the second server's JSON. Redirect destinations are not revalidated. A compromised or misconfigured model server can therefore cross the intended origin boundary. External SSRF, private-network reachability and transmission of a generation prompt were not exercised; POST redirect behavior depends on response status. Other controller provider clients already have a no-redirect policy.

**Remediation:** reject redirects for all project-model requests, including preflight and generation; alternatively validate every destination against the original exact scheme/host/port with a strict hop bound. Keep proxy bypass and response limits. Add GET and POST redirect rejection tests for 301, 302, 303, 307 and 308 without contacting external hosts.

### F03 — Medium: untrusted export verification lacks decompression limits

**Categories:** A10, A08. **Evidence:** `pratirodh/projects/export.py:38–77`; local probe “Bundle decompression before trust rejection”.

The verifier checks duplicates, signatures, identity, inventory hashes and unsigned extra members, but calls `ZipFile.read()` without first bounding member size, total expanded size, entry count or compression ratio. A compressed 128 KiB `trust.pub` was fully read before rejection against a trusted 32-byte public key. Much larger attacker-controlled members could consume excessive memory/CPU before trust validation. This is an offline verifier availability issue; no web bundle-upload endpoint was found, and no destructive compression bomb was run.

**Remediation:** inspect central-directory metadata before reads, enforce exact key/signature sizes, set per-member/total/member-count ceilings, and use bounded streaming reads with explicit errors. Enforce limits even for signed material and reject malformed paths/duplicates before processing. Add temporary-directory tests proving oversize rejection occurs before decompression, while legitimate campaign exports still verify.

### F04 — High, conditional: container dependencies and rebuild provenance need hardening

**Category:** A03. **Evidence:** `pratirodh/projects/Dockerfile:2–5`; installed worker package audit and normalized advisory inventory.

Fresh auditing of the actual project-worker image found **nine distinct advisories across three installed packages**. The audit tool emitted duplicate records; counts below deduplicate by package and advisory identifier. These are confirmed affected component versions, not nine proven application exploits. The dashboard and controller runner Python inventories, and frontend production/development npm dependencies, reported no known advisories in these checks.

- Flask `3.1.2`: [GHSA-68rp-wp8r-4726](https://github.com/advisories/GHSA-68rp-wp8r-4726), low; fix `3.1.3`. Its session/cache conditions must be present for exploitation.
- pytest `8.3.5`: [GHSA-6w46-j5rx-g56g](https://github.com/advisories/GHSA-6w46-j5rx-g56g), medium; fix `9.0.3`.
- Starlette `0.46.2`: [GHSA-2c2j-9gv5-cj73](https://github.com/advisories/GHSA-2c2j-9gv5-cj73), medium; fix `0.47.2`.
- Starlette `0.46.2`: [GHSA-7f5h-v6xp-fcq8](https://github.com/advisories/GHSA-7f5h-v6xp-fcq8), high; fix `0.49.1`. File-serving routes are a prerequisite for the documented Range-header denial of service.
- Starlette `0.46.2`: [GHSA-86qp-5c8j-p5mr](https://github.com/advisories/GHSA-86qp-5c8j-p5mr), medium; fix `1.0.1`.
- Starlette `0.46.2`: [GHSA-wqp7-x3pw-xc5r](https://github.com/advisories/GHSA-wqp7-x3pw-xc5r), high; fix `1.1.0`. The documented Windows UNC/NTLM condition does not match the Linux worker OS.
- Starlette `0.46.2`: [GHSA-x746-7m8f-x49c](https://github.com/advisories/GHSA-x746-7m8f-x49c), medium; fix `1.1.0`.
- Starlette `0.46.2`: [GHSA-82w8-qh3p-5jfq](https://github.com/advisories/GHSA-82w8-qh3p-5jfq), high; fix `1.3.1`.
- Starlette `0.46.2`: [GHSA-jp82-jpqv-5vv3](https://github.com/advisories/GHSA-jp82-jpqv-5vv3), low; fix `1.3.0`.

The project-worker build also uses a floating Python base tag, unversioned apt packages and incompletely locked transitive Python dependencies. Runtime image-digest attestation binds the image that actually ran, but does not make future rebuilds reproducible. Existing CI audits controller dependencies without covering the complete installed worker inventory. Worker network isolation, ephemeral scratch space and resource limits reduce exposure; they do not justify calling these package versions patched.

Completed Trivy image scans expanded this finding beyond top-level Python packages:

- Dashboard `pratirodh-dashboard:reconciled` and runner `pratirodh-runner:0.1`, Debian 13.7: **51 high OS package/advisory rows, 11 distinct CVE identifiers per image**.
- Worker `pratirodh-project-worker:0.2`, Debian 12.15: **348 high/critical OS package/advisory rows, 277 distinct CVE identifiers**; 334 high rows and 14 critical rows. Repeated source-package associations are not distinct exploits.
- All three contain setuptools-vendored `jaraco.context 5.3.0` ([GHSA-58pv-8j8x-9vj2](https://github.com/advisories/GHSA-58pv-8j8x-9vj2), fixed `6.1.0`) and `wheel 0.45.1` ([GHSA-8rrh-rw8j-w5fx](https://github.com/advisories/GHSA-8rrh-rw8j-w5fx), fixed `0.46.2`). These high advisories require vulnerable archive/unpack operations; dashboard reachability was not demonstrated. Vendored copies are outside the `pip freeze` audit inventory, so upgrading only a separately installed package may leave them unchanged.
- A dashboard scanner critical result for `tree-kill 1.2.1` comes from `benchmark/recipes/javascript-cve-2019-15599/overlay/package.json`, an intentional historical fixture manifest. It is excluded from live dependency counts; it does not establish an installed/running dashboard Node dependency.

OS results are **scanner candidates requiring package/function/reachability triage**, not hundreds of proven exploits. For example, a kernel advisory associated with `linux-libc-dev` headers is not evidence of a vulnerable running host kernel; some zlib findings concern separately built minizip functionality. Isolation and dropped capabilities affect exploitability. Some candidates have available fixes: the [Debian PCRE2 tracker](https://security-tracker.debian.org/tracker/CVE-2026-103111) lists patched Bookworm and Trixie security versions; this advisory requires attacker-controlled regex plus certain JIT API usage. Other candidates have no fixed version in the scanner database. They require explicit applicability/risk records rather than invented patched versions or silent suppression.

**Remediation:** upgrade a compatible FastAPI/Starlette stack plus Flask and pytest, refresh/minimize OS packages, update or remove unnecessary packaging tools including affected vendored copies, resolve and lock transitive dependencies, pin the worker base digest, and audit all deployed/worker images in CI. FastAPI `0.115.12` constrains Starlette below `0.47.0`, so forcing only a newer Starlette is not a supported fix. Rebuild derived images, rerun functional/Docker checks, update image attestations and obtain fresh qualification evidence after changing runtime inputs. Do not fabricate or reuse stale qualification signatures.

### F05 — Medium: evidence-integrity failures lack application security events

**Category:** A09. **Evidence:** `pratirodh/web.py:447–452`, `:460–473`; local probe “Evidence tamper security event”.

A controlled signed report was modified. The dashboard correctly rejected it with HTTP 409 and did not render the altered report, but emitted no application log event for that integrity failure. Host, authentication and CSRF denials already have logging; the finding concerns integrity denials and the absence of a demonstrated alert/retention pipeline. Proxy access logging might capture a 409, but does not provide its integrity-specific cause. No external logging infrastructure was tested.

**Remediation:** emit structured, sanitized security events for invalid signatures, invalid exports and stale/unauthorized evidence actions. Include a validated record identifier, event code, timestamp and request correlation identifier; exclude credentials, raw source, private keys and exception content that could contain secrets. Configure retention and alerts for repeated integrity/authentication failures. Test both fail-closed behavior and event emission.

### F06 — Medium: GitHub main has no enforced branch protection

**Categories:** A03, A08. **Evidence:** fresh GitHub API inspection: `main.protected=false`, effective branch rules `[]`.

The repository's main branch has no required review/status-check protection. The current integration follows a PR route and CI passed, but a principal with sufficient write permission can bypass that workflow. Four remote branches are present: `main`, `codex/main-integrated-demo`, `codex/pratirodh-final`, and `codex/pratirodh-upstream-validation`. Branch count is not a vulnerability. Main remains at `5ae927daf3cfb1f9f76ecb2aa53b12b4477c2c43`; the integration is in PR #1.

**Remediation:** configure an appropriate branch protection/ruleset requiring PR review and relevant successful checks, blocking force-push/deletion, and controlling bypass permissions. Repository administration was only inspected; no settings or branches were modified.

## Coverage of all ten categories

**A01 — Broken Access Control.** Anonymous requests to all nine enumerated static review GET routes returned 401. Eight execution/replay POST routes returned 403 in authenticated read-only mode with a valid CSRF token. Unexpected Host returned 403. Project workers use isolated Docker contexts, no host mounts/socket/keys, disabled networking and non-root target execution. F02 remains an origin-boundary finding. Multi-user authorization/IDOR isolation is not implemented or claimed: one shared operator identity has access to its evidence store.

**A02 — Security Misconfiguration.** Reviewed production startup requirements, deployment defaults, Docker capabilities, read-only mounts, CSP, HSTS, cache policy and Waitress. The CLI explicitly sets an 8 KiB request-body ceiling and suppresses tracebacks. Session cookies showed Secure, HttpOnly and SameSite=Strict. F02 remains open. Authenticated plaintext HTTP is accepted by the application; Compose binds loopback and the Caddy example supplies TLS. Actual external HTTPS, proxy trust and network exposure require deployment verification. HSTS alone does not protect the first plaintext request.

**A03 — Software Supply Chain Failures.** Reviewed dependency manifests, image provenance, pinned GitHub actions, permissions, packaging exclusions and source preparation. Dashboard/runner Python and npm audits were clean; F04 and F06 remain open. A clean controller audit does not imply a clean worker or OS image. Advisory results are dated observations, not permanent assurances.

**A04 — Cryptographic Failures.** Reviewed Ed25519 signatures, SHA-256 content inventories, external export trust anchors and key storage. Tampering was rejected; CLI export verification requires a separately supplied trust key. F01 remains open. Actual production key rotation, backup access, Windows NTFS ACLs and an external TLS endpoint were not verified. Unix `chmod(0600)` alone is not evidence of correct Windows ACLs.

**A05 — Injection.** Reviewed parameterized SQLite operations, safe relative paths, patch/edit policy, HTML escaping, argument-array process invocation and separation of approved commands from model suggestions. Existing regression tests and the fresh suite passed, including escaping and patch policy. Untrusted project code deliberately executes inside an isolated worker; this does not grant it authority over the host. No injection bypass was confirmed within reviewed paths. This is not an exhaustive fuzzing result for every upstream parser.

**A06 — Insecure Design.** Reviewed model-output authority, immutable/protected harnesses, exact violation oracles, qualification gating, equal-budget enforcement and resumable accounting. Budget/qualification negative tests passed. F01 remains open. Completed in-memory job/cancellation dictionaries have no evident retention cap (`web.py`); treat bounded retention as a design improvement, not a demonstrated memory-exhaustion exploit. No load test or multi-tenant design review was performed.

**A07 — Authentication Failures.** Production startup without credentials fails closed. Password comparisons are constant-time; failed attempts are bounded; Unicode failures are handled cleanly. Shared Basic authentication is suitable only for the documented limited operator model with TLS. MFA, named identities, password recovery and per-user revocation are not provided. External TLS and identity-provider controls remain deployment work; no authentication bypass was confirmed.

**A08 — Software or Data Integrity Failures.** Reviewed signed full-artifact inventories, freshness, qualification signatures, manifest/source revision matching and bundle trust verification. Tampered/unsigned exports and invalid evidence are rejected by existing tests. F03 and F06 remain open. Signatures attest recorded contents and signer identity under a trusted key; they do not prove an arbitrary repair is secure or an upstream campaign completed.

**A09 — Security Logging and Alerting Failures.** Authentication, Host and CSRF denials and internal errors have logs. F05 demonstrates missing integrity-specific event emission. Central collection, monitoring, incident response, retention and alert delivery were not demonstrated.

**A10 — Mishandling of Exceptional Conditions.** Reviewed generic HTTP errors, bounded model responses, worker output/time/memory/PID/disk budgets, cancellation cleanup and budget refusal. Docker isolation and cancellation checks passed. F03 remains open. OS-level exhaustion, disk-full behavior, sustained load, every network failure mode and disaster recovery were not independently exercised.

## Verification results and evidence

- Fresh focused Python suite: **45 passed, no skips**, 14.38 seconds; includes real Docker isolation and cancellation checks. JUnit: `run_output/owasp-assessment-20261007/security-tests.xml`.
- Fresh frontend tests: **3 passed, no skips**.
- Fresh npm production and complete dependency audits: **0 reported vulnerabilities**.
- Fresh installed Python package audits: dashboard **0**, runner **0**, project worker **9 unique advisories / 3 packages**. Advisory severity is recorded separately from assessed deployment risk.
- Fresh Bandit scan of `pratirodh` at medium/high threshold: **no medium/high findings**. Static analysis is supplementary, not proof of absence.
- Fresh tracked-file heuristic scan: **no matches** for complete private-key blocks, GitHub token formats or AWS key IDs. This is not exhaustive secret detection and does not contradict F01's synthetic intake demonstration.
- Prior complete combined Linux CI at the assessed commit: **208 Python tests passed**, plus frontend/build/audit/image checks. Push and PR CI runs succeeded; see `docs/RECONCILIATION.md` and the PR. The complete suite was not needlessly repeated for assessment-only documentation.
- Bounded probe output: `run_output/owasp-assessment-20261007/probes.json`; reproduction script: `run_output/owasp_probe.py`. Controlled fixtures are unrelated to the application's real evidence store.
- Governance and normalized advisory results: `github-governance.json`, `worker-advisories-normalized.json` in that same ignored assessment directory. A release-safe summary is in `docs/OWASP_ASSESSMENT_20261007.json`.

Container OS and vendored-library scans completed using official Trivy `0.75.0`, scanner image digest `sha256:af6acf9a6b85dfe389a1941505c0ce9efef52a4719635e1a962f022a3d855daa`. Public vulnerability database updated `2026-10-06T19:11:49Z`, downloaded from the official GHCR repository. Docker Scout required authentication and direct binary downloads failed; the pinned official scanner-container fallback succeeded. Saved image archives were scanned with `--offline-scan --scanners vuln --severity HIGH,CRITICAL`; no application source was uploaded. Raw `dashboard-trivy.json`, `runner-trivy.json` and `worker-trivy.json` remain ignored with the image acquisitions/cache. Image identities, normalized candidates and hashes are recorded in the JSON summary. These scans cover installed image packages, not the running Windows/Docker host kernel or every derived upstream image. No scanner login was requested.

## Remaining assurance limits and next actions

Resolve F01–F03 before importing sensitive/unfamiliar projects or verifying untrusted bundles. Resolve F04 with compatible dependency upgrades and requalification, implement F05 events/alerts, and apply F06 repository governance before relying on enforced PR security gates. Remediation needs its own review and regression checks; this assessment did not silently patch runtime behavior.

A public deployment still needs HTTPS/edge configuration validation, host patch review and container finding triage/remediation, IAM/network/firewall review, key management/rotation and backup access checks, alert delivery verification and availability testing. These were not inferred from local tests. Azure runtime qualification, the independent 216-run campaign and 19 upstream preparation blockers remain separate from this application assessment.

This document completes category coverage for the stated local/code scope. It does not close the findings, qualify Azure, complete the upstream campaign, or substitute for an independent penetration test against the actual deployment.
