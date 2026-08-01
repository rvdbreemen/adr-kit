---
id: TASK-87
title: >-
  Detect the local embedding runtime at setup, and offer install, configure or
  remote
status: To Do
assignee: []
created_date: '2026-08-01 10:55'
labels:
  - spec-gap
  - R16
  - setup
  - embeddings
dependencies: []
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
- [ ] #1 Setup and upgrade detect whether a local runtime is reachable and whether it carries an embedding model, reusing the existing probe rather than a second implementation
- [ ] #2 A reachable runtime with a suitable model makes local embedding the default with no question asked
- [ ] #3 An absent runtime produces a clear report plus three offered routes: install, configure an existing or alternative runtime, or use a remote endpoint
- [ ] #4 No GPU produces a warning before any download starts, with the remote route recommended
- [ ] #5 Download size is stated before a model pull begins
- [ ] #6 Installing third-party software happens only on explicit consent, never with silent elevation, and declining leaves a working installation
- [ ] #7 The chosen route is written to the settings surface and can be changed later
- [ ] #8 Detection failure is a normal outcome: setup completes, and the kit works without embeddings
<!-- AC:END -->
