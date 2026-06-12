---
name: upgrade
description: Refresh a project's installed adr-kit artifacts after a plugin update, and migrate legacy footprints. Runs adr-guardian artifacts to detect copied wrappers (git pre-commit hook, project-scoped settings entry, guide file) that lag the installed plugin version, refreshes them idempotently, and still handles the legacy v0.11 to v0.12 migration (CLAUDE.md stub, guide copy, hook install, Enforcement backfill). Safe to re-run.
argument-hint: "[no arguments]"
disable-model-invocation: true
allowed-tools: [Read, Write, Edit, Bash, Task]
---

# adr-kit upgrade

You bring a project's **installed adr-kit artifacts** in line with the **installed plugin version**. Two jobs, run in order:

1. **Artifact refresh (any version, the common case).** Plugin-level hooks refresh automatically when the plugin updates, but artifacts copied into the project freeze at install time: the git pre-commit wrapper, the project-scoped guardian entry in `.claude/settings.json`, and `.claude/adr-kit-guide.md`. Step 0 detects and refreshes them.
2. **Legacy footprint migration (v0.11 to v0.12, one-time).** Steps 1-4 below. Skip them when the project is already on the v0.12 footprint.

If the project has no ADRs yet, point the user to `/adr-kit:init` instead.

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
