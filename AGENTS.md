# adr-kit Agent Instructions

These instructions adapt the repository guidance for Codex and other coding
agents working in `adr-kit`.

## Task management

- Treat Backlog.md as the source of truth for meaningful work.
- Search for an existing task before starting implementation work.
- If no task exists, create one before editing code or docs.
- Prefer the Backlog MCP tools for reading, searching, creating, and updating
  tasks. Use the `backlog` CLI only when MCP is unavailable or insufficient.
- Do not edit files in `backlog/tasks/` directly.
- Keep tasks small enough to finish in one focused pass.

## Repo conventions

- Keep changes small, focused, and dependency-free unless the roadmap says
  otherwise.
- Follow the existing adr-kit conventions in `README.md`, `ROADMAP.md`, and
  `CLAUDE.md`.
- Favor deterministic, stdlib-first changes over new runtime dependencies.

## Verification

- Run the smallest test or check that proves the change.
- Broaden verification when the change touches shared behavior, tooling,
  package layout, or user-facing workflow.
- Before marking work done, make sure the task status and notes in Backlog are
  updated to match the actual change.
