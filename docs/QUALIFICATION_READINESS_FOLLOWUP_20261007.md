# Qualification and campaign readiness follow-up — 2026-10-07

This batch verifies preparation and execution gates locally. It does not qualify
upstream cases, start Azure resources, or execute campaign runs. Public deployment
and production activation remain deferred. No harness, acquisition, original
checkout, budget ledger or controller intake policy was changed.

## Executable local results

- Existing preparation, reconstruction, Requests preparation, qualification,
  campaign generation/preflight/deadline, cloud budget, Azure budget capture and
  model-readiness tests: **80 passed in 5.33 seconds; zero skips**.
- Fresh static validation of the retained reconstructed recipes: **24 total,
  5 structurally ready, 19 blocked**. The checker reports qualification
  `NOT_CHECKED`, behavioral review `REQUIRED`, and audit independence
  `NOT_VERIFIED`. Its non-success exit is expected for the 19 retained blockers.
- Read-only mapping validation: all **24** source/fix mappings agree between
  the tracked source catalogue, per-case mappings and reconstruction receipt;
  **49 overlay/adaptation hashes** match the tracked files, with zero errors.
  Original assignments remain **6 development / 18 evaluation**.
- Verified qualifications remain **0/24**; verified campaign runs remain
  **0/216**. Static readiness and passing gate tests are not signed runtime
  qualification evidence.

Ignored receipts:

- `run_output/qualification-followup-tests-20261007.xml`
- `run_output/qualification-followup-static-20261007.json`
- `run_output/qualification-followup-mappings-20261007.json`

Reproduction, from the integrated repository root:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_preparation.py tests/test_reconstruct_targets.py tests/test_requests_preparation.py tests/test_campaign_generation.py tests/test_campaign_preflight.py tests/test_campaign_deadline.py tests/test_cloud_budget.py tests/test_azure_budget_capture.py tests/test_model_smoke_preflight.py tests/test_upstream_qualification.py -q
.venv/Scripts/python.exe -X utf8 scripts/check_preparation.py --recipes run_output/upstream-parallel-20261007/recipes
```

The second command needs the separately retained source acquisition/preparation
inputs. These ignored inputs are not shipped in the release. Do not reconstruct
over existing output or alter upstream checkouts to make the checker pass.

## Every case's disposition

The following five cases are statically prepared, but still await runtime
behavior, worker identity, independent audit and signed qualification:

- `cpp-cve-2014-9130` (libyaml)
- `javascript-cve-2019-15599` (tree-kill)
- `javascript-cve-2021-23369` (handlebars)
- `javascript-cve-2021-23664` (cors-anywhere)
- `javascript-cve-2021-29300` (opened)

Additional harness work for those five projects was previously rejected by
automatic safety review for possible cybersecurity risk. It was not retried,
rerouted or treated as an accepted risk. Existing static inputs do not resolve
that separate behavioral-work restriction.

All **19 intake-blocked cases** retain their acquired upstream assets:

- `cpp-cve-2018-25032`: 11 non-UTF-8 fixtures/sources.
- `cpp-cve-2019-1000019`: non-UTF-8 source, one oversized file, 1,018 files and
  14,380,114 bytes exceed intake quotas.
- `cpp-cve-2020-12762`: 20 upstream links and non-UTF-8 expected-test output.
- `cpp-cve-2022-43680`: upstream README link, four oversized files and
  86,643,516 total bytes.
- `cpp-cve-2023-4863`: four non-UTF-8 fixtures and two oversized files.
- `cpp-cve-2023-50472`: non-UTF-8 Unity PDF fixture.
- `cpp-cve-2024-25062`: two links, 140 non-UTF-8 inputs, four oversized files,
  4,068 files and 27,817,926 total bytes.
- `javascript-cve-2018-6835`: 11 non-UTF-8 fixtures, including a PDF.
- `javascript-cve-2019-10767`: credential/private-key fixtures and 20 non-UTF-8 inputs.
- `javascript-cve-2021-37712`: five links, two non-UTF-8 inputs, two oversized
  files and 23,160,729 total bytes.
- `javascript-cve-2024-56334`: 39 non-UTF-8 assets.
- `python-cve-2018-18074`: two non-UTF-8 assets and one oversized file. The
  separate reduced Requests demonstration is not full upstream qualification.
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

These reasons come from the full advisory inventory in the retained preparation
receipt, not only the first rejection. Missing generated manifests for blocked
cases are downstream consequences of rejected intake; manufacturing manifests
would not repair unsupported content. Controller limits stay UTF-8-only,
1 MiB/file, 1,000 files and 10 MiB total, with private-material and link rejection.

Future binary-fixture support requires an approved controller-owned bounded
asset contract with immutable raw-byte hashes, explicit paths, quotas and export
verification. Credential fixtures need a separate policy decision; oversized
repositories and links need their own reviewed representation. None is solved
by discarding fixtures, enlarging limits or labelling preparation qualification.

## Cloud gate and remaining inputs

The retained read-only Azure observation at **22:09 IST on 2026-10-07**
(`2026-10-07T16:39:49.702898Z`) recorded model, execution and audit VMs as
deallocated. This is a dated observation, not a fresh live assertion.

Its retail reconciliation records a **$31.69 modeled upper bound** (already
including 15% contingency) and unavailable actual invoiced billing. A later
gate check at **22:19 IST** rejected the existing ledger with
`approved usage allowance is exhausted`. A new retail estimate cannot reset
prior accrued consumption or replace the conservative ledger automatically.
The approved **$35 total cap includes the $2 shutdown reserve**.

Required gates, in dependency order:

1. **Budget:** reviewed, fresh evidence must establish an allowed positive
   execution window while preserving all prior consumption, reserve and other
   billable resources. No ledger reset, lowered accrual or cap increase is
   authorized. Pending this, resource start remains prohibited.
2. **Worker/model readiness:** fresh matching pinned-image attestations from
   distinct execution and audit guests; sandbox proofs on each worker; model
   service identity/readiness. Mock tests do not replace remote attestations.
3. **Shutdown protection:** current acknowledgement covering the same workers,
   cost evidence and earliest execution deadline. No live guard was armed here.
4. **Case eligibility:** supported source intake plus independently reviewed
   behavioral and audit definitions. Previously rejected harness work remains
   blocked pending an authorized resolution outside this batch.
5. **Qualification:** one eligible case must pass actual runtime verification
   and produce current signed, source/image/identity-bound qualification. No
   stale or synthetic evidence can satisfy this gate.
6. **Campaign:** start a pilot only after qualification passes, preserve prior
   campaign consumption on resume, and use equal-budget batches subject to the
   earliest deadline and remaining allowance. Stop with accurately counted
   partial results if the cap prevents expansion.

Deallocation does not eliminate disk, IP and storage charges. No cloud billing
completion, full benchmark completion, public safety or production-readiness
claim follows from this local follow-up.
