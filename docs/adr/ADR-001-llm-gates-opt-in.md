# ADR-001 Make Per-Commit LLM Gates Opt-In

## Status

Accepted, 2026-05-31

## Context

Since v0.13.0 (adr-judge LLM pass) and v0.16.0 (adr-suggest), the adr-kit
pre-commit hook has fired up to **2 Claude Sonnet calls per commit**
(`claude -p --model claude-sonnet-4-6`, 120-second timeout each) whenever
`llm_judge: true` ADRs exist in the project. Both passes were default-on:

- `templates/githooks/pre-commit` hard-coded `--llm` in the adr-judge invocation
  (line that became `ADR_OUT=$(... "$ADR_JUDGE" --diff - --adr-dir ... --llm 2>&1)`).
- `bin/adr-judge` at the LLM-mode-resolution block (`bin/adr-judge:1208–1213`)
  activated the LLM pass whenever `judge.llm_default` was set, with no
  user-facing "on/off" master switch separate from the env escape hatch.
- `bin/adr-suggest` documented `suggest.enabled` (default `true`) but never
  read the flag — the opt-out was a documented-but-unread no-op.
- No concurrency guard existed: rapid commits (e.g. `git commit --amend`,
  IDE auto-commit, `git rebase -i` with `exec`) could fan out unbounded
  concurrent `claude -p` processes, each with a 120-second timeout.

The concrete cost and latency impact on a project with 50 `llm_judge: true`
ADRs: roughly $0.10–$0.30 per commit and 5–10 seconds of added latency per
commit on Sonnet 4.6 with prompt caching — paid on every commit, including
trivial ones like documentation fixes or version bumps.

New users who ran `/adr-kit:init` were not asked whether they wanted per-commit
LLM judging. The LLM pass started silently on the first commit after init,
causing surprise API spend.

## Decision

Make the per-commit LLM pass opt-in, add a concurrency guard, and ask
interactively in `/adr-kit:init`:

1. **Add `judge.llm_enabled` (default `false`)** as the user-facing master
   switch in `.adr-kit.json`. `bin/adr-judge` activates the LLM pass when
   `--llm` is passed, OR `judge.llm_enabled` is `true`, OR the legacy
   `judge.llm_default` is `true` (kept for CI back-compat).
2. **Remove the hard-coded `--llm` from the pre-commit hook template.**
   Replace with `_LLM_FLAG=""` + `[ "${ADR_KIT_LLM:-0}" = "1" ] && _LLM_FLAG="--llm"`.
   The hook self-activates LLM only when `ADR_KIT_LLM=1` (per-commit) or
   `judge.llm_enabled:true` drives `adr-judge` internally.
3. **Fix `bin/adr-suggest` to honor `suggest.enabled` (default `false`).**
   Flip the `suggest.*` default from `true` to `false`. The check fires before
   any diff reading so skipped commits pay zero overhead.
4. **Add a flock concurrency guard** to the hook. Take a non-blocking advisory
   lock at `$ROOT/.git/adr-kit-judge.lock`. Under contention: keep the cheap
   declarative pass, set `ADR_KIT_NO_LLM=1` for that commit. `flock` absent
   (bare Windows cmd.exe): degrade to no-lock silently.
5. **`/adr-kit:init` interactive opt-in.** After hook install, print a cost
   notice (up to 2 Sonnet calls/commit, 120s timeout, ~$0.10–$0.30/commit) and
   ask two Y/N questions (both default No). Write the result to
   `docs/adr/.adr-kit.json`. LLM review remains available on demand via
   `/adr-kit:judge` and `adr-judge --llm` regardless.

## Alternatives Considered

### Alternative A: Keep default-on, add only the flock guard

The flock guard addresses the unbounded-concurrency problem but does not address
the surprise-cost problem. Users who installed the hook via `/adr-kit:init` or
`/adr-kit:install-hooks` before noticing the per-commit cost would still pay on
every commit. Rejected: the cost/latency surprise is the larger user-experience
failure; concurrency is secondary.

