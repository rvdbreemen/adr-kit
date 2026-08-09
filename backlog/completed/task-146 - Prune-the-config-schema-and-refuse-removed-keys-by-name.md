---
id: TASK-146
title: Prune the config schema and refuse removed keys by name
status: Done
assignee: []
created_date: '2026-08-09 10:34'
updated_date: '2026-08-09 12:31'
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Removed from the schema: judge.openrouter_model/ollama_model/openai_model/llm_cmd/llm_model/llm_default and suggest.llm_cmd/llm_model (suggest.llm_model added to the named set: same nature as the rest). New REMOVED_KEYS category in bin/adr_config.py, distinct from the accept-and-ignore RETIRED_KEYS: each removed key is refused by name with the sentence naming what replaced it (ADR-036). legacy_command_warnings and the now-dead check_repo_llm_cmd allowlist machinery removed from adr_llm.py (a validated config cannot carry the keys); the TASK-60 threat-model tests were kept end-to-end and now pin the stronger property: payload never executes, exit 2, removal named. judge.llm_default resolution dropped from adr-judge. Settings --list: 44 keys. Full suite: 1740 passed, 14 skipped; adapters changed=0.
<!-- SECTION:FINAL_SUMMARY:END -->
