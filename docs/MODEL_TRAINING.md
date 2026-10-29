# Local model training pilot

Open `tools/training/pratirodh_qlora_pilot.ipynb` in Google Colab and select a free T4 GPU. Run the cells in order. No paid service, Drive mount, secret, or Azure resource is needed. The notebook embeds the reviewed scripts so it does not depend on unpublished GitHub changes.

The base is Qwen/Qwen2.5-Coder-7B-Instruct at revision bc87297e12fd3333dcdf947661177bdc647f994e (Apache-2.0). The eight original MIT fixtures have four training, two validation and two held-out records. They exercise CWE-22 and CWE-89 only. This is a pipeline smoke experiment, not a representative generalization dataset. More independent reviewed examples are required for promotion. Protected project benchmarks and their repairs are excluded.

The isolated requirements are in tools/training/requirements.txt. TorchVision 0.23.0 is pinned with PyTorch 2.8.0 to avoid the observed Colab import mismatch. Restart the Python session after replacing preloaded packages, then resume from the script-preparation cell. Training console output is streamed and retained in `training-console.log`; a failed process remains a failure. QLoRA uses NF4, rank 8, seed 1207, 1536-token maximum, 16 optimizer steps, and batch 1 with accumulation 4. Oversized prompts fail rather than truncate; user/source tokens are masked from training loss. Model loading refuses remote code and requires safetensors. The notebook does not execute dataset source.

Dataset validation rejects unknown provenance, unsupported licenses, secret-like material, excess size and cross-split family/source clones. The curated fixtures are proved separately by tests/test_training_pilot.py. These checks cannot establish absence of all poisoning or secrets in arbitrary datasets; arbitrary dataset ingestion is not supported.

Checkpoints are saved every four steps; rerunning the training cell resumes only matching inputs. Free Colab can disconnect, and checkpoints on its ephemeral disk can be lost. Download the resulting adapter ZIP immediately. The ZIP excludes optimizer pickle files and contains adapter safetensors, configuration, tokenizer and hashes. A loss value is not a security-repair result.

After training, retain the base model and run the candidate under the same repair budgets, retrieval profile and independent checks. Require an increase in verified held-out repairs, no legitimate-behavior regression and intact verifier/security controls. Do not promote this eight-example pilot based on its tiny holdout. Full held-out controller evaluation, GGUF/adapter conversion, Ollama import and signed real-repair acceptance remain required before changing the default. No training or promotion result is predeclared.

Local checks: `python tools/training/prepare.py run_output/new-training-data` (new output only), then `python tools/training/train.py --data run_output/new-training-data --output run_output/new-training-output --check`. Install training packages only inside Colab or a separate GPU environment, never into the application environment.

## Observed free-T4 pilot — 9 October 2026

The uploaded Colab notebook completed all 16 optimizer steps on a Tesla T4 with 14.6 GiB VRAM. Training took 71.7594 seconds after acquisition/loading; final validation loss was 0.1638648212. These values describe training, not repair acceptance. The initial TorchVision import failure was corrected with the compatible 0.23.0 pin.

An equal-budget paired generation used the exact pinned base with its adapter disabled/enabled, one call per held-out case, a 768-token maximum and 120-second generation limit. The two authored held-out examples were checked in local offline Docker containers with no host mounts, a read-only root, an unprivileged user and resource limits. Both variants passed SQL lookup. The base path proposal blocked escape attacks but rejected legitimate two-dot filenames and internal absolute paths. The adapter proposal allowed sibling-directory and symlink escapes. Both variants fully passed one of two examples; the security regression prevents promotion. The product continues using its existing verified Ollama model.

This is a tiny authored pilot comparison, not independent controller qualification, a comparison against GGUF inference, or a general model score. The proposal sources were read from visible Colab output with JSON code fences parsed and comments omitted; raw prediction files and the adapter still need preservation from Colab. The generated ZIP is about 21 MB, with observed SHA-256 `341deccff8f0e50a16cfe9d78a02ec7dbb126a527da4e72de93d90c9084bd783`. Automated downloads timed out without a saved file. Download it manually before the free session expires; do not claim local adapter verification until its hashes are checked.

[Observed training and paired-check receipt](MODEL_PILOT_20261009.json). At the time of the pilot, project changes were still uncommitted; this record describes that historical state.
