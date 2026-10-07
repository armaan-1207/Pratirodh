"""Legacy Kavach diagnostic score; never authorizes deployment.

Use PRATIRODH's executable contract and mutation pipeline for review readiness.
"""
WEIGHTS = {"pov": .30, "diff_replay": .30, "regression": .15, "post_fuzz": .15, "diff_size": .10}
THRESHOLD_AUTO = .75
THRESHOLD_REVIEW = .45


def score(pov_result, diff_result, reg_result, patch_result, fuzz_result=None):
    mandatory = [pov_result, diff_result, reg_result, fuzz_result or {"status": "SKIPPED"}]
    components = {name: 1.0 if value.get("status") == "PASS" else 0.0
                  for name, value in zip(("pov", "diff_replay", "regression", "post_fuzz"), mandatory)}
    changed = sum(line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
                  for line in patch_result.get("unified_diff", "").splitlines())
    components["diff_size"] = max(0.0, min(1.0, 1 - max(0, changed - 10) / 90))
    diagnostic = round(sum(WEIGHTS[name] * value for name, value in components.items()), 4)
    if any(value.get("status") == "FAIL" for value in mandatory):
        decision = "REJECT"
        rationale = "A mandatory security or functionality check failed."
    else:
        decision = "INSUFFICIENT_EVIDENCE"
        rationale = "Legacy checks lack trusted executable security assertions and mutation qualification. Use pratirodh verify-patch."
    return {"score": diagnostic, "decision": decision, "components": components, "weights": WEIGHTS,
            "thresholds": {}, "rationale": rationale, "safety_cap_applied": True}
