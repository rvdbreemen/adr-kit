<!-- ADR-KIT STUB START -->
<!-- DO NOT regenerate manually. Updated by `/adr-kit:init`, `/adr-kit:upgrade`, `/adr-kit:setup`. -->
## ADR Kit

This project uses [adr-kit](https://github.com/rvdbreemen/adr-kit). All architectural decisions live as ADRs in `docs/adr/`. Full guide: @.claude/adr-kit-guide.md

Authoring: `/adr-kit:adr` (or the `adr-generator` subagent).
Pre-commit verification: `bin/adr-judge` runs declarative `Enforcement` rules at commit time. ADRs with `llm_judge: true` are reviewed in-session via `/adr-kit:judge`.
<!-- ADR-KIT STUB END -->

## Backlog.md

This repository uses Backlog.md (`backlog/`) as the source of truth for work.

- Search for an existing task before starting any meaningful implementation or
  design work.
- If no task exists, create one before editing code or docs.
- Prefer the Backlog MCP tools for reading, searching, creating, and updating
  tasks. Use the `backlog` CLI only as a fallback.
- Keep tasks small enough to complete in one focused pass.
- Do not edit files in `backlog/tasks/` directly.
