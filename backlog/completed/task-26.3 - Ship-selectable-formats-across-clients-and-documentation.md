---
id: TASK-26.3
title: Ship selectable formats across clients and documentation
status: Done
assignee:
  - Codex
created_date: '2026-07-18 15:34'
updated_date: '2026-07-18 16:19'
labels:
  - clients
  - documentation
  - release
dependencies:
  - TASK-26.2
documentation:
  - README.md
  - INSTALL.md
  - ROADMAP.md
  - INSTALL-AGENT.md
  - docs/research/adr-format-evaluation.md
  - docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md
modified_files:
  - INSTALL-AGENT.md
  - README.md
  - INSTALL.md
  - ROADMAP.md
  - CHANGELOG.md
  - agents/adr-generator.md
  - skills/adr/SKILL.md
  - skills/context/SKILL.md
  - skills/init/SKILL.md
  - skills/lint/SKILL.md
  - skills/migrate/SKILL.md
  - skills/supersede/SKILL.md
  - templates/adr-kit-guide.md
  - templates/adr-template.md
  - templates/adr-template.madr.md
  - templates/adr-template.nygard.md
  - templates/adr-template.canonical.md
  - examples/.adr-kit.sample.json
  - examples/ADR-template.md
  - codex/
  - copilot/
  - .github/workflows/validate.yml
  - scripts/sync-agent-plugins.py
  - tests/test_agent_installer.py
  - tests/test_documentation_contracts.py
  - tests/test_python_compatibility.py
  - tests/test_selectable_formats.py
parent_task_id: TASK-26
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Propagate the approved selectable-format implementation through Claude, Codex, Copilot, portable workflows, installation guidance, README, migration documentation, and generated payloads. Verify client parity and release-quality documentation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Claude, Codex, and Copilot skills/templates expose the same supported formats and selection semantics.
- [x] #2 Generated client payloads are synchronized deterministically and their checks pass on supported platforms.
- [x] #3 README and INSTALL explain the recommended default, format-selection configuration, format tradeoffs, migration, and compatibility guarantees.
- [x] #4 ROADMAP and security/maintenance documentation match the implemented architecture and supported runtime floor.
- [x] #5 ADR doctor/lint/index checks and the broad test suite pass, with any platform-specific limitations documented.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
After TASK-26.2: regenerate/synchronize Claude, Codex, Copilot, and portable payloads from canonical sources; update README, INSTALL, ROADMAP, CHANGELOG, schema/template/migration guidance; verify client parity and Windows newline behavior; run ADR health checks and the broad test suite; document and close the completed work.

Add a root-level, client-neutral INSTALL-AGENT.md runbook. Link it before the long README body so coding agents can detect, preview, install, validate, and initialize ADR Kit without reading the full README. Cover native Claude Code, Codex, and Copilot paths plus MCP, Agent Skills, and direct-CLI fallbacks for other coding agents; add documentation contract tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User added an explicit requirement on 2026-07-18: installation guidance must be agent-friendly, prominent near the top of README, and usable by all coding agents rather than tied to one client's command syntax.

Delivery verification completed on Windows/Python 3.12: `python scripts/sync-agent-plugins.py --check` passed; `python bin/adr-doctor docs/adr` reported index_ok=True, lint_ok=True, findings=0; strict ADR lint and generated-index checks passed; ADR-005 relationship graph has no dangling references and quality is grade A (0.92). Final broad suite: 555 passed, 3 skipped in 137.91 seconds. Agent-install documentation tests and installer tests pass; native detection found Claude Code, Codex, and standalone Copilot CLI, and dry-run preview completed without changing client state.

Added `INSTALL-AGENT.md` as the short client-neutral installation contract and linked it before the README overview. It covers safe detection/preview, native per-client installation, real runtime validation, project initialization, and MCP/Agent Skills/direct-Python fallbacks with absolute-path instructions for unlisted coding agents.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped selectable MADR, Nygard, and canonical profiles consistently across Claude, Codex, Copilot, portable templates, schemas, skills, examples, and release documentation. Added a prominent `INSTALL-AGENT.md` runbook so coding agents can install and validate ADR Kit without reading the full README, with native routes plus guaranteed MCP/direct-Python fallbacks. Client payload drift is newline-stable and synchronized. Verification: 555 tests passed (3 skipped), sync check passed, strict lint/index passed, ADR doctor found zero issues, and ADR-005 remains grade A with a clean reciprocal supersession graph.
<!-- SECTION:FINAL_SUMMARY:END -->
