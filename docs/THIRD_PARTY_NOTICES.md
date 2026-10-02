# Third-party notices and architectural references

The new project workflow modules are original PRATIRODH code. No Buttercup, Theori or other external repair-system implementation was copied. These systems are architectural references from the design plan; redistribution or component reuse would require checking the exact component license first. AGPL components must not be copied into the intended MIT workflow codebase.

The original Kavach-CRS source and history are retained. Its historical README is in `KAVACH_README.md`. Existing files retain their existing authorship.

The operator-prepared worker uses separately distributed Python, Flask, FastAPI, pytest, Bandit, Node.js/npm, Clang and CMake packages and their transitive dependencies. Their packages retain their own license notices in the execution image; this repository does not relicense those packages. Prepared image builders must preserve notices and record the exact dependency/image inventory.

Models and optional Atheris, Jazzer.js, Schemathesis, CrossHair, CBMC and llama.cpp tools are separate installations. The Qwen 7B model card identifies Apache-2.0; check every chosen model/tool revision and quantization's license before distributing artifacts. No weights are bundled here and no repair run downloads a model.

Primary implementation references:

- [Ollama model inventory API](https://docs.ollama.com/api/tags)
- [Ollama generation API](https://docs.ollama.com/api/generate)
- [llama.cpp](https://github.com/ggml-org/llama.cpp)
- [Qwen2.5-Coder 7B model card](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)
- [Atheris](https://github.com/google/atheris)
- [Jazzer.js](https://github.com/CodeIntelligenceTesting/jazzer.js)
- [Schemathesis](https://github.com/schemathesis/schemathesis)
- [libFuzzer](https://llvm.org/docs/LibFuzzer.html)
- [CrossHair](https://github.com/pschanely/CrossHair)
- [CBMC](https://diffblue.github.io/cbmc/)
