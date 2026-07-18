---
name: upgrade
description: Refresh Codex project artifacts after an ADR Kit plugin update while preserving local edits and unrelated instructions.
license: MIT
---

# Upgrade ADR Kit project artifacts

Resolve the current plugin root from this skill's absolute catalog path.
Compare the version stamp in `.agents/adr-kit-guide.md` with
`<plugin-root>/templates/adr-kit-guide.md`.

Refresh only:

- the `ADR-KIT CODEX` managed block in `AGENTS.md`
- `.agents/adr-kit-guide.md`, after showing a diff when locally edited
- ADR Kit's own pre-commit wrapper through `$adr-kit:install-hooks`

Do not edit `CLAUDE.md`, `.claude/settings.json`, Codex global config, or
Copilot settings. Finish with `$adr-kit:lint`.
