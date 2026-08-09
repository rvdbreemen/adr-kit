---
id: TASK-143
title: Name the retired judge keys when the LLM pass degrades to declarative-only
status: Done
assignee:
  - '@claude'
created_date: '2026-08-09 08:10'
updated_date: '2026-08-09 08:12'
labels:
  - bug
  - judge
dependencies: []
priority: medium
ordinal: 114500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A project config that still carries judge.llm_model or judge.llm_cmd (both retired since ADR-017/TASK-72) degrades the LLM pass silently: the judge prints 'no LLM backend is configured' while the claude CLI works fine, so the symptom points at the wrong cause. Observed 2026-08-09 on OTGW-firmware otgw-1.x.x, upgraded from footprint v0.13.0: judge.llm_model=claude-sonnet-4-6 was ignored and the operator diagnosed a missing CLI first. --set-backend already removes the retired keys when it runs, but nothing tells a degraded project TO run it. The degradation message must name the retired key it found and point at --set-backend.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 When the LLM pass degrades and the judge config contains llm_model or llm_cmd, the warning names the key(s) and suggests --set-backend
- [ ] #2 When the config contains neither, the existing message is unchanged
- [ ] #3 Unit test covers both paths
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
REPRODUCTION FAILED, and that closes the task. On a clean repro (judge.llm_model set, no backend, empty diff, plugin 0.47.0 binary) the full stderr already contains BOTH missing pieces this task asked for:

  [adr-judge] WARN: judge.llm_model is ignored: ... Use judge.openrouter_model or judge.ollama_model ...
  [adr-judge] WARN: judge.backend is host but no client was recorded in .adr-kit.local.json; the LLM pass will not run. Register one with adr-judge --set-backend host --host-client <...> or via /adr-kit:init.

The original observation on OTGW-firmware was piped through grep -iE "WARN|DEGRADED|OK|violation" AND tail -4, which cut the two explanatory lines and left only the generic DEGRADED line. The symptom was an artifact of the observers own filter, not of adr-kit. legacy_command_warnings() (bin/adr_llm.py:243) plus the host-backend unavailable_reason already cover both ACs.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Not a bug. Clean reproduction shows 0.47.0 already prints both the retired-key warning and the concrete --set-backend instruction on the degrade path; the original report observed output through a grep/tail filter that removed exactly those lines. No code change. Lesson recorded: reproduce with unfiltered stderr before filing.
<!-- SECTION:FINAL_SUMMARY:END -->
