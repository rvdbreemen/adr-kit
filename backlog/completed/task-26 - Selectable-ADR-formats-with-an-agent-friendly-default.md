---
id: TASK-26
title: Selectable ADR formats with an agent-friendly default
status: Done
assignee:
  - Codex
created_date: '2026-07-18 15:33'
updated_date: '2026-07-18 16:28'
labels:
  - adr-kit
  - architecture
  - templates
  - research
dependencies: []
documentation:
  - docs/adr/ADR-003-template-profile-compatibility.md
  - templates/adr-template.md
  - README.md
  - INSTALL.md
  - ROADMAP.md
  - INSTALL-AGENT.md
  - docs/research/adr-format-evaluation.md
  - docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md
modified_files:
  - docs/research/adr-format-evaluation.md
  - docs/adr/ADR-003-template-profile-compatibility.md
  - docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md
  - docs/adr/ADR-INDEX.md
  - docs/adr/README.md
  - bin/adr_format.py
  - bin/adr
  - bin/adr-audit
  - bin/adr-context
  - bin/adr-index
  - bin/adr-judge
  - bin/adr-lint
  - bin/adr-migrate
  - bin/adr-quality
  - bin/adr-related
  - bin/adr-retire
  - bin/adr-suggest
  - bin/adr-watch
  - bin/adr_schema.py
  - schemas/adr-frontmatter.schema.json
  - schemas/adr-kit-config.schema.json
  - templates/adr-template.md
  - templates/adr-template.madr.md
  - templates/adr-template.nygard.md
  - templates/adr-template.canonical.md
  - templates/adr-kit-guide.md
  - skills/
  - agents/adr-generator.md
  - codex/
  - copilot/
  - scripts/sync-agent-plugins.py
  - examples/
  - INSTALL-AGENT.md
  - README.md
  - INSTALL.md
  - ROADMAP.md
  - CHANGELOG.md
  - .github/workflows/validate.yml
  - tests/test_selectable_formats.py
  - tests/test_template_profiles.py
  - tests/test_agent_installer.py
  - tests/test_documentation_contracts.py
  - tests/test_python_compatibility.py
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Research the dominant ADR document formats, evaluate them for human adoption and AI-agent reliability, supersede ADR-003 with an evidence-backed format strategy, and implement selectable templates across adr-kit. Preserve deterministic local tooling, canonical machine-readable metadata, lifecycle history, enforcement compatibility, and migration safety while allowing projects to choose a supported body format.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A cited research comparison covers the most common ADR formats and evaluates adoption, structure, tooling ecosystem, migration cost, deterministic parseability, token efficiency, and agent reliability.
- [x] #2 A Proposed successor to ADR-003 records the selected default format, supported alternatives, compatibility model, risks, and migration strategy; ADR-003 is superseded only after explicit approval and verification.
- [x] #3 Project configuration can select a supported ADR template format and all ADR creation/lifecycle workflows honor that selection without breaking canonical metadata or Enforcement blocks.
- [x] #4 Lint, index, context, judge, lifecycle, migration, and generated client payloads operate correctly for every supported format, with explicit behavior for unsupported or hybrid documents.
- [x] #5 README, INSTALL, migration guidance, schemas, templates, and client-specific distributions document the selectable formats and recommended agent-friendly default.
- [x] #6 Focused format tests and the broad suite verify backward compatibility, deterministic output, migration safety, and cross-platform behavior.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved execution plan:
1. Research primary sources for Nygard/adr-tools, MADR, Y-Statements, and other materially adopted ADR templates; compare adoption signals, structure, tooling, deterministic parseability, token cost, evidence quality, status/history, enforcement extensibility, and migration risk.
2. Run ADR context/relationship checks, write a cited research report, and draft ADR-005 as the Proposed successor to ADR-003 with the recommended default, supported profiles, compatibility rules, and migration strategy.
3. Complete the approved supersession lifecycle, verifying reciprocal links, append-only history, four authoring gates, and generated index.
4. Implement one shared semantic format registry used by configuration, templates, proposal/lifecycle operations, lint, index, context, judge, related, retire, doctor, migration, and unsupported/hybrid detection.
5. Preserve legacy adr-kit records, invariant frontmatter/status history/enforcement metadata, dry-run/idempotent migration, deterministic output, and Python runtime compatibility.
6. Synchronize Claude/Codex/Copilot/portable payloads and update README, INSTALL, ROADMAP, schema, templates, migration guidance, and changelog.
7. Run focused profile tests, synchronization checks, ADR gates, doctor/index/judge checks, and the broad test suite; then verify acceptance criteria and close TASK-26.1, TASK-26.2, TASK-26.3, and TASK-26 in dependency order.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User explicitly approved the expanded plan on 2026-07-18 and asked to execute TASK-26 through completion. TASK-25 remains paused so this architecture initiative stays the active scope.

TASK-26.1 completed: cited comparison published; ADR-005 accepted as the user-approved successor; ADR-003 is Superseded with reciprocal metadata and append-only status history.

TASK-26.1, TASK-26.2, and TASK-26.3 are all Done. Final verification on 2026-07-18: 555 tests passed and 3 skipped; generated client sync check passed; strict lint passed for all five project ADRs; generated ADR index was current; ADR doctor reported zero findings; ADR-005 quality was 0.92/A and the ADR-003 supersession graph was reciprocal with no dangling references. `git diff --check` found no whitespace errors (only the checkout's expected LF-to-CRLF conversion warnings).

The requested agent-first installation path is complete: README links `INSTALL-AGENT.md` before the overview, and the runbook covers Claude Code, Codex, Copilot, MCP, Agent Skills, and a direct-Python fallback for any shell-capable coding agent. Native installer detection and dry-run were verified without modifying installed client state.

Documentation follow-up: the MADR-default rationale now appears in README.md, INSTALL.md, INSTALL-AGENT.md, and the installed `templates/adr-kit-guide.md`, with synchronized Codex and Copilot copies. CHANGELOG records the clarification. The explanation distinguishes agent reliability from global popularity and gives explicit selection guidance for Nygard and canonical.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the selectable ADR-format initiative. Published a cited comparison of common ADR formats, selected MADR as the agent-friendly default, retained Nygard and canonical as supported profiles, accepted ADR-005, and superseded ADR-003 with reciprocal history. Implemented a shared stdlib format registry across creation, lifecycle, lint, index, context, judge, migration, maintenance, and all native client payloads. Added dry-run/idempotent all-pairs migration, explicit unsupported/hybrid handling, Python/runtime and newline-stability coverage, and a prominent client-neutral agent installation runbook. Verification: 555 passed, 3 skipped; strict lint/index/sync checks passed; doctor found zero issues; ADR-005 is grade A with no dangling relationships.

Expanded the format-choice explanation across public, installation, and installed-agent documentation. Canonical and generated client guides are synchronized; 21 focused documentation/profile tests passed and all 8 affected Markdown files lint clean.
<!-- SECTION:FINAL_SUMMARY:END -->
