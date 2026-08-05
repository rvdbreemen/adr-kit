# v0.44.1 sweep — what is left, in what order, and what it waits on

Written 2026-08-05. Twelve open tasks were investigated in depth before any of them
was implemented; three landed, nine did not. This file carries the two things that
are expensive to rediscover: the **ordering constraints** and the **atomic
pairings**. Per-task findings live in each `backlog/tasks/task-NNN` record's
Implementation Notes, which were corrected where the investigation contradicted
them.

**Realistic size: eight to nine focused sessions.** Two tasks each need a session
of their own. Four maintainer acceptance gates sit in the middle and cannot be
worked around — an agent may not run `bin/adr accept --confirm` for itself
(ADR-027).

## Landed

| Task | What shipped |
|---|---|
| TASK-130 | `judge.llm_timeout_seconds` describes the per-ADR loop and states the worst case |
| TASK-131 | Nine unread config keys removed, non-breaking via `adr_config.RETIRED_KEYS`, plus a gate |
| TASK-128 | `tests/conftest.py` tree snapshot; the drift check no longer asserts on a tree other tests write to |
| TASK-92 | Verified already done; the record was stale, not the repository |
| TASK-132 | AC#2 and AC#3 only — import-convention gate and a CI collect step |

## Not landed, in recommended order

1. **TASK-132 AC#4** — raise `dev`'s required contexts. *Deferred pending a decision*,
   see below.
2. **TASK-125** — `bin/adr-doctor` from a generated tree. **Land before every other
   regeneration-heavy task.** It is the only task that changes *which* files are
   mirrored (16 new files per mirror); after it, every `--check` diff is readable,
   before it they are not.
3. **TASK-123 + TASK-124** — *one commit, dedicated session*. They share
   `hooks/manifest.json`, `hook_benchmark.py`, `reference-corpus.json` and
   `test_hook_performance.py`. Must consume TASK-129's exemption mechanism rather
   than invent a second one. Blocks on a quiet-machine certification run and a
   maintainer-accepted ADR.
4. **TASK-129** — the ceiling gate, on top of the recalibrated manifest. Landing it
   after 123 means it gates real numbers rather than numbers about to change.
5. **TASK-95** — *dedicated session*. Reads the recalibrated budgets at run time, so
   it cannot be reviewed before 123. Riskiest change in the sweep: it makes the file
   every hook runs through able to write, under a lock, on the hot path.
6. **TASK-121 + TASK-122** — *one commit*. Same template lines (`:212-216`), and the
   two drafts contradict each other.
7. **TASK-127 AC#2** — the declared-gate decay check. Vacuous until 5 and 8 ship real
   anchors; landing it here means those anchors arrive already covered.
8. **TASK-96** — Open Questions append-only.
9. **TASK-126** — **measure last.** Items 7 and 8 both move `adr-lint`'s number and
   item 3 moves the hook side; rows measured before them are stale on arrival.

### Commits that must be atomic

- TASK-123 + TASK-124 (shared files, and splitting them recalibrates budgets in a
  file whose coverage gate does not yet exist)
- TASK-121 + TASK-122 (same template lines, contradictory drafts)
- TASK-95 code **+ ADR-021's `gate`/`binding` flip**
- TASK-96 code **+ ADR-022's `gate`/`binding` flip**

The last two matter because TASK-127's check fails when a gate name exists in the
tree while the ADR naming it still says `gate: null`. Landing the code without the
flip poisons that check.

### The shared mutation

`COPY_ROOTS = ("bin", "schemas", "templates", "instructions")` plus
`HOOK_RUNTIME_FILES`. **Seven of the nine remaining tasks force a regeneration of
`codex/` and `copilot/`.** Only TASK-126, TASK-129 and TASK-132 do not.

The CRLF trap is live: `codex/templates/githooks/pre-commit` and its Copilot twin
carry 275 CR each against an LF source. Verify with `git diff --stat`, not a byte
comparison, and **do not "fix" the mirrors to LF** — that hides TASK-57.

## Waiting on the maintainer

Four ADRs must be accepted by a person before the tests that depend on them can be
green. Each stalls a pull request until it happens.

| ADR | Blocks |
|---|---|
| The hook-budget recalibration ADR (to be written) | TASK-123/124 |
| The pull-request-moment amending ADR (to be written) | TASK-129's ceiling gate |
| ADR-021 `gate`/`binding` flip | TASK-95 |
| ADR-022 `gate`/`binding` flip | TASK-96 |

## The one decision that changed after it was made

**TASK-132 AC#4 was authorised, then found to cost more than the question said.**

Raising `dev`'s required contexts to `main`'s four adds
`ADR Enforcement (declarative)`, produced by `adr-judge-self.yml` — a workflow with
**no push trigger, which cannot have one**, because `GITHUB_BASE_REF` is empty on
push. Once applied, **direct pushes to `dev` are rejected permanently** and every
commit must arrive through a pull request.

That is a workflow change, not a settings tweak. It is deliberately not applied.
It also has to be **last**: applying it mid-sweep would force every remaining
commit through a PR.

The `strict: true` half of the protection — the part that actually closes the hole
TASK-132 is about, by rejecting checks that ran on an older commit — was already
applied on 2026-08-04 and is in force on both branches.

## Evidence worth keeping

The hook budgets were not arbitrary; they were exactly right for a host that no
longer ships. Measured on Windows 11 / CPython 3.12.9, same payloads, 2026-08-05:

| event | native `adr-hook.exe` p50 | Python `adr-hook.py` p50 |
|---|---|---|
| PreToolUse | 20.2 ms | 273.6 ms |
| SessionStart | 24.6 ms | 269.6 ms |

20 ms sits inside the declared 25 ms p50 / 100 ms hard timeout. ADR-029 retired
that host, and the budgets were left describing a path that no longer runs. Seven
of the eight declared events now fail their own budget; the one that passes,
`pr-create`, is the one whose budget violates ADR-015's ceiling.

The interpreter floor alone — `python -c pass`, 182.6 ms p50 on this machine —
exceeds the 100 ms hard timeout on three events. No optimisation inside the hook
can fix that while the host is CPython: the process has not reached the first line
of `adr-hook.py` yet.
