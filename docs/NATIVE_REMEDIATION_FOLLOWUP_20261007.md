# Native worker remediation follow-up — 7 October 2026

## Outcome and release boundary

Read-only package inspection and a fresh primary-source review found no supported, compatible Trixie package upgrade that closes all current native XML library advisories. The general compiler worker remains restricted to dedicated, offline, disposable execution. Shared public or sensitive workloads remain outside the verified scope. Passing containment tests does not establish that installed libraries are patched or prove protection against container escape.

No Dockerfile, package pin, advisory exception, target harness or original acquisition was changed by this follow-up. No cloud resource was started. Historical security observations remain intact.

## Exact observations

The tracked policy contains **249 reviewed high/critical candidate rows**: dashboard 46, runner 44, general worker 115, Requests worker 44. These are package/advisory rows, not 249 distinct proven exploits. The policy has 246 high and three critical rows: an intentional source-only tree-kill fixture, libxml2, and build-only linux-libc-dev headers. Twelve rows retain the `unfixed-residual-risk` disposition. Review expires **6 November 2026**.

Read-only inspection of `pratirodh-project-worker:0.2` returned:

- libxml2: `2.12.7+dfsg+really2.9.14-2.1+deb13u3`.
- libexpat1: `2.8.3-1~deb13u1`.
- libcurl4t64: `8.14.1-2+deb13u5`.
- clang-19 and libllvm19: `1:19.1.7-3+b1`; CMake `3.31.6-2`.
- linux-libc-dev: `6.12.111-1` (headers, not the running host kernel).

Installed dependency metadata ties libxml2 to LLVM/libarchive and libexpat1 to CMake. Removing these packages would remove or break required compiler/build behavior. The image pins Python's Trixie base and signed Debian repositories at `20261006T000000Z`; merely running another build cannot import fixes absent from that snapshot.

The existing corrected operations scan passed `tools/check_image_advisories.py` with all 249 rows reviewed. This verifies the existing policy against existing reports; it is **not a newly downloaded vulnerability scan**. Its database metadata records update time `2026-10-07T07:38:55.515026687Z` and next update `2026-10-08T07:38:55.515026457Z`.

Installed worker image ID is `sha256:3c9d4d79d83fa2ff38a71971376f7a00c027bc492487d4092601e8209e2014a4`; corrected scanner metadata reports `sha256:2a8687b9998de4d077f513920fd9c61708b726f82f12766e5bf3ea43b5bfd0f1`. All 15 ordered uncompressed layer hashes and the creation timestamp match. These facts support matching package layers, but the differing representations must not be described as an exact image-ID match. Future scan receipts should preserve export/config digests and ordered layers alongside the runtime image ID.

## Primary-source review and prioritized disposition

1. **libxml2 — blocked pending compatible supported packages or a qualified rebuild.** Debian lists the inspected Trixie version as vulnerable for [CVE-2026-6653](https://security-tracker.debian.org/tracker/CVE-2026-6653) and [CVE-2026-86138](https://security-tracker.debian.org/tracker/CVE-2026-86138); testing/unstable has fixed `2.15.4+dfsg-1`. Debian also retains Trixie-vulnerable entries for [74860](https://security-tracker.debian.org/tracker/CVE-2026-74860), [86139](https://security-tracker.debian.org/tracker/CVE-2026-86139), [86140](https://security-tracker.debian.org/tracker/CVE-2026-86140), [86142](https://security-tracker.debian.org/tracker/CVE-2026-86142), [86143](https://security-tracker.debian.org/tracker/CVE-2026-86143) and [86144](https://security-tracker.debian.org/tracker/CVE-2026-86144). Newer packages are candidates for a separately pinned whole-worker migration, not drop-in replacement libraries. No ABI compatibility or comprehensive remediation claim is made.
2. **Expat — blocked pending a compatible maintained Trixie update or qualified source/package backport.** Debian lists inspected `2.8.3-1~deb13u1` as vulnerable for [66046](https://security-tracker.debian.org/tracker/CVE-2026-66046), [76956](https://security-tracker.debian.org/tracker/CVE-2026-76956), [76957](https://security-tracker.debian.org/tracker/CVE-2026-76957) and [93990](https://security-tracker.debian.org/tracker/CVE-2026-93990). Fixes in other suites do not establish a compatible upgrade for this worker. A Bookworm downgrade is not a complete fix because libxml2 findings remain there.
3. **Minimal Requests execution — retain the locally verified separate image.** Requests does not require the general compiler toolchain; its smaller image already excludes OS libxml2/libexpat/libcurl and LLVM/CMake. Preserve that image and its independently audited CPython components. This reduction must not be claimed as remediation of the general compiler worker or signed upstream qualification.
4. **All other native candidates — retain exact dated dispositions.** Service absence, build-only headers, privilege restrictions and network restrictions are conditional applicability/impact findings. Renew reviews for changed runtime conditions, new distribution fixes, scanner updates or expiry. Patch the actual worker host separately; updating headers does not patch its kernel.

## Next integration procedure and acceptance

When supported compatible packages exist, update the base digest and signed snapshot together on a separately reviewed candidate. Alternatively, propose a whole-worker toolchain migration before touching release pins. Do not mix testing/unstable libraries into the present runtime, copy shared objects manually, strip required tools or suppress findings.

Acceptance requires verified package provenance and dependency resolution; actual Clang/LLVM, CMake, C/C++, JavaScript and Python workflow success; sanitizer support; containment/failure/recovery tests; installed/vendored dependency audits; a fresh scan with scanner/database and image/export identities; and an explicit review of every changed advisory. Qualification remains separate and must not inherit a prior image's signed approval.

Repository-relative commands for the **next authorized integration**, after candidate images exist:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_worker_boundary.py tests/test_image_advisory_policy.py -q
.venv/Scripts/python.exe tools/scan_container_images.py --images <dashboard-image> <runner-image> <worker-image> <requests-image> --output run_output/native-followup-candidate-scans --cache run_output/native-followup-candidate-cache
.venv/Scripts/python.exe tools/check_image_advisories.py --reports run_output/native-followup-candidate-scans
```

Fresh scan or changed-input failures require real review; do not copy scanner output into the policy automatically. The complete Docker-enabled suite and clean release-image/wheel checks follow focused acceptance. Earlier rejected upstream harness work is excluded from this procedure and must not be retried through another route.

## Implemented scan provenance improvement

The scanner now inspects each local image and exports its immutable image ID, preventing a moved tag from changing the scanned image. It hashes the exact export archive and scanner report, requires valid runtime/scanner image digests and nonempty ordered layer digests, and fails missing or unequal layers. After all four roles pass binding, it writes an allowlisted `image-bindings.json` receipt without environment variables, credentials or raw image configuration. Different scanner/config IDs remain explicitly recorded rather than treated as equal.

`tests/test_scan_image_bindings.py` plus the existing advisory-policy tests passed **19 tests, zero skips**. These are synthetic receipt and policy tests, not a new vulnerability scan. The scanner source change was reviewed and its policy input hash updated before subsequent acceptance. Advisory rows, suppressions and review expiry are unchanged.

Ignored evidence for this read-only review is `run_output/native-followup-20261007.json`, including package output, source links, report hashes, runtime image IDs and layer comparisons. It contains no credentials, private keys or target sources.
