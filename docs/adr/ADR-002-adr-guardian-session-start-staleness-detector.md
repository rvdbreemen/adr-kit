---
id: "ADR-002"
title: "ADR Guardian: SessionStart Staleness Detector with Two-Tier Cadence"
status: "Accepted"
date: "2026-05-31"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
topics:
  - "staleness"
  - "guardian"
  - "cadence"
  - "session start"
aliases:
  - "ADR rot"
  - "drift detector"
  - "two-tier sweep"
components:
  - "adr-guardian"
  - "lifecycle hooks"
---
# ADR-002 ADR Guardian: SessionStart Staleness Detector with Two-Tier Cadence

## Status

Accepted, 2026-05-31

## Context

adr-kit v0.17.0 introduced opt-in LLM gates at commit time (`adr-judge --llm`,
`adr-suggest`) but added no mechanism for periodic project-wide ADR health
checks. Between commits, an ADR set rots silently in at least three ways:

1. **Drift**: code in the repository violates an Accepted ADR Enforcement block
   between commits (added before the hook was installed, or via a commit that
   bypassed the hook).
2. **Staleness**: Accepted ADRs become outdated because the technology they
   describe was removed, superseded, or the policy changed, with no commit
   touching the ADR file itself to trigger the hook.
3. **Missing ADRs**: new architectural decisions accumulate without anyone
   running adr-suggest -- the per-commit pass is opt-in and covers only the
   most recent staged diff, not the broader commit history.

The concrete trigger was the removal of the cozempic daemon on 2026-05-31: a
background process that ran health checks on a schedule was identified as
producing orphaned processes, surprise cost, and zero visibility into what was
running. The anti-pattern: periodic work done by a silent daemon the developer
does not see and cannot control.

The need for periodic health checks is real. The daemon-shaped solution is not
acceptable. Existing tools `adr-judge`, `adr-retire`, `adr-lint`, `adr-status`,
and `adr-suggest` already cover all four health signals. What is missing is a
lightweight mechanism to decide when to run them and to surface that decision to
a developer who is about to start a coding session.

## Decision

Implement the ADR Guardian as a dumb SessionStart detector plus in-session smart
sweep, with two-tier cadence and no background processes:

1. **`bin/adr-guardian check`** (the hook entry point): pure-stdlib Python,
   read-only on ADRs, always exits 0, never spawns subprocesses. Reads
   `docs/adr/.adr-kit-state.json` and `docs/adr/.adr-kit.json`, computes which
   health tier(s) are due by comparing `last_run` timestamps against configurable
   thresholds, applies `nudge_cooldown_hours` throttle, and emits the
   `[adr-guardian] ... DUE` block as Claude Code
   `hookSpecificOutput.additionalContext` JSON. Writes only `last_nudged` (to
   prevent re-nagging within the cooldown window). Silent when nothing is due.

2. **Two-tier cadence**: cheap tier (declarative drift via `adr-judge`, stale
   detection via `adr-retire`, health via `adr-lint`/`adr-status`) at 1-day
   default (`guardian.drift_stale_days: 1`); LLM tier (`adr-suggest` missing-ADR
   detection, `adr-judge --llm` full audit) at 14-day default
   (`guardian.llm_stale_days: 14`). The cheap tier is always free. The LLM tier
   costs approximately $0.10-0.30 per run on claude-sonnet-4-6.

3. **Mix-by-finding-type in-session responses** (via `/adr-kit:guardian` skill):
   drift violations surfaced prominently with file:line context; missing-ADR
   suggestions passive (user picks which to author); stale ADRs get an autonomous
   retirement/supersession draft never auto-applied; ADR-set health issues reported
   with a fix offer. The model does the intelligent work; the hook is dumb.

4. **LLM tier is opt-in** (`guardian.llm_autorun: false` default): the skill
   always asks before spending on the LLM tier, consistent with ADR-001 opt-in
   posture. The cheap tier is default-on and free.

5. **Both hook-install paths shipped**: plugin-level (the adr-kit plugin declares
   the `SessionStart` hook in `.claude-plugin/plugin.json`; the cwd-guard makes
   it safe everywhere) and project-scoped (JSON-structural add/remove in
   `.claude/settings.json`; idempotent, never clobbers other hooks).

6. **State file is gitignored** (`docs/adr/.adr-kit-state.json`): per-machine
   state avoids per-session working-tree churn and diff noise.

## Alternatives Considered

### Alternative A: Background daemon (cron/scheduled process)

Run `adr-guardian` on a system-level cron schedule or as a background service.
This was the cozempic pattern: a daemon that periodically polls for health and
posts results to a channel.

