# Local release dispositions — 7 October 2026

This candidate is prepared locally; remote publication and public deployment
are deferred. Local
release verification is separate from upstream qualification and the 216-run
campaign. No risk acceptance overrides an automatic action rejection.

- **Upstream harness work — deferred.** Additional runtime/harness edits for
  tree-kill, cors-anywhere, opened, handlebars and libyaml were automatically
  rejected for possible cybersecurity risk. They are not retried through another
  route. Preserve their source and preparation inputs; current runtime status
  remains unqualified. The full case inventory and 19 preparation blockers remain
  in the reconciliation inventory and upstream preparation documentation.
- **Cleanup deletions — retained/excluded.** Earlier local cache and obsolete image
  cleanup attempts were blocked by policy. Retain remaining local caches and image
  artifacts. Do not repeat deletion commands. Environments, generated evidence,
  acquisition trees, billing captures, databases and keys are excluded from the
  intended release. Historical source archives are deliberately retained in the
  source release, but excluded from Python packaging, test discovery and images.
  Personal screenshots outside the checkout remain untouched.
- **Requests CI inconsistency — open.** Push run 37632194569 returned
  INSUFFICIENT_EVIDENCE for the reference fix; PR run 37632202872 passed on the
  same published head, 65a0e9210b577af767425b0df7abdcd4ac4fa9ed. Its original logs
  do not identify the missing evidence. Local reruns are supporting evidence,
  not proof of the historical cause. The next authorized CI run will preserve
  allowlisted execution summaries; no assertion is relaxed and no hidden retry
  is introduced. Publishing this diagnostic change is outside this batch.
- **Cloud qualification/campaign — deferred until prerequisites pass.** Five
  snapshots are prepared, 19 cases are blocked, signed qualifications are zero,
  and the campaign is 0/216. Keep VMs deallocated when identities, readiness,
  budget evidence or shutdown-guard acknowledgement are invalid. The approved
  ceiling is $35 total, including a $2 shutdown reserve; it is not a guarantee
  that the full campaign fits. No qualification is inferred from local mocks.
- **Security — scoped local assurance.** All ten OWASP categories have an existing
  dated application review. Residual native OS advisories require dedicated,
  offline, disposable workers. Public TLS, production permissions, external
  alerts and operating procedures remain outside verified local scope. No
  certification or complete production-readiness claim is made.

Acceptance for this batch is verified release exclusions, current local tests,
browser checks and local deployment evidence. CI remains unresolved until the
inconsistent execution is explained; the release must not be labelled fully
production ready while that blocker remains.
