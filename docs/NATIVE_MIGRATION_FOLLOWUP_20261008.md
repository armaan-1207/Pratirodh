# Native worker migration follow-up — 8 October 2026

An isolated Ubuntu 24.04 worker candidate was built from a pinned Ubuntu
snapshot over HTTPS. It uses Python 3.12.3, Clang/LLVM 18 and CMake from the
distribution; no shared libraries were copied from the current Debian worker.
The candidate image is `pratirodh-project-worker:ubuntu24-experimental` and
its build recipe, package inventory and image archive remain in ignored local
output under `run_output/native-ubuntu-candidate-20261008/`.

The installed/vendored Python audit reported no applicable advisories and two
previously reviewed partial-component candidates. This is only one advisory
dimension; it does not replace the full four-image scan or the native OS
review. The initial unsigned-transport attempt and the corrected signed
snapshot acquisition are both retained in the ignored build logs.

The candidate **failed the first compatibility boundary proof** before the
compiler, timeout and output-limit cases could run: the synthetic probe did
not return the required `COMPLETE`/zero-exit result. Because the candidate did
not pass the existing boundary contract, it was not promoted, tagged as the
release worker, scanned as a release image, or used for qualification. No
package pin, advisory exception, controller policy or current worker image was
changed.

The retained failure is now explained. The probe invoked `python`, while the
worker entrypoint intentionally sanitizes runtime `PATH` to
`/usr/local/bin:/usr/bin:/bin`. Ubuntu supplies `python3` but no `python` in
that path, so the observation was `MISSING_DEPENDENCY` with
`FileNotFoundError`; the target code never started. The candidate recipe was
updated locally to install a small `/usr/local/bin/python` wrapper that execs
the already installed `/opt/python/bin/python` virtual-environment interpreter.
This wrapper is necessary: a direct symlink outside the virtual environment
loses the venv prefix and cannot import the pinned `pytest` dependency.

An initial derived-image check passed the original native boundary proof and
one Python synthetic repair workflow (`READY_FOR_REVIEW`). Later checks and
scan bindings are recorded below. The derived image was not promoted or used
for qualification.

Follow-up receipts bound to corrected image ID
`sha256:7c3b774b86ef50daa1070410d56197e8b6a73713291ca44dc3c29e9597e55326`
show the native boundary, Python repair/discover, and Node repair/discover
synthetic workflows passing with `READY_FOR_REVIEW`. The C++ repair and
discover runs did not produce a completed receipt in this host session: the
bounded local runner was interrupted while the candidate container was active.
Those interrupted attempts are preserved as `BLOCKED_RUNNER_SESSION`, not
candidate defects or successful observations. Existing receipts are per-proof
and ignored under `run_output/native-ubuntu-candidate-20261008/`.

A retained, awaited controller session subsequently completed both C++ cases
with the existing test assertions and timeouts. Repair passed in **80.891
seconds**; discover passed in **81.250 seconds**. Both required
`READY_FOR_REVIEW`, caught confirmed mutations and matching signed stored
evidence. New receipts and sanitized reports are in
`run_output/native-ubuntu-candidate-20261008/cpp-final-proof/`; the interrupted
receipts were not overwritten. The candidate now has **seven successful local
proofs**: native boundary plus repair/discover for Python, Node and C++.
This resolves the candidate interpreter-path defect and local synthetic
compatibility checks. It does not qualify any upstream case, establish a host
kernel assurance claim or approve replacement of the release worker.

The complete combined suite subsequently passed **430 tests with Docker
enabled, zero skips, in 642.19 seconds** with compiler-worker inspection
explicitly redirected to that immutable candidate image in a separate test
process. Other Docker roles were unchanged. The observer recorded **209 actual
candidate Docker dispatches** and verified that the configured release-worker
tag still referenced `sha256:3c9d4d79d83fa2ff38a71971376f7a00c027bc492487d4092601e8209e2014a4`
before and after the run. Its JUnit and execution-scope receipts are retained
under `run_output/native-ubuntu-candidate-20261008/combined-suite-v2/`.

