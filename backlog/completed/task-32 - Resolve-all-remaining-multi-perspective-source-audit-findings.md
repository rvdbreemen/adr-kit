---
id: TASK-32
title: Resolve all remaining multi-perspective source-audit findings
status: Done
assignee:
  - Codex
created_date: '2026-07-18 19:52'
updated_date: '2026-07-18 20:54'
labels:
  - source-audit
  - security
  - reliability
  - portability
  - goal
dependencies: []
references:
  - docs/reviews/2026-07-18-source-audit/FINDINGS.md
documentation:
  - ROADMAP.md
  - docs/adr/ADR-002-adr-guardian-session-start-staleness-detector.md
  - docs/adr/ADR-004-layered-adr-context-injection.md
  - docs/adr/ADR-005-selectable-agent-friendly-adr-formats.md
  - docs/adr/ADR-006-prepare-platform-local-marketplaces-for-native-installs.md
  - docs/adr/ADR-007-json-adr-graph-index-for-agent-retrieval.md
modified_files:
  - bin/
  - scripts/install-agent-envs.py
  - schemas/adr-kit-config.schema.json
  - .claude-plugin/
  - .gitattributes
  - .githooks/pre-commit
  - .github/actions/adr-judge/action.yml
  - .github/workflows/validate.yml
  - templates/
  - skills/
  - codex/
  - copilot/
  - tests/
  - README.md
  - INSTALL.md
  - INSTALL-AGENT.md
  - CONTRIBUTING.md
  - ROADMAP.md
  - CHANGELOG.md
  - docs/format-migration.md
  - docs/reviews/2026-07-18-source-audit/FINDINGS.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Umbrella remediation for every source-audit finding F-01 through F-20 that remains open or partial after TASK-25, TASK-26, and TASK-29. Make the enforcement floor genuinely fail-closed, make lifecycle/release/shared-state mutations safe, close residual portability and CI contract gaps, verify prior fixes, and update the durable findings handoff.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every finding F-01 through F-20 is marked resolved, explicitly accepted as a documented limitation with rationale, or superseded by a narrower verified finding; no unexplained Open or Partial status remains.
- [x] #2 F-01 through F-05 enforcement bypass and hang reproductions have regression tests and pass with fail-closed, staged-snapshot-correct behavior.
- [x] #3 F-08, F-15, and F-16 mutation paths preflight fully and preserve consistent state under injected failure or concurrency tests.
- [x] #4 F-09 and F-10 public semantics match actual context and generated-validator behavior with contract tests.
- [x] #5 Residual F-06, F-14, F-19, and F-20 portability, installer, CI, generated-document, and metadata gaps are closed and previously fixed findings remain covered.
- [x] #6 README, supporting documentation, ROADMAP, CHANGELOG, and the findings report describe the final verified behavior without stale claims.
- [x] #7 Generated client payloads and ADR index artifacts are synchronized.
- [x] #8 Focused tests, strict ADR lint, ADR judge, packaging checks, and the complete repository suite pass.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Decompose work into focused child tasks aligned to enforcement, lifecycle/state, release/portability, and documentation verification.
2. Implement in dependency order with reproductions first and no weakening of ADR-004's fail-open injection versus fail-closed enforcement boundary.
3. Synchronize generated payloads and documents only after source contracts stabilize.
4. Re-run every focused reproduction, full regression suite, strict ADR lint, ADR judge, index checks, and payload checks.
5. Update the findings report status/evidence and close the epic only when no open/partial finding remains.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Resolved the complete F-01 through F-20 source-audit program. All actionable findings are fixed; the validated Codex mcpServers wrapper is explicitly retained as a compatibility choice. Enforcement is schema-validated, bounded, fail-closed, and exact for staged/worktree snapshots and Git paths. Generated validators enforce their declared subset or reject unsupported rules. Lifecycle, release, and shared state updates are rollback-safe/serialized. Context authority is explicit. Manual and prepared packaging now work across Windows, macOS, and Linux, including real MCP and Claude hook smoke tests. Public docs, audit evidence, changelog links, metadata, modes, CI, and generated payloads are synchronized. Final evidence: 635 passed/4 skipped full suite; 5/5 OTGW corpus tests; 7 ADRs strict-lint clean; generated README/Markdown/JSON indexes current; payload sync current; judge zero violations/advisories; git diff check clean.
<!-- SECTION:FINAL_SUMMARY:END -->
