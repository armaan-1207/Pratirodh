# Local PRATIRODH security assistant

The `security-v1` profile adds bounded, reviewed security references to the
existing local repair generator. It is an assistant built around an existing
model; no weights have been trained or fine-tuned. Generation remains a proposal
until the controller independently verifies the repair.

## Start the assistant

The initial reference pack covers path traversal (CWE-22) and SQL injection
(CWE-89). It selects at most 2,200 bytes of original guidance from bundled
controller-owned cards. It never downloads documents during inference or indexes
target-provided text, protected harnesses, held-out solutions or audit assertions.
The source links, review date, card IDs, corpus hash and selected-context hash are
recorded in model usage, which becomes part of the signed run report.

```powershell
./Start-Updated-Demo.ps1 -Port 8779 -Model qwen2.5-coder:7b -Assistant security-v1
```

Normal restart restores both model and assistant selection with the verified
evidence store. Use `-Assistant off` to restore the original generation behavior.
This profile currently applies to the controlled Python/Flask fixture adapter;
the separate project/campaign model adapter retains its approved profiles.
It does not expand the set of independently verifiable weaknesses or languages.

## Import the official Hugging Face GGUF

The reviewed artifact is Qwen's Apache-2.0
[Qwen2.5-Coder-7B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF),
revision `13fb94bfda8c8cf22497dc57b78f391a9acb426a`, single-file Q4_K_M.
Its SHA-256 is
`509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c`.
Downloads belong outside the repository and remain excluded from Git.

If Ollama can download directly, Hugging Face supports
`hf.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M`. The direct pull failed on this
Windows machine because Ollama's outbound socket was denied. A downloaded local
GGUF can instead be imported using the ordinary supported Ollama import process:

```powershell
curl.exe -L --fail --retry 3 -C - -o "$env:USERPROFILE\Downloads\qwen2.5-coder-7b-instruct-q4_k_m.gguf" "https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/13fb94bfda8c8cf22497dc57b78f391a9acb426a/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
./.venv/Scripts/python.exe scripts/import_hf_model.py --gguf "$env:USERPROFILE\Downloads\qwen2.5-coder-7b-instruct-q4_k_m.gguf"
./Start-Updated-Demo.ps1 -Port 8779 -Model pratirodh-qwen:7b-hf -Assistant security-v1
```

The importer verifies raw bytes, refuses an existing model entry, uses loopback
Ollama with cloud disabled and records both the artifact checksum and resulting
Ollama model identity. The local name is a deployment configuration, not a claim
of newly trained weights or improved performance. Import success does not prove
repair acceptance: run an actual bounded repair and verify its signed export.

References: [Hugging Face GGUF integration](https://huggingface.co/docs/hub/ollama),
[Ollama GGUF import](https://docs.ollama.com/import).

## Build a useful security corpus before fine-tuning

CVE advisories describe incidents; OWASP categories organize risks. Neither is a
complete patch-training dataset. Start with a small, reviewed corpus organized
by CWE, language and affected dependency. Use advisories as dated, cited context
only when the dependency and version match the project. Prefer specific OWASP
Cheat Sheets for remediation over treating the Top 10 as executable requirements.

For future training examples, require an upstream URL and immutable revision,
license, CVE/CWE references, vulnerable code, reviewed fix, legitimate-behavior
requirements and independent regression outcomes. Remove credentials and private
material. Deduplicate by repository and patch lineage; split by repository and
vulnerability family before training. Keep all held-out benchmark cases and their
fixes, protected tests and independent audit assertions out of retrieval and
training. Do not automatically turn a model's own accepted output into ground
truth; require review and independent reproducibility.

Only consider LoRA/QLoRA after a frozen baseline comparison shows a specific gap.
The current 16 GB RAM / integrated-graphics laptop has demonstrated quantized
inference, not training capacity. Training hardware, license review and any
spending require a separate scope decision. Azure remains frozen.

No version of this assistant is promised to fix every vulnerability. Unsupported
or uncertain repairs must keep their rejection or insufficient-evidence outcome.

## Local verification — 9 October 2026

The resumed 4,683,073,536-byte download matched the reviewed SHA-256. Ollama
imported it as `pratirodh-qwen:7b-hf`, model digest
`da3ee7a94df9e0f15e8ecf8045f649110c956affa380457c623cbe18a79e48b0`.
Two bounded local fixture runs used this model and the reviewed reference pack:

- SQL injection: `4cae41c4bd0d4a0fa97efa9ef9a2fbef`, one model call,
  READY_FOR_REVIEW, 55/55 security checks and 2/2 legitimate-behavior checks.
- Path traversal: `a41d6f4a6a7c455fb9dd7dd9a9df3ea3`, two model calls, REJECT.
  Both proposed repairs used an unsafe string-prefix boundary and permitted a
  sibling directory. The final candidate passed 62/65 security checks and 2/2
  legitimate checks; unsupported mutation patterns also remained explicit gaps.

Both exports verified independently against the retained public key. A tampered
Hugging Face run export was rejected. A separate installed-registry-Qwen baseline
with the same assistant pack reached review readiness on path traversal with one
call; that result does not replace the failed Hugging Face run.

The complete Docker-enabled Python suite passed 441 tests with zero skips;
frontend tests passed 7/7. Focused integration checks passed 46 tests. Static
security checks found no medium/high issues in changed runtime code. Wheel and
deployment-image inspection included the assistant module and excluded private
and generated inputs. Normal launcher restart retained the Hugging Face model,
assistant profile and all 15 signed records without regenerating demonstrations.

These results establish working inference and verification, not superiority to
the existing model or general security accuracy. The Expat advisory remains a
separate release blocker; Azure evaluation remains frozen and incomplete. These
assistant changes are included in the local candidate branch; GitHub CI has not
evaluated them.
