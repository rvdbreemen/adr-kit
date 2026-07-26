---
id: TASK-56
title: Release v0.42.0 to the three marketplaces
status: In Progress
assignee: []
created_date: '2026-07-26 13:35'
labels:
  - release
dependencies: []
priority: high
ordinal: 56500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Release everything on dev since v0.41.0 to the public repository (git-source marketplaces for Claude Code, Codex, Copilot) per docs/RELEASING.md and ADR-012.

Payload since v0.41.0:
- PR #48: perf(cli) single-pass repo scans in adr-lint/adr-retire (2s user-wait goal, TASK-55) + fix(hooks) SessionStart timeout hardening
- PR #46: feat(release) main-to-dev merge-back guard (check + runbook step)
- PR #45: test(release) release payload path-leak gate
- PR #44/#47: README and documentation-index refresh (v0.34-v0.40 feature coverage)

Version: 0.42.0 (minor: contains a feature).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 bump-version.py 0.42.0 executed; no hand-edited version sites
- [ ] #2 build-client-adapters.py regenerated client trees
- [ ] #3 CHANGELOG 0.42.0 section written to release-note quality (Keep a Changelog)
- [ ] #4 All five local gates green (check-release-version, adapters --check, adr-lint --strict, adr-index --check, pytest)
- [ ] #5 PR to main green; merge handed off to maintainer (protected branch)
- [ ] #6 Tag v0.42.0 pushed after maintainer merge; release-publish.yml green
- [ ] #7 Local prepared-directory marketplace advanced via install-agent-envs.py --clients all
<!-- AC:END -->
