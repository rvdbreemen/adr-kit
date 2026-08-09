---
id: TASK-56
title: Release v0.42.0 to the three marketplaces
status: Done
assignee: []
created_date: '2026-07-26 13:35'
updated_date: '2026-07-26 13:55'
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
- [x] #1 bump-version.py 0.42.0 executed; no hand-edited version sites
- [x] #2 build-client-adapters.py regenerated client trees
- [x] #3 CHANGELOG 0.42.0 section written to release-note quality (Keep a Changelog)
- [x] #4 All five local gates green (check-release-version, adapters --check, adr-lint --strict, adr-index --check, pytest)
- [x] #5 PR to main green; merge handed off to maintainer (protected branch)
- [x] #6 Tag v0.42.0 pushed after maintainer merge; release-publish.yml green
- [x] #7 Local prepared-directory marketplace advanced via install-agent-envs.py --clients all
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
v0.42.0 released to all three marketplaces per docs/RELEASING.md.

- Bump: scripts/bump-version.py wrote 0.42.0 to all 10 version sites; adapters regenerated (changed=10).
- CHANGELOG: 0.42.0 section written to release-note quality (perf single-pass scans with measured evidence, SessionStart timeout 1s->5s, merge-back drift gate, payload path-leak gate). README "What's new" updated for 0.41.0 + 0.42.0.
- Gates: check-release-version 10/10, adapters --check clean (on release branch), adr-lint --strict clean, adr-index --check clean, pytest 898 passed / 5 skipped. PR #49 CI 10/10 green.
- Maintainer merged PR #49 (e44165b); tag v0.42.0 pushed; release-publish.yml green; GitHub Release live: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.42.0
- Local prepared-directory marketplace advanced (install-agent-envs.py --clients all); verified claude/codex/copilot all report adr-kit 0.42.0.
- Merge-back (runbook step 4): PR #50 sync/release-to-dev open, CI watch + merge running.

Known issue found during release (not a blocker): build-client-adapters.py --check false-positives on Windows checkouts — it compares raw bytes while git normalizes CRLF, so a freshly checked-out tree reports 13 drifted files with an empty git diff. Linux CI check is authoritative. Candidate follow-up task.
<!-- SECTION:FINAL_SUMMARY:END -->
