---
name: upgrade
description: "Upgrade ADR Kit project artifacts and legacy layouts. Use after a plugin update, for stale wrappers, guide refresh, or migration."
argument-hint: "[no arguments]"
disable-model-invocation: true
allowed-tools: [Read, Write, Edit, Bash, Task]
---

# adr-kit upgrade

`$ARGUMENTS` should be empty. Stop for confirmation before any breaking
migration or backup-backed rewrite.

You bring a project's **installed adr-kit artifacts** in line with the **installed plugin version**. Two jobs, run in order:

1. **Artifact refresh (any version, the common case).** Plugin-level hooks refresh automatically when the plugin updates, but artifacts copied into the project freeze at install time: the git pre-commit wrapper, the project-scoped guardian entry in `.claude/settings.json`, and `.claude/adr-kit-guide.md`. Step 0 detects and refreshes them.
2. **Legacy footprint migration (v0.11 to v0.12, one-time).** Steps 1-4 below. Skip them when the project is already on the v0.12 footprint.

If the project has no ADRs yet, point the user to `/adr-kit:init` instead.

After resolving `ADR_KIT` in Step 0 and before refreshing artifacts, run
format discovery:

```bash
python3 "$ADR_KIT/bin/adr-migrate" --plan docs/adr/
```

Report every migration notice. Do not apply any migration during upgrade.
Supported legacy records receive a deterministic dry-run command; external,
hybrid, or ambiguous formats receive `/adr-kit:migrate <path>` guidance.
Continue the artifact upgrade regardless of whether notices exist.

## Step 0 — Artifact freshness check and refresh

Resolve the plugin path and run the detector:

```bash
ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1)
python3 "$ADR_KIT/bin/adr-guardian" artifacts --format json
```

The report lists each copied artifact with its embedded version stamp and a `stale` flag (the guardian SessionStart nudge uses the same detection, so this is the same signal that brought most users here). For each stale artifact:

- **`git-pre-commit-wrapper`** (`.githooks/pre-commit` or `.git/hooks/pre-commit`): overwrite it with the current `$ADR_KIT/templates/githooks/pre-commit` (same target path it already occupies). Show a unified diff first when the installed wrapper differs from any shipped template version (the user may have local edits); ask `replace | keep | merge by hand` only in that case, otherwise replace silently. Preserve the executable bit.
- **`settings-guardian-entry`** (`.claude/settings.json`): replace the guardian hook entry with the current `$ADR_KIT/templates/cc-settings/guardian-hook-entry.json` content using JSON-structural editing (never clobber sibling hooks; same posture as `/adr-kit:install-hooks`).
- **`.claude/adr-kit-guide.md`**: if its version line (first line, `<!-- adr-kit-guide vX.Y.Z -->`) lags the plugin, refresh it from `$ADR_KIT/templates/adr-kit-guide.md` (diff-and-ask when the project copy has local edits, like Step 2 below).

When the report shows no stale artifacts AND the project is already on the v0.12 footprint, exit with `everything up to date; nothing to do`.

Artifacts the plugin cannot refresh from here (report them, do not edit): GitHub Action pins (`uses: ...adr-judge@vX` in workflows; suggest a Dependabot/Renovate rule or a manual bump) and a `pre-commit` framework `rev:` (suggest `pre-commit autoupdate`).

## Step 1 — Detect the installed footprint

Inspect the current state:

- `CLAUDE.md` exists? Read it. Look for a v0.11-style `## ADR Kit Rules` section (free-form heading, no markers) OR a v0.12 `<!-- ADR-KIT STUB START -->` block (markers).
- `docs/adr/` exists? Count `ADR-*.md` files. Scan for any existing `## Enforcement` blocks and tally them.
- `.githooks/pre-commit` exists?
- `.claude/adr-kit-guide.md` exists? If yes, check the version line (first line of the plugin template is `<!-- adr-kit-guide vX.Y.Z -->`).

Report the detected state to the user in a 4–6 line summary before changing anything.

If all of the following are true, the project is already on v0.12:
- CLAUDE.md has the marker-bracketed stub
- `.claude/adr-kit-guide.md` matches the plugin's current version
- `.githooks/pre-commit` is the adr-kit hook
- All Accepted ADRs either have `## Enforcement` blocks or have been explicitly skipped

