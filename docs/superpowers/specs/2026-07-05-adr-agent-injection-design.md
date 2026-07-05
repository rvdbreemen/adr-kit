# Design Spec: Layered ADR Context Injection for Agent Work

Companion to ADR-004. Date: 2026-07-05. Status: draft, pending approval.

This spec turns ADR-004's decision into a phased, testable implementation plan.
Nothing here is built until ADR-004 is Accepted and this plan is approved.

## Goal

Put the right ADR decision in front of a coding agent at the right moment, using
only deterministic, key-free mechanisms, with one fail-closed floor at commit.

## Design invariants (inherited from ADR-002 hook contract)

- Every injection hook and bin ALWAYS exits 0. Advisory only. Never blocks an edit.
- Self-guard: silent exit 0 when there is no `docs/adr/` with `ADR-*.md` in cwd.
- No LLM, no network in the injection path. stdlib only. Deterministic.
- Sub-100ms for 50 ADRs: read each ADR file once, precompile regexes, linear-time
  patterns only (respect the adr-watch ReDoS history).
- Read only the pinned canonical fields: scope = `## Enforcement` `path_glob`;
  status = `## Status` line. No new status/scope source.

## Canonical fields (Phase 0, prerequisite)

Both the index reader and the edit-tier injector read exactly what `bin/adr-judge`
already reads:

- **Scope**: the `path_glob` of each rule in the ADR's `## Enforcement` block.
- **Status**: the `## Status` line, cross-checked against the first
  `status_history` entry. Only `Accepted` ADRs are injected.

No schema change to the ADR format. This phase is documentation plus a shared
helper so the three readers (judge, index, injector) cannot drift.

## Phases

Each phase is independently shippable, testable, and reversible. Config lands in
`.adr-kit.json` under a new `inject` block, validated by
`schemas/adr-kit-config.schema.json`.

### Phase 0 -- Canonical fields and shared helper (Option foundation)

- Factor the scope/status extraction the bins already do into one shared helper
  (mirrors the reuse of `glob_to_regex` between adr-judge and adr-watch).
- Document the pinned fields in `templates/adr-kit-guide.md`.
- Tests: helper returns identical scope/status for a fixture ADR as adr-judge and
  adr-watch compute today (regression lock against drift).

### Phase 1 -- Static ADR index, session tier (Option A)

- New `bin/adr-index`: parse all `ADR-*.md`, emit `docs/adr/ADR-INDEX.md` with one
  row per ADR (id, status, one-line decision, `path_glob` scope). `--format
  md|json`. Deterministic, no LLM, exit 0.
- `/adr-kit:init` and `/adr-kit:setup` add a `@docs/adr/ADR-INDEX.md` import stub to
  `CLAUDE.md` (idempotent, never clobbers other imports).
- CI: `.github/workflows/adr-index-check.yml` fails if the committed index is stale
  relative to a fresh regenerate (keeps the generated artifact honest).
- Tests: `tests/test_adr_index.py` -- row-per-ADR, status filter, stable ordering,
  empty-dir self-guard.

### Phase 2 -- Edit-time injector, edit tier (Options B + C)

- New bin (either `bin/adr-inject` or an adr-watch `--pre-edit` mode; decide during
  build to maximise matcher reuse): given the target path from a `PreToolUse`
  payload, run the adr-watch matcher, take the single top-ranked Accepted ADR, and
  emit its `## Decision` text bounded to `inject.max_tokens` (default budget, tuned)
  as `hookSpecificOutput.additionalContext`. Honour the adr-watch cooldown.
- Hook wrapper `.claude-plugin/hooks/pre-tool-use` (polyglot, mirrors
  `run-hook.cmd`/`post-tool-use`), reads the PreToolUse JSON from stdin.
- `.claude-plugin/plugin.json`: add a `PreToolUse` entry matching
  `Edit|MultiEdit|Write`.
- Keep the existing adr-watch `PostToolUse` nudge as the confirmation backstop.
- `.adr-kit.json` `inject` block: `enabled`, `max_tokens`, `cooldown_hours`
  (default reuses watch cooldown).
- Tests: `tests/test_adr_inject.py` -- glob match beats keyword, decision text
  truncated to budget, cooldown suppresses re-injection, always exit 0 on malformed
  payload, self-guard on non-ADR project.

### Phase 3 -- Document the MCP pull-feed, task tier (Option D)

- No new code; `adr_context` and `adr_judge` already exist key-free in `bin/adr-mcp`.
- Document in `templates/adr-kit-guide.md` how a subagent or workflow calls them to
  retrieve decisions and self-check a diff before committing.
- Tests: none beyond existing `tests/test_adr_mcp.py`.

### Phase 4 -- Enforcement-floor lint (Option E)

- Extend `bin/adr-lint` (or Check 7 wiring) to warn when an Accepted ADR has a code
  surface (a non-empty `path_glob` scope) but no declarative Enforcement rules, so
  the fail-closed floor actually covers governed code.
- Tests: `tests/test_adr_lint.py` addition -- code-surface ADR without declarative
  rules produces the warning; governance ADR does not.

### Deferred -- Write-back freshening (Option F)

A `PostToolUse` "this looks like a decision, no ADR covers it" nudge. Deferred:
steering plus enforcement matters more, and the authoring step is the least
deterministic. Revisit after Phases 0-4 are bedded in.

## Rollout order and dependencies

- Phase 0 is a hard prerequisite for 1 and 2 (shared field reader).
- Phases 1, 2, 4 are independent after Phase 0 and can land in any order.
- Phase 3 is documentation only and can land anytime.

## Verification per phase

- `python -m pytest tests/test_adr_*.py` green for the touched module.
- The new hooks exit 0 under: normal payload, malformed payload, non-ADR cwd.
- Latency check: injector under 100ms against the repo's own ADR set.
- `bin/adr-judge` behavior unchanged (the floor is untouched).

## Out of scope

- No change to the ADR Markdown format or `schemas/adr-enforcement.schema.json`.
- No change to the `llm_judge` opt-in posture (ADR-001).
- No daemon, no scheduler, no background process (ADR-002 anti-pattern).
