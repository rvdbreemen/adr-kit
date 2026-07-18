---
name: init
description: Bootstrap ADR Kit in a project from GitHub Copilot CLI, including instructions, an architecture audit, initial ADR proposals, and the pre-commit gate.
license: MIT
---

# Initialize ADR Kit from GitHub Copilot CLI

This is a mutating workflow. Confirm the workspace root, then:

1. Follow `the ADR Kit setup skill` to add the managed `AGENTS.md` block and guide.
2. If `<workspace>/docs/adr` exists, run
   `python <plugin-root>/bin/adr-migrate --plan <workspace>/docs/adr`.
   Report deterministic preview commands and guided notices; do not migrate.
3. Run `python <plugin-root>/bin/adr-audit --root <workspace>`.
4. Present discovered decisions in small batches. Create only the choices the
   user approves, using `the ADR Kit adr skill`.
5. Follow `the ADR Kit install-hooks skill`.
6. Run `python <plugin-root>/bin/adr-doctor --fix-index docs/adr/` and report
   any migration notices from lint.

Resolve `<plugin-root>` from this skill's absolute catalog path. Never use a
Claude plugin cache path. Keep existing `AGENTS.md` content byte-stable outside
the ADR Kit managed markers.
