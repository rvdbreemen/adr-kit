---
id: TASK-58.5
title: Document the adr-mcp dual-era support and accept ADR-016
status: To Do
assignee: []
created_date: '2026-07-29 22:49'
updated_date: '2026-07-30 05:28'
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
- [ ] #1 The four deferred require_pattern rules are present in ADR-016's Enforcement block
- [ ] #2 `bin/adr-judge --dry-run-enforcement ADR-016` is shown to fire on a deliberate violation and stay silent on the compliant implementation
- [ ] #3 The xfail(strict=True) marker on test_gate_adr_mcp_dual_era_v1_server_discover is removed and the gate test passes on its own merits
- [ ] #4 `bin/adr document ADR-016 --verified-in <pointer>` has been run so documents_shipped is true and verified_in is non-empty
- [ ] #5 The bin/adr-mcp module docstring describes the shipped dual-era surface, not pending work
- [ ] #6 `.claude/adr-kit-guide.md` states which protocol eras the MCP server serves
- [ ] #7 The research note appends what changed without rewriting its original non-compliance finding
- [ ] #8 The C4 code-level and container-level MCP docs no longer describe the pre-change server, and the TASK-58 limitation note is resolved
- [ ] #9 CHANGELOG.md has an entry following Keep a Changelog, no emoji
- [ ] #10 ADR-INDEX.md and ADR-INDEX.json are regenerated and agree with the final state
- [ ] #11 The version bump is done with bin/bump-version, not by hand-editing manifests
- [ ] #12 The Enforcement path_glob set covers all three shipped copies of the server (`bin/adr-mcp`, `codex/bin/adr-mcp`, `copilot/bin/adr-mcp`), which are byte-identical modulo line endings, or the ADR states explicitly why binding only the source copy is sufficient
- [ ] #13 The `llm_judge: true` flag is either backed by `judge.llm_enabled: true` in docs/adr/.adr-kit.json, or the ADR records that the semantic half is unenforced until someone opts in per commit with ADR_KIT_LLM=1 — the flag alone enforces nothing (ADR-001)
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
<!-- COMMENTS:END -->
