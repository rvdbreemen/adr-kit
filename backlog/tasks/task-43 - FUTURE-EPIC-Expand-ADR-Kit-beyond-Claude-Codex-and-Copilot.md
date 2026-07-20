---
id: TASK-43
title: 'FUTURE EPIC: Expand ADR Kit beyond Claude, Codex, and Copilot'
status: To Do
assignee: []
created_date: '2026-07-19 19:02'
updated_date: '2026-07-19 19:02'
labels:
  - epic
  - future
  - client-expansion
  - plugins
dependencies: []
references:
  - 'https://opencode.ai/docs/plugins/'
  - 'https://kilo.ai/docs/automate/extending/plugins'
  - 'https://www.kimi.com/code/docs/en/'
  - 'https://cursor.com/docs/reference/plugins'
  - 'https://code.visualstudio.com/docs/agent-customization/agent-plugins'
  - 'https://goose-docs.ai/'
  - 'https://github.com/QwenLM/qwen-code'
  - 'https://omp.sh/docs'
  - 'https://pi.dev/'
documentation:
  - docs/research/cross-client-plugin-hooks-report.md
  - docs/reviews/cross-client-plugin-planning-findings.md
  - docs/plans/cross-client-plugin-implementation-plan.md
modified_files:
  - clients/
  - skills/
  - prompts/
  - hooks/
  - scripts/
  - tests/
  - docs/clients/
  - docs/client-support.md
priority: low
ordinal: 43000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Preserve and eventually execute ADR Kit support expansion beyond the current Claude Code CLI, Codex CLI, and GitHub Copilot CLI scope. This future epic owns generic portability and every additional client or IDE surface researched in TASK-38, including OpenCode, Kilo Code, Kimi Code, Cursor, VS Code Agent Plugins, goose, Qwen Code, Gemini CLI, OMP, Pi, and the remaining watchlist candidates. It is deliberately independent from TASK-40: it must not delay, change, or become a release dependency for the three-client program. Work starts only after explicit maintainer activation and a fresh capability/adoption/maintenance review.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The epic remains independent from TASK-40 and is not part of Claude/Codex/Copilot release certification or completion.
- [ ] #2 Before implementation, official contracts, current versions, adoption, maintenance activity, OS/surface availability, and licensing are refreshed for every nominated client.
- [ ] #3 The maintainer explicitly selects each expansion wave; research inclusion alone never authorizes an adapter or support claim.
- [ ] #4 A generic standards layer may package Agent Skills, AGENTS.md, generated ADR guidance, local MCP intent, and portable prompts/workflows, but its exact promise is decided when this epic is activated.
- [ ] #5 OpenCode, Kilo Code CLI/VS Code, Kimi Code, Cursor surfaces, VS Code Agent Plugins, goose, Qwen Code, Gemini CLI, OMP, Pi, and remaining TASK-38 candidates are retained in the future candidate register with separate surface identities.
- [ ] #6 Every selected client receives its own bounded implementation and certification task; shared libraries do not couple independent client completion or promotion.
- [ ] #7 Only environments that satisfy the then-current full ADR Kit requirements and impact/adoption policy can become first-class; partial compatibility is labeled honestly.
- [ ] #8 Each promoted client proves native or explicitly approved generic discovery, workflows, instructions, hooks/outcome degradations, MCP, install/update/rollback/uninstall, doctor, latency, OS scope, and documentation.
- [ ] #9 No future client is installed by default, advertised as supported, or added to a release gate before its independent evidence passes and the maintainer approves promotion.
- [ ] #10 Archived TASK-40.8/.9/.10/.11/.12/.14 and TASK-38 remain historical inputs; their old assumptions must be revalidated rather than copied as current facts.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Activation gate: do not start until the maintainer explicitly selects this epic after the three-client program. Phase 1 refreshes TASK-38 evidence and records current capabilities, adoption, maintenance, OS/surface, licensing, and maintenance budget. Phase 2 decides the generic standards promise and selects a small expansion wave. Phase 3 creates one bounded implementation/certification task per approved client surface. Phase 4 promotes clients independently from passing evidence and updates installer defaults only with explicit approval. Stop whenever a client lacks the full required contract, sustainable maintenance, or a current user priority; retain it as compatibility/watchlist rather than building around gaps.
<!-- SECTION:PLAN:END -->
