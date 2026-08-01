---
id: TASK-76
title: 'Judge the branch before the PR exists, and ship the PR workflow downstream'
status: To Do
assignee: []
created_date: '2026-08-01 10:32'
labels:
  - spec-gap
  - R2
  - hooks
  - ci
dependencies: []
priority: high
ordinal: 81500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
spec.md R2, clause 1. Today the only always-installed gate is the git pre-commit hook: one commit, `--snapshot staged`, upstream of push. A true branch-range judge exists in `.github/actions/adr-judge/action.yml:97` (`git diff origin/$BASE_REF...HEAD`) but it triggers on `pull_request` — after the diff has already become a PR — and no shipped command installs it: `templates/github-workflows/` contains only `adr-guardian-audit.yml` and `adr-readiness.yml`.

Two independent fixes, both wanted.

**Track 2, the harness hook.** Opening a PR is a tool call: `gh pr create` through the shell tool. A `PreToolUse` matcher on the shell tool, filtered to that command shape, can run the judge over `origin/<base>...HEAD` before the PR exists. That is earlier than CI can ever be, because CI only learns of the PR once it is there. Unlike the injection hooks this one may block: a violation here is exactly the case where the coding agent should fix the code first.

**Track 3, the CI template.** Ship `templates/github-workflows/adr-judge.yml` so a downstream project gets the PR gate by copying a file, the same way it already gets readiness and the guardian audit. `/adr-kit:install-hooks` should offer it.

Note the interaction with TASK-73: a branch-range diff is what the separate `--max-diff-bytes` budget exists for. The harness hook needs the same budget, not the commit-sized one.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A pre-tool hook recognises a PR-creating shell command and runs the judge over the branch diff before it executes
- [ ] #2 That hook blocks on a violation and explains which ADR was violated; it fails open when the tooling is unavailable, like every other hook
- [ ] #3 The hook uses the CI-sized diff budget, not judge.max_diff_bytes
- [ ] #4 templates/github-workflows/adr-judge.yml ships and is offered by /adr-kit:install-hooks
- [ ] #5 Command matching is precise enough not to fire on unrelated gh invocations, and a test covers both a match and a near-miss
- [ ] #6 docs/client-support.md records which clients expose a hookable shell tool and what happens on the ones that do not
<!-- AC:END -->
