---
id: TASK-85
title: Reach LM Studio and any OpenAI-compatible endpoint
status: Done
assignee: []
created_date: '2026-08-01 10:35'
updated_date: '2026-08-02 01:57'
labels:
  - spec-gap
  - R12
  - llm-routing
dependencies: []
modified_files:
  - bin/adr_llm.py
  - bin/adr-settings
  - bin/adr_embedding_runtime.py
  - schemas/adr-kit-config.schema.json
  - tests/test_adr_openai_compatible_backend.py
  - tests/test_adr_judge_llm.py
  - CHANGELOG.md
  - codex/
  - copilot/
priority: medium
ordinal: 90500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R12. Three backends ship and are reachable — `host` (the client's own CLI, no model flag so each CLI resolves its user's model), `openrouter` (HTTPS, key from `OPENROUTER_API_KEY` only) and `ollama` (local daemon) — through one registry in `bin/adr_llm.py`, selected by `judge.backend`.

**LM Studio is not supported at all.** A repo-wide case-insensitive grep for `lm.?studio|localhost:1234|127.0.0.1:1234` returns exactly one hit: spec.md itself. It is not a distinct backend and it is not reachable through the OpenAI-compatible path either, because `OpenRouterBackend.endpoint` is bound to a module constant with no `base_url` override. The backend set is a closed enum.

**The cheapest correct fix is a base URL, not a fourth backend.** LM Studio serves the OpenAI chat-completions shape on `127.0.0.1:1234/v1`, the same shape OpenRouter already speaks. An overridable endpoint plus an optional key turns one backend into a family: LM Studio, a self-hosted vLLM, a corporate gateway, an Azure deployment.

**Keep the security property that makes the registry defensible.** ADR-017 holds that repository-tracked configuration may *select* a backend but never *introduce* a command, an endpoint or a credential. An overridable base URL crosses that line if it is read from the tracked config, because a repo could then point the judge at an attacker's endpoint and exfiltrate the diff. Read it from the machine-local file or the environment, and refuse it in `.adr-kit.json` the way credential-shaped keys are already refused.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An OpenAI-compatible endpoint can be configured by base URL, with LM Studio working out of the box against its default port
- [x] #2 The base URL is read from machine-local config or environment and is refused in the repository-tracked config
- [x] #3 Setup offers the choice, and /adr-kit:settings can change it later
- [x] #4 A misconfigured endpoint degrades to advisory like every other backend failure, and says which endpoint it tried
- [x] #5 Docs state which providers are covered by the compatible path versus which are distinct backends
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
An `openai-compatible` backend joins the registry, so LM Studio, a self-hosted vLLM, a corporate gateway and an Azure deployment are all reachable through one code path.

The task's own recommendation held up: this is a base URL, not a fourth vendor. LM Studio speaks the chat-completions shape OpenRouter already speaks, so the class exists for exactly one reason - the endpoint is configurable. LM Studio works out of the box on `http://127.0.0.1:1234/v1`.

The security property is the part worth reading twice. The base URL is machine-local and refused in the committed config, because an endpoint a repository can name is an endpoint a repository can redirect - and the judge posts the diff to it. Resolution is `ADR_KIT_OPENAI_BASE_URL`, then `judge.openai_base_url` in `.adr-kit.local.json`. A base URL written into the tracked file is ignored, with a warning that explains the redirect risk rather than just refusing. `judge.openai_model` stays a project setting: which model judges is a team decision, where the endpoint lives is a fact about one machine.

Small correctness detail with a real failure behind it: no Authorization header is sent when no key is configured. A local runtime that needs none rejects an empty Bearer, which fails in a way that looks like a broken endpoint rather than a wrong header.

Two contract tests restated the backend list as a literal and broke on the fourth entry. They now assert that the schema enum and `BACKEND_NAMES` agree, so the next backend is one edit rather than three.

The embedding runtime report's configure route now names the concrete commands, so TASK-87's "point at a runtime you already run" is actionable instead of aspirational.

Gates: 1298 passed / 12 skipped, adapter drift clean.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
