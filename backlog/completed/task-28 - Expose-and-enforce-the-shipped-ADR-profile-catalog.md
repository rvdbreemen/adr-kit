---
id: TASK-28
title: Expose and enforce the shipped ADR profile catalog
status: Done
assignee: []
created_date: '2026-07-18 17:07'
updated_date: '2026-07-18 17:17'
labels:
  - formats
  - agents
  - templates
  - documentation
dependencies: []
modified_files:
  - bin/adr_format.py
  - bin/adr
  - codex/bin/adr_format.py
  - codex/bin/adr
  - copilot/bin/adr_format.py
  - copilot/bin/adr
  - schemas/adr-kit-config.schema.json
  - codex/schemas/adr-kit-config.schema.json
  - copilot/schemas/adr-kit-config.schema.json
  - skills/adr/SKILL.md
  - codex/skills/adr/SKILL.md
  - copilot/skills/adr/SKILL.md
  - agents/adr-generator.md
  - templates/adr-kit-guide.md
  - codex/templates/adr-kit-guide.md
  - copilot/templates/adr-kit-guide.md
  - README.md
  - INSTALL.md
  - INSTALL-AGENT.md
  - docs/format-migration.md
  - CHANGELOG.md
  - tests/test_selectable_formats.py
  - tests/test_documentation_contracts.py
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make every non-default ADR format an explicitly shipped, agent-discoverable profile. MADR remains preferred; Nygard and canonical remain the only supported alternatives. Agents and users must be able to discover the catalog and matching templates deterministically, and ADR creation must reject unsupported or incomplete profile installations before writing a record.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The shared profile catalog lists exactly madr, nygard, and canonical, with MADR marked preferred.
- [x] #2 Every selectable profile resolves to a bundled template and a missing template fails before ADR creation writes a file.
- [x] #3 A human-readable and JSON CLI command exposes supported profiles, preference, guidance, and template availability for coding agents.
- [x] #4 Root, Codex, and Copilot payloads contain synchronized templates for every selectable profile.
- [x] #5 Agent-facing installation and ADR guidance accepts only shipped profile identifiers and tells agents to use the selected matching template.
- [x] #6 README and documentation explain why MADR is preferred and how to choose a supported alternative.
- [x] #7 Focused tests, full tests, payload sync checks, lint, and documentation checks pass.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented a single ordered PROFILE_CATALOG in bin/adr_format.py. MADR is the sole preferred profile; Nygard and canonical are the only alternatives. Added fail-closed profile_template_path resolution and `adr profiles` human/JSON discovery with exact installed template paths and availability. `adr new` validates the shipped template before creating the target ADR directory. Updated Claude, Codex, Copilot, installed project guide, README, install docs, schema wording, migration docs, and synchronized package payloads.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-18 17:17
---
Completion evidence recorded: full suite 572 passed / 3 skipped; focused profile and documentation suite 34 passed; strict self-lint passed all 5 ADRs; markdownlint 0 issues; synchronized payload and diff checks passed.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped an enforceable, agent-readable ADR profile catalog. Agents can run `python bin/adr profiles --format json`, accept only returned ids with `available:true`, and use the matching bundled template. MADR remains the preferred agent-friendly default; Nygard and adr-kit canonical are the supported pre-made alternatives. Arbitrary template filenames do not become profiles, and a missing registered template blocks creation before project files are written. Verification: 572 passed, 3 skipped; focused profile/documentation tests 34 passed; strict self-lint passed 5 ADRs; markdownlint reported 0 issues; generated client payload drift check and git diff check passed.
<!-- SECTION:FINAL_SUMMARY:END -->
