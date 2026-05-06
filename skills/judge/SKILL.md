---
name: judge
description: Interactive in-session judge of a staged git diff against the project's Accepted ADRs. Runs bin/adr-judge for the deterministic declarative pass; for ADRs flagged llm_judge:true, evaluates the diff against the ADR text using the active Claude Code session (no shell-out to claude -p, no extra API key). On violation, walks the user through three resolution paths (write a new ADR, supersede an existing ADR, fix the code). Pairs with the pre-commit hook — invoke before committing on important changes, or after the hook blocks you.
argument-hint: "[no arguments]"
allowed-tools: [Read, Bash, Edit, Write, Task]
---

# adr-kit judge

You are running an interactive in-session judge of the user's staged git diff against the project's Accepted ADRs. The pre-commit hook covers declarative rules at commit time; you cover the same plus the LLM judging that the hook deliberately defers to a session.

## Step 1 — Capture context

Run these (assume cwd is the repo root the user's session was started in; if not, use `git rev-parse --show-toplevel`):

```bash
git diff --cached --unified=0 > /tmp/adr-judge-diff.patch
git diff --cached --stat
```

If the staged diff is empty, tell the user nothing is staged and stop. Suggest: `git add <files> first, then re-invoke /adr-kit:judge`.

## Step 2 — Run the deterministic pass

Resolve the plugin path (same resolver as in `/adr-kit:init`):

```bash
ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1)
"$ADR_KIT/bin/adr-judge" --diff /tmp/adr-judge-diff.patch --adr-dir docs/adr/ --json > /tmp/adr-judge-result.json
```

Capture the exit code. Read the JSON. Surface its output verbatim to the user — they need to see what the hook would say.

## Step 3 — In-session LLM pass

Read every Accepted ADR (`docs/adr/ADR-*.md` where `Status: Accepted`). Identify the subset where the Enforcement block has `"llm_judge": true`. For each such ADR:

1. Read the ADR's full body (Context, Decision, Consequences). Form a clear understanding of what the rule is.
2. Read the staged diff (you already have it at `/tmp/adr-judge-diff.patch`).
3. Make a verdict: `compliant` | `violation: <one-line reason>` | `unsure: <ask>`.
4. For `unsure`: ask the user a clarifying question. Don't fabricate a verdict.

Aggregate the LLM verdicts together with the deterministic findings from step 2. The combined output structure:

```
[deterministic]
  <0..N declarative violations from adr-judge>
  <0..M advisory entries from adr-judge>
[in-session LLM]
  <0..K llm_judge findings>
```

If everything is clean (no violations, no unsure verdicts): tell the user the diff is clear to commit, and stop.

## Step 4 — Resolution paths

If there is at least one violation (declarative or LLM-judged), ask the user which resolution path to take **per violation**. Three options, each delegating to existing primitives:

### (a) Write a new ADR

The diff introduces a new architectural pattern that no current ADR covers. Invoke the `adr-generator` subagent with:

- **Title** drawn from the user's intent for the change.
- **Context** drawn from the diff hunks and the user's stated rationale.
- **At least two alternatives** with rejection reasons (the user may need to provide these).
- **Consequences** in both directions.
- **Enforcement block** when the new pattern is mechanically expressible (encourage the user toward declarative rules).

The agent writes `docs/adr/ADR-NNN-<kebab-title>.md` with `Status: Proposed`. Tell the user to flip to `Accepted` after their own review.

### (b) Supersede an existing ADR

The violation is real because the current ADR is wrong / out of date. Use the supersession workflow defined in `skills/adr/SKILL.md` (which this judge skill links to, not duplicates):

1. Invoke `adr-generator` with `--supersedes ADR-<old>` (or pass `Related Decisions: Supersedes ADR-<old>` in the prompt).
2. After the new ADR is `Accepted`: edit ONLY the old ADR's Status line to `Superseded by ADR-<new>, <today>.` Leave every other section untouched.

Never edit Decision/Context/Consequences/Alternatives of an Accepted/Deprecated ADR.

### (c) Fix the code

The violation is real and the ADR stands; the diff needs to change. Propose the smallest fix that makes the diff comply. Show the user the proposed change as a unified diff fragment. Do **not** apply the change without explicit user confirmation. After the user accepts and applies the fix, suggest re-staging and re-running `/adr-kit:judge`.

## Step 5 — Wrap-up

Once all violations are resolved (option a/b/c chosen for each), tell the user:

```
adr-judge in-session pass complete.
- declarative: <N> violations resolved
- llm:         <M> violations resolved
- new ADRs:    <list of ADR-NNN files added>
- superseded:  <list of supersession chains>
- code fixes:  <list of files touched (none if user applied themselves)>

Next step: re-stage your changes, then commit. The pre-commit hook will re-run the declarative pass on the corrected diff.
```

## Constraints

- **No `claude -p` shell-out.** All LLM judging happens in this session, using the model already loaded.
- **No silent code changes.** Resolution path (c) shows a proposed diff and waits for explicit user confirmation.
- **Do not auto-flip ADRs to Accepted.** New ADRs created during judging start at `Proposed`; the human flips them after review.
- **Re-entry safe.** A user can run `/adr-kit:judge` multiple times in one session — each run re-reads the staged diff and the current ADR set.
- **Model can self-call.** This skill is NOT `disable-model-invocation`. The model running a coding task may invoke `/adr-kit:judge` before requesting a commit on the user's behalf.