If so, exit with `already on v0.12; nothing to do`.

## Step 2 — Refresh CLAUDE.md stub + guide file

Resolve the plugin path:

```bash
ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1)
```

Three migration paths for `CLAUDE.md`:

- **v0.11 inline `## ADR Kit Rules` section present.** Replace the entire section (heading through the next `## ` heading, or EOF) with the v0.12 stub:
  ```markdown
  <!-- ADR-KIT STUB START -->
  <!-- DO NOT regenerate manually. Updated by `/adr-kit:init`, `/adr-kit:upgrade`, `/adr-kit:setup`. -->
  ## ADR Kit

  This project uses [adr-kit](https://github.com/rvdbreemen/adr-kit). All architectural decisions live as ADRs in `docs/adr/`. Full guide: @.claude/adr-kit-guide.md

  Authoring: `/adr-kit:adr` (or the `adr-generator` subagent).
  Pre-commit verification: `bin/adr-judge` runs declarative `Enforcement` rules at commit time. ADRs with `llm_judge: true` are reviewed in-session via `/adr-kit:judge`.
  <!-- ADR-KIT STUB END -->
  ```
  Surrounding content (everything outside the section) stays byte-exact. Verify by diff after the edit.

- **v0.12 stub already present.** Replace just the contents between the markers with the current stub text. Idempotent.

- **No ADR-kit footprint.** Append the v0.12 stub at the end of `CLAUDE.md`, with one blank line of separation.

For `.claude/adr-kit-guide.md`:

- If absent: create it from `$ADR_KIT/templates/adr-kit-guide.md`.
- If present and byte-identical to the plugin template: no-op.
- If present and differs: read both, show a unified diff (3 context lines), ask the user `keep project version | replace with plugin version | merge by hand`. Apply.

## Step 3 — Install the pre-commit hook (default-on)

Delegate to `/adr-kit:install-hooks` (or do its work inline if delegation is awkward). Same logic as that skill — detect existing hook, prepend / replace / abort, set `core.hooksPath`. **Do not prompt for installation itself; the hook is default-on as of v0.12.** If the user wants to opt out, they can disable per-commit with `ADR_KIT_HOOK_DISABLE=1` or remove via `/adr-kit:install-hooks --uninstall`.

## Step 4 — Enforcement-block backfill (the only slow step)

For every `Status: Accepted` ADR in `docs/adr/` that does NOT already have a `## Enforcement` section, propose one. Walk them one at a time (not batched) — each proposal needs the ADR's full Decision/Context to make a judgement, and the user's input is per-ADR.

For each ADR:

1. Read the ADR. Summarise its Decision in one line.
2. Decide which of three categories it falls into:
   - **Declarative.** The rule is mechanically expressible. Examples: "no String class in hot paths" → `forbid_pattern: \\bString\\b ... in src/**`; "use addOTWGcmdtoqueue() for OTGW commands" → `require_pattern: addOTWGcmdtoqueue\\(`.
   - **LLM-judgeable.** The rule is too nuanced for regex but a model can read the diff and decide. Set `llm_judge: true`.
   - **Manual review only.** No code surface (e.g., a process or governance ADR). Suggest the user add `<!-- adr-kit-judge: skip -->` near the heading, or simply omit the Enforcement block (the judge skips ADRs without one).
3. Print: `[ADR-NNN] <one-line title> → proposed category: <declarative | llm-judge | manual>; proposed block:` and show the JSON.
4. Ask the user: `accept | edit | skip this ADR | skip rest`.
   - `accept`: Edit the ADR file, append the `## Enforcement` section.
   - `edit`: Show the user the proposal, let them edit it inline; apply when satisfied.
   - `skip this ADR`: leave it alone.
   - `skip rest`: stop the backfill loop entirely.

Do NOT modify any other section of the ADR. Only append the new `## Enforcement` section. Accepted ADRs are otherwise immutable.

## Step 4b — LLM judge: opt-out migration (ask before writing)

`llm_judge` defaults to **true** as of TASK-74. ADRs written before that carry an explicit `"llm_judge": false` that is indistinguishable from a deliberate refusal, so the upgrade proposes turning them on — and the user gets the chance to decline.

Run the deterministic scan first. It writes nothing:

```bash
python3 "$ADR_KIT/bin/adr-migrate" docs/adr/ --enable-llm-judge --dry-run --format json
```