### Alternative B: Keep default-on, improve documentation only

Better README and CHANGELOG language would warn new users, but would not help
users who installed before reading the docs. The default behaviour still fires
API calls on every commit. Rejected: documentation does not fix a default that
surprises users in practice.

### Alternative C: Remove per-commit LLM judging entirely

The `llm_judge: true` mechanism is valuable for semantic compliance checks that
regex cannot express — it drives `/adr-kit:judge` and direct `adr-judge --llm`
invocations. Removing it entirely would degrade the toolkit's on-demand review
capability. Rejected: the right answer is opt-in, not removal.

### Alternative D: Per-commit interactive prompt (ask each time)

Prompting the user before each LLM-enabled commit ("LLM pass will fire, OK?")
is not feasible inside a git hook: hooks cannot reliably read from the terminal
(stdin is connected to the diff pipe, not the user's tty). Rejected:
technically infeasible in a hook context.

## Consequences

### Positive

- **No surprise API spend.** Users who install the hook on an existing project
  with `llm_judge: true` ADRs will not incur Sonnet costs until they explicitly
  opt in.
- **Faster commits by default.** The declarative gate adds negligible latency
  (~50–200ms). Commits without opt-in LLM no longer pay the 5–10s Sonnet
  round-trip.
- **Explicit configuration.** `judge.llm_enabled: true` in `.adr-kit.json` is
  a 1-line opt-in that is discoverable, version-controlled, and documented.
- **Concurrency safety.** The flock guard caps at 1 concurrent LLM invocation
  per repo, preventing runaway spend on rapid-commit workflows.
- **On-demand LLM review preserved.** `/adr-kit:judge` and `adr-judge --llm`
  are unaffected; the full LLM review workflow is available whenever the user
  wants it.

### Negative

- **Breaking default change.** Existing projects that relied on the per-commit
  LLM pass (i.e. had `llm_judge: true` ADRs and expected hook enforcement) will
  silently lose that coverage after upgrading to v0.17.0. Migration: add
  `{"judge":{"llm_enabled":true}}` to `docs/adr/.adr-kit.json`. This is
  a one-line change, but it is a change that existing users must make
  intentionally.
- **`adr-suggest` opt-out users unaffected, opt-in users newly required.**
  Users who previously relied on `suggest.enabled: false` to disable the pass
  already have the correct config and see no behaviour change. Users who relied
  on the pass being on by default must now add `suggest.enabled: true`.

## Related Decisions

None. This is the first ADR for the adr-kit project itself.

## References

- `templates/githooks/pre-commit` — pre-commit hook template; the hard-coded
  `--llm` flag was removed in this change.
- `bin/adr-judge` lines 1208–1217 — LLM mode resolution block; `llm_enabled`
  added as the third opt-in signal.
- `bin/adr-suggest` lines 573–599 — opt-in gate inserted before `read_diff`.
- `schemas/adr-kit-config.schema.json` — `judge.llm_enabled` property added,
  `suggest.enabled` default flipped to `false`.
- `skills/init/SKILL.md` — Step 4a interactive LLM opt-in added.
- `CHANGELOG.md` — v0.17.0 section documents the breaking default change.

## Enforcement

Manual review only. The rule "the hook must not hard-code `--llm` in the
`adr-judge` invocation line" cannot be expressed safely as a regex: the flag
`--llm` also appears legitimately in `_LLM_FLAG="--llm"` (the assignment), in
`--llm-cmd`, `--llm-timeout`, and in comments. A `forbid_pattern` broad enough
to catch the violation would produce false positives on the legitimate
occurrences. Reviewers should verify during PR review that the `adr-judge`
invocation in `templates/githooks/pre-commit` constructs the LLM flag via
`$_LLM_FLAG` and does not hard-code `--llm` directly.
