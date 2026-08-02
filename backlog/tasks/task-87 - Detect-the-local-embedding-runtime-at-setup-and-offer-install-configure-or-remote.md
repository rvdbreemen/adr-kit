---
id: TASK-87
title: >-
  Detect the local embedding runtime at setup, and offer install, configure or
  remote
status: Done
assignee: []
created_date: '2026-08-01 10:55'
updated_date: '2026-08-02 01:32'
labels:
  - spec-gap
  - R16
  - setup
  - embeddings
dependencies: []
modified_files:
  - bin/adr_embedding_runtime.py
  - bin/adr-settings
  - skills/setup/SKILL.md
  - skills/upgrade/SKILL.md
  - tests/test_adr_embedding_runtime.py
  - CHANGELOG.md
  - codex/
  - copilot/
priority: high
ordinal: 92500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R16. Setup and upgrade must find out whether a local embedding runtime is available and act on it, instead of leaving the user to discover the gap when retrieval silently falls back.

**Part of this already exists.** `bin/adr_doctor_probes.py:117-137` (`_ollama_candidates`) does exactly the detection: stdlib `urllib`, 1 s timeout, `GET http://127.0.0.1:11434/api/tags`, returns the model names, and fails soft on any OSError, URLError or malformed payload. It is deterministic, local, key-free and already in the shipped code. What is missing is the wiring into setup and upgrade, plus checking whether one of the listed models is an *embedding* model rather than a chat model.

**Flow to build.**

- Reachable with an embedding model present: local embedding becomes the default and embedding-backed features are on. No question asked.
- Reachable without one: offer to pull the model, with its download size stated first.
- Not reachable: report it plainly, explain how to install Ollama, and offer three routes — install now (Ollama plus the Qwen embedding model), configure an existing or alternative runtime (LM Studio, a remote host — see TASK-85), or use a remote API endpoint such as OpenRouter.
- Before installing anything, check for a GPU. Without one, warn and recommend the remote route: an embedding model on CPU makes the 2 s hook budget of ADR-015 unreachable, which turns the feature into a regression.

**Three things that need care rather than code.**

1. **Installing third-party software is a posture change.** adr-kit ships stdlib-only with zero runtime dependencies (ADR-016) and has never installed anything. An installer that downloads and runs a vendor script — even with consent — deserves its own ADR before it ships. Consent must be explicit, elevation must be asked for, and refusing must leave a working system.
2. **The GPU check is a heuristic.** `nvidia-smi`, Apple Silicon via `uname -m`, `wmic path win32_VideoController` on Windows — each is partial and none is authoritative. Present it as advice about speed, not a capability gate. Ollama runs on CPU.
3. **Size before download.** `qwen3-embedding:8b` is about 4.7 GB. State that before starting, and offer a smaller variant where one exists.

Whatever the user picks lands in the settings surface (TASK-78) so it can be changed later without re-running setup.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Setup and upgrade detect whether a local runtime is reachable and whether it carries an embedding model, reusing the existing probe rather than a second implementation
- [x] #2 A reachable runtime with a suitable model makes local embedding the default with no question asked
- [x] #3 An absent runtime produces a clear report plus three offered routes: install, configure an existing or alternative runtime, or use a remote endpoint
- [x] #4 No GPU produces a warning before any download starts, with the remote route recommended
- [x] #5 Download size is stated before a model pull begins
- [x] #6 Installing third-party software happens only on explicit consent, never with silent elevation, and declining leaves a working installation
- [x] #7 The chosen route is written to the settings surface and can be changed later
- [x] #8 Detection failure is a normal outcome: setup completes, and the kit works without embeddings
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`adr-settings --check-embedding` backed by `bin/adr_embedding_runtime.py`, wired into the setup and upgrade skills as step 4c.

Three states, each with the answer a setup step can act on. `ready` asks nothing, because there is no question when the answer is already yes. `runtime-without-model` offers the pull with the download size stated first - 4.7 GB is a decision, not a detail - and a smaller variant alongside. `absent` reports the normal outcome it is, saying in the same sentence that retrieval keeps working on lexical ranking, then offers install, configure-an-existing-runtime, or remote.

The three things the task flagged as needing care rather than code:

- **Installing third-party software is consent-gated.** The route says so in its own note, promises no silent elevation, and states that declining leaves a working installation. adr-kit still installs nothing itself; it names the commands.
- **The GPU check declares itself a heuristic**, in the payload and in the rendered output. `nvidia-smi`, Apple Silicon and a Windows video-controller query each answer part of it. Without acceleration the remote route becomes the recommendation, and the warning says why in terms of speed: an embedding model on CPU cannot meet the 2 s hook budget of ADR-015, which would turn the feature into a regression nobody sees. Ollama runs on CPU either way.
- **Size before download**, with `nomic-embed-text` offered next to `qwen3-embedding:8b`.

Detection reuses the shape of the existing doctor probe rather than a second implementation: stdlib urllib, one loopback address, 1 s budget, every failure treated as absent. Embedding models are told apart from chat models by name marker, because Ollama does not label them and pulling a manifest per model would cost more than the answer is worth.

Verified live on this machine: nine embedding models found and the RTX 3080 detected via nvidia-smi, so the report correctly asks nothing.

Packaging caught what Windows always catches: three new entrypoints landed in the git index as 100644. Fixed to 100755 before the contract test could ship broken.

Gates: 1287 passed / 12 skipped, adapter drift clean, adr-lint --strict clean.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
