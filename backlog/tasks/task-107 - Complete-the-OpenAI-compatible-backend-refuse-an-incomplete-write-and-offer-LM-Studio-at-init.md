---
id: TASK-107
title: >-
  Complete the OpenAI-compatible backend: refuse an incomplete write, and offer
  LM Studio at init
status: To Do
assignee: []
created_date: '2026-08-03 19:34'
labels:
  - llm
  - settings
  - bug
dependencies: []
priority: medium
ordinal: 3400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A user running LM Studio is never told it is supported, and can be congratulated on a configuration that silently degrades to declarative-only at commit time.

**Discoverability.** `skills/init/SKILL.md:405` offers `[1] host [2] openrouter [3] ollama [4] off`. A case-insensitive grep for `lm studio|lmstudio|openai-compatible` across `skills/`, `templates/`, `instructions/`, `clients/`, `docs/` and `.github/` returns zero hits. The one reachable mention is `bin/adr_embedding_runtime.py:205-207` from setup step 4c — and there only as an *embedding* route, never as the judge backend.

**Incomplete write.** `apply_backend_setting` has completeness refusals for host, openrouter and ollama, and none for openai-compatible. `--set-backend openai-compatible` exits 0 and writes `{"judge":{"backend":"openai-compatible","llm_enabled":true}}` with no base URL and no model — contradicting its own docstring: "a settings command that writes a config the judge then degrades on is worse than no command".

No ADR needed: ADR-017 already governs backend selection and the trust boundary. Note where each half lands, because R12.1 governs it: the base URL is a fact about the machine and goes to the machine-local file; which model judges is a team decision and goes to the project file.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The init backend question offers the OpenAI-compatible route and names LM Studio, with its default `http://127.0.0.1:1234/v1` as the suggested base URL
- [ ] #2 The base URL is written machine-local and the model name project-scoped, per R12.1
- [ ] #3 `adr-judge` accepts `--base-url` and reuses `--model`, so one call can write a complete choice
- [ ] #4 `apply_backend_setting` refuses an incomplete openai-compatible write with the same shape the other three backends use
- [ ] #5 A test asserts the refusal, and a test asserts a complete write is accepted
<!-- AC:END -->