The result has three lists — `enabled` (what would be turned on), `opted_out` (rule-less blocks the scan proposes to mark as having no code surface), and `unchanged` — plus a `summary` carrying the two numbers that decide this step: `judged_after` (how many ADRs the LLM pass evaluates once the migration lands) and `unbounded_after` (how many of those declare no `path_glob`).

**Then ask the user, once, with the whole picture in front of them.** Show:

- **the `summary` totals first.** The `enabled` list is only this run's delta; on an upgraded repository the dominant cost sits in ADRs that are already on. A dry-run reading "6 enabled, 0 unbounded" has been accepted on a set that ended at 64 unscoped of 68 judged, which at the measured 20–28 s per isolated call is ~25 minutes of blocking per commit;
- how many ADRs would be enabled, and for each one its id, its one-line Decision and its rule count;
- which ADRs carry `unbounded_scope: true` — those have no `path_glob` to narrow with, so enabling them costs a model call on **every** commit, not only on commits that touch their area;
- which ADRs the scan proposes to mark as no-code-surface, and why.

Offer these answers:

- **accept all** (the default) — apply as proposed.
- **opt out of specific ADRs** — name them; each needs a reason, which is written into the ADR as `llm_judge_reason` so no later upgrade re-proposes it.
- **enable a rule-less ADR anyway** — name it under `--force-enable`; say plainly that this means one call per commit until the ADR declares a scope.
- **skip entirely** — change nothing; the next upgrade will ask again.

Apply the answer:

```bash
python3 "$ADR_KIT/bin/adr-migrate" docs/adr/ --enable-llm-judge \
  --except ADR-006,ADR-011 --reason "reviewed manually in the release checklist" \
  --force-enable ADR-014
```

Report exactly which ADRs were enabled and which were left off. State the cost shape in the same breath, and state it for the whole set: a commit makes one isolated call per scoped ADR whose `path_glob` the diff touches, **plus one call for every unscoped ADR regardless of the diff**. "A commit outside every scope makes none" holds only when `unbounded_after` is zero.

Re-running the command after this is a no-op and says so.

## Step 4b² — Make the pass runnable, and decide where it runs

Enabling `llm_judge` on ADRs configures what SHOULD be judged; it does not make the judge able to run, and it does not decide where the cost lands. An upgrade that stops here can leave a project whose pass degrades silently on every commit, or one whose commits block for half an hour. Finish both halves:

**1. The backend.** Read the effective configuration:

```bash
python3 "$ADR_KIT/bin/adr-judge" --show-config
```

- Retired keys (`judge.llm_cmd`, `judge.llm_model`) present → they are ignored and the warning says so; running `--set-backend` removes them as a side effect.
- No backend, or `host` without a recorded client → walk the user through it now rather than leaving it to the first degraded commit:

```bash
python3 "$ADR_KIT/bin/adr-judge" --set-backend host --host-client claude-code-cli
# or: --set-backend ollama --model <tag> / --set-backend openrouter --model <slug>
```

**2. The cadence.** Take `unbounded_after` from Step 4b's summary and put the multiplication in front of the user: `unbounded_after × ~20 s` is what every commit will block, sequentially, because the pass makes one isolated call per ADR. Two honest configurations exist:

- `unbounded_after` is small (a handful): per-commit judging is affordable; leave `judge.llm_enabled` on.
- `unbounded_after` is large: per-commit judging is not viable, and no faster backend fixes a per-ADR multiplier. Offer `judge.llm_enabled: false` (the declarative pass keeps blocking, at milliseconds) with the **guardian llm tier** as the semantic cadence — `guardian.llm_stale_days` in `docs/adr/.adr-kit.json` (default 14; 7 for a weekly pass) makes the SessionStart nudge raise it when due, cost-gated by `guardian.llm_autorun: false`.

Record the choice in the wrap-up so the next reader of `.adr-kit.json` sees a decision, not an accident.

## Step 4c — Embedding runtime: detect, then offer

ADR-018 permits a precomputed embedding store, and spec R16 asks setup to find
out whether this machine can build one rather than letting the user discover the
gap when retrieval quietly falls back.

```bash
python3 "$ADR_KIT/bin/adr-settings" --adr-dir docs/adr --check-embedding
```

Read-only: it installs nothing and changes nothing. Three outcomes.

