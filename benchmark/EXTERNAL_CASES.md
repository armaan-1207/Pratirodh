# External reproduction cohort

`external-v1/manifest.json` identifies seven real-world-derived reproductions and discloses a nine-case shortfall from the sixteen-case target. Four cases are reserved for evaluation; three are development cases. Previously inspected synthetic scenarios remain in `scenarios/` as a separate development/regression cohort. No supplemental reference-data cohort was included in this version.

Each external fixture is an original minimal Flask implementation of a documented vulnerability mechanism, with synthetic data and harmless effects. No upstream source was copied. Public advisories, vulnerable and fixed revisions, source-patch hashes, licensing, adaptation details, and exclusions are recorded in the manifest and `external-v1/sources.json`. The upstream projects retain their own licenses; adaptations do not change those terms.

The original fixture source, contract, patch variants, and team-authored audit requests in `external-v1/cases/` and `audit-v1/` are dedicated to the public domain under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/legalcode). Advisory descriptions and upstream facts remain attributable to the linked sources.

`external-v1/freeze.json` records the inventory and pre-measurement calibration of vulnerable originals and known repairs. Do not overwrite it to tune measured outcomes. Changed fixtures, audit assertions, or verification behavior require a new version. The final audit is team-authored, not independent third-party certification.

Generation isolation is explicit: the template Docker worker mounts only its two generator code files; the local model receives original source, public requirements, and ordinary verification feedback. The final audit runs through a separate supervisor after candidate generation. Its assertion definitions and request corpus are not mounted into generation or candidate containers and are absent from repair feedback. Trusted operators can read the repository; this is process separation, not protection against a malicious operator controlling the host.

See [the comparison report](../docs/COMPARISON.md) for measured decisions, audit outcomes, costs, and limitations.
