# PRATIRODH comparison v1

## Measured scope

This report covers a frozen, team-authored evaluation of real-world-derived reproductions. It is not independent third-party certification, an evaluation of complete production applications, or evidence of market-wide superiority. The machine-readable record is [COMPARISON_RESULTS_V1.json](COMPARISON_RESULTS_V1.json); the application exposes it through the read-only comparison view.

The development/regression cohort of 36 synthetic scenarios and 144 supplied patches was already inspected and remains separately disclosed in [BENCHMARK_RESULTS.json](BENCHMARK_RESULTS.json). The external cohort has seven eligible cases from public advisories and upstream fixes: three development cases and four evaluation cases, one per supported CWE. The target was sixteen; nine cases remain unavailable. No invented real-world cases or supplemental reference-data cases filled this shortfall.

The four evaluation fixtures derive from Khoj static-file containment, Django date-extraction SQL interpolation, Paddle command construction, and Allstar shared webhook credentials. Each is an original minimal Flask reproduction with synthetic data and harmless effects. The full cohort includes related Django and MLflow cases, while the four evaluation cases come from distinct upstream projects. Source revisions, licensing, adaptation details, and exclusions are recorded in [the manifest](../benchmark/external-v1/manifest.json) and [source record](../benchmark/external-v1/sources.json).

## Freeze and audit separation

[The freeze](../benchmark/external-v1/freeze.json) records 51 exact file hashes and calibration against all seven vulnerable originals and known repairs. Every original demonstrated the declared violation while preserving legitimate behaviour; every known repair passed the final audit. The freeze preceded outcome measurement. Generation and verification algorithms were not tuned on evaluation outcomes.

The final audit runs in a separate supervisor process after generation. Template containers mount only the template worker and template registry. The restricted local model receives original source, public requirements, and ordinary verification feedback; it receives no final audit requests or assertions. Candidate containers receive request definitions and synthetic fixtures for execution, while assertion evaluation remains in the supervisor. The audit directory is not mounted into generation or candidate containers. This separation assumes a trusted operator controlling the host.

## Experiments and budgets

Verification compares the same sixteen evaluation patches: a correct, incomplete, alternative unsafe, and functionality-breaking variant for each case. The historical native gate retains its native checks and configuration, with a 300-second transport ceiling. A separately labelled historical analysis shares a 120-second execution ceiling with PRATIRODH. Guided mutation qualification is charged to PRATIRODH's budget; the unguided analysis uses the same ceiling. These produce 64 verification runs. Combined repair and local AI share one verification gate, so they are not presented as different verification algorithms.

Repair compares the adapted historical workflow, Ollama-only PRATIRODH, and combined repair. Each evaluation case has three repetitions per arm, producing 36 repair runs. Scheduling rotates arms across cases and repetitions and interleaves the verification experiment. Each repair permits at most two model calls, 180 seconds per generation, and ten minutes total. The common local model is `qwen2.5-coder:3b`, digest `f72c60cabf6237b07f6e632b2c48d533cef25eda2efbd34bed21c5e9c01e6225`, with temperature zero, seed zero, 8,192 context tokens, and 2,048 maximum generated tokens. Only one evaluation model generation runs concurrently.

The execution cap is twelve hours, including a one-hour final reserve for auditing already-generated candidates. Checkpoints retain failed candidates, errors, missing evidence, timeouts, and unstarted work. Final audit requests and calibration requests are recorded separately from verifier requests. Native Atheris request counts are unavailable, so historical request totals are lower bounds. Runs share a development machine with release checks; elapsed times do not establish controlled latency superiority.

## Historical baseline compatibility

The historical source is pinned to `edffe24`, and the prior PRATIRODH source to `8f57db6`. [The baseline record](HISTORICAL_BASELINE.json) preserves source hashes, locked dependencies, immutable image identity, model identity, environment, and wrapper hash. Historical dependencies remain inside a disposable Docker image. No historical decision can promote source.

Native `AUTO_MERGE`, `HUMAN_REVIEW`, and `REJECT` labels remain distinct. Only `AUTO_MERGE` is a historical positive decision; a review referral is not verified readiness. PRATIRODH's positive decision is `READY_FOR_REVIEW`, which still requires separate human approval.

The historical verification wrapper preserves its native HTTP routes and corpus rather than injecting PRATIRODH requirements. Missing routes and absent upstream regression suites remain compatibility gaps, not detection failures. The end-to-end baseline uses its native template first and the restricted local Ollama whole-file transport when needed. This changes its original snippet/span transport, removes cloud fallback, and limits model retries; it is an adapted baseline. Native human review remains a terminal referral. Consequently, results describe these registered adaptations and cannot establish universal superiority over the original product.

## Reproduction

