# ADR Guardian — Design Spec

- **Date:** 2026-05-31
- **Status:** Draft (awaiting review)
- **Target release:** adr-kit v0.18.0 (sequences *after* v0.17.0 LLM-opt-in)
- **Related:** ADR-001 (LLM gates opt-in); a new ADR-002 will record the guardian decision.

## 1. Problem & goal

adr-kit today acts only at two moments: the **pre-commit hook** (drift enforcement on a single staged diff) and **on-demand slash commands** (`/adr-kit:adr`, `/adr-kit:judge`). Nothing runs *periodically* or looks at the project *as a whole*. So an ADR set silently rots: code drifts from Accepted decisions between commits, new architectural decisions go unrecorded, and Accepted ADRs become stale (tech removed, superseded, policy changed) with nobody noticing.

**Goal:** turn adr-kit into a *guardian* — a low-friction, cost-aware mechanism that keeps a project's ADR set honest over time by periodically (a) checking for drift, (b) suggesting missing ADRs, and (c) flagging stale ADRs, then acting per finding-type. It must do this **without** the failure modes of a background daemon (surprise cost, orphaned processes, zero visibility) — explicitly the anti-pattern of the cozempic SessionStart guard removed on 2026-05-31.

## 2. Non-goals

- No CI/CD runner in this iteration (dev-local guardian; CI is a possible later trigger sharing the same engine).
- No background processes, no cron, no daemon. Ever.
- No automatic LLM spend. The LLM tier always asks first.
- No auto-applied edits. The guardian drafts; humans approve.

## 3. Core decisions (locked)

| Axis | Decision |
|---|---|
| Action model | **Mix by finding-type** (see §6) |
| Execution | **SessionStart hook = dumb staleness detector**; the **in-session model** reads the injected block and acts; the heavy sweep runs **in-session**, never in the hook |
| Hook scope | Hook is a read-mostly detector + nudge; intelligence lives in-session |
| Cadence | **Two-tier:** cheap tier (drift + retire + lint) = **daily**; LLM tier (suggest + audit) = **bi-weekly (14d)** |
| State | **gitignored local** state file (avoids per-session working-tree churn from the `last_nudged` write) |
| Hook install | **Offer both:** plugin-level (cwd-guarded, frictionless, default) + project `.claude/settings.json` (explicit per-project) |
| Cost posture | Detection is free (no LLM) and default-on; LLM-tier execution is opt-in/interactive (`llm_autorun:false`), consistent with ADR-001 |

## 4. Architecture & data flow

```
SessionStart hook
   │  (plugin-level, cwd-guarded — or project settings.json)
   ▼
bin/adr-guardian-check        reads .adr-kit-state.json + .adr-kit.json
  (NEW, stdlib, <100ms,       computes which tier(s) are due (two-tier clocks)
   read-mostly, exit 0)       prints [adr-guardian] block as additionalContext
   │                          writes last_nudged (throttle); SILENT when nothing due
   ▼
in-session model reads the block → offers/triggers the due work per §6.
   │  (LLM tier: confirms cost first)
   ▼
/adr-kit:guardian  (NEW skill)   orchestrates existing bins, applies §6 responses,
   │                              stamps .adr-kit-state.json (via bin/adr-guardian-state)
   ▼
findings surfaced in-session (+ optional written report). Human approves any action.
```

### Components

1. **`docs/adr/.adr-kit-state.json`** (NEW, gitignored) — two-tier clocks + last-run summary counts:
   ```json
   {
     "cheap_tier": { "last_run": "2026-05-30T08:00:00Z", "drift_violations": 0, "retire_candidates": 2, "lint": "0F/3A" },
     "llm_tier":   { "last_run": "2026-05-17T08:00:00Z", "suggest_hits": 1, "audit_findings": 3 },
     "retire_seen": ["ADR-014"],          // for change-based nudging
     "last_nudged": "2026-05-30T08:01:00Z"
   }
   ```
2. **`bin/adr-guardian-check`** (NEW) — pure-stdlib detector the hook calls. Reads state+config, computes due tiers vs thresholds, prints the block, writes `last_nudged`. Read-only on ADRs. **Never** runs an LLM, **never** spawns anything, **always exits 0** (must not block session start).
3. **`bin/adr-guardian-state`** (NEW, small) — shared read/write helper for the state file so the check (read) and the skill (write) use one consistent schema/locking.
4. **`skills/guardian/SKILL.md`** (NEW) — the in-session sweep. Orchestrates `adr-judge` (declarative, drift), `adr-suggest` (LLM), `adr-retire` (stale), `adr-lint`/`adr-status`/`adr-quality` (health). Applies §6 mapping. Confirms cost before any LLM-tier phase. Stamps the state file on completion. Accepts an optional arg to run a single tier/phase.
5. **Hook wiring** — see §7.
6. **Guide/stub instructions** — a **Guardian** section in `templates/adr-kit-guide.md` and the CLAUDE.md stub telling the in-session model: *on seeing an `[adr-guardian] … DUE` block, proactively offer to run the due tier; confirm cost before the LLM tier; apply the §6 responses; the skill stamps state when done.*

## 5. Two-tier cadence

