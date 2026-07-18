---
name: setup
description: Register ADR Kit in a Copilot CLI project by adding a managed AGENTS.md block and a versioned local guide. Idempotent.
license: MIT
---

# Set up a Copilot CLI project

This is a mutating workflow. Resolve the plugin root from this skill's absolute
catalog path. Read `AGENTS.md` before editing it.

Copy `<plugin-root>/templates/adr-kit-guide.md` to
`.agents/adr-kit-guide.md`. Add or refresh only this managed block:

```markdown
<!-- ADR-KIT CODEX START -->
## ADR Kit

Read `.agents/adr-kit-guide.md` before architectural changes. Architecture
decisions live in `docs/adr/`. Use `the ADR Kit context skill` before implementation,
`the ADR Kit adr skill` to author a decision, and `the ADR Kit judge skill` before commit.
<!-- ADR-KIT CODEX END -->
```

Preserve all content outside the markers. Re-running with current content is a
no-op. Do not create or change `CLAUDE.md`.
