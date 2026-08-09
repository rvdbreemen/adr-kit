---
id: TASK-146
title: Prune the config schema and refuse removed keys by name
status: To Do
assignee: []
created_date: '2026-08-09 10:34'
labels: []
dependencies:
  - TASK-144
  - TASK-145
references:
  - docs/plans/kiss-simplification-plan.md
priority: medium
ordinal: 117500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 3 of docs/plans/kiss-simplification-plan.md. Requires TASK-144 and TASK-145. Remove from schemas/adr-kit-config.schema.json and the settings surface: judge.openrouter_model, judge.ollama_model, judge.openai_model, and the already-ignored judge.llm_cmd, judge.llm_model, judge.llm_default, suggest.llm_cmd. Each removed key is refused BY NAME with one sentence saying what replaced it, so an existing config fails loudly instead of silently (same posture as the credential refusal). Target: 66 config keys down to roughly 40-45.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A config carrying any removed key fails validation with a message naming that key and its replacement
- [ ] #2 python -m pytest -q passes; build-client-adapters.py --check reports changed=0
<!-- AC:END -->