The first combined-suite harness attempt failed during Windows collection:
the observer replaced the subprocess class with a function, incompatible with
the standard library's asynchronous subprocess subclass. No candidate workload
started in that attempt. The observer was corrected to retain class semantics;
the failed JUnit, scope receipt and original harness source remain preserved
under `combined-suite/`. No application assertion, timeout, retry policy or
worker configuration was changed to obtain the passing result.

The corrected-image advisory scan reported 175 rows (170 high and 5 critical),
all `linux-libc-dev` 6.8.0-146.146 with no fixed version; it produced no
libxml2 or Expat rows. The scan used the fresh pinned database and strict
ordered-layer bindings; configuration IDs were recorded as non-equal and no
suppression or finding closure was applied. This does not close the host-kernel
scope or establish qualification.

The independently captured runtime package query identifies `linux-libc-dev`
as development headers, consistent with the official
[Ubuntu package description](https://packages.ubuntu.com/search?keywords=linux-libc-dev).
The installed XML libraries are `libxml2` `2.9.14+dfsg-1.3ubuntu3.9` and
`libexpat1` `2.6.1-2ubuntu0.6`. Absence of rows for those libraries in this
dated database is not proof of zero vulnerabilities. No package was removed
to hide findings; all 175 rows remain visible and unapproved for migration.
The scan completed at 2026-10-08T05:14:16Z using database metadata updated at
2026-10-07T07:38:55Z and due for refresh at 2026-10-08T07:38:55Z. The strict
ordered-layer and archive/report hash receipt is retained at
`run_output/native-ubuntu-candidate-20261008/corrected-scan/binding-review.json`.

The existing Debian worker remains the configured release worker. The Ubuntu
candidate is locally compatible within these synthetic checks, with its image
scan bound to exact filesystem layers. Further migration acceptance requires
review of the 175 header findings, current host/worker identity evidence and fresh signed
runtime qualification. Until then, native workloads remain restricted to the
dedicated offline disposable worker; shared or public workloads remain outside
the verified scope. No release pin, exception, evidence requirement or budget
policy was weakened to complete these proofs.

## Reproducible recipe and header applicability review

The experimental recipe is now preserved in
`deploy/experimental/ubuntu24-worker.Dockerfile`, with repository-relative
build instructions. Its local build produced image
`sha256:204144f9962a5094958961a0ad82bb99009907b3ad687a14670ee4f27f726f6f`.
The first 12 filesystem layers and runtime configuration match the tested
`7c3b774` candidate. The final wrapper layer differs, although the wrapper's
contents have the same SHA-256. This is not artifact identity equivalence:
the rebuilt image has not inherited the candidate's scan, combined-suite
result or qualification. Neither image replaces the default release worker.

An offline, read-only, capability-free inspection at
2026-10-08T06:18:05Z found 990 regular package files in `linux-libc-dev`,
including 988 headers, zero ELF files, zero executable files and no package
paths under `/boot/` or `/lib/modules/`. Both images returned the same package
inventory hash and wrapper-content hash. These observations narrow the image
finding to a development-header package; they do not prove the running host
kernel safe or make the 175 advisory rows false positives. All rows retain
`HEADER_PACKAGE_HOST_KERNEL_STATUS_UNVERIFIED`, with no policy exception.
The ignored receipt binds the exact image IDs and scan hash at
`run_output/final-followup-review-20261008/native-header-review.json`.

The official [Ubuntu record for CVE-2026-64564](https://ubuntu.com/security/CVE-2026-64564),
reviewed on 8 October, identifies a kernel SCTP issue and lists Noble's `linux`
package as vulnerable with work in progress. Container header inventory cannot
establish the host's installed kernel or module exposure. Four other critical
advisory pages could not be retrieved during this review; their findings remain
open. No host configuration or mitigation was changed. Migration acceptance
still requires host-specific advisory assessment and signed runtime evidence.
