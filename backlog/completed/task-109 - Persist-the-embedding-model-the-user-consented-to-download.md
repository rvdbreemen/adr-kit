---
id: TASK-109
title: Persist the embedding model the user consented to download
status: Done
assignee: []
created_date: '2026-08-03 19:34'
updated_date: '2026-08-03 22:26'
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
- [x] #1 `embedding.model` (and `embedding.enabled` if warranted) exist in `schemas/adr-kit-config.schema.json` and in `FEATURED` in `bin/adr-settings`
- [x] #2 `adr-embed build` reads the configured model as its default instead of the hardcoded constant
- [x] #3 Setup step 4c writes the chosen model through `adr-settings --set embedding.model=<...>` immediately after a consented pull
- [x] #4 `adr-embed build` is named in the setup skill, so the build step R6.1 depends on is discoverable
- [x] #5 A test pulls-then-configures on a fixture and asserts the store records the configured model identity
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`embedding.model` and `embedding.enabled` now exist in the schema and in `FEATURED`, `adr-embed build` reads the configured model as its default, and setup writes it immediately after a consented pull.

Verified on this repository: `/adr-kit:settings` shows

```
embedding.enabled              true   [default]
embedding.model                (unset)   [unset]
```

**The reader is fail-soft, and the reasoning is worth keeping.** No file, malformed JSON, an empty document, a block without the key, a blank string and a wrong type all fall through to `DEFAULT_EMBED_MODEL` — six parametrised cases. Refusing to build a store over a typo in an unrelated key would be a worse trade than building it with the default model and recording *that* identity honestly, since ADR-018's staleness check then reports the mismatch rather than hiding it.

The model name is project-scoped rather than machine-local, unlike the judge's base URL: which model embeds a team's ADRs determines what every teammate's retrieval returns, so it is a team decision. The runtime serving it is not.

AC#4 mattered more than it looked. The string `adr-embed` appeared in no skill, template, workflow or README — the build step the whole vector layer depends on was undiscoverable. Setup now names `adr-embed build` alongside the `--set embedding.model=` write, and says why it is an explicit step: nothing embeds because a prompt was submitted.

121 settings, embed, schema, documentation-contract and client-generation tests pass.
<!-- SECTION:FINAL_SUMMARY:END -->
