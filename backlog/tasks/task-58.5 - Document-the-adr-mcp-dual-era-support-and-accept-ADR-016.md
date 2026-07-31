---
id: TASK-58.5
title: Document the adr-mcp dual-era support and accept ADR-016
status: Done
assignee: []
created_date: '2026-07-29 22:49'
updated_date: '2026-07-30 23:54'
labels:
  - mcp
  - docs
  - adr
dependencies:
  - TASK-58.4
references:
  - >-
    docs/adr/ADR-016-serve-both-mcp-protocol-eras-from-one-hand-rolled-stdio-server.md
  - docs/RELEASING.md
modified_files:
  - bin/adr-mcp
  - tests/test_adr_mcp.py
  - .claude/adr-kit-guide.md
  - docs/research/2026-07-29-mcp-2026-07-28-revision.md
  - C4-Documentation/c4-code-bin-cli-mcp.md
  - CHANGELOG.md
  - >-
    docs/adr/ADR-016-serve-both-mcp-protocol-eras-from-one-hand-rolled-stdio-server.md
parent_task_id: TASK-58
priority: medium
ordinal: 63500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Close the loop: bring the written record in line with the shipped behaviour, tighten the Enforcement block, and retire the gate's expected-failure marker.

**ADR-016 is already Accepted** (2026-07-30, human acceptance by Robert van den Breemen, recorded in Status History with a `Decision Maker:` line). The acceptance step of this task is therefore done. What remains is everything that was deliberately deferred at acceptance.

**1. Add the deferred `require_pattern` rules.** ADR-016 was accepted with `require_pattern: []` on purpose, because a rule requiring `MODERN_PROTOCOL_VERSIONS` or `server/discover` would fail on every commit touching `bin/adr-mcp` until the implementation existed, forcing TASK-58.1 and 58.2 into one commit or pushing the author to `ADR_KIT_HOOK_DISABLE=1`. The ADR body records the four intended rules in a table under "Why require_pattern is empty at acceptance". Move them into the JSON block once TASK-58.2 has landed:

| Pattern | Scope |
|---|---|
| `MODERN_PROTOCOL_VERSIONS` | `bin/adr-mcp` |
| `server/discover` | `bin/adr-mcp` |
| `UNSUPPORTED_PROTOCOL_VERSION` | `bin/adr-mcp` |
| `server/discover` | `tests/test_adr_mcp.py` |

Then run `bin/adr-judge --dry-run-enforcement ADR-016` and confirm the rules fire on a deliberate violation and stay silent on the compliant implementation. A rule that cannot distinguish the two is worse than none — fix or drop it rather than shipping a decorative one.

**2. Retire the gate marker.** `tests/test_adr_mcp.py` now registers gate `adr-mcp-dual-era-v1` as `@pytest.mark.xfail(strict=True)`. It exists so the Accepted binding ADR has findable evidence (the consistency gate requires a named gate to be present in the tree), and it fails honestly while the feature is absent. Because the marker is strict, the suite FAILS with XPASS the moment the implementation works. Removing the marker is the deliberate act that turns the gate green. Do not remove it earlier.

**3. Set the lifecycle metadata.** After the implementation is verified, run `bin/adr document ADR-016 --verified-in <pointer>` so `documents_shipped` and `verified_in` reflect reality; both are currently false and empty.

**Documentation to update:**
- `bin/adr-mcp` module docstring — it currently states the server speaks the handshake era only and points at ADR-016/TASK-58 as pending. Rewrite it to describe the shipped dual-era surface.
- `.claude/adr-kit-guide.md` — add a short factual note on which protocol eras the MCP server serves.
- `docs/research/2026-07-29-mcp-2026-07-28-revision.md` — section 7 records the non-compliance. Append what changed; do not rewrite the original finding, it is the historical record.
- `C4-Documentation/c4-code-bin-cli-mcp.md` and the container-level doc — both describe the pre-change server and carry a known-limitation note pointing at TASK-58.
- `CHANGELOG.md` — Keep a Changelog format, no emoji, since release-publish.yml reads it directly for release notes.

