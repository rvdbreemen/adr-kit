---
id: TASK-23
title: Install Backlog instructions in adr-kit AGENTS.md and CLAUDE.md
status: Done
assignee: []
created_date: '2026-07-07 09:24'
updated_date: '2026-07-07 09:24'
labels:
  - backlog
  - agent-instructions
dependencies: []
modified_files:
  - AGENTS.md
  - CLAUDE.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add repo-local agent instructions so Codex/Claude agents use the adr-kit Backlog workflow consistently, including the task-first requirement, MCP/CLI preference, and the repo-specific guidance needed by agents.md and Claude.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 AGENTS.md exists at the repo root and instructs agents to use Backlog MCP/CLI for meaningful work in adr-kit.
- [x] #2 CLAUDE.md includes the corresponding backlog guidance in a form that Claude Code will read at session start.
- [x] #3 The instructions do not clobber unrelated repo guidance and keep the existing adr-kit conventions intact.
<!-- AC:END -->



## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Moved from the LLmWiki-KennisBank backlog: added a repo-root AGENTS.md with Backlog-first agent instructions and appended a Backlog workflow section to CLAUDE.md so Claude Code picks it up at session start. Existing adr-kit guidance was preserved and the change was kept to repo-local instructions only.
<!-- SECTION:FINAL_SUMMARY:END -->
