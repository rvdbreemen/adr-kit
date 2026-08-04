---
id: TASK-109
title: Persist the embedding model the user consented to download
status: To Do
assignee: []
created_date: '2026-08-03 19:34'
labels:
  - retrieval
  - settings
  - bug
dependencies:
  - TASK-105
priority: medium
ordinal: 3600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R16's route 1 asks the user to consent to a 4.7 GB `qwen3-embedding:8b` pull, and the chosen model then lands nowhere. `bin/adr-embed:53` hardcodes `DEFAULT_EMBED_MODEL = "nomic-embed-text"`, overridable only by `--model`, and the config schema has no embedding key at all.

Under ADR-018's own rule a model-identity mismatch marks the store stale, so the visible outcome is either a wasted download or retrieval quietly falling back to lexical — exactly the discover-it-later failure R16 exists to prevent.

A second gap in the same area: the string `adr-embed` appears in no skill, template, workflow or README. The build step R6.1 depends on is not documented anywhere a user would look.

No ADR needed: ADR-018 (and its successor, TASK-92) already decides which registry selects the embedding backend and that a changed model identity marks the store stale.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `embedding.model` (and `embedding.enabled` if warranted) exist in `schemas/adr-kit-config.schema.json` and in `FEATURED` in `bin/adr-settings`
- [ ] #2 `adr-embed build` reads the configured model as its default instead of the hardcoded constant
- [ ] #3 Setup step 4c writes the chosen model through `adr-settings --set embedding.model=<...>` immediately after a consented pull
- [ ] #4 `adr-embed build` is named in the setup skill, so the build step R6.1 depends on is discoverable
- [ ] #5 A test pulls-then-configures on a fixture and asserts the store records the configured model identity
<!-- AC:END -->
