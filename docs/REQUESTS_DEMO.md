# Requests redirect-security demonstration

This local demonstration verifies supplied patches against pinned Requests source for CVE-2018-18074. It does not use a model, modify the acquired source, qualify an upstream case, or perform the separate final audit.

## Prepare from a fresh clone

Install the project in a Python 3.11 virtual environment and start Docker with Linux containers. From the repository root:

```powershell
python -m pip install -e .
python scripts/prepare_requests_demo.py
python scripts/start_demo.py --requests --port 8767
```

Use the virtual environment's interpreter. The preparation command fetches public source and both pinned Git revisions into `run_output/upstream-acquisition/python-cve-2018-18074/upstream`. It builds the general worker when missing and the dependency image. Acquisition and image preparation need network access; verification containers have no external network. Existing acquired source is preserved. The startup command runs nine synthetic paths and two Requests paths before serving the dashboard.

`python scripts/run_requests_demo.py --output run_output/requests-example` runs just the Requests verification and writes its signed evidence plus `requests-summary.json`. Choose a new output directory for each run. `python scripts/start_demo.py --store run_output/requests-example/evidence` reopens recorded evidence without rerunning checks. Workspace provides a live Requests action after preparation.

## Source and behavioral contract

- Repository: https://github.com/psf/requests
- Vulnerable revision: `dd754d13de250a6af8a68a6a83a8b4419fd429c6`
- Reference fix: `c45d7c49ea75133e52ab22a8e9e13173938e36ff`
- The reduced snapshot retains the upstream package and LICENSE. The generated manifest and source artifacts record revisions, hashes and adaptations.
- Same-origin redirects and standard HTTP-to-HTTPS upgrades preserve credentials as legitimate controls.
- HTTPS-to-HTTP downgrade and same-host port changes must strip the Authorization header.
- The deliberately weakened scheme/port decision must reproduce unsafe behavior and be caught by the checks.

The reviewed transport adapter answers redirects in memory and inspects the resulting requests. It exercises actual Requests redirect logic, not real TLS connections or external servers. The worker uses hash-locked urllib3 2.8.0, chardet 3.0.4, idna 3.20 and certifi 2026.7.22 with Python 3.11. This is a recorded, in-memory redirect harness; legacy Requests dependency warnings do not establish real-network or TLS compatibility. Missing dependencies are errors; no dependency stubs are used. Sessions ignore host proxy and netrc settings, and the harness verifies that it imported the supplied Requests source.

Expected decisions are REJECT for the incomplete repair and READY_FOR_REVIEW for the reference fix, with one confirmed unsafe mutation caught. Execution failures remain errors or insufficient evidence. A ready result is scoped to the declared checks and requires human review. Signed exports protect integrity, not assertion correctness or whole-application security.