**Version bump.** Use `bin/bump-version` on dev (ADR-013's declarative registry with a writer) rather than hand-editing plugin.json and marketplace.json.

**Note on four pre-existing clarity FAILs.** Running lint with the full gate set (schema,completeness,audit,evidence,clarity,consistency,policy — what `bin/adr accept` uses) shows ADR-001 through ADR-004 failing the clarity gate on unexpanded acronyms. These predate this work and do not block it: the default gate set that CI runs is clean. Worth a separate task rather than silent scope creep here.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The four deferred require_pattern rules are present in ADR-016's Enforcement block
- [x] #2 `bin/adr-judge --dry-run-enforcement ADR-016` is shown to fire on a deliberate violation and stay silent on the compliant implementation
- [x] #3 The xfail(strict=True) marker on test_gate_adr_mcp_dual_era_v1_server_discover is removed and the gate test passes on its own merits
- [x] #4 `bin/adr document ADR-016 --verified-in <pointer>` has been run so documents_shipped is true and verified_in is non-empty
- [x] #5 The bin/adr-mcp module docstring describes the shipped dual-era surface, not pending work
- [x] #6 `.claude/adr-kit-guide.md` states which protocol eras the MCP server serves
- [x] #7 The research note appends what changed without rewriting its original non-compliance finding
- [x] #8 The C4 code-level and container-level MCP docs no longer describe the pre-change server, and the TASK-58 limitation note is resolved
- [x] #9 CHANGELOG.md has an entry following Keep a Changelog, no emoji
- [x] #10 ADR-INDEX.md and ADR-INDEX.json are regenerated and agree with the final state
- [x] #11 The version bump is done with bin/bump-version, not by hand-editing manifests
- [x] #12 The Enforcement path_glob set covers all three shipped copies of the server (`bin/adr-mcp`, `codex/bin/adr-mcp`, `copilot/bin/adr-mcp`), which are byte-identical modulo line endings, or the ADR states explicitly why binding only the source copy is sufficient
- [x] #13 The `llm_judge: true` flag is either backed by `judge.llm_enabled: true` in docs/adr/.adr-kit.json, or the ADR records that the semantic half is unenforced until someone opts in per commit with ADR_KIT_LLM=1 — the flag alone enforces nothing (ADR-001)
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: claude-session-2026-07-30
created: 2026-07-30 05:28
---
Two findings from the adversarial verify pass remain open and are folded into this task.

1. **path_glob coverage.** Every Enforcement rule binds `bin/adr-mcp` only. `clients/installer/payload.py:175` ships `root/bin`, `root/codex/bin` and `root/copilot/bin`, and all three `adr-mcp` copies are byte-identical modulo CRLF. A drift introduced in a mirror is therefore invisible to the judge. Either widen the globs or state why the source copy is the only one that can drift.

2. **llm_judge enforces nothing today.** `docs/adr/.adr-kit.json` has no `judge.llm_enabled` key, so per ADR-001 the LLM pass is off, and ADR-016 is the only ADR in the corpus with `llm_judge: true` (every other sets it false). With `require_pattern` deliberately empty at acceptance, the semantic half of the Decision Contract is currently enforced by nothing at all. The two `forbid_*` rules do work. This was stated too optimistically when the empty require_pattern was agreed; recording it so the gap is closed deliberately rather than forgotten.
---

created: 2026-07-30 23:16
---
Twelve of thirteen criteria are met. **Only AC11 (version bump) is open**, and deliberately so: the judge-backend agent is still working TASK-59, and bumping before its changes land would ship a version that does not describe the release. It is the last step, not a skipped one.

**AC1/AC2 — the four require_pattern rules are in, and the reasoning inverted.** ADR-016 had declined them, not deferred them, on two reproduced failure modes. Both have since been removed by other work rather than argued away:

- The first was conditional on the implementation being absent. TASK-58.1 and 58.2 landed it.
- The second was called permanent: `--snapshot diff` has no post-image for a modified file, so every `require_pattern` on `bin/adr-mcp` reported a violation through the MCP tool forever. TASK-65 fixed exactly this — and it is the change ADR-016 itself called for two paragraphs later ("`bin/adr-mcp:469` should pass `--snapshot worktree` rather than `diff`").

Re-measured against the shipped implementation before adding anything, in a scratch copy:

| Scenario | Result |
|---|---|
| innocent one-line change, `--snapshot worktree` | 0 violations |
| same, `--snapshot diff` | 0 violations, 4 advisories |
| modern surface stripped, `--snapshot worktree` | 3 violations, each naming its missing symbol |

That satisfies AC2 literally: the rules fire on a deliberate violation and stay silent on the compliant implementation. The original "Declined, not deferred" text is kept verbatim as the historical record, with a dated Resolved callout above it — same treatment the research note gets under AC7.

**AC12 was already satisfied**: every glob is scoped `{bin,codex/bin,copilot/bin}/adr-mcp`, so a drift introduced in a mirror is caught. **AC13**: `llm_judge` is `false`, not `true` as this task's comment #1 assumed, and the ADR records why — `extract_decision` resolves only the `## Decision Outcome` heading, so the Must / Must Not text a judge would need never reaches the prompt. The gap is closed by the declarative rules rather than left to an unenforced flag. **AC3** was already done: the xfail marker is gone and the gate is live.

**AC6 caught a real distribution bug, not just a doc edit.** The MCP section existed only in `.claude/adr-kit-guide.md`, which is gitignored (`.gitignore:23`). It would have shipped to nobody. Copied into `templates/adr-kit-guide.md`, the canonical source the generator mirrors. This is the second time today that trap appeared — the same thing had happened to the supersession section under TASK-67.

**AC8** — four stale passages in `C4-Documentation/c4-code-bin-cli-mcp.md` resolved with dated notes rather than deletion: the `--snapshot diff` gap (fixed by TASK-65), the mirror-parity risk (the mirrors *are* generated, and `--check` runs in three CI workflows), the ADR-015 latency open question (measured in TASK-58.4; the corpus entry is deliberately still absent), and `ping` (kept on the handshake surface, where all three validated clients live).

Verification: `bin/adr-judge --dry-run-enforcement ADR-016` 0/0. Full working-tree diff through the enforcement floor: 0 violations, 0 advisory. `bin/adr-lint --strict docs/adr` 17/17 PASS. 113 tests passed across mcp, lifecycle, lint and adapter generation. Mirrors regenerated through `scripts/build-client-adapters.py`; `--check` reports changed=0.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All thirteen criteria met. Version bumped 0.42.0 → 0.43.0 through `bin/bump-version`, not by hand.

**The bump exposed a defect in the release tooling itself.** `bin/bump-version` reported nine files written and `tests/test_version_sites.py` immediately went red on two README pins. Root cause: ADR-013 is titled "Declare version sites in one registry and bump by writing", the registry exists at `packaging/version-sites.json`, and the *verifier* reads it — but the writer never opens it. `bin/bump-version:182-193` carries its own hard-coded tuple of 10 paths, and both `README.md` entries are missing from it.

The stale pins were the copy-paste snippets users paste into their own workflow and pre-commit config, so this would have shipped a wrong version to every new consumer. Updated by applying the registry's own regexes, which is the point: the declared patterns were correct all along, nothing consumed them. Filed as **TASK-71**, high priority, because the real fault is structural — adding a site to the registry currently gets you verification without writing, and that gap only surfaces as a red test mid-release.

Worth stating in ADR-013's favour: the verifier is the only reason this was caught rather than released. Half the decision was implemented well; the other half was never implemented at all.

**The other twelve criteria** are covered in comment #2. The headline is AC1/AC2: ADR-016 had *declined* the four `require_pattern` rules, not deferred them, on two reproduced failure modes — and both had since been removed by other work. The second, which the ADR called permanent, was fixed by TASK-65, the very change ADR-016 itself proposed two paragraphs later. Re-measured before adding anything: 0 violations on an innocent change under `worktree`, 4 advisories under `diff`, 3 violations with the modern surface stripped. The original reasoning is kept verbatim with a dated Resolved callout above it.

Also of note, AC6 was a distribution bug rather than a doc edit: the MCP section lived only in `.claude/adr-kit-guide.md`, which is gitignored, so it would have shipped to nobody. That is the second time today that trap appeared.

**Final verification at 0.43.0:** full suite `1201 passed, 10 skipped, 0 failed`. `bin/adr-lint --strict docs/adr` 17/17 PASS, 0 FAIL. Enforcement floor over the whole working tree: 0 violations, 0 advisory. `scripts/build-client-adapters.py` reports `changed=0`. Indexes regenerated and unchanged.

**Not done here, deliberately:** nothing is committed, staged, tagged or pushed. The release itself is the owner's call.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
