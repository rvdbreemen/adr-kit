---
id: TASK-65
title: >-
  adr-mcp passes --snapshot diff to the judge, producing unactionable
  require_pattern violations
status: Done
assignee: []
created_date: '2026-07-30 21:14'
updated_date: '2026-07-30 22:09'
labels:
  - mcp
  - judge
  - review-finding
dependencies: []
references:
  - >-
    docs/adr/ADR-016-serve-both-mcp-protocol-eras-from-one-hand-rolled-stdio-server.md
  - .full-review/02-security-performance.md
  - docs/adr/ADR-009-bound-heuristic-gates-to-findings-an-author-can-act-on.md
modified_files:
  - bin/adr-mcp
  - bin/adr-judge
  - tests/test_adr_git_diff_semantics.py
  - .claude/adr-kit-guide.md
  - templates/adr-kit-guide.md
  - codex/templates/adr-kit-guide.md
  - copilot/templates/adr-kit-guide.md
priority: medium
ordinal: 70500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Surfaced by ADR-016 and by the enforcement-floor review (finding M1). Left unclaimed by TASK-58.1 and TASK-58.2 because it appears in no acceptance criterion of either, and ADR-016 explicitly calls it "a TASK-58 opportunity, not a requirement of this decision". Recording it so it does not evaporate.

`bin/adr-mcp:469` invokes `bin/adr-judge` with `--snapshot diff`. In that mode the judge cannot reconstruct a post-image for a **modified** file — only for a new one, whose content it rebuilds from the added lines. A `require_pattern` rule therefore fails closed with the message "the explicit diff does not contain a complete post-image".

That message describes the tool's input mode, not the author's code. It is a direct violation of ADR-009 ("bound heuristic gates to findings an author can act on"): the person reading it changed nothing that could fix it.

**Who is affected.** The pre-commit paths dodge this entirely — `.githooks/pre-commit:195` and `bin/adr-judge-precommit:69` both pass `--snapshot staged`. The MCP tool does not, so an agent self-checking its own diff through `adr_judge` gets a fabricated violation for every modified file matched by a require rule. The CI action and any direct CLI caller hit the same default.

**Two candidate fixes, and they are not equivalent:**

1. Change the call site at `bin/adr-mcp:469` to `--snapshot worktree`. Narrow, fixes the MCP consumer, leaves the trap for everyone else.
2. Change the judge's own default from `diff` to `staged` (`bin/adr-judge:1622-1629`). `diff` mode's inability to see a modified post-image is a limitation of a legacy input mode, not a policy stance, and it should not be what a caller gets by accident. Broader blast radius, so it needs its own regression check.

The review recommended option 2 with option 1 as a companion. If the default cannot change for backwards compatibility, then `require_pattern` under `diff` mode should emit **advisory** rather than violation — an unactionable finding must never block a commit.

Decide deliberately rather than picking the smaller diff by default; the second option is the one that stops other callers walking into it.</description>
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An agent calling the MCP `adr_judge` tool on a diff touching a modified file no longer receives a require_pattern violation caused by snapshot mode
- [x] #2 The chosen fix is stated with its reasoning: call-site only, judge default, or advisory downgrade
- [x] #3 If the judge's default snapshot mode changed, a regression test covers each mode and the pre-commit paths still behave identically
- [x] #4 No finding remains whose message describes the tool's input mode rather than something the author can act on (ADR-009)
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed with options 1 + 3. Option 2 — flipping the judge default from `diff` to `staged` — was **declined**, and not for backwards compatibility: it relocates the defect instead of removing it. In a non-git directory, or when nothing is staged, `git show :path` fails and the judge returns `missing` → "the file is absent in the selected snapshot", which is equally unactionable and would now be the *default*. It also puts a `git show` subprocess on the default path for callers who never asked for git semantics.

**What changed**

- `bin/adr-judge` `_read_snapshot_content` returns a new `"indeterminate"` state for the diff-mode-modified-file case, distinct from `"unknown"`. The split is the point: `"unknown"` still covers the path-traversal refusal (`_safe_repo_path` → None) and the worktree `OSError`, and both stay fail-closed. A blanket downgrade on `"unknown"` would have weakened a security check.
- `apply_rules_to_diff` emits `severity: "advisory"` for `"indeterminate"`, naming the remedy (`--snapshot staged` or `--snapshot worktree`). The exit code counts only `violation`, so it no longer blocks. `"missing"` (deleted or unstaged file) remains a violation — that one *is* actionable.
- `bin/adr-mcp:533` — one line, `--snapshot diff` → `--snapshot worktree`. Needed for AC4, not only AC1: an advisory that still says "no post-image" describes the input mode; only `worktree` makes the finding about the agent's own code.
- `--snapshot` help text no longer claims `diff` "fails closed".
- Documentation followed: the `require_pattern` bullet in all four copies of the ADR kit guide said "post-diff content" flatly. It now names the snapshot modes and the advisory carve-out. The two client mirrors were regenerated through `scripts/build-client-adapters.py`, not hand-edited (`--check` reports changed=0).

**The fail-closed floor (ADR-004) is provably untouched, so no ADR was needed.** Verified independently rather than taken on trust: `_read_snapshot_content` returns before the final statement in both `staged` and `worktree` mode, so `"indeterminate"` is unreachable outside `diff` mode; and the floor never uses `diff` — `templates/githooks/pre-commit:201` and `bin/adr-judge-precommit:69` both pass `--snapshot staged`. This is a bug fix within an existing pattern, which the guide explicitly exempts from needing an ADR.

**Empirical check against the live ADR-011 rule** (`require_pattern: adr_readiness` on `bin/adr-mcp`), the exact case ADR-016:884 documents. A one-line docstring change to `bin/adr-mcp`: before → 1 violation, exit 1. After → `diff` mode gives 1 advisory, 0 violations, exit 0; `worktree` (what MCP now uses) gives 0 findings, exit 0.

**Caller audit.** Every shipped caller passes `--snapshot` explicitly: hook and `adr-judge-precommit` use `staged`, the CI action and the guardian/review skills use `worktree`. The one default-inheriting invocation is `skills/upgrade/SKILL.md:138`, a smoke test with an empty diff, so no file is ever evaluated.

**Tests.** 8 new or rewritten in `tests/test_adr_git_diff_semantics.py` (not `test_adr_judge.py` as this task guessed — all snapshot semantics already live there). All three modes: `diff` advisory, `worktree` pass *and* `worktree` still blocking on a real breach (proving the downgrade is not a bypass), `staged` against a real git index with a dirtied worktree and `core.autocrlf=false` pinned so the `^REQUIRED$` anchor is not defeated by CRLF on Windows. Plus deleted-file-still-blocks, unsafe-path-still-unknown, and a functional test that the MCP tool asks for `worktree`.

Full suite after the change: 1133 passed, 10 skipped, 1 xfailed (the xfail is ADR-017's gate placeholder, unrelated).</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
