---
id: TASK-145
title: Reduce LLM backends to host plus the operator escape hatch
status: Done
assignee: []
created_date: '2026-08-09 10:34'
updated_date: '2026-08-09 11:59'
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
bin/adr_llm.py reduced to the host backend plus the operator escape hatch: HttpBackend, OpenRouterBackend, OllamaBackend, OpenAICompatibleBackend, their factories, endpoints and credential env vars removed (826 -> ~480 lines, no urllib import left). Retired backend names get the precise ADR-036 refusal in resolve_llm_backend; committed configs naming one fail schema validation fail-closed (TASK-32.1 policy). adr-judge --set-backend is host-only; --model/--base-url flags gone; retired keys are dropped on write. The judgment.local installer-settings shape, its ollama discovery and the doctor model probes are removed. Schema enum is ['host']. Gate adr-host-only-judge-v1 replaced its strict-xfail placeholder with the real conformance suite: registry host-only, retired-name refusals, degrade-never-block, and an AST walk proving no network-capable import in adr_llm.py. ADR-036 verified_in updated. Full suite: 1767 passed, 15 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
