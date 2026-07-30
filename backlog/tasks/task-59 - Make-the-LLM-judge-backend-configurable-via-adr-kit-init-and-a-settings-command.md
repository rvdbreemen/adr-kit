---
id: TASK-59
title: >-
  Make the LLM judge backend configurable via /adr-kit:init and a settings
  command
status: To Do
assignee: []
created_date: '2026-07-30 05:49'
labels:
  - mcp
  - judge
  - config
  - skills
dependencies: []
references:
  - docs/adr/ADR-001-llm-gates-opt-in.md
  - skills/init/SKILL.md
modified_files:
  - skills/init/SKILL.md
  - schemas/adr-kit-config.schema.json
  - bin/adr_config.py
  - clients/workflows.json
priority: medium
ordinal: 64500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The judge backend must be choosable by the user at setup time and changeable afterwards, without hand-editing JSON.

Depends on the ADR now being drafted (turns the LLM pass on by default and makes it use the host agent's model, with OpenRouter and local Ollama as opt-in alternatives). That ADR supersedes ADR-001. Do not start until it is Accepted — this task implements a decision, it does not make one.

**What exists today**

- `skills/init/SKILL.md` already has section "4a — Interactive LLM opt-in (new in v0.17.0)". It prints a cost notice naming `claude-sonnet-4-6`, up to 2 Sonnet calls per commit, a 120s timeout and an estimated $0.10–$0.30 per commit, then asks two Y/N questions both defaulting to No, and writes the answers to `docs/adr/.adr-kit.json`. That whole section is built on the opt-in default the new ADR reverses, so its text and its defaults both change.
- There is **no** settings skill in adr-kit. The skill set is: adr, context, grill, guardian, init, install-hooks, judge, lint, migrate, related, retire, review, setup, supersede, upgrade. Compare `kennisbank:settings` in the user's KennisBank vault for the shape of a toggle-listing settings command.
- `schemas/adr-kit-config.schema.json` already carries `judge.llm_enabled` (default false), `llm_default`, `llm_model`, `llm_cmd` (array or shell string), `llm_timeout_seconds`, `advisory_only`. Any new backend keys must be added there, because the config is schema-validated by `bin/adr_config.py`.
- The three client distributions are generated per client (`clients/installer/payload.py`), which is relevant if the chosen backend has to differ per distribution.

**Work**

1. Rewrite `skills/init/SKILL.md` section 4a: replace the two Y/N opt-in questions with a backend choice, and correct the cost notice so it no longer names a pinned model if the default becomes host-native. Keep the notice honest about cost — that is the whole reason ADR-001 made this opt-in, and reversing the default does not make the cost disappear.
2. Add a settings surface so the choice is changeable later. Either a new `/adr-kit:settings` skill listing the toggles with their current values, or an extension of an existing skill — decide and say why. It must show what is currently configured, not just accept new input.
3. Extend the config schema with whatever the ADR's backend registry defines, with descriptions good enough that someone reading the schema can configure it without the ADR.
4. Mirror the changes into the generated `codex/` and `copilot/` skill trees via the normal generation path, not by hand-editing the mirrors.
5. The OpenRouter API key must be read from the environment and must never be written into `docs/adr/.adr-kit.json`, which is committed. The init flow must not prompt for a key and store it.

**Verification**

Run `/adr-kit:init` end to end in a scratch project for each backend choice and confirm the resulting config validates and the judge actually runs with it. A settings command that writes a config the judge then rejects is worse than no command.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `/adr-kit:init` offers an explicit backend choice (host-agent-native, OpenRouter, local Ollama) instead of the two opt-in Y/N questions
- [ ] #2 The init cost notice is accurate for the new default and no longer names a pinned model that is not used
- [ ] #3 A settings surface exists that shows the CURRENT judge configuration and can change it, without hand-editing JSON
- [ ] #4 `schemas/adr-kit-config.schema.json` carries every new backend key with a usable description, and `bin/adr_config.py` validates a config produced by init
- [ ] #5 The OpenRouter API key is read from the environment; no code path writes it into the committed .adr-kit.json, and init never prompts to store it
- [ ] #6 The codex/ and copilot/ skill trees are regenerated through the normal generation path, not hand-edited
- [ ] #7 `/adr-kit:init` has been run end to end in a scratch project for each backend, and the judge verifiably runs with the resulting config
- [ ] #8 No change is made before the governing ADR is Accepted
<!-- AC:END -->
