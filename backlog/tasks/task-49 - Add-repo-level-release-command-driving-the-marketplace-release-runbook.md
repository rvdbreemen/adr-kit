---
id: TASK-49
title: Add repo-level /release command driving the marketplace release runbook
status: Done
assignee:
  - '@claude'
created_date: '2026-07-22 18:54'
updated_date: '2026-07-22 19:54'
labels:
  - release
  - tooling
dependencies: []
priority: medium
ordinal: 50500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Provide a repository-scoped Claude Code slash command (.claude/commands/release.md -> /release) that orchestrates docs/RELEASING.md locally: bump + regenerate adapters, run the version-consistency and governance gates, update CHANGELOG, commit + tag + push (triggers release-publish.yml), then run install-agent-envs.py for the local prepared-directory publish. Repo-level, not shipped inside the plugin kit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 .claude/commands/release.md exists and is invocable as /release in this repo
- [x] #2 The command drives the documented runbook steps and calls check-release-version.py, build-client-adapters.py --check, adr-lint --strict, adr-index --check, pytest
- [x] #3 The command tags + pushes to trigger release-publish.yml and runs the local install-agent-envs.py step
- [x] #4 C:/Program Files/Git/release prepares CHANGELOG release notes (grouped, GitHub Release body) and updates README version-pinned examples
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added the repo-level /release-adr-kit command (.claude/commands/release-adr-kit.md) that drives docs/RELEASING.md locally: prepare version + CHANGELOG release notes + README version pins, run every gate, tag and push, then advance this machine prepared marketplace and verify each client. Tracked in git via a .gitignore exception for .claude/commands/.
<!-- SECTION:FINAL_SUMMARY:END -->
