---
name: guardian
description: "Check ADR health, drift, stale decisions, and lint. Use for ADR guardian, health sweep, stale ADRs, or an [adr-guardian] DUE notice."
argument-hint: "[cheap | llm | all]"
allowed-tools: [Read, Bash, Edit, Write, Task, Glob, Grep]
---

# adr-kit guardian

Use `$ARGUMENTS` as `cheap`, `llm`, or `all`; default to the due tier when it
is empty. Never start paid or cloud judgment without explicit permission.

You are running the ADR-set health sweep. Your job is to run whichever tier(s) are due (or were requested), surface findings using the mix-by-finding-type responses below, and stamp the state file when done.

## Before you start

Resolve the plugin bin path (same resolver used in /adr-kit:judge and /adr-kit:init):

```bash
ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ 2>/dev/null | sort -V | tail -1)
```

If `ADR_KIT` is empty (plugin not installed), fall back to a local checkout:

```bash
# try local checkout
ADR_KIT=$(git rev-parse --show-toplevel 2>/dev/null)/
```

Verify the guardian bin exists:

```bash
ls "$ADR_KIT/bin/adr-guardian" 2>/dev/null || echo "guardian not found"
```

## Step 1 — Determine which tier(s) to run

If invoked with an explicit argument (`cheap`, `llm`, or `all`), honour it.

Otherwise, read the current state to determine due tiers:

```bash
"$ADR_KIT/bin/adr-guardian" state
```

Compute which tier is due based on `cheap_tier.last_run` vs `guardian.drift_stale_days` and `llm_tier.last_run` vs `guardian.llm_stale_days` (defaults: 1d cheap, 14d LLM). If neither is due, report "Both tiers are current — nothing to sweep" and stop.

Read `docs/adr/.adr-kit.json` if it exists to get any custom `guardian.*` config.

## Step 2 — Cheap tier (drift + stale + lint)

Run only when cheap tier is due or explicitly requested.

### 2a. Drift check (declarative, adr-judge)

```bash
git diff HEAD~5 HEAD --unified=0 | "$ADR_KIT/bin/adr-judge" \
    --diff - \
    --adr-dir docs/adr/ \
    --repo-root "$(git rev-parse --show-toplevel)" \
    --snapshot worktree \
    --json > /tmp/guardian-drift.json 2>&1
DRIFT_EXIT=$?
```

Read `/tmp/guardian-drift.json`. Count violations and advisories.

**Response (mix-by-finding-type: Drift):** Surface prominently. List each violation with file:line + ADR id. Offer to (a) fix the code, (b) write a new ADR covering the new pattern, or (c) supersede the violated ADR. Highest-priority finding type.

### 2b. Stale ADR detection (adr-retire)

```bash
"$ADR_KIT/bin/adr-retire" \
    docs/adr/ \
    --format json > /tmp/guardian-retire.json 2>&1
```

Read `/tmp/guardian-retire.json`. Collect the candidate set: extract the list of ADR ids flagged for retirement (candidates).

**Change-based filtering:** Read `retire_seen` from the state file (`adr-guardian state`). Compare the fresh candidate set against `retire_seen`. Only surface candidates that are *new* (present in fresh set but not in `retire_seen`). This avoids daily nagging about the same stale ADRs. If all candidates are already in `retire_seen`, skip the retire response silently for this sweep.

**Response (mix-by-finding-type: Stale ADR):** For each **new** retire candidate, draft a retirement/supersession skeleton for human review — never auto-apply. Show:
- The ADR id and title.
- The retirement signal (tech removed / superseded target missing / policy drift / age threshold).
- A draft Status flip: `Deprecated, <today>` or `Superseded by ADR-NNN, <today>` (if a superseding ADR exists).
- Ask the user to confirm or skip each.

### 2c. Health lint (adr-lint / adr-status)

