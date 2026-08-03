---
id: TASK-105
title: >-
  Make the setup skills write one layout, and fix the command Codex and Copilot
  document
status: To Do
assignee: []
created_date: '2026-08-03 19:34'
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
- [ ] #1 The command line in `codex/skills/setup/SKILL.md` and `copilot/skills/setup/SKILL.md` runs as written, or `setup-project.py` gains the positional and the `--client` alias its own documentation assumes
- [ ] #2 A test executes the literal command each setup skill documents, so a divergence fails CI rather than a user's install
- [ ] #3 `/adr-kit:setup` and `/adr-kit:init` shell out to `scripts/setup-project.py` instead of re-implementing an older layout in prose
- [ ] #4 The Codex and Copilot setup paths reach `adr-settings --check-embedding`, so R16's detection happens on all three clients
- [ ] #5 A fresh Codex project and a fresh Copilot project each end with ADR instructions in the file that client actually reads
<!-- AC:END -->
