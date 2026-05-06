---
name: judge
description: Interactive judge of a staged git diff against the project's Accepted ADRs. Runs bin/adr-judge with the LLM pass (Claude Sonnet by default, since v0.13.0) — same engine the pre-commit hook uses, so verdicts are consistent. On violation, walks the user through three resolution paths (write a new ADR, supersede an existing ADR, fix the code). Pairs with the pre-commit hook — invoke before committing on important changes, or after the hook blocks you to drive the resolution.
argument-hint: "[no arguments]"
allowed-tools: [Read, Bash, Edit, Write, Task]
---

# adr-kit judge

You are running an interactive judge of the user's staged git diff against the project's Accepted ADRs. As of adr-kit v0.13.0, the LLM evaluation is done by `bin/adr-judge --llm` (Claude Sonnet by default) — same engine and same prompt as the pre-commit hook, so a verdict here matches the verdict the hook would emit. Your job is to drive the resolution loop the hook can't drive: walk the user through fixing each violation interactively.

## Step 1 — Capture context

Run these (assume `pwd` is the repo root the user's session is in; if not, use `git rev-parse --show-toplevel`):

```bash
git diff --cached --unified=0 > /tmp/adr-judge-diff.patch
git diff --cached --stat
```

If the staged diff is empty, tell the user nothing is staged and stop. Suggest: `git add <files> first, then re-invoke /adr-kit:judge`.

## Step 2 — Run the full judge (declarative + LLM)

Resolve the plugin path (same resolver as in `/adr-kit:init`):

```bash
ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1)
"$ADR_KIT/bin/adr-judge" \
    --diff /tmp/adr-judge-diff.patch \
    --adr-dir docs/adr/ \
    --llm \
    --json > /tmp/adr-judge-result.json
EXIT=$?
```

The `--llm` flag enables the Sonnet pass — `bin/adr-judge` shells out to `claude -p --model claude-sonnet-4-6` (configurable via `judge.llm_model` in `docs/adr/.adr-kit.json`). The runner falls back to declarative-only with a WARN line if the `claude` CLI is missing.

Read `/tmp/adr-judge-result.json`. Show the user:

- Total ADRs checked.
- Each violation: ADR id, rule kind (declarative / llm_judge), file:line if applicable, the message.
- Each advisory.

If `EXIT == 0` and `summary.violations == 0`: tell the user the diff is clear to commit, suggest `git commit ...`, and stop.

## Step 3 — Resolution paths

When `summary.violations >= 1`, ask the user which resolution path to take **per violation**. Three options, each delegating to existing primitives:

### (a) Write a new ADR

The diff introduces a new architectural pattern that no current ADR covers, and the existing `llm_judge` ADR's verdict is a false positive on the boundary case. Invoke the `adr-generator` subagent with:

- **Title** drawn from the user's intent for the change.
- **Context** drawn from the diff hunks and the user's stated rationale.
- **At least two alternatives** with rejection reasons.
- **Consequences** in both directions.
- **Enforcement block** when the new pattern is mechanically expressible (encourage declarative rules over `"llm_judge": true` to keep the hook fast).

The agent writes `docs/adr/ADR-NNN-<kebab-title>.md` with `Status: Proposed`. Tell the user to flip to `Accepted` after their own review.

### (b) Supersede an existing ADR

The violation is real because the current ADR is wrong / out of date. Use the supersession workflow defined in `skills/adr/SKILL.md`:

1. Invoke `adr-generator` with `--supersedes ADR-<old>` (or pass `Related Decisions: Supersedes ADR-<old>` in the prompt).
2. After the new ADR is `Accepted`: edit ONLY the old ADR's Status line to `Superseded by ADR-<new>, <today>.` Leave every other section untouched.

Never edit Decision/Context/Consequences/Alternatives of an Accepted/Deprecated ADR.

### (c) Fix the code

The violation is real and the ADR stands; the diff needs to change. Propose the smallest fix that makes the diff comply. Show the user the proposed change as a unified diff fragment. Do **not** apply the change without explicit user confirmation. After the user accepts and applies the fix, suggest re-staging and re-running `/adr-kit:judge` (or just `git commit`, since the same checks fire there).

## Step 4 — Optional: second-opinion with a different model

If the user disagrees with a Sonnet verdict and wants a sanity check from a different model (Opus 4.7 for nuanced architectural calls; Haiku 4.5 to confirm a fast judgement), re-run with an override:

```bash
"$ADR_KIT/bin/adr-judge" --diff /tmp/adr-judge-diff.patch --adr-dir docs/adr/ \
    --llm --llm-cmd "claude -p --model claude-opus-4-7" --json
```

Show both verdicts and let the user decide which to trust. Don't auto-second-guess — only run this when the user asks.

## Step 5 — Wrap-up

Once all violations are resolved (option a/b/c chosen for each), tell the user:

```
adr-judge pass complete.
- declarative: <N> violations resolved
- llm:         <M> violations resolved
- new ADRs:    <list of ADR-NNN files added>
- superseded:  <list of supersession chains>
- code fixes:  <list of files touched (none if user applied themselves)>

Next step: re-stage your changes, then commit. The pre-commit hook will re-run the same judge on the corrected diff.
```

## Constraints

- **Re-use `bin/adr-judge --llm`.** Do NOT re-implement the LLM pass in-session. Same engine in skill and hook is the whole point of v0.13.0 — verdicts are reproducible regardless of who triggers the check.
- **No silent code changes.** Resolution path (c) shows a proposed diff and waits for explicit user confirmation.
- **Do not auto-flip ADRs to Accepted.** New ADRs created during judging start at `Proposed`; the human flips them after review.
- **Re-entry safe.** A user can run `/adr-kit:judge` multiple times in one session — each run re-reads the staged diff and the current ADR set.
- **Model can self-call.** This skill is NOT `disable-model-invocation`. The model running a coding task may invoke `/adr-kit:judge` before requesting a commit on the user's behalf.
