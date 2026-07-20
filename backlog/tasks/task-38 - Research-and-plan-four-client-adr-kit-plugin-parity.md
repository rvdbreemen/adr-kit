---
id: TASK-38
title: Research and plan broad cross-client ADR Kit plugin parity
status: Done
assignee: []
created_date: '2026-07-19 16:51'
updated_date: '2026-07-19 17:25'
labels:
  - research
  - plugins
  - hooks
  - cross-client
dependencies: []
references:
  - 'https://learn.chatgpt.com/docs/hooks'
  - 'https://code.claude.com/docs/en/hooks'
  - 'https://docs.github.com/en/copilot/reference/hooks-reference'
  - 'https://cursor.com/docs/reference/plugins'
  - 'https://antigravity.google/docs/plugins'
  - 'https://opencode.ai/docs/plugins/'
  - 'https://pi.dev/'
  - 'https://github.com/can1357/oh-my-pi'
  - 'https://code.visualstudio.com/docs/agent-customization/agent-plugins'
  - 'https://qwenlm.github.io/qwen-code-docs/en/users/extension/introduction/'
  - 'https://geminicli.com/docs/extensions/reference/'
  - 'https://ampcode.com/manual'
  - 'https://goose-docs.ai/docs/guides/context-engineering/hooks/'
  - 'https://github.com/letta-ai/letta-code'
  - 'https://docs.openhands.dev/sdk/guides/plugins'
  - 'https://github.com/HKUDS/OpenHarness'
  - 'https://omo.dev/docs'
  - 'https://agents.md/'
  - 'https://agentskills.io/'
  - 'https://github.com/warpdotdev/Warp'
  - 'https://www.kimi.com/code/docs/en/kimi-code-cli/customization/plugins.html'
  - 'https://www.kimi.com/code/docs/en/kimi-code-cli/customization/hooks.html'
  - 'https://github.com/NousResearch/hermes-agent'
  - 'https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins'
  - 'https://zcode.z.ai/en/docs/plugin'
  - 'https://kiro.dev/docs/cli/hooks/'
  - 'https://github.com/sorrycc/awesome-code-agents'
  - 'https://github.com/bradagi/awesome-cli-coding-agents'
documentation:
  - docs/adr/
  - README.md
  - ROADMAP.md
modified_files:
  - docs/research/cross-client-plugin-hooks-report.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Produce a durable, evidence-backed landscape report covering KennisBank lifecycle hooks and ADR Kit packaging across major and emerging coding-agent environments. Apply a strict admission gate so only clients with supportable skills, prompts/commands, persistent instructions, lifecycle/tool hooks, MCP or an equivalent bridge, native or safely owned updates, and a verifiable doctor can become first-class. Include idempotent install/update/rollback, legacy detection, non-clobbering AGENTS.md/CLAUDE.md/Copilot instructions, a canonical ADR guide, hard-exit recovery, and a phased implementation plan.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Report compares official hook and plugin contracts for Claude Code, Codex, GitHub Copilot CLI, Cursor, Antigravity, and OpenCode, applies an explicit full-capability admission gate, and clearly separates first-class recommendations from portable fallbacks.
- [x] #2 Report evaluates KennisBank-style retrieval, capture, transcript archiving, compaction, subagent, and hard-exit use cases per available hook, including latency and failure-mode tradeoffs.
- [x] #3 Plan defines a canonical adr-kit capability model with thin adapters only for admitted first-class clients, covering skills, slash commands or prompts, hooks, packaging, and non-clobbering managed instruction blocks plus a shared adr-kit-guide.md.
- [x] #4 Installer plan detects supported installed clients and previous adr-kit versions, is idempotent, defaults to recommended automated behavior, preserves user-owned configuration, and identifies any controls that require explicit user choice.
- [x] #5 Report includes phased implementation tasks, verification strategy, migration and rollback behavior, and a focused list of proposed optional controls for user confirmation.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Establish an official-document capability and adoption gate. 2. Compare major-client hooks and normalize KennisBank lifecycle semantics. 3. Screen named and discovery-list environments, separating full targets, contract tests, compatibility, and exclusions. 4. Define a canonical Python core, generated adapters, portable skills/prompts, managed instruction blocks, installer/update/rollback, and cross-client doctor. 5. Specify phased delivery and executable certification gates before any client is advertised as supported.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Completed a primary-source landscape pass and tightened admission to require the complete lifecycle, >=2,000 GitHub stars plus recent maintenance for community clients, or material impact plus an official contract for proprietary clients. Added Kimi Code as the highest-priority full target; Hermes as a compaction-gated candidate; and explicit analyses for Warp, Cursor CLI, Kiro, Crush, Z Code, MiMo, Aider, CodeBuff, Groq Code CLI, Neovate, and the two supplied discovery lists. Warp passes adoption but fails lifecycle/plugin parity. Verification: `git diff --check`; `python bin/adr-lint --strict docs/adr` (9 PASS, 0 FAIL); `python bin/adr-index --check docs/adr` (all generated artifacts current).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Produced a durable cross-client ADR Kit and KennisBank research report covering official plugin/hook contracts, a strict capability-plus-adoption support gate, hook-by-hook retrieval/capture/archive guidance, hard-exit recovery, latency targets, and a broad environment screening. Defined one deterministic Python core with generated native adapters, portable skills and slash workflows, non-clobbering AGENTS.md/CLAUDE.md/Copilot instruction blocks pointing to `.adr-kit/ADR-guide.md`, idempotent legacy-aware installation, verified updates with rollback, and a common doctor. The plan now distinguishes supported targets from contract-test candidates and partial compatibility, with Kimi Code promoted and Warp correctly excluded from full support. Verified repository ADR health and index freshness; this task changes documentation only.
<!-- SECTION:FINAL_SUMMARY:END -->
