---
name: context
description: Find the Architecture Decision Records most relevant to a task before implementation. Read-only and deterministic.
license: MIT
---

# ADR context for Codex

Take the topic from the invocation. If it is missing, ask for one short task
description. Call the `adr-kit.adr_context` MCP tool with:

- `query`: the topic
- `limit`: 5
- `project_root`: the absolute active workspace root

Read each returned ADR and summarize its Decision in one line with its path and
relevance score. Keep the highest-relevance ADR closest to the implementation
handoff. If the result is empty, say so without inventing a constraint.

This workflow is read-only.
