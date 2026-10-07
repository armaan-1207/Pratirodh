# Functional release verification — 7 October 2026

The local repair lab now uses the selected installed Ollama model for both
availability checks and repair generation. `PRATIRODH_LOCAL_MODEL` or the launcher
`--model` selects it; an explicit adapter model still takes precedence, and the
historical default remains Qwen 3B. No cloud fallback or model download was added.

Reviewed CWE-22 fixture mutations now support a conservative Python AST adapter
when exact text matching is unavailable. It recognizes one explicit containment
guard and one canonical-path assignment, including renamed variables and reversed
guard polarity. The containment adapter disables that predicate; the canonicalization
adapter changes the selected `resolve()` to `absolute()`. Unknown families, altered
reviewed definitions, ambiguous guards and unsupported shapes still abstain.
Construction is recorded separately from qualification: every mutant must preserve
legitimate behavior and reproduce its contract's unsafe witness before it counts.
Assertions, canaries, probes, budgets and acceptance requirements are unchanged.

A fresh local Qwen 7B run reached `READY_FOR_REVIEW` with one model call in
107.031 seconds. It satisfied 55/55 recorded security requests and 2/2 legitimate
requests, with zero failed checks or evidence gaps. Both mutation families reproduced
the symlink witness and were caught. This is bounded local evidence for one repair,
not proof of all model repairs or independent campaign success. Its signed evidence
and private signing key remain outside release files.

The preceding Requests follow-up, including its smaller hash-locked worker and
Windows evidence-writer fixes, is included in this release. Historical security
observations remain in `SECURITY_REMEDIATION_20261007.md`; further security and
public deployment assurance work is deferred to the next stage.

## Local checks

The combined suite passed **261 Python tests with Docker enabled and no skips**
in 672.69 seconds. A subsequent preparation input-diagnostics change passed all
21 preparation/reconstruction tests, including preservation and overwrite refusal.
Three frontend tests passed; rebuilding assets produced no changes. Homepage,
animation, navigation and frontend source are unchanged. Bandit reported no
medium/high findings. Controller and production npm dependency audits passed.
The deployment image built; its installed Python dependencies and those in all
three execution images had no applicable advisories. The dated OS advisory gate
passed with reviewed residual rows: dashboard 46, runner 44, general worker 112,
Requests 44. Residual findings are not described as patched or absent.

During publication, the refreshed scanner database added three high kernel-source
findings for the general worker's `linux-libc-dev` 6.12.111-1: [CVE-2026-89811](https://security-tracker.debian.org/tracker/CVE-2026-89811),
[CVE-2026-90111](https://security-tracker.debian.org/tracker/CVE-2026-90111) and
[CVE-2026-90315](https://security-tracker.debian.org/tracker/CVE-2026-90315).
Direct inspection found 2,559 regular package payload files, all headers or
documentation, and no kernel images or modules. These exact image-package
applicability reviews retain the open host-kernel qualification requirement;
they do not claim host patching or exclude other kernel advisories. Refreshed
scan/gate counts are dashboard 46, runner 44, general worker 115 and Requests 44.
The release gate still rejects unknown findings, version/severity/fix changes,
expired reviews and changed build inputs. The earlier 112-row worker observation
above remains dated evidence from the preceding database.

Wheel inspection confirmed the new mutation adapter and Requests tools lock are
packaged and archives, source acquisitions, prepared snapshots and private inputs
are excluded. A clean export of 1,002 release files reconstructed the same cohort:
five prepared and nineteen explicitly blocked. Private-key/token scanning found
no matching release content. All 1,264 inventoried original file hashes and all
24 original nested source heads remain unchanged.

Twenty-four dangling acquisition gitlinks, with no submodule definitions, were
removed from the release index. Their original directories remain intact. Recipes,
pinned source mappings and captured overlays remain tracked; acquisitions stay
local and are reconstructed from pinned Git objects. Missing or accidentally
parent-resolved Git inputs now produce an actionable source-root/cache error
before any snapshot is written. Preparation refuses existing output.

## Qualification and campaign blockers

Neither Azure runtime qualification nor the 216-run campaign was executed.
Bounded read-only probes to both configured SSH workers timed out. There is no
current signed qualification index. Execution still requires valid budget evidence,
shutdown-guard acknowledgement, separately attested execution/audit workers and
signed qualifications. No Azure resources were started, no budget bypass was
introduced, and qualification success was not manufactured.

The clean reconstruction retains these explicit case limitations:

| Case | Blocker |
| --- | --- |
| cpp-cve-2018-25032 | Binary `contrib/blast/test.pk` unsupported by UTF-8 intake. |
| cpp-cve-2019-1000019 | Non-UTF-8 `contrib/libarchive.1aix53.spec`. |
| cpp-cve-2020-12762 | Upstream test links and non-UTF-8 `tests/test_parse.expected`. |
| cpp-cve-2022-43680 | Upstream README link and intake file/disk budget exceeded. |
| cpp-cve-2023-4863 | Binary `examples/test.webp`. |
| cpp-cve-2023-50472 | Binary PDF in the Unity test documentation. |
| cpp-cve-2024-25062 | Upstream Relax NG test links and binary documentation assets. |
| javascript-cve-2018-6835 | Binary Easysync documentation PDF. |
| javascript-cve-2019-10767 | Upstream `conf/cert.key` rejected by credential intake policy. |
| javascript-cve-2021-37712 | Windows path limit on long filename fixtures. |
| javascript-cve-2024-56334 | Binary Android icon in documentation assets. |
| python-cve-2018-18074 | Binary Requests logo in documentation assets. |
| python-cve-2018-7750 | Upstream `demos/test_rsa.key` rejected by credential intake policy. |
| python-cve-2020-25459 | Binary `cluster-deploy/images/arch_en.png`. |
| python-cve-2021-21330 | Binary aiohttp icon in documentation assets. |
| python-cve-2021-32633 | Binary editor image in documentation assets. |
| python-cve-2021-33203 | Upstream documentation links and binary compiled locale assets. |
| python-cve-2022-0767 | Binary `cps/static/cmaps/78-EUC-H.bcmap`. |
| python-cve-2025-43859 | Binary documentation close-label image. |

Raw upstream acquisitions are retained. These limits require an explicitly
reviewed bounded asset/path support design or disclosed snapshot adaptation;
silently deleting assets, accepting private material or weakening intake limits
is not a valid preparation fix. The separate reduced Requests demo does not qualify
the full upstream Requests case.

Publication uses a PR targeting `main`; no force-push or merge is included.
