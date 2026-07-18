---
id: TASK-30
title: Add deterministic JSON ADR graph index for agent retrieval
status: Done
assignee:
  - Codex
created_date: '2026-07-18 18:54'
updated_date: '2026-07-18 19:21'
labels:
  - adr
  - agent-retrieval
  - index
  - governance
dependencies: []
references:
  - bin/adr-index
  - bin/adr-context
  - bin/adr-related
documentation:
  - docs/adr/ADR-004-layered-adr-context-injection.md
  - docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md
  - README.md
  - INSTALL-AGENT.md
modified_files:
  - .github/workflows/adr-index-check.yml
  - .github/workflows/validate.yml
  - CHANGELOG.md
  - CLAUDE.md
  - INSTALL-AGENT.md
  - INSTALL.md
  - README.md
  - agents/adr-generator.md
  - bin/adr_catalog.py
  - bin/adr-context
  - bin/adr-index
  - bin/adr-related
  - schemas/adr-index.schema.json
  - docs/adr/ADR-007-json-adr-graph-index-for-agent-retrieval.md
  - docs/adr/ADR-INDEX.md
  - docs/adr/ADR-INDEX.json
  - docs/adr/README.md
  - skills/adr/SKILL.md
  - skills/context/SKILL.md
  - skills/init/SKILL.md
  - skills/setup/SKILL.md
  - templates/adr-kit-guide.md
  - codex/bin/adr_catalog.py
  - codex/bin/adr-context
  - codex/bin/adr-index
  - codex/bin/adr-related
  - codex/schemas/adr-index.schema.json
  - codex/templates/adr-kit-guide.md
  - copilot/bin/adr_catalog.py
  - copilot/bin/adr-context
  - copilot/bin/adr-index
  - copilot/bin/adr-related
  - copilot/schemas/adr-index.schema.json
  - copilot/templates/adr-kit-guide.md
  - tests/test_adr_context.py
  - tests/test_adr_index.py
  - tests/test_documentation_contracts.py
  - tests/test_selectable_formats.py
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Provide agents and local tooling with a versioned, deterministic machine-readable ADR catalog that combines lifecycle metadata, decision summaries, enforcement scope, and typed ADR relationships while retaining Markdown ADRs as the source of truth and ADR-INDEX.md as the compact human/session view.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A Proposed ADR documents the JSON graph-index contract, alternatives, consequences, risks, compatibility, and its relationship to ADR-004 and ADR-005.
- [x] #2 A versioned JSON Schema defines the generated graph index and validates the repository artifact.
- [x] #3 adr-index deterministically generates ADR-INDEX.json without volatile timestamps and check mode detects missing or stale JSON output.
- [x] #4 The JSON index exposes normalized ADR identity, title, path, format, lifecycle status, decision summary, enforcement scope, relevant frontmatter metadata, and typed resolved or dangling relationships.
- [x] #5 adr-context uses the shared indexed record model and returns actionable metadata, source paths, decision summaries, and explainable relevance signals while retaining compatible fields.
- [x] #6 Markdown and JSON indexes remain generated from the same semantic format-aware parsing path across MADR, Nygard, and canonical ADRs.
- [x] #7 README, agent guidance, installation/use documentation, and release notes explain how agents should discover ADRs through the JSON index and then open source ADRs.
- [x] #8 Focused index, context, relationship, schema, profile, synchronization, and documentation tests pass, followed by the full supported test suite.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Preserve the existing TASK-25–29 work on a dedicated integration branch and record it as a separate baseline commit so the JSON-index changes remain reviewable.
2. Author ADR-007 as Proposed using the preferred MADR profile. Define Markdown ADRs as source of truth, ADR-INDEX.json as a generated versioned machine interface, a normalized node/edge graph, deterministic output, and compatibility with ADR-004/005.
3. Refactor the index pipeline around one semantic, format-aware record loader. Add a versioned JSON Schema and generate both ADR-INDEX.md and ADR-INDEX.json from the same records without timestamps.
4. Reuse the same graph extraction semantics as adr-related, representing declared relationship types and dangling targets deterministically; keep inferred mentions separate from declared edges.
5. Enrich adr-context JSON/text results with path, status, format, decision summary, scope, and explainable signals while preserving existing keys and ranking behavior.
6. Synchronize root, Codex, and Copilot distributable payloads; update README, INSTALL-AGENT.md, agent guide, release notes, and architecture documentation with a JSON-first discovery/open-source-ADR workflow.
7. Add focused schema/index/context/graph/profile/synchronization/documentation tests, regenerate artifacts, run lint/doctor and the full test suite, and repair regressions.
8. Check acceptance criteria as evidence is obtained, finalize TASK-30, commit the feature, merge the integration branch into main, and report the resulting commits and verification.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User explicitly authorized the expanded plan, implementation, commit, and merge in the same request; no additional plan-approval pause is required.

Repository began on main with prior user-directed TASK-25–29 changes uncommitted. They will be preserved as a separate baseline commit before TASK-30 implementation.

ADR-007 was created in MADR format and passes strict lint. It extends ADR-004 and ADR-005 without conflict; Markdown ADR files remain authoritative.

Implemented a shared stdlib adr_catalog module, deterministic schema-versioned node/edge graph, additive actionable context metadata, shared explicit relationship parsing, and tolerant fallback for malformed frontmatter while strict lint remains responsible for reporting it.

Found and fixed a regression during focused tests: adr-context could rank generated ADR-INDEX.md as an ADR after index generation. Discovery now uses the shared numbered-ADR filename filter.

Verification: focused final slice 113 passed; exact final full suite 591 passed, 3 skipped in 145.43s; strict lint 7 PASS/0 advisory/0 fail; ADR-007 quality 0.90 grade A; AJV draft-2020 schema validation passed; sync-agent-plugins --check passed; adr-index --check reported all three views fresh; adr-doctor reported index_ok=true, lint_ok=true, findings=0.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## Summary

Added a deterministic, versioned JSON ADR graph for agent discovery while keeping Markdown ADRs authoritative. ADR-007 defines the contract; `adr_catalog.py` supplies one format-aware semantic record and relationship model to index, context, and related tooling. `adr-index docs/adr` now refreshes the README block, compact Markdown map, and `ADR-INDEX.json`, while check mode detects drift across all three. `adr-context` retains compatible ranking fields and adds source path, status, format, decision summary, scope, relationships, and invariant metadata.

Added `schemas/adr-index.schema.json`, AJV CI validation, deterministic node/edge and stale-artifact tests, multi-profile coverage, malformed-frontmatter tolerance, synchronized Codex/Copilot payloads, and agent-first README/install/skill guidance.

## Verification

- `python -m pytest -q` -> 591 passed, 3 skipped
- focused graph/context/profile/docs/MCP slice -> 113 passed
- `python bin/adr-lint --strict docs/adr` -> 7 pass, 0 advisory, 0 fail
- `python bin/adr-quality ...ADR-007...` -> 0.90, grade A
- AJV draft-2020 validation -> ADR-INDEX.json valid
- `python scripts/sync-agent-plugins.py --check` -> clean
- `python bin/adr-index --check docs/adr` -> all views fresh
- `python bin/adr-doctor --fix-index --format json docs/adr` -> index/lint healthy, 0 findings

## Compatibility and risk

The old `adr-index --format json` flat-list output remains available with additive title/format fields; the graph is printed with `--format graph` and tracked as ADR-INDEX.json. Query-specific relevance scores are not persisted. Proposed ADRs may still rank and must be verified in source. No runtime dependency or hosted service was added.
<!-- SECTION:FINAL_SUMMARY:END -->
