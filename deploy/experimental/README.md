# Experimental Ubuntu compiler worker

This recipe preserves the corrected interpreter wrapper, signed Ubuntu
snapshot, pinned trust/Node build stages and locked dependencies used for the
local migration experiment. It is not selected by the controller, CI release
workflow or deployment image. No qualification carries over from another image.

From the repository root:

```powershell
docker build -f deploy/experimental/ubuntu24-worker.Dockerfile -t pratirodh-project-worker:ubuntu24-reproduced pratirodh/projects
```

Inspect the resulting immutable image ID before testing. A new build may have a
different configuration/attestation identity; verify ordered filesystem layers
and runtime configuration against the tested candidate, then bind any new scan
and qualification to its actual ID. The recipe never retags the release worker.

The controller supplies the restricted user, network, mount, capability and
resource options verified by its worker-boundary tests. Do not launch imported
projects directly with the image's default builder user. Native execution stays
within the dedicated offline disposable scope.

Local candidate `7c3b774` passed 430 combined tests with Docker enabled and zero
skips, six language/workflow checks and the native boundary proof. Its scan
reported 175 kernel-header candidates needing explicit applicability/host review.
See [the dated migration record](../../docs/NATIVE_MIGRATION_FOLLOWUP_20261008.md).
Runtime qualification and migration approval remain unfinished. The dated
snapshot is evidence of a reproducible experiment, not an automatic update feed.
