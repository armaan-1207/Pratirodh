# Evidence-preserving evaluation contracts — design only

Implementation and runtime activation are deferred at the budget stop recorded
in `AZURE_EVALUATION_GATE_20261009.md`. These requirements define the next
controller change; they do not add an alternative execution path today.

## Accounting migration

Add a separate reviewed migration operation to the existing accounting tools.
Its inputs must bind the prior ledger SHA-256, prior report/input hashes, current
resource-group inventory, creation-to-observation allocation history, metered
cost coverage, documented currency conversion, noncompute components, unreported
usage headroom and reviewer identity. A self-declared completeness flag alone
must not establish billing completeness.

Generate a proposal first, without writing a replacement ledger. Partition costs
by resource/component and time interval; every charge belongs to exactly one
partition. Compare metered and modeled bounds within corresponding partitions
and conservatively retain the greater bound rather than adding overlapping
representations of the same usage. Uncovered periods retain modeled headroom.
Any correction to the previous planning accrual requires an explicit explanation
and evidence; merely obtaining a lower fresh quote must not reduce the balance.

Archive the exact old ledger and evidence before applying an independently
reviewed proposal. Require exclusive access and recheck the prior hash immediately
before atomic replacement at the original path. Reject concurrent changes,
incomplete coverage, stale observations, mismatched scope/currency, changed
reserve, cap uplift or a proposal leaving insufficient allowance. Keep an
append-only provenance chain binding old and new hashes. Do not automatically
fall back to a separate ledger or permit execution during migration.

Resume accounting must reconcile incurred charges with preserved campaign
consumption without subtracting either twice. Existing four-hour freshness,
reserve, identity and guard gates remain mandatory. Implement this only after
the billing evidence and review process are available; do not manufacture a
reviewer or completeness watermark.

## Immutable assets and source quotas

Introduce a versioned, additive manifest asset section distinct from editable
UTF-8 source. Each reviewed asset needs a relative path, raw-byte SHA-256,
exact byte length, purpose and acquisition/revision binding. Each approved
case needs explicit asset and source quotas, derived from the full inventory
and available worker limits. Existing manifests retain the current text-only
limits; no automatic schema upgrade or global quota increase is allowed.

Assets are staged through a controller-owned bounded stream into an immutable
worker mount, never an editable/model source map. Validate path/name and private
material rules before staging; use bounded inspection rather than assuming a
binary extension is safe. Bind asset hashes and quota policy to inventory,
source revision, worker protocol, qualification, frozen campaign inputs and
signed export verification. The worker must reject missing, extra, replaced or
oversized assets and confirm their hashes before execution. Do not encode
binary assets into the model-visible source as a workaround.

For each upstream link, retain provenance but materialize only a separately
reviewed mapping to a hash-bound regular file inside the pinned acquisition.
Resolve without following filesystem links; reject traversal, absolute paths,
cycles, unexpected targets or any content/hash disagreement. The prepared output
contains regular files only and refuses existing conflicting snapshots.

Credential/private-key fixtures remain blocked under current intake policy.
Their presence cannot be legalized by the new asset section or lab provenance.
Oversized and unsupported originals remain preserved until a reviewed contract
can represent them faithfully. Protected harness/audit bytes stay outside
editable and model-visible inputs.

## Required tests before activation

Accounting tests must reject missing periods/components, invented zero costs,
unverified currency conversion, stale/tampered evidence, overlap double counting,
changed prior ledger, lowered reserves and exhausted allowance. They must verify
preserved prior consumption and restart/resume behavior.

Asset tests must cover bounded reads, binary retention, content replacement,
missing/extra files, traversal, symlinks/junctions, cycles, quota exhaustion,
private material and attempted model/patch edits. Signed export verification
must fail after asset or policy changes. Clean-export reconstruction must leave
all original acquisitions intact. Complete Docker and release-security checks
are required after executable changes, before any cloud qualification.