```bash
"$ADR_KIT/bin/adr-lint" docs/adr/ 2>&1 | tail -20
"$ADR_KIT/bin/adr-status" --adr-dir docs/adr/ 2>&1 | tail -5
```

**Response (mix-by-finding-type: Health):** Emit a PASS/ADVISORY/FAIL summary. For FAILs: list the gate name and ADR, offer to fix via `/adr-kit:adr` (re-run the adr-generator subagent on that ADR).

Also read the Enforcement coverage percent for the trend history:

```bash
"$ADR_KIT/bin/adr-status" --adr-dir docs/adr/ --format json > /tmp/guardian-status.json 2>&1
```

Extract `summary.coverage_pct` from `/tmp/guardian-status.json`. You will pass it
to the stamp call below so the trend log records coverage per sweep.

### 2c-bis. Generated-index freshness (adr-index)

```bash
"$ADR_KIT/bin/adr-index" docs/adr/ --check 2>&1 | tail -5
```

Exit 1 means `README.md`, `ADR-INDEX.md` or `ADR-INDEX.json` no longer matches
the ADRs they are generated from. The lifecycle CLI regenerates all three inside
its own transaction, so a stale index means an ADR was edited by hand or written
straight to disk — the common case when a coding agent uses a Write tool.

**Response (mix-by-finding-type: Health):** this one is safe to fix, because the
files are generated rather than authored. Offer to run `bin/adr-index docs/adr`
and show the diff. Do not fix it silently: the regenerated index is a commit the
user has to make.

### 2d. Stamp cheap tier

After completing 2a–2c, record the sweep. The `--retire-seen` argument must contain
the full fresh candidate set (all ids, not just the new ones). The detector uses
the stored set for the next session's change comparison. `--coverage` records the
Enforcement coverage percent (from 2c) in the append-only trend log.

```bash
"$ADR_KIT/bin/adr-guardian" stamp cheap \
    --violations <N_drift_violations> \
    --retire <N_retire_candidates> \
    --lint "<F>F/<A>A" \
    --coverage <coverage_pct_from_adr_status> \
    --retire-seen '<json_array_of_ALL_retire_candidate_ids>'
```

## Step 3 — LLM tier (suggest + audit) — ALWAYS confirm cost first

**MANDATORY cost confirmation gate.** Before running this tier, read `docs/adr/.adr-kit.json`:

- If `guardian.llm_autorun` is `false` (default), print:

  ```
  [adr-guardian] LLM tier: adr-suggest + full audit will invoke claude-sonnet-4-6.
  Estimated cost: ~$0.10–0.30. Run now? (y/N)
  ```

  And wait for an explicit `y` / `yes`. If the user says no (or presses Enter on the default), skip the LLM tier and stop at Step 4.

- If `guardian.llm_autorun` is `true`, proceed without asking (user opted in explicitly in config).

Run only when llm tier is due or explicitly requested (and user has confirmed cost).

### 3a. Missing-ADR detection (adr-suggest)

```bash
git diff HEAD~10 HEAD --unified=0 | "$ADR_KIT/bin/adr-suggest" \
    --diff - \
    --adr-dir docs/adr/ \
    --json > /tmp/guardian-suggest.json 2>&1
```

Read `/tmp/guardian-suggest.json`.

**Response (mix-by-finding-type: Missing ADR):** Passive. List candidates where `needs_adr=true` with `confidence >= medium`. Offer to author selected ones via the `adr-generator` subagent. User picks; never auto-create.

### 3b. Full audit (adr-judge with LLM pass)

```bash
git diff HEAD~10 HEAD --unified=0 | "$ADR_KIT/bin/adr-judge" \
    --diff - \
    --adr-dir docs/adr/ \
    --repo-root "$(git rev-parse --show-toplevel)" \
    --snapshot worktree \
    --llm \
    --json > /tmp/guardian-audit.json 2>&1
```

Read `/tmp/guardian-audit.json`. Same response as Step 2a drift, but covering semantic violations not expressible as regex.

