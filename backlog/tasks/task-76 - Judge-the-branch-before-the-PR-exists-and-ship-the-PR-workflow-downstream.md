---
id: TASK-76
title: 'Judge the branch before the PR exists, and ship the PR workflow downstream'
status: Done
assignee: []
created_date: '2026-08-01 10:32'
updated_date: '2026-08-02 07:14'
labels:
  - spec-gap
  - R2
  - hooks
  - ci
dependencies: []
modified_files:
  - hooks/adr_pr_guard.py
  - hooks/adr-hook.py
  - hooks/adapters/claude.py
  - hooks/manifest.json
  - templates/github-workflows/adr-judge.yml
  - skills/install-hooks/SKILL.md
  - tests/test_adr_pr_guard.py
  - CHANGELOG.md
  - codex/
  - copilot/
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
- [x] #1 A pre-tool hook recognises a PR-creating shell command and runs the judge over the branch diff before it executes
- [x] #2 That hook blocks on a violation and explains which ADR was violated; it fails open when the tooling is unavailable, like every other hook
- [x] #3 The hook uses the CI-sized diff budget, not judge.max_diff_bytes
- [x] #4 templates/github-workflows/adr-judge.yml ships and is offered by /adr-kit:install-hooks
- [x] #5 Command matching is precise enough not to fire on unrelated gh invocations, and a test covers both a match and a near-miss
- [x] #6 docs/client-support.md records which clients expose a hookable shell tool and what happens on the ones that do not
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Both halves shipped: a pre-tool guard that judges the branch before the PR exists, and the CI workflow template downstream projects were missing.

The guard intercepts `gh pr create` on the shell tool and judges `origin/<base>...HEAD` before the command runs. It is the only hook that may block, which is the point: a branch violating an Accepted ADR should be fixed before it becomes a proposal. The denial names the ADR, the file and line, and the way out - supersede the decision if it is wrong, or record an override if the exception is deliberate. A block that does not name an exit is just an obstacle.

Everything that is not a violation fails open: no judge, no git, no base branch, a timeout, or exit 2 including a diff over the cap. A check that cannot run must not pretend it did, and a configuration error is a fact about the invocation rather than about the code.

Command matching is anchored on the command shape rather than a substring, and the near-miss cases are tested explicitly: `gh pr list`, `gh pr view`, `ghost pr create`, and a commit message quoting the command all pass through. A guard that blocks unrelated commands is worse than no guard.

**One architectural collision, resolved rather than papered over.** The guard must spawn `adr-judge`, and ADR-018's gate anchor asserts that `adr_hook_core` imports nothing able to reach a model or the network - `subprocess` included, because spawning a CLI is how this toolkit reaches a model. Putting the guard in its own module keeps that assertion true and honest; weakening the gate to fit a new feature would have been the easy wrong answer. A test pins it.

The workflow template ships and install-hooks now offers all three, with the note that the CI gate stays worth installing even with the guard: it covers pushes from a laptop, a different client, and anyone not working through an agent at all.

Gates: 1336 passed / 12 skipped, adapter drift clean.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
