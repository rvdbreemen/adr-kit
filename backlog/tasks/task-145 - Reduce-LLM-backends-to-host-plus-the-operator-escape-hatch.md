---
id: TASK-145
title: Reduce LLM backends to host plus the operator escape hatch
status: To Do
assignee: []
created_date: '2026-08-09 10:34'
labels: []
dependencies:
  - TASK-143
references:
  - docs/plans/kiss-simplification-plan.md
priority: high
ordinal: 116500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 3 of docs/plans/kiss-simplification-plan.md. Requires TASK-143. In bin/adr_llm.py delete OpenRouterBackend, OllamaBackend, OpenAICompatibleBackend, HttpBackend and their factories; keep SubprocessBackend, the BACKENDS registry shape, the host resolution from .adr-kit.local.json, the ADR_KIT_LLM_CMD / --llm-cmd escape hatch, and the credential refusal (R12.1 stands and becomes structurally true). Update adr-judge --set-backend surface and adr-settings accordingly. Remove test_adr_openai_compatible_backend.py and the HTTP-backend halves of test_adr_judge_llm.py.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 BACKEND_NAMES contains only host; judge.backend values other than host are refused with a message naming the plan/ADR
- [ ] #2 No urllib request path remains in bin/adr_llm.py
- [ ] #3 python -m pytest -q passes; build-client-adapters.py --check reports changed=0
<!-- AC:END -->
