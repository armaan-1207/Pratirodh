import ast
import json
from pathlib import Path
import subprocess
import tempfile


def apply_diff(source, diff, entrypoint):
    if len(diff.encode()) > 131072:
        raise ValueError("patch exceeds size limit")
    if any(line.startswith(("rename ", "copy ", "GIT binary", "new file", "deleted file", "old mode", "new mode"))
           for line in diff.splitlines()):
        raise ValueError("only textual edits to the existing entrypoint are allowed")
    check = subprocess.run(["git", "apply", "--numstat", "-"], input=diff.encode("utf-8"),
                           capture_output=True, timeout=10)
    files = [line.split("\t")[-1] for line in check.stdout.decode("utf-8").splitlines()]
    if check.returncode or files != [entrypoint]:
        raise ValueError("patch must change exactly the allowlisted entrypoint")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / entrypoint
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8", newline="\n")
        result = subprocess.run(["git", "apply", "--whitespace=nowarn", "-"], input=diff.encode("utf-8"),
                                capture_output=True, cwd=directory, timeout=10)
        if result.returncode:
            raise ValueError("patch does not apply to the exact source")
        updated = path.read_text(encoding="utf-8")
        ast.parse(updated)
        return updated


def static_scan(source, budget):
    result = subprocess.run(["bandit", "-q", "-f", "json", "-"], input=source, text=True,
                            encoding="utf-8", capture_output=True, timeout=min(15, budget.remaining()))
    if result.returncode not in {0, 1}:
        raise RuntimeError("Bandit could not complete")
    output = json.loads(result.stdout)
    if output.get("errors"):
        raise RuntimeError("Bandit scan contains errors")
    findings = [{"id": r["test_id"], "line": r["line_number"], "severity": r["issue_severity"],
                 "confidence": r["issue_confidence"], "message": r["issue_text"]}
                for r in output["results"]]
    return {"status": "FAIL" if any(f["severity"] in {"MEDIUM", "HIGH"} for f in findings) else "PASS",
            "findings": findings, "tool": "Bandit"}