The public repository contains recorded results and the harness, but excludes historical source. Supply the pinned archive described in [the README](../README.md#rerunning-the-historical-comparison) to rebuild the historical arm. Running the PRATIRODH demo does not require that archive.

```powershell
python tools/build_baseline.py --archive /path/to/historical-edffe24.tar
python -m pratirodh compare --prepare
python -m pratirodh compare --hours 12 --output run_output/reproduced-comparison-v1.json
```

Use `--resume` only to continue an interrupted record within its original execution cap. Resume refuses changed implementation or cohort hashes. Windows line endings are part of the recorded execution environment; frozen fixture and wrapper bytes are protected by Git attributes. A fresh run records its own environment and source hashes. Use a new version for changes to fixture, audit, or verification behavior.

Public results normalize only legacy presentation branding in native diagnostic prose. Native labels, checks, candidate code, audit observations, and metrics are unchanged; raw native execution records remain in local ignored evidence. This publication step does not feed back into repair generation.

## Outcome

All 100 scheduled runs completed in 2,044.797 seconds (about 34 minutes), within the twelve-hour cap. All 112 executable candidates were audited; twelve additional generated proposals failed patch policy and remain in the record. There were no unstarted runs, generation transport failures, recorded detection misses among the four eligible fixtures, or budget exhaustion. All 36 model requests returned valid responses. The cohort does not measure general detector accuracy or unsupported classes.

### Identical-patch verification

- **Historical native:** five automatic decisions and eleven human referrals across sixteen patches. The audit demonstrated one unsafe automatic decision and two functionality-breaking automatic decisions. Two of four known correct repairs received automatic decisions; the other two received referrals. None was rejected. The budget-matched historical arm reached the same labels and audited outcomes.
- **PRATIRODH full:** four ready, eleven rejected, and one unresolved. All four known correct repairs were ready. No positive decision was demonstrated unsafe or broken by the final audit.
- **PRATIRODH unguided:** five ready and eleven rejected. The additional ready patch was the incomplete Khoj containment repair, demonstrated unsafe by the final audit. Full verification withheld readiness because its required mutation evidence was unavailable; this was an abstention, not a successful exploit detection.

Each PRATIRODH arm used 1,088 verification requests; each historical arm recorded at least 632. Each arm's final audit used 52 further requests. Native historical request counts exclude unavailable Atheris counts. The full-versus-unguided result differs from the disclosed synthetic cohort, where their decisions tied. This external endpoint supports a narrower observed advantage in withholding one unsafe readiness decision, with an unresolved outcome and additional elapsed verification work. It does not establish general protection superiority.

### End-to-end repair

- **Combined:** six ready, three rejected, and three unresolved across twelve attempted runs. Six template repairs were both working in the final audit and ready for review. A further model candidate worked in the audit but remained unresolved, giving seven attempts with any working candidate. Six workflows made no model calls. Total: twelve model calls, 1,212 verification requests, 57 audit requests, and 348.327 summed workflow seconds.
- **Ollama-only:** five rejected and seven unresolved; none was ready. Four attempts contained a working candidate, including three working final selected candidates that remained unresolved. Total: twenty-four model calls, 1,212 verification requests, 60 audit requests, and 514.966 summed workflow seconds. Working audit results did not override missing verification evidence.
- **Adapted historical:** six automatic decisions and six referrals, with zero model calls. Its six working template repairs all received referrals; none of its automatic decisions was confirmed working. Three automatic decisions broke legitimate functionality, and three had indeterminate audits. Total: at least 474 verifier requests, 39 audit requests, and 203.608 summed workflow seconds. A referral is never counted as an approved repair.

The final audit had twelve indeterminate candidate outcomes: three historical, three combined, and six Ollama-only. These are missing observations, not successful protection and not automatically attributed to a detected vulnerability. The verification experiment had no indeterminate audits. Calibration used 46 requests; outcome auditing used 364, charged separately from both systems' verification costs.

### Per-class repair outcomes

- **CWE-22:** combined produced three ready working template repairs without model calls; historical produced three working referrals; Ollama-only produced working candidates in all three attempts but left them unresolved after six model calls.
- **CWE-89:** no arm produced an audited working repair. Combined and Ollama-only rejected all three runs; historical automatically accepted three candidates with indeterminate audits. Each PRATIRODH arm made six model calls.
- **CWE-78:** combined produced three ready working template repairs without model calls; historical produced three working referrals; Ollama-only left all three attempts unresolved, with no working audit result after six model calls.
- **CWE-798:** combined left all three runs unresolved, with one attempt containing a working model candidate. Ollama-only had one unresolved and two rejected runs, with one attempt containing a working model candidate. Each made six model calls. Historical automatically accepted three functionality-breaking template repairs.

Per-CWE identical-patch outcomes, native compatibility gaps, every proposal, and individual audit observations remain in the machine-readable record.

### Scenario-level uncertainty and conclusion

For **any audited working candidate per attempted repair**, combined exceeded historical by 8.3 percentage points and Ollama-only by 25 points in this named cohort. The case-cluster descriptive 95% bootstrap intervals were respectively [0, 25] and [0, 75] percentage points; both include a tie. Three repetitions and related patch variants were grouped within each of four scenarios, not counted as independent applications. The paired improvements came from one scenario each: one additional working credential attempt versus historical, and the command fixture versus Ollama-only.

Combined therefore demonstrated usable template contributions and fewer local model calls in these four reproductions. Overall superiority remains inconclusive. PRATIRODH's full gate withheld unsafe or broken positives observed in the identical-patch historical comparison, but native route compatibility, the convenience sample, unresolved working model candidates, and incomplete observation outcomes limit that conclusion. Larger separately versioned cohorts and improved generation need further evaluation. The product is ready for the scoped demonstration; it does not promise reliable repairs for arbitrary applications.