- **Cheap tier — daily** (`guardian.drift_stale_days: 1`): `adr-judge` declarative drift (working tree / last-N commits vs Accepted Enforcement) + `adr-retire` scan + `adr-lint`/`adr-status` health. All free (no LLM). Retire detection runs daily but only *nudges* when the candidate set changes vs `retire_seen` (no daily nagging).
- **LLM tier — bi-weekly** (`guardian.llm_stale_days: 14`): `adr-suggest` (missing-ADR detection) + full audit. Costs money; `llm_autorun:false` ⇒ never runs without an in-session yes.

## 6. Mix-by-finding-type responses

| Finding | Tool | Tier | In-session response |
|---|---|---|---|
| **Drift** — code violates an Accepted ADR's Enforcement | `adr-judge` (declarative) | daily | **Surfaced prominently.** List violations w/ file:line + ADR; offer to fix or open a task. Highest signal. |
| **Missing ADR** — new decision not yet recorded | `adr-suggest` (LLM) | bi-weekly | **Passive.** List candidates + confidence; offer to author selected ones via `adr-generator`. User picks. |
| **Stale ADR** — tech removed / superseded / policy drift | `adr-retire` (free) | daily-detect, nudge-on-change | **Autonomous draft.** Draft the retirement/supersession edit (status flip + superseding-ADR skeleton) for review; never auto-apply. |
| **ADR-set health** — gate failures, broken chains, dup numbers | `adr-lint`/`adr-status`/`adr-quality` (free) | with each run | **Report.** PASS/ADVISORY/FAIL summary; offer to fix FAILs via `adr-generator`. |

## 7. Hook install (offer both)

The SessionStart hook is a **Claude Code** hook (configured in settings.json / plugin manifest), **not** a git hook (those live in `.githooks/` via `core.hooksPath`). Two registration paths, both shipped:

- **Plugin-level (default, frictionless):** declare the SessionStart hook in adr-kit's plugin manifest so it auto-registers whenever the plugin is enabled. `bin/adr-guardian-check` **self-guards**: it no-ops instantly (exit 0, no output) unless the current working directory has a `docs/adr/` with ADRs. Trade-off: runs (cheaply) in every project you open.
- **Project-scoped (explicit):** `init` / `install-hooks` writes the SessionStart entry into the project's `.claude/settings.json`. Contained to ADR projects. **Must** be strictly idempotent on add and fully clean on uninstall — this is the same file class the cozempic mess polluted, so add/remove gets the same care (marker-delimited block, byte-exact removal).

Docs explain both; default is plugin-level + cwd-guard, with the project-scoped path documented for users who want explicit control or who don't enable the plugin globally.

## 8. Config (`.adr-kit.json` new `guardian` block)

```json
"guardian": {
  "enabled": true,            // detection default-ON (free, no LLM)
  "drift_stale_days": 1,      // daily cheap tier
  "llm_stale_days": 14,       // bi-weekly LLM tier (suggest + audit)
  "nudge_cooldown_hours": 24, // never re-nag within a day
  "llm_autorun": false        // LLM tier ALWAYS asks before spending
}
```
Add to `schemas/adr-kit-config.schema.json` with full descriptions + defaults. Absent block ⇒ defaults (guardian on, detection only).

## 9. Staleness block format

When due (silent + exit 0 otherwise):
```
[adr-guardian] ADR health — 2 item(s) due
  • drift:     last 3d ago (daily)      DUE
  • llm-tier:  last 15d ago (bi-weekly) DUE   (suggest + audit, costs $)
  state: 79 ADRs · last sweep: 0 drift · 1 suggestion · 2 retire candidates
  → /adr-kit:guardian   (LLM tier asks before spending)
```

## 10. Sequencing & dependencies

- **Depends on v0.17.0** (LLM opt-in): shares the config schema, the opt-in semantics (`llm_autorun` mirrors `judge.llm_enabled`), and the hook-hygiene patterns. Land 0.17.0 first.
- Then v0.18.0 guardian: detector + state helper → skill → schema → hook wiring (both paths) → guide/stub → init/install-hooks → docs/CHANGELOG/version → tests → ADR-002.

## 11. Testing

- `bin/adr-guardian-check`: due/not-due logic across both clocks; cwd-guard no-op when no `docs/adr/`; throttle via `nudge_cooldown_hours`; change-based retire nudge; always exit 0.
- `skills/guardian`: orchestration dry-runs; LLM-tier cost-confirm gate (fake-claude harness); state stamping.
- Idempotent project-scoped install/uninstall of the settings.json block.

## 12. Risks / open items

- **cwd-guard correctness** (plugin-level): must be airtight so it's invisible in non-ADR projects.
- **settings.json edit safety** (project-scoped): idempotent add + clean remove; learn from the cozempic cleanup.
- **additionalContext mechanism**: confirm the exact Claude Code SessionStart hook output contract for injecting context.
- **State file location**: `docs/adr/.adr-kit-state.json` (gitignored) vs under `.git/`. Spec assumes the former (discoverable); revisit if churn/visibility argues otherwise.
- **ADR-002**: the guardian is architecturally significant → its own Proposed ADR before Accepted.
