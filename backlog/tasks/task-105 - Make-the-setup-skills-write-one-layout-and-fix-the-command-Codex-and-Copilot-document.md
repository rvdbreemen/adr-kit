---
id: TASK-105
title: >-
  Make the setup skills write one layout, and fix the command Codex and Copilot
  document
status: Done
assignee: []
created_date: '2026-08-03 19:34'
updated_date: '2026-08-03 22:06'
labels:
  - setup
  - bug
  - clients
dependencies: []
priority: high
ordinal: 3200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A Codex or Copilot user who follows the documented setup path gets no ADR instructions in the file their agent reads. On Copilot, where there is no PreToolUse tier by design, nothing else tells the agent either.

**Two independent failures.**

(a) `skills/setup/SKILL.md:44-64` and `skills/init/SKILL.md:174-190` append the legacy `<!-- ADR-KIT STUB START -->` block and drop `.claude/adr-kit-guide.md` — exactly the footprint `scripts/project_setup.py:25-28` classifies as `LEGACY_GUIDES` and migrates away from. Neither mentions `AGENTS.md`. The Codex and Copilot setup skills correctly delegate to `scripts/setup-project.py`, so the divergence is Claude-only.

(b) That delegated command does not work as written. `scripts/setup-project.py` defines no positional argument, so `... --client <client-id> <workspace>` gives `unrecognized arguments`; and the flag is `--clients` (plural) taking `claude`/`codex`/`copilot`, so `--client codex-cli` survives argparse prefix matching and then dies on the dict lookup with exit 2. The working invocation — `--clients codex --project-root <p>` — is documented nowhere.

There is a third hole in the same area: `grep -rn check-embedding` finds exactly two callers, both Claude skills, while the mirrored `bin/adr-settings` carries the flag on every client. R16 says setup must find out whether a local embedding runtime exists; on two of three clients it never asks.

No ADR needed: ADR-004 already governs the layered instruction surface. This is convergence between two implementations of one decision.

Blocks the dogfooding task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The command line in `codex/skills/setup/SKILL.md` and `copilot/skills/setup/SKILL.md` runs as written, or `setup-project.py` gains the positional and the `--client` alias its own documentation assumes
- [x] #2 A test executes the literal command each setup skill documents, so a divergence fails CI rather than a user's install
- [x] #3 `/adr-kit:setup` and `/adr-kit:init` shell out to `scripts/setup-project.py` instead of re-implementing an older layout in prose
- [x] #4 The Codex and Copilot setup paths reach `adr-settings --check-embedding`, so R16's detection happens on all three clients
- [x] #5 A fresh Codex project and a fresh Copilot project each end with ADR instructions in the file that client actually reads
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All three failures fixed, and the fix for the first one is belt and braces on purpose.

**The documented command now runs, and the script no longer punishes the caller for using the other vocabulary.** Both were done rather than either:

- `clients/workflows.json` — the single source both generated skills come from — now says `--client <client-id> --project-root <workspace>`.
- `setup-project.py` accepts a positional workspace, `--client` as a singular alias, and full client ids (`codex-cli` → `codex`). An unknown client is refused **by name** with the valid values listed, instead of dying on a `KeyError` after argparse already accepted it.

Reproduced first: `--client codex-cli <workspace>` exited 2 with `unrecognized arguments`. All five spellings now exit 0.

**One layout.** `skills/setup/SKILL.md` and `skills/init/SKILL.md` no longer hand-write a stub block or a `.claude/` guide; both shell out to `scripts/setup-project.py`, which owns `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md` and `.adr-kit/ADR-guide.md`. The v0.11 detection stays in the skills, because refusing to migrate silently is a judgement the writer should not make. Four further stragglers were caught by the test and removed: the summary block, the suggested first-commit command, the "read before write" constraint and both skills' opening summaries all still described the old layout.

**R16 reaches all three clients.** The `--check-embedding` step moved into the `setup` workflow procedure, so it is generated into the Codex and Copilot skills rather than living only in Claude prose. The init workflow also now names the openai-compatible backend alongside the other three, with the `--base-url` + `--model` requirement TASK-107 added.

**The test executes the documentation rather than grepping it.** `tests/test_setup_project_command.py` extracts the command from each generated skill, substitutes the placeholders, and runs it — 15 cases. A string assertion would have passed against the broken command for as long as the string was present.
<!-- SECTION:FINAL_SUMMARY:END -->
