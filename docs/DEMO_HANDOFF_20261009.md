# Local demo preparation — 9 October 2026

Target: a working local demonstration on 10 October morning. The demo uses the installed Ollama model and local Docker; Azure and paid compute are not involved. Changes are uncommitted.

## Start and recovery

From the integrated repository root, run:

```powershell
./Start-Updated-Demo.ps1 -Port 8779
```

Keep the terminal open. Normal restart restores the model, assistant configuration and verified evidence store. Start Docker Desktop with Linux containers and the installed local Ollama service before launching. The launcher reports unavailable dependencies/model, invalid stores and occupied ports rather than silently replacing results.

The local URL is http://127.0.0.1:8779/. The current interface has the restored charcoal/cyan palette, the restored cube/landscape Three.js hero with the newer headline and content, React Bits pointer effects and Lenis scrolling. All browser assets are local. A different port or older checkout can show an older frontend; use this integrated checkout for the demo.

## Supported demonstration scope

- Python, JavaScript and C++ supplied-patch comparisons: incomplete repairs are rejected and corrected repairs reach human review readiness.
- Pinned Requests redirect repair: incomplete/reference-fix decisions remain explicitly labeled local demonstration evidence.
- Genuine local Qwen repair on registered Python fixtures: recorded model identity and model calls, independent checks and signed decisions. Generated repairs may fail; an unsuccessful attempt stays inspectable.
- Result inspection: overview, candidate patch, challenge results, request observations and provenance.
- Signed evidence: exports are verified against a separately retained public key. Historical records are preserved, and changed source/environment bindings make evidence stale.

The main repair-generation form is at the top of Workspace. Supplied-repair demonstrations are grouped under “Compare supplied repairs.” Walkthrough can open recorded results without rerunning them; these remain clearly labeled records.

## Verification and limitations

The prior complete Docker suite passed 456 Python tests with zero skips, and the current frontend lifecycle suite passed seven tests after restoring the palette. The final launcher/web checks passed 18 tests with zero skips. All 11 freshly prepared supplied-patch outcomes matched expectations. A fresh genuine AI repair (`860edde2f94849dc88e1bef06f31a5bf`) reached `READY_FOR_REVIEW` with one model call in 100.438 seconds, 55/55 security requests and 2/2 legitimate requests satisfied. Its signature was verified and freshness current before and after normal Windows-launcher restart. All 12 records, the model, assistant setting and public trust key survived restart without regeneration. [Exact verification receipt](DEMO_VERIFICATION_20261009.json).

This is a local demonstration, not public production clearance. The Expat image advisory remains an enforced release blocker. Fine-tuning, external deployment and the 24-case/216-run evaluation are outside tomorrow's demo acceptance. Browser automation has denied the actual signed-evidence download even after renewed user approval; no alternate download route has been used to bypass that denial.

## Hero-only follow-up — 10 October 2026

The newer content is retained with the preferred cube animation. The fresh AI run `f475ceca325a41458a603abaa94744f5` reached review readiness in 92.078 seconds with one model call, 55/55 security requests and 2/2 legitimate requests. Signature and freshness were verified current, including after restart. The launcher reopened all 13 signed records. Older records remain retained but their runner binding is historical after rebuilding license artifacts. Seven frontend and twelve Docker-enabled web tests passed without skips; the prior combined-suite receipt is not relabeled as a new full-suite run. Fresh browser-download acceptance remains pending.