Rejected: produces orphaned processes when the developer closes their editor or
suspends their laptop; has zero visibility (the developer does not know it is
running or what it cost); can fan out concurrent LLM processes with no contention
guard; cannot interact with the in-session model to walk through resolution paths.
Explicitly identified as the anti-pattern to avoid per spec section 2.

### Alternative B: CI-only periodic check

Run health checks in CI on a schedule (GitHub Actions schedule trigger or
equivalent). No local daemon; results visible in CI logs.

Rejected for this iteration: CI is not dev-local, so it cannot interact with the
developer in-session model to offer resolution paths or confirm LLM spend before
it happens. A CI-side guardian sharing the same engine is a possible later addition;
it does not replace the dev-local mechanism. Noted in spec section 2 ("CI is a
possible later trigger sharing the same engine").

### Alternative C: On-demand only (no cadence enforcement)

Rely entirely on the developer running `/adr-kit:guardian` manually. No
SessionStart hook, no periodic nudge.

Rejected: without a cadence signal, health checks accumulate technical debt
between sessions. Projects can see 2-4 weeks between voluntary health sweeps,
during which several drift violations and 3-5 stale ADR candidates accumulate
silently. A cadence-free approach is no better than the pre-guardian baseline.

### Alternative D: Single global clock (no tier split)

One stale threshold applies to all checks (cheap and LLM alike). Simpler config.

Rejected: the cheap checks (declarative drift, retire scan, lint) can safely run
daily at zero cost and finish in under 1 second. The LLM checks cost $0.10-0.30
and take 5-30 seconds; running them daily would impose significant cost on active
projects. The two-tier split (1-day cheap, 14-day LLM) allows frequent free health
checks while keeping LLM spend proportional to the bi-weekly cadence where
structural decisions actually shift.

## Consequences

**Positive**

- No background processes. The SessionStart hook is a read-only detector that
  exits in under 100ms. No daemon, no scheduler, no orphaned process.
- Free default posture. The cheap tier runs daily at zero cost. LLM spend is
  bounded to at most 1 bi-weekly run per project per developer.
- Visible and interruptible. The `[adr-guardian]` block appears in the session
  context; the developer sees it and chooses whether to act. No silent background
  work.
- Builds on existing tools. `adr-judge`, `adr-retire`, `adr-lint`, `adr-suggest`
  already exist and are tested. The guardian orchestrates them without duplicating
  logic.
- Two timestamps; independent clocks. The cheap and LLM tier clocks do not
  interfere: a failed LLM run does not reset the cheap timer, and vice versa.
  Stamps update only the tier that completed.

**Negative**

- Requires session start to trigger. Long periods without a session will silently
  accumulate ADR rot (bounded by the next session open rather than the next manual
  invocation).
- State file adds a per-machine artifact. `docs/adr/.adr-kit-state.json` must be
  gitignored and is not portable across machines. Developers on multiple machines
  each get independent clocks; no shared team sweep timestamp. Acceptable given
  the dev-local focus.
- cwd-guard must be airtight. The plugin-level hook fires in every Claude Code
  session regardless of project. A false no-op is safe (feature does not fire);
  a false positive in an unrelated project would be confusing.

## Related Decisions

- Builds on ADR-001 (Make Per-Commit LLM Gates Opt-In): shares the same opt-in
  posture (`llm_autorun: false` mirrors `llm_enabled: false`), the same
  cost-confirm-before-spending principle, and the same config schema extensibility
  pattern.

## References

- Design spec: `docs/superpowers/specs/2026-05-31-adr-guardian-design.md`
- Implementation: `bin/adr-guardian` (detector + stamp + state subcommands)
- In-session skill: `skills/guardian/SKILL.md`
- Config schema: `schemas/adr-kit-config.schema.json` (guardian block)
- Hook manifests: `.claude-plugin/plugin.json` and `.claude-plugin/hooks/`
- State file pattern: `docs/adr/.adr-kit-state.json` (gitignored)
- SessionStart hook contract (Claude Code): verified from
  `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/hooks/session-start`
  -- CLAUDE_PLUGIN_ROOT set (without COPILOT_CLI) implies
  hookSpecificOutput.additionalContext envelope.
- ADR-001: `docs/adr/ADR-001-llm-gates-opt-in.md`

## Enforcement

```json
{
  "llm_judge": false,
  "llm_judge_reason": "no code surface: this decision governs process or documentation, so there is no diff for a model to judge it against"
}
```

Manual review only. The guardian correctness properties are behavioral
(always-exit-0 invariant, silent-when-not-due, throttle logic, JSON envelope
format) rather than syntactic. These cannot be expressed as regex patterns
without broad false-positive risk. Reviewers should verify: (a) `bin/adr-guardian
check` exits 0 in all tested code paths, (b) the cwd-guard fires correctly on
non-ADR project directories, and (c) the `stamp` subcommand does not mutate
state when the `check` subcommand runs.
