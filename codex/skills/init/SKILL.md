---
name: init
description: Bootstrap ADR Kit in a project from Codex, including instructions, an architecture audit, initial ADR proposals, and the pre-commit gate.
license: MIT
---

# Initialize ADR Kit from Codex

This is a mutating workflow. Confirm the workspace root, then:

1. Follow `$adr-kit:setup` to add the managed `AGENTS.md` block and guide.
2. Run `python <plugin-root>/bin/adr-audit --root <workspace>`.
3. Present discovered decisions in small batches. Create only the choices the
   user approves, using `$adr-kit:adr`.
4. Follow `$adr-kit:install-hooks`.
5. Run `python <plugin-root>/bin/adr-doctor --fix-index docs/adr/`.

Resolve `<plugin-root>` from this skill's absolute catalog path. Never use a
Claude plugin cache path. Keep existing `AGENTS.md` content byte-stable outside
the ADR Kit managed markers.
