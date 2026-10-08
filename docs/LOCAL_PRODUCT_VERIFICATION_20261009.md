# Local working-product verification — 9 October 2026

The Windows local workflow is verified: launch, generate a real model repair, inspect checks, download and independently verify signed evidence, restart, and reopen the result. This follow-up to CI-verified revision `984359db1c0a27fe9557a12adac9321255be0cf1` is published on `codex/readiness-followup`. The acceptance checks were performed locally before publication; CI results apply separately to the submitted revision.

## Start and recovery

From the integrated repository in PowerShell:

```powershell
./Start-Updated-Demo.ps1 -Port 8776 -Model qwen2.5-coder:7b
```

The current preview is `http://127.0.0.1:8776/`. An occupied port produces an actionable error; use a free port or stop your own existing launcher before restarting. Keep the launcher terminal open.

Start Ollama in a separate terminal with `OLLAMA_HOST=127.0.0.1:11434` and `OLLAMA_NO_CLOUD=1`. First setup creates a Python 3.11 virtual environment and installs hash-locked dependencies. Docker Desktop must provide Linux containers for execution. `-Check` validates prerequisites; `-Fresh -Requests` prepares new demonstrations while preserving existing evidence. `-Store PATH -ReadOnly` opens a verified store without executing repairs.

Normal restart restores the saved store and model. Supplied demonstration preparation no longer clears the model choice. Invalid stores are rejected without rewriting their contents. The exported-checkout environment was bootstrapped from the lock and subsequently launched and restarted against the existing verified store; it did not silently create replacement results.

## Executed acceptance results

- Full Python suite: **435 passed, zero failures/errors/skips**, Docker enabled, **891.03 seconds**. JUnit receipt: `run_output/local-product-final-tests.xml`.
- Frontend: **7 passed, zero skips**. Rebuild matches tracked browser assets. Reduced-motion changes, asynchronous loading, missing graphics and context restoration pass frontend tests.
- Supplied repairs: all **11 outcomes** match their declared decisions. Python, JavaScript and C++ each include an incomplete repair rejected, a valid repair ready for review and a successful discovery workflow. Requests includes an incomplete redirect repair rejected and the pinned upstream reference fix ready for review.
- Actual local model repair: run `9f82ee6d408d427cb4f5dca116d886f3`, scenario `cwe-22-development-01`, **READY_FOR_REVIEW**, **one model call**, **55/55 security requests**, **2/2 legitimate requests**, no failed required checks or evidence gaps. Execution recorded **112.656 seconds**.
- Model identity: Ollama **0.35.0**, `qwen2.5-coder:7b`, manifest SHA-256 `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`. All five manifest-referenced blobs matched their byte lengths and hashes before inference.
- Export: the browser-downloaded AI bundle verifies independently against the preserved public key. A copy with changed `report.json` bytes is rejected for artifact integrity failure. Trust fingerprint: `fe2c1f8ebd3e5c3f97b9e26e9f5b2131e1eb469fd3af08364c001e4ac62dc825`.
- Restart: all **12 signed records** reopen; the actual AI result remains current. The clean exported checkout also reopens those records after restart. Read-only execution and unapproved hosts return **403**; services bind only to `127.0.0.1`.
- Browser: 320px/390px mobile and 1280px desktop checked without horizontal overflow. Cube animation remains active across resizing. Supplied language outcomes, Requests decisions, signed exports and completed-result controls were inspected. Main product pages present capabilities; dated scope remains in Validation.
- Dependency checks: locked controller Python and production npm audits report no known vulnerabilities; `pip check` passes. Bandit reports zero medium/high findings and 84 low findings. Four image Python inventories have no applicable advisories; two known partial-component candidates retain their explicit review.
- Packaging: wheel and dashboard image build and inspection pass; signing material, databases, environments, prepared snapshots, acquisitions and inactive archives are excluded. The image runs as UID **65534**. Native OS advisory acceptance remains a separate dated control, not a claim of vulnerability-free images.
- **Failed release-security check:** the refreshed OS advisory gate rejects one new unreviewed HIGH finding in the project worker: **CVE-2026-77214**, `libexpat1` **2.8.3-1~deb13u1**. The [Debian security tracker](https://security-tracker.debian.org/tracker/CVE-2026-77214) lists trixie as vulnerable and a fix in unstable, not a fixed trixie version. [Upstream fix](https://github.com/libexpat/libexpat/commit/13c5f63a7f1c52c2feee3b16a1134d4fb68e9ea0) adds parse-buffer bounds checks. The existing advisory policy remains unchanged; this finding is not accepted or suppressed. Image release clearance requires a reviewed dependency remediation and verification against the resulting worker image. Local functional results above remain valid for their recorded image bindings.
- Preservation: **1,264 original files** and **24 nested upstream repository revisions** match the reconciliation inventory. GitHub main remains `c164369e952e0b954f3f3e5199459121fd11d2fe`. No commit, push, PR, merge or Azure execution was performed in this batch.

## Assessed source and retained receipts

Executable product/source snapshot SHA-256:

`4dba0b67bf9be5e83d69e43f656b4e27c014d555778f01559f2dbe48c2b59a74`

The hash covers 115 files: the application and browser sources/assets, launcher, dependency locks and packaging inputs. It hashes canonical sorted path-to-SHA256 JSON using raw file bytes; documentation is excluded to avoid circular metadata. The full map is retained locally in `run_output/local-product-source-hashes.json`. Raw generated records, signing keys, acquired source, scanner reports and billing captures stay outside release files.

## Boundaries

One successful registered Python fixture repair does not establish general model accuracy or arbitrary-project AI support. Public deployment, external operations activation, model training, the 24-case signed qualification and 216-run independent campaign remain separate. Azure execution stays frozen under the $35 cap including the $2 shutdown reserve. Existing native-library restrictions and dated security findings remain applicable. This local product acceptance is not production certification.
