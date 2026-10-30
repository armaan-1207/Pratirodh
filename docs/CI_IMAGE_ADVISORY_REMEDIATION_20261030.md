# CI image advisory remediation — 30 October 2026

## Result

The worker image now contains Debian Trixie's patched Expat package, `libexpat1 2.9.0-1~deb13u1`. The refreshed Trivy 0.75.0 scan no longer reports CVE-2026-77214. The worker also replaces npm's bundled Undici 6.28.1 with 6.29.1, pinned by the registry tarball SHA-256 in `pratirodh/projects/npm-worker-pins.json`; the three corresponding high-severity findings are absent from the rebuilt image report.

The advisory checker now passes against a fresh local scan of all four CI images. It reports 46 reviewed high/critical package findings for the dashboard, 44 for the runner, 123 for the project worker, and 44 for Requests demo (257 total). These are package/advisory observations, not 257 demonstrated exploits. The policy records exactly match the current scan, are bound to the current security inputs, and expire on 6 November 2026.

This result closes the previously unreviewed Expat finding and resolves the CI review-record mismatch introduced by changed pinned dependencies. It does **not** assert that all findings are fixed or that the worker is safe for public or multi-tenant workloads. The worker retains documented libxml2 risk and Linux kernel implementation advisories surfaced against its userspace headers. Container isolation and network/capability restrictions limit exposure but do not prove host-kernel safety or prevent every container escape.

## Reproduction

From the repository root, with Docker available:

```powershell
$env:DOCKER_CONTEXT = 'default'
python -m pratirodh project build-worker
python tools/audit_container_dependencies.py --images pratirodh-dashboard:ci pratirodh-runner:0.1 pratirodh-project-worker:0.2 pratirodh-requests-demo:0.2
python tools/scan_container_images.py --images pratirodh-dashboard:ci pratirodh-runner:0.1 pratirodh-project-worker:0.2 pratirodh-requests-demo:0.2
python tools/check_image_advisories.py
```

Local scan used pinned scanner image `aquasec/trivy@sha256:af6acf9a6b85dfe389a1941505c0ce9efef52a4719635e1a962f022a3d855daa` (Trivy 0.75.0) and its refreshed database, updated 30 October 2026. The worker runtime image ID was `sha256:74eebc7777947512f12bb52b5ce701112e01dea56a24e4b17f29179fcf7248eb`; the scanner confirmed matching ordered filesystem layers. Run outputs remain in ignored local `run_output/` storage and are not release files.

## Remaining security boundary

The CI gate checks that all current high/critical image findings have a dated, source-bound review and that protected build inputs have not changed since that review. Passing it means no current high/critical item is unreviewed. It does not mean the residual items are patched. Continue to restrict the native compiler worker to isolated, disposable, offline execution; keep public deployment blocked until the native-library and host-kernel requirements receive a separate compatible remediation and qualification.

Historical observations in `NATIVE_REMEDIATION_FOLLOWUP_20261007.md`, `LOCAL_PRODUCT_VERIFICATION_20261009.md`, and earlier dated records are preserved as historical snapshots. This report supersedes their Expat package observation only for the worker image rebuilt from the current candidate.