### 3c. Stamp LLM tier

If the cheap tier did not run in this sweep, read `summary.coverage_pct` from
`"$ADR_KIT/bin/adr-status" --adr-dir docs/adr/ --format json` and pass it via
`--coverage` (when omitted, the trend entry carries the last known coverage).

```bash
"$ADR_KIT/bin/adr-guardian" stamp llm \
    --suggest <N_suggest_hits> \
    --audit <N_audit_findings> \
    --coverage <coverage_pct_from_adr_status>
```

## Step 4 — Wrap-up

Refresh the disposable Proposed decision queue after the deterministic sweep,
outside SessionStart:

```bash
"$ADR_KIT/bin/adr-guardian" refresh-readiness \
  --project-root "$(git rev-parse --show-toplevel)" --diff
```

Then report at most the first three cached actions. The queue ranks active
implementation links, shipped-but-Proposed records, ready-for-confirmation
records, open human questions, age, and lowest quality in that order. Each
action must use `/adr-kit:grill ADR-NNN`. The cache is derived, expiring,
gitignored, safe to delete, and never authoritative for acceptance.

Print a summary:

```
[adr-guardian] sweep complete
  cheap tier:  <X> drift violations · <R> retire candidates · <lint_summary>
  llm tier:    <S> missing-ADR suggestions · <A> audit findings   (or: skipped)
  → use /adr-kit:adr to author new ADRs, /adr-kit:judge for detailed resolution
```

## Constraints

- **Never auto-apply ADR edits.** All stale/retire changes are drafts for human review.
- **Never auto-create ADRs.** Missing-ADR suggestions are presented; user picks.
- **Never skip the cost-confirm gate** when `llm_autorun: false`.
- **Always stamp after each tier completes** so the next session's cooldown is correct.
- **Model can self-call.** This skill is NOT `disable-model-invocation`. When the session model sees an `[adr-guardian] ... DUE` block injected at SessionStart, it should proactively offer to run the due tier via `/adr-kit:guardian`.

## Team mode

The guardian has two complementary triggers; use both on team projects:

- **SessionStart nudge (per developer).** The local hook plus this skill gives each developer a freshness signal on their own machine. The state file (`docs/adr/.adr-kit-state.json`) is gitignored, per-machine, advisory data: atomic writes keep it safe across parallel Claude Code sessions, and last-writer-wins is the accepted semantics.
- **CI-cron sweep (shared team visibility).** A weekly GitHub Actions workflow (`.github/workflows/adr-guardian-audit.yml`; downstream copy-paste variant in `templates/github-workflows/adr-guardian-audit.yml`) runs the cheap tier only (lint + retire + status) and maintains a single "ADR guardian audit" tracking issue. Report-only: it never fails the build, never runs an LLM (ADR-001 posture), and needs no secrets beyond `GITHUB_TOKEN`.

Both can coexist: the CI sweep does not read or write the local state file, and the local nudge cadence is unaffected by CI runs. The LLM tier remains local and opt-in only.

## SessionStart block handling (for in-session model)

When the in-session model reads an `additionalContext` block starting with `[adr-guardian]`:

When at least two sweeps have been stamped, the block also carries a one-line
delta vs the previous sweep, e.g. `trend: drift 2 -> 0, retire 1 -> 2,
coverage 40% -> 45%`. Use it to call out improving or degrading KPIs when
offering the sweep.

1. Check which tier(s) are marked `DUE`.
2. For the **cheap** tier: offer immediately: "ADR drift/health check is due — run `/adr-kit:guardian cheap` to sweep (free, ~30s)?"
3. For the **llm** tier: offer: "ADR semantic check is due (bi-weekly) — run `/adr-kit:guardian llm`? This will confirm cost (~$0.10–0.30) before spending."
4. If the user accepts either, invoke this skill with the appropriate argument.
5. Apply the mix-by-finding-type responses as documented above.
