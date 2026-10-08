# Local release verification — 7 October 2026

Assessed foundation: commit `65a0e9210b577af767425b0df7abdcd4ac4fa9ed`, plus
the locally verified candidate changes. Tests were run before the candidate
commit; their source inventory identifies that working-tree snapshot. GitHub main remains
`c164369e952e0b954f3f3e5199459121fd11d2fe`. The final source inventory and hashes
are retained in the ignored local inspection receipt; they are not a signed
upstream qualification or an immutable published release.

The security status record identifies assessed source using Git-index byte hashes
after newline normalization. The ignored release inspection receipt separately
preserves the working-tree file hashes used for the local artifact export.

## Current executable evidence

- Real Requests reference-fix Docker test: three consecutive passes, in 52.87
  seconds (four-test focused run), 52.97 seconds and 66.40 seconds. Original
  decision assertions are unchanged. Historical push CI failure remains open.
- Frontend: seven tests passed; rebuilding preserves the same 25 browser asset
  hashes. Animation eligibility responds to viewport and reduced-motion changes;
  context-loss handling permits browser restoration. Phone-width fallback now
  follows the copy and links rather than overlapping them. At the initial
  checkpoint, 390 CSS pixels selected the static fallback; the subsequent mobile
  animation change below supersedes that viewport restriction.
- Bandit: zero medium/high findings; 83 low findings remain. Production npm audit
  and locked deployment Python audit report no known vulnerabilities.
- Four image Python package audits: 20 dashboard, 8 runner, 66 general-worker and
  12 Requests distributions. No applicable advisories; two general-worker partial
  component candidates retain their explicit reviews. Native OS advisories are
  separate and remain subject to the dated advisory policy.
- Four-image native advisory gate passed using the database updated on 7 October
  2026 at 13:08 IST. Reviewed high/critical candidate counts are 46 dashboard,
  44 runner, 115 general worker and 44 Requests. These 249 residual candidates
  are not claims of 249 demonstrated exploits or zero vulnerabilities. No
  unreviewed findings, changed severities or changed fix availability passed
  the policy gate.
- Local synthetic deployment: trusted HTTPS and hostname verification, untrusted
  CA rejection, anonymous 401, authenticated 200, read-only POST 403, unexpected
  host 403 at proxy and backend, secure cookies/headers, signed restore and tamper
  rejection passed. One sanitized alert was delivered to a temporary local
  receiver after five failures. This does not verify public alert delivery or
  operator backup infrastructure.
- Release inspection: current intended files, including new untracked changes,
  contain no matching private-key/token material. Wheel and image exclude
  environments, acquisition/prepared trees, archives, keys and generated evidence.
  Historical archives remain deliberately included in the source release only.
- Preservation: all 1,264 recorded original file hashes and 24 nested repository
  heads are unchanged.

The complete current Python suite passed: **295 tests with Docker enabled and
no skips, in 694.78 seconds**. The ignored receipt is
`run_output/local-release-final-suite.xml`. Focused post-documentation checks
also passed. Local evidence receipts are excluded from publication.

## Cloud and release limitations

Read-only Azure capture at **19:57 IST on 7 October 2026** reports all three VMs
deallocated. The modeled upper bound is $31.39, the total authorized ceiling is
$35 and the shutdown reserve is $2. This is a retail allocation bound, not an
actual invoice. A currently validated ledger window, worker/model identity and
readiness, and an armed acknowledged shutdown guard are required before any
execution; none is assumed from this capture. No resources were started.

All 24 source mappings remain present. Five snapshots are prepared, 19 cases are
blocked, current signed qualifications are zero and the campaign remains 0/216.
Rejected harness work is not retried. Public deployment remains deferred.

The local release is functionally verified; it is not labelled fully production
ready while CI inconsistency and applicable residual risks remain unresolved.
See [blocked-operation dispositions](LOCAL_RELEASE_BLOCKERS_20261007.md).

## Subsequent mobile animation update

At the user's request, the cube now animates below 650 pixels as well. Narrow
layouts center the core and cap renderer resolution at 1.25 device pixels per
CSS pixel. Resizing adjusts framing without disposing the scene. Reduced-motion
preferences, unavailable WebGL and lost-context recovery retain their fallbacks;
off-screen and hidden-document rendering pauses remain. Seven updated frontend
tests passed and the bundled assets were rebuilt. A 390-pixel browser viewport
shows the live scene, with no horizontal overflow. Physical-device performance
has not been measured. The 295-test Python result above precedes this frontend
update; no backend execution or security policy changed.
