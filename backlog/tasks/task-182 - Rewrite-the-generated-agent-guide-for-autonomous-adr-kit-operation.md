---
id: TASK-182
title: Rewrite the generated agent guide for autonomous adr-kit operation
status: In Progress
assignee: []
created_date: '2026-08-19 20:51'
updated_date: '2026-08-19 21:20'
labels:
  - docs
  - agents
dependencies: []
priority: medium
type: enhancement
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The generated .adr-kit/ADR-guide.md describes the development cycle (context before implementation, advisory hooks during, lint + judge before completion) but assumes a human-driven flow. Rewrite the canonical source of the guide so a coding agent can operate adr-kit autonomously: which tool to call at which phase (MCP tool names and CLI equivalents side by side), what is read-only vs mutating, what requires a human (acceptance per ADR-011, signer per ADR-027), and how to react to each outcome (lint findings, judge violations, readiness verdicts). Must be edited in the canonical source, never in generated output; regenerate afterwards.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Canonical source of ADR-guide.md located and edited (not the generated file)
- [x] #2 Guide maps each development phase to MCP tool + CLI command with expected outcomes and agent reactions
- [x] #3 Guide states explicitly which actions stay human-gated (accept, signer, supersede approval)
- [x] #4 Regenerated artifacts are deterministic; adapter --check reports changed=0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Canonical source instructions/ADR-guide.md rewritten for autonomous agent operation: tool-surface table (MCP tool vs CLI, mutates yes/no), per-phase steps with expected outcomes and reactions (lint verdicts, judge violations, readiness classification), and an explicit human-gated list (accept, supersede, reject, signer per ADR-011/ADR-027). Deployed copy .adr-kit/ADR-guide.md updated; codex/copilot copies regenerated via build-client-adapters (--check changed=0).
<!-- SECTION:NOTES:END -->
