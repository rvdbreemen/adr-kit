---
id: TASK-37
title: Publish ADR Kit v0.35.0 superseding patch release
status: In Progress
assignee:
  - Codex
created_date: '2026-07-19 11:38'
updated_date: '2026-07-19 11:39'
labels:
  - release
  - version
  - documentation
dependencies: []
documentation:
  - CHANGELOG.md
modified_files:
  - .claude-plugin/marketplace.json
  - .claude-plugin/plugin.json
  - .github/plugin/marketplace.json
  - codex/.codex-plugin/plugin.json
  - copilot/plugin.json
  - templates
  - codex/templates
  - copilot/templates
  - CHANGELOG.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Promote the completed quiet three-client integration release from v0.34.2 to the user-requested v0.35.0 minor line. Update every release manifest, copied-artifact version stamp, changelog heading/link, tag the merged commit, publish the public GitHub Release, and record that v0.35.0 supersedes v0.34.2.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All ADR Kit client manifests and copied-artifact version stamps report 0.35.0.
- [x] #2 CHANGELOG documents v0.35.0 and its comparison links without losing v0.34.2 history.
- [x] #3 Version, packaging, generated-payload, and documentation checks pass.
- [ ] #4 A green pull request is merged to main, annotated tag v0.35.0 is pushed, and a public GitHub Release explains that it supersedes v0.34.2.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Branch from current main after the v0.34.2 release-finalization merge. 2. Replace every active 0.34.2 manifest and copied-artifact stamp with 0.35.0, then synchronize generated Codex/Copilot payloads. 3. Add a v0.35.0 changelog entry that points to the same quiet-integration feature set and explicitly records v0.34.2 as the immediately superseded patch release. 4. Run version, payload, packaging, index, and documentation checks. 5. Commit, push, merge a green PR, tag the merged commit as v0.35.0, publish the release, and finalize TASK-37 in a follow-up task-only merge.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Updated all five client/marketplace manifests and copied-artifact stamps to 0.35.0; synchronized Codex/Copilot payloads; retained v0.34.2 history with an explicit superseding v0.35.0 changelog entry. Generated payload, ADR index, version, packaging, documentation, and diff checks pass (28 passed, 1 skipped).
<!-- SECTION:NOTES:END -->
