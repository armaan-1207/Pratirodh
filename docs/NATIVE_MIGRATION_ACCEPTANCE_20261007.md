# Native migration acceptance — 7 October 2026

## Current decision

The general compiler worker remains eligible only for the previously verified
dedicated, offline, disposable local scope. Native remediation is **blocked**:
this follow-up found no supported drop-in package change that closes the current
XML-library risks. No image pins, advisory exceptions, harnesses, qualification
records or acquisition files were changed. Public activation remains deferred.

Read-only inspection of `pratirodh-project-worker:0.2` again returned libxml2
`2.12.7+dfsg+really2.9.14-2.1+deb13u3`, Expat `2.8.3-1~deb13u1`, Clang/LLVM
`1:19.1.7-3+b1`, and CMake `3.31.6-2`. The query ran with network disabled,
read-only filesystem, all capabilities dropped and no-new-privileges.

A fresh review of the official [Debian libxml2 tracker](https://security-tracker.debian.org/tracker/source-package/libxml2)
still shows open Trixie vulnerabilities, while testing/unstable carries
`2.15.4+dfsg-1`. The official [Debian Expat tracker](https://security-tracker.debian.org/tracker/source-package/expat)
still shows Trixie `2.8.3-1~deb13u1` with open issues; testing `2.8.4-2` retains
some issues that unstable `2.9.0-1` fixes. These observations do not establish
an ABI-compatible upgrade or justify mixing distribution suites. A whole-worker
migration is the next candidate for review, rather than a selective shared-library swap.

The current checked scanner reports retain 249 reviewed high/critical candidate
rows; the package trackers are separate evidence, not a replacement scan. A
new database may add findings and must pass actual review before release.

## Minimum evidence before replacing the worker

| Gate | Concrete proof required | Failure disposition |
| --- | --- | --- |
| Supported packages | Maintained distribution/supported backport provenance, exact base digest and signed snapshot, complete installed package inventory and successful dependency resolution | Keep current release pins; reject manually copied libraries and mixed-suite installations |
| ABI and toolchain | Actual C/C++ compilation with the required sanitizer, CMake configure/build, plus existing Python and JavaScript workflows against the replacement image | Candidate remains isolated; do not strip necessary tools to reduce findings |
| Containment boundary | Existing worker boundary tests: malformed/crashing responses cannot become signed readiness, denied network/privilege checks, bounded execution and cleanup | Candidate cannot replace the current worker |
| Scan provenance | Fresh scan of the candidate's immutable runtime image ID with export/report hashes and matching ordered layer hashes for all four roles | Missing or unequal bindings fail; scanner/config ID differences remain explicit |
| Advisory review | Every changed high/critical row, fixed-version availability and current review expiry checked against source-bound policy | New findings require review; a passing historical scan cannot close them |
| Runtime qualification | New worker/audit identity attestations and current signed qualification bound to the new image and case source | Keep qualification unfinished; never inherit the old image's approval |

No custom migration checker was added: the existing scanner, advisory gate,
boundary suite and qualification controller already enforce the executable
parts. A manifest containing operator-written `PASS` fields would add no
independent proof of package compatibility or runtime qualification.

## Reproduction and handoff

From the integrated repository root:

```powershell
$env:PRATIRODH_DOCKER_TESTS='1'
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_worker_boundary.py tests/test_image_advisory_policy.py tests/test_scan_image_bindings.py -q
```

For a separately built candidate, use the existing scanner with fresh database
acquisition, followed by `tools/check_image_advisories.py`; use a new ignored
output directory and preserve failing receipts. Complete the Docker-enabled
suite and clean release packaging checks only after the focused gates pass.
No candidate package installation or cloud start occurred in this follow-up.

The focused boundary/advisory/binding suite passed **33 tests in 13.95 seconds,
zero skips**, with Docker enabled. Its ignored execution receipt is
`run_output/native-migration-boundary-20261007.xml`. This result proves the
existing local boundary and receipt behavior; it does not test a replacement
distribution, establish native remediation or constitute qualification.

The reduced Requests worker remains a locally verified scope option for
Requests-only demonstrations; it does not qualify the full upstream Requests
case or remediate the compiler worker. The 19 preparation blockers and the five
earlier rejected harness operations retain their existing dispositions.
Runtime qualification remains **0/24** and campaign execution **0/216**.

The cloud allowance remains **$35 including the $2 shutdown reserve**. An
exhausted ledger cannot be reset to fund migration or qualification. Dedicated
offline containment and passing boundary tests do not demonstrate a patched
native library, container-escape resistance or full production assurance.
