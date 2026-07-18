---
name: init
description: Bootstrap ADR Kit in a project from Codex, including instructions, an architecture audit, initial ADR proposals, and the pre-commit gate.
license: MIT
---

# Initialize ADR Kit from Codex

This is a mutating workflow. Confirm the workspace root, then:

1. Follow `$adr-kit:setup` to add the managed `AGENTS.md` block and guide.
2. If `<workspace>/docs/adr` exists, run
   `python <plugin-root>/bin/adr-migrate --plan <workspace>/docs/adr`.
   Report deterministic preview commands and guided notices; do not migrate.
3. Run `python <plugin-root>/bin/adr-audit --root <workspace>`.
4. Present discovered decisions in small batches. Create only the choices the
   user approves, using `$adr-kit:adr`.
5. Follow `$adr-kit:install-hooks`.
6. Run `python <plugin-root>/bin/adr-doctor --fix-index docs/adr/` and report
   any migration notices from lint.

Resolve `<plugin-root>` from this skill's absolute catalog path. Never use a
Claude plugin cache path. Keep existing `AGENTS.md` content byte-stable outside
the ADR Kit managed markers.
