# Pinned upstream preparation

Install the current package in a Python 3.11 virtual environment. Preparation
fetches source only; it does not run targets, models or cloud workers.

```powershell
python scripts/reconstruct_targets.py --dry-run
python scripts/reconstruct_targets.py --case python-cve-2018-18074 --output run_output/requests-preparation.json
python scripts/check_preparation.py --output run_output/preparation-review.json
```

The source cache lives under `run_output/upstream-source-cache`. Every repository,
source revision, reference fix and captured adaptation is recorded in
`benchmark/upstream-sources.json` and each case's `target-source.json`.

For all 24 cases, omit `--case`. `--source-root` can read an existing directory of
case/target Git checkouts without modifying them. The prepared target and generated
manifest live inside the case's ignored `prepared/` directory. Use a new checkout
for repeated reconstruction; existing snapshots are refused rather than replaced.

Exit 2 means explicit preparation blockers. Raw source files and unsupported
fixtures are retained; these outcomes do not mean the vulnerability was reproduced.
Prepared inputs need reviewed dependencies, behavioral checks, worker identities
and current signed qualification before campaign execution. The campaign generator
never creates qualification evidence or marks the release complete.

The separate local Requests demonstration deliberately uses a reduced, disclosed
library snapshot with an in-memory transport adapter. Its passing result does not
remove blockers in the full upstream Requests case.

## Recorded static preparation, 2026-10-07

The complete pinned-source reconstruction recorded 24 cases: 5 `PREPARED` and
19 `BLOCKED`. Every result remains `qualification: NOT_RUN`. The detailed local
receipt is `run_output/upstream-parallel-20261007/result.json`, SHA-256
`8e588a0349b18ae2fbe5a715a0e8c8f9885fc8b85f25d90fd9a5500b385589f7`.
This generated receipt is excluded from release files; the dated summary below
records the limitations without publishing fixture contents or private material.

Prepared cases are `cpp-cve-2014-9130`, `javascript-cve-2019-15599`,
`javascript-cve-2021-23369`, `javascript-cve-2021-23664` and
`javascript-cve-2021-29300`. Static preparation does not establish exploit
reproduction, audit independence or runtime qualification.

Each blocked case has the following remaining intake conflicts. Counts describe
the reconstructed snapshot, including captured overlays, rather than only the
first file rejected by the controller.

- `cpp-cve-2018-25032`: 11 non-UTF-8 fixtures/sources, including `contrib/blast/test.pk`.
- `cpp-cve-2019-1000019`: non-UTF-8 source, an oversized file, 1,018 files and
  14,380,114 bytes exceed the file-count and total-byte budgets.
- `cpp-cve-2020-12762`: 20 upstream links and non-UTF-8 `tests/test_parse.expected`.
- `cpp-cve-2022-43680`: upstream `README.md` link, four oversized files and
  86,643,516 total bytes.
- `cpp-cve-2023-4863`: four non-UTF-8 fixtures and two oversized files.
- `cpp-cve-2023-50472`: retained Unity PDF fixture is non-UTF-8.
- `cpp-cve-2024-25062`: two links, 140 non-UTF-8 inputs, four oversized files,
  4,068 files and 27,817,926 total bytes.
- `javascript-cve-2018-6835`: 11 non-UTF-8 fixtures, including the EasySync PDF.
- `javascript-cve-2019-10767`: credential/private-key fixtures and 20 non-UTF-8 inputs.
- `javascript-cve-2021-37712`: five links, two non-UTF-8 inputs, two oversized
  files and 23,160,729 total bytes.
- `javascript-cve-2024-56334`: 39 non-UTF-8 assets.
- `python-cve-2018-18074`: two non-UTF-8 assets and one oversized file; the
  separate reduced Requests demonstration does not qualify this full case.
- `python-cve-2018-7750`: credential/private-key fixtures and three non-UTF-8 inputs.
- `python-cve-2020-25459`: credential fixture, 154 non-UTF-8 inputs, 15 oversized
  files, 2,096 files and 72,113,310 total bytes.
- `python-cve-2021-21330`: credential fixtures and six non-UTF-8 inputs.
- `python-cve-2021-32633`: 205 non-UTF-8 inputs and 15,180,615 total bytes.
- `python-cve-2021-33203`: four links, 1,321 non-UTF-8 inputs, 6,385 files and
  39,345,378 total bytes.
- `python-cve-2022-0767`: 265 non-UTF-8 inputs, one oversized file and
  18,658,255 total bytes.
- `python-cve-2025-43859`: two non-UTF-8 assets.

`intake_diagnostics` is advisory: it reports all observed file and aggregate
conflicts, including rejected links, without reading through links or changing
`inventory`/`load` decisions. Unsupported archive links are recorded with their
paths and targets, but are not materialized. Original Git acquisitions preserve
the complete upstream content. Oversized files are not decoded from truncated
prefixes, so the diagnostic does not falsely label a split UTF-8 character as
binary content.

## Bounded asset support requires a separate controller change

The current controller accepts UTF-8 inputs under 1 MiB per file, 1,000 files and
10 MiB total, and rejects credential/private-key material and links. These gates
are retained. Removing upstream assets, decoding binary fixtures as text or
raising the intake limits would change the input contract and is not a valid
preparation fix.

A future bounded fixture channel would need controller-owned explicit asset
paths, raw-byte hashes bound to the approved manifest, per-file and aggregate
quotas, and immutable staging inside the isolated worker. It would also require
hashes to survive export verification and worker identity/qualification checks,
and negative tests for replacement, escaping paths, links and quota exhaustion.
Binary assets must stay outside editable/model-source inputs. Credential fixtures
need a separately reviewed policy; lab provenance alone must not bypass the
current private-material rejection. Such a channel would not by itself resolve
oversized repositories or qualify any case. No asset-channel support or success
qualification is claimed by this release.
