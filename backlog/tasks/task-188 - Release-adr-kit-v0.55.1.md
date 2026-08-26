---
id: TASK-188
title: Release adr-kit v0.55.1
status: In Progress
assignee: []
created_date: '2026-08-26 04:35'
labels: []
dependencies:
  - TASK-186
  - TASK-187
references:
  - docs/RELEASING.md
  - >-
    docs/adr/ADR-012-release-to-the-three-coding-agent-marketplaces-from-the-public-repository.md
  - >-
    docs/adr/ADR-013-declare-version-sites-in-one-registry-and-bump-by-writing.md
priority: high
type: chore
ordinal: 32000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Release adr-kit v0.55.1 to the three certified coding-agent marketplaces (Claude Code, Codex, GitHub Copilot) and stage the OpenCode npm package, following docs/RELEASING.md and ADR-012.

The version number skips 0.55.0 deliberately. The tag v0.55.0 was pushed at the dev tip (77278c1) before the version bump was committed, so every version site at that commit still read 0.54.0 and the release-publish gate refused to publish it (run 32908217579, failed after 8s). No GitHub Release for v0.55.0 exists and nothing was ever published under that number. The tag is left in place rather than moved, because a pushed tag is a public ref that consumers may register a marketplace from.

Release content: ADR-029 carried out (native hook binary retired, Python is the only hook host) and adr-mcp JSON-RPC conformance tightened. Closes the work tracked in TASK-186 and TASK-187.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every publish surface reports 0.55.1 via scripts/check-release-version.py --expect v0.55.1
- [ ] #2 Generated client adapters show changed=0 under scripts/build-client-adapters.py --check
- [ ] #3 adr-lint --strict, adr-index --check and the full python -m pytest -q suite pass on the release commit
- [ ] #4 PR from release/v0.55.1 into main is green and merged by the maintainer
- [ ] #5 Tag v0.55.1 points at the merged main commit and release-publish.yml completed green with a GitHub Release created from the CHANGELOG section
- [ ] #6 main is merged back into dev and scripts/check-branch-sync.py reports in sync
- [ ] #7 scripts/install-agent-envs.py --clients all advanced the local prepared-directory marketplace and each client reports 0.55.1
<!-- AC:END -->
