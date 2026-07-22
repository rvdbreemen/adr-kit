---
id: TASK-49
title: Add repo-level /release command driving the marketplace release runbook
status: In Progress
assignee:
  - '@claude'
created_date: '2026-07-22 18:54'
updated_date: '2026-07-22 18:54'
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
- [ ] #1 .claude/commands/release.md exists and is invocable as /release in this repo
- [ ] #2 The command drives the documented runbook steps and calls check-release-version.py, build-client-adapters.py --check, adr-lint --strict, adr-index --check, pytest
- [ ] #3 The command tags + pushes to trigger release-publish.yml and runs the local install-agent-envs.py step
<!-- AC:END -->
