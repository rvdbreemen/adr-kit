---
id: TASK-238
title: Reply in the user's language across skills and agent
status: Done
assignee: []
created_date: '2026-10-13 21:21'
updated_date: '2026-10-13 21:39'
labels: []
dependencies: []
modified_files:
  - skills/*/SKILL.md
  - agents/adr-generator.md
  - scripts/client_generation_model.py
  - scripts/client_generation_artifacts.py
  - codex/skills/*/SKILL.md
  - copilot/skills/*/SKILL.md
  - tests/test_reply_language.py
  - CHANGELOG.md
type: feature
ordinal: 80000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
adr-kit skills have no reply-language rule, so the host default decides. Add one identical rule to every canonical SKILL.md and agents/adr-generator.md: reply in the language the user writes in, default English. Command output, identifiers, paths and ADR file content stay unchanged; ADR document language remains governed by the project (adr-generator rule). Regenerate client adapters and guard with a contract test.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every skills/*/SKILL.md and agents/adr-generator.md carries the identical reply-language sentence directly under the H1
- [x] #2 ADR document-language rule in adr-generator.md is unchanged
- [x] #3 build-client-adapters --check reports changed=0 after regeneration
- [x] #4 A contract test fails when a SKILL.md lacks the sentence
- [x] #5 CHANGELOG has an Unreleased entry
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added one reply-language rule ("Reply in the language the user writes in; default to English. Keep command output, identifiers, paths, and ADR file content unchanged.") directly under the H1 of all 17 canonical skills and agents/adr-generator.md. Codex and Copilot skills are rendered from clients/workflows.json, so the sentence lives as REPLY_RULE in scripts/client_generation_model.py and render_skill() emits it; regenerated 34 files, --check changed=0. Document language stays project-governed (adr-generator rule unchanged). tests/test_reply_language.py guards all three client surfaces. Full suite: 2142 passed, 25 skipped. Limitation: a host-level language setting (Claude Code `language`) overrides skill text.
<!-- SECTION:FINAL_SUMMARY:END -->