- **`ready`** — a runtime with an embedding model is present. Say so and move on;
  there is no question to ask when the answer is already yes.
- **`runtime-without-model`** — offer the pull, with the download size stated
  *before* it starts. 4.7 GB is a decision, not a detail.
- **`absent`** — report it as the normal outcome it is (retrieval keeps working
  on lexical ranking) and offer the three routes: install, point at a runtime you
  already run, or use a remote endpoint.

**Before offering to install, read the GPU line.** Without acceleration the
recommended route is the remote one, and the reason belongs in the sentence: an
embedding model on CPU cannot meet the 2 s hook budget, which turns the feature
into a regression nobody sees. The check is a heuristic and says so; Ollama runs
on CPU either way. This is advice about speed, not a capability gate.

Installing third-party software happens only on explicit consent, never with
silent elevation, and declining must leave a working installation.

## Step 4d — The signer: propose, never assume

Every lifecycle command writes a Status History entry naming who decided, and it
refuses to sign on the user's behalf. That refusal is right, and it should not be
the user's first experience of the tool.

```bash
python3 "$ADR_KIT/bin/adr" signer --suggest --adr-dir docs/adr
```

Read-only: it finds candidates and writes nothing. It looks at the signed-in
GitHub account (`gh api user`, when the CLI is available) and at
`git config user.name`, ranks them, and shows each with its source — a proposal
the user cannot trace is one they cannot judge, and this value lands in an
immutable history.

- **Candidates found** — show them and ask which to adopt, or let the user type a
  different name. Then write it:
  `python3 "$ADR_KIT/bin/adr" signer --set "User: <chosen>"`.
- **Already configured** — say so and move on. Do not overwrite it.
- **Nothing found** — the GitHub CLI is absent or signed out and git names nobody
  usable. Ask for the name outright rather than guessing.

**Bot and CI identities are deliberately not offered.** `github-actions[bot]`,
`runner`, a bare `user`: those are configured values that name a machine, and
R8 asks for evidence of which *human* accepted a decision.

The value is machine-local by design (`docs/adr/.adr-kit.local.json`, gitignored)
because writing one person's name into the tracked config would sign every
teammate's acceptances. Each machine, container and CI runner needs its own.

## Step 5 — Final lint

```bash
"$ADR_KIT/bin/adr-lint" docs/adr/
```

Report the result. Then optionally run a no-op judge to confirm hook plumbing:

```bash
echo "" | "$ADR_KIT/bin/adr-judge" --diff - --adr-dir docs/adr/
```

Should exit 0 with `OK — 0 violations, 0 advisory`.

## Wrap-up

Print the final summary:

```
adr-kit upgrade complete:
- CLAUDE.md: <unchanged | refreshed | migrated from v0.11>
- guide:     .claude/adr-kit-guide.md (created | refreshed | unchanged)
- hook:      <installed | already present>
- backfill:  <N> ADRs got declarative rules, <M> got llm_judge:true, <K> skipped, <Q> already had Enforcement
- lint:      <P> PASS, <A> ADVISORY, <F> FAIL
- formats:   <N> deterministic migration notices, <M> guided notices; 0 auto-migrated
- judge:     backend <name | none>, <judged_after> ADRs judged, <unbounded_after> unscoped;
             cadence <per-commit | guardian llm tier every <D>d | declarative-only>
```

Suggest a commit:

```bash
git add CLAUDE.md .claude/adr-kit-guide.md .githooks/pre-commit docs/adr/
git commit -m "chore(adr-kit): upgrade to v0.12"
```

Do not run the commit yourself.

## Constraints

- **Per-ADR backfill is opt-in.** Never silently rewrite ADR contents. Each proposal is shown, the user accepts/edits/skips.
- **Surrounding CLAUDE.md content stays byte-exact.** Only the marked stub block (or v0.11 `## ADR Kit Rules` section being replaced) may change.
- **Re-runnable.** A second invocation should detect "already on v0.12" and exit cleanly.
- **No new ADRs.** This skill never invokes `adr-generator`. New ADRs come from `/adr-kit:init` (first-time bootstrap) or `/adr-kit:adr` (on-demand authoring).
- **Default-on hook.** Don't prompt for hook installation as if it were optional. The opt-out path is `--uninstall`, not pre-install consent.
