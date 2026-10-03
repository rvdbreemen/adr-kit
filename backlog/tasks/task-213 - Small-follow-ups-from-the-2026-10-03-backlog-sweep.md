---
id: TASK-213
title: Small follow-ups from the 2026-10-03 backlog sweep
status: To Do
assignee: []
created_date: '2026-10-03 15:52'
labels:
  - chore
dependencies: []
priority: low
type: chore
ordinal: 57000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Side findings recorded while working TASK-191..211. None is fixed; each needs its premise checked first.
1. skills/lint/SKILL.md refers to output of the deterministic CLI, but allowed-tools is Read/Glob/Grep, so the skill never runs it. A model that tries Bash meets a permission prompt.
2. This repository's .githooks/pre-commit lags templates/githooks/pre-commit in comment text: backend selection versus ADR-036, and suggest opt-in versus ADR-035. The version registry syncs only the stamp.
3. Something in the full pytest run writes into codex/ and copilot/: they showed as modified before an adapter regeneration that reported written=0.
4. `bin/adr answer` rewrites a CRLF file to LF, like the other lifecycle writers.
5. .githooks/pre-commit runs adr-judge without its own timeout; the LLM pass ceiling from TASK-210 now bounds it, but the declarative pass is not bounded there.
<!-- SECTION:DESCRIPTION:END -->
