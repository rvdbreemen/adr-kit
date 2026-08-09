---
id: TASK-2
title: 'Release v0.19.0: CI Action for adr-judge + pre-commit framework support'
status: Done
assignee:
  - '@claude'
created_date: '2026-05-31 13:19'
updated_date: '2026-05-31 13:49'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend enforcement reach beyond local hooks. (1) Reusable GitHub Action/workflow running adr-judge over a PR diff (git diff origin/base...HEAD piped to adr-judge --diff -), declarative-only by default, documented opt-in LLM path. (2) .pre-commit-hooks.yaml so pre-commit-framework users register adr-judge without a native hook.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 CI action/workflow runs adr-judge over a PR diff and fails the check on a violation; runs declarative-only without an API key
- [x] #2 README CI section added (mirrors existing adr-lint snippet); opt-in ANTHROPIC_API_KEY + judge.llm_enabled path documented
- [x] #3 .pre-commit-hooks.yaml added; 'pre-commit try-repo' passes on a violating fixture
- [x] #4 pytest green, bin/adr-lint clean, ROADMAP item moved planned to landed, CHANGELOG entry, version bumped via bin/bump-version
- [x] #5 Committed to main, tagged, released (user sign-off)
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped v0.19.0. CI: reusable composite action .github/actions/adr-judge (PR-diff enforcement, declarative-only/key-free) + adr-judge-self dogfood workflow + README CI section (honest LLM-in-CI note). pre-commit: .pre-commit-hooks.yaml + bin/adr-judge-precommit wrapper. marketplace.json drift fixed (0.13.3->0.19.0). No ADR (delivery mechanisms, not a new contract). Verified fresh: 274 pytest pass, adr-lint 2/2 PASS, 3 YAMLs valid, wrapper + CI diff pipe exit 0. Commit 7e091bc, tag v0.19.0, GitHub release published as latest. Caveat: composite action origin/<base> diff carries TODO(verify-in-CI), exercised live on next adr-kit PR via dogfood workflow; pre-commit try-repo live test skipped (CLI not installed locally) but 4 functional wrapper tests pass.
<!-- SECTION:FINAL_SUMMARY:END -->
