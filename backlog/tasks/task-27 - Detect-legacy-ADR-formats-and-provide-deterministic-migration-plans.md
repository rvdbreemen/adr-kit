---
id: TASK-27
title: Detect legacy ADR formats and provide deterministic migration plans
status: Done
assignee: []
created_date: '2026-07-18 16:31'
updated_date: '2026-07-18 16:55'
labels:
  - adr-kit
  - migration
  - formats
  - installer
  - lint
dependencies: []
documentation:
  - docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md
  - docs/research/adr-format-evaluation.md
  - README.md
  - INSTALL.md
  - INSTALL-AGENT.md
  - docs/format-migration.md
  - templates/adr-kit-guide.md
modified_files:
  - bin/adr_format.py
  - bin/adr_schema.py
  - bin/adr-migrate
  - bin/adr-lint
  - scripts/install-agent-envs.py
  - skills/init/SKILL.md
  - skills/migrate/SKILL.md
  - skills/upgrade/SKILL.md
  - skills/lint/SKILL.md
  - codex/skills/init/SKILL.md
  - codex/skills/migrate/SKILL.md
  - codex/skills/upgrade/SKILL.md
  - codex/skills/lint/SKILL.md
  - copilot/skills/init/SKILL.md
  - copilot/skills/migrate/SKILL.md
  - copilot/skills/upgrade/SKILL.md
  - copilot/skills/lint/SKILL.md
  - codex/bin/
  - copilot/bin/
  - templates/adr-kit-guide.md
  - codex/templates/adr-kit-guide.md
  - copilot/templates/adr-kit-guide.md
  - README.md
  - INSTALL.md
  - INSTALL-AGENT.md
  - CHANGELOG.md
  - docs/format-migration.md
  - tests/test_migration_discovery.py
  - tests/test_documentation_contracts.py
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a shared, read-only format discovery and migration-planning path. Detect supported legacy records and common unsupported ADR families deterministically where reliable; surface exact dry-run migration commands or guided-review guidance during project/client installation, upgrade, and lint. Never rewrite ADRs automatically, preserve ADR-005's first-class supported profiles, and keep unknown/hybrid handling safe and explicit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A shared deterministic scanner classifies supported profiles, legacy metadata needs, and reliably identifiable common external ADR families without treating supported profiles as requiring conversion.
- [x] #2 A read-only migration-plan command reports per-file detection, whether deterministic migration is available, and an exact preview-first command; it never writes files.
- [x] #3 Lint surfaces actionable migration notices for legacy/unsupported/hybrid records in human and JSON output without weakening existing strict failures.
- [x] #4 Project/client install and upgrade workflows run or instruct the same read-only discovery path and inform the user without automatically migrating ADR content.
- [x] #5 Documentation and agent guides explain detection, supported automatic paths, guided fallbacks, and the no-silent-rewrite safety contract.
- [x] #6 Focused migration/detection/install/lint tests, generated client sync, ADR checks, and the broadest practical suite pass.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented under Accepted ADR-005 rather than creating a new architecture decision: this extends its explicit requirements for deterministic profile detection, preview-first migration, first-class MADR/Nygard/canonical support, and safe handling of unknown/hybrid formats. The planner is data-driven in bin/adr_format.py, read-only by contract, and reused by migration, lint, installer, init, and upgrade surfaces. Conservative external detectors cover Y-Statement, Tyree/Akerman, and arc42; these route to guided review because semantic rewriting is not reliably lossless. Supported legacy MADR/Nygard/canonical records receive an executable absolute preview command, supported-profile extension completion, legacy H1 normalization, and a deterministic target filename, but the user must approve application and perform the reported rename.

Verification completed on 2026-07-18: 73 focused migration/profile/installer/documentation tests passed; full suite 567 passed and 3 skipped. Client payload sync check passed. Strict lint passed all five project ADRs with zero migration notices. ADR doctor reported lint/index clean with zero findings; both generated indexes were current. Fourteen affected Markdown files passed markdownlint. `git diff --check` reported no whitespace errors, only expected checkout LF-to-CRLF warnings. ADR-005 remains grade A (0.92) with a reciprocal, non-dangling ADR-003 supersession graph.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a safe, deterministic upgrade path for existing ADR formats. `adr-migrate --plan` now scans canonical and recognizable legacy filenames without writing, distinguishes supported MADR/Nygard/canonical records from conservative Y-Statement, Tyree/Akerman, arc42, hybrid, and unknown detections, and returns exact absolute dry-run commands or guided migration instructions. Supported legacy records can be normalized within their current profile, including invariant metadata, extension sections, legacy H1, and a reported canonical filename; the proven path finishes strict-lint clean. Client installation accepts `--project-root` and runs discovery fail-open after validation. Init, upgrade, lint, Claude/Codex/Copilot guides, README, install runbooks, changelog, and a dedicated migration guide all carry the same no-silent-rewrite contract. Verification: 567 passed, 3 skipped; payload sync, strict ADR lint, doctor, indexes, Markdown lint, and diff checks are clean.
<!-- SECTION:FINAL_SUMMARY:END -->
