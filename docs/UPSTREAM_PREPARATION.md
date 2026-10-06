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
