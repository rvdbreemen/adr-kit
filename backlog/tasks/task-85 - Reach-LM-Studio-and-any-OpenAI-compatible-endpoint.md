---
id: TASK-85
title: Reach LM Studio and any OpenAI-compatible endpoint
status: To Do
assignee: []
created_date: '2026-08-01 10:35'
labels:
  - spec-gap
  - R12
  - llm-routing
dependencies: []
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
- [ ] #1 An OpenAI-compatible endpoint can be configured by base URL, with LM Studio working out of the box against its default port
- [ ] #2 The base URL is read from machine-local config or environment and is refused in the repository-tracked config
- [ ] #3 Setup offers the choice, and /adr-kit:settings can change it later
- [ ] #4 A misconfigured endpoint degrades to advisory like every other backend failure, and says which endpoint it tried
- [ ] #5 Docs state which providers are covered by the compatible path versus which are distinct backends
<!-- AC:END -->
