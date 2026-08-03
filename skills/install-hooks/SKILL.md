---
name: install-hooks
description: "Install or remove ADR Kit's deterministic pre-commit gate. Use for ADR hooks, pre-commit enforcement, or uninstalling the owned git hook."
argument-hint: "[--uninstall]"
disable-model-invocation: true
allowed-tools: [Read, Write, Edit, Bash]
---

# adr-kit install-hooks

Use `$ARGUMENTS` only for `--uninstall`; empty means install. Reject all other
arguments.

You install or uninstall the adr-kit pre-commit hook in the project the user is currently in (`pwd` should be the project root).

## Default behaviour: install

### Step 1 — Resolve the plugin's hook template

```bash
ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1)
TEMPLATE="$ADR_KIT/templates/githooks/pre-commit"
```

If `$TEMPLATE` does not exist or is empty, exit with an error: the plugin install is broken; tell the user to reinstall via `/plugin install adr-kit@rvdbreemen-adr-kit`.

### Step 2 — Detect existing hooks

Three cases:

- **No `.githooks/pre-commit`.** Mkdir `.githooks/`, copy the template, `chmod +x`, set `core.hooksPath`. Done.
- **Existing `.githooks/pre-commit` is byte-identical to the template.** No-op. Tell the user it's already installed.
- **Existing `.githooks/pre-commit` differs.** Read both. Show the user the existing content (truncated to first 30 lines). Ask:
  - `prepend adr-kit before existing` — write a wrapper script that calls adr-kit then `exec`s the original. Save the original as `.githooks/pre-commit.adr-kit-saved`.
  - `replace` — overwrite. Save the old hook as `.githooks/pre-commit.backup-<timestamp>` for safety.
  - `abort` — do nothing.
  Apply the user's choice.

### Step 3 — Activate

Run `git config core.hooksPath .githooks`. Confirm with `git config --get core.hooksPath`. If the project already has `core.hooksPath` set to a different directory, do NOT overwrite — tell the user, ask whether to change the config or to symlink the hook into the existing hooks dir.

### Step 4 — Confirm

Print:

```
Pre-commit ADR judge installed.
- hook: .githooks/pre-commit (mode 755)
- core.hooksPath: .githooks
- disable a single commit:  ADR_KIT_HOOK_DISABLE=1 git commit ...
- remove permanently:       /adr-kit:install-hooks --uninstall
- LLM pass is opt-in (off by default). Enable per-project: judge.llm_enabled:true in docs/adr/.adr-kit.json. Enable one commit: ADR_KIT_LLM=1 git commit ...
- ADR-suggest is opt-in too: suggest.enabled:true, or ADR_KIT_SUGGEST=1 for one commit.
```

## Uninstall behaviour: `--uninstall`

When invoked as `/adr-kit:install-hooks --uninstall`:

1. Read `.githooks/pre-commit`. Verify it is the adr-kit hook (look for the line `# adr-kit pre-commit hook` near the top). If it is NOT the adr-kit hook, refuse — tell the user the hook in place isn't ours and we won't touch it.
2. Three paths:
   - **No saved original** (`.githooks/pre-commit.adr-kit-saved` does not exist). Remove `.githooks/pre-commit`. If `.githooks/` is now empty, remove it too. Run `git config --unset core.hooksPath`.
   - **Saved original exists.** Restore: rename `.githooks/pre-commit.adr-kit-saved` → `.githooks/pre-commit`. Leave `core.hooksPath` set to `.githooks`.
   - **`.githooks/pre-commit.backup-<timestamp>` exists** (from a prior `replace` install). Tell the user the backup is there and ask whether to restore that instead. Apply choice.
3. Confirm with one line: `Pre-commit ADR judge uninstalled. (restored prior hook | removed .githooks/ | unset core.hooksPath)`

## Guardian (SessionStart) hook — project-scoped install

The ADR Guardian has **two registration paths** (spec §7):

- **Plugin-level (default, frictionless):** The adr-kit plugin declares a `SessionStart` hook in its manifest. It auto-registers in every Claude Code session when the plugin is enabled globally, and self-guards (exits silently when no `docs/adr/` with ADRs is present). This is the recommended path.
- **Project-scoped (explicit):** Adds the guardian's `SessionStart` entry directly to the project's `.claude/settings.json`. Contained to this project only. Use when the user wants explicit per-project control or does not enable the plugin globally.

### Adding the project-scoped guardian hook

When the user asks to add the guardian hook to the project's `.claude/settings.json`:

1. Read `.claude/settings.json` (create it as `{}` if missing).
2. Check if `hooks.SessionStart` already contains an entry whose `command` contains the string `adr-guardian`. If yes: print "Already installed" and stop.
3. If no SessionStart array exists: create it. Parse the JSON structurally — never do text substitution on a JSON file.
4. Append the following hook object to `hooks.SessionStart[0].hooks` (create the array path if absent):

   ```json
   {
     "type": "command",
     "command": "ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ 2>/dev/null | sort -V | tail -1) && [ -n \"$ADR_KIT\" ] && _PY=$(command -v python3 || command -v python || command -v py) && [ -n \"$_PY\" ] && \"$_PY\" \"$ADR_KIT/bin/adr-guardian\" check 2>/dev/null || true",
     "timeout": 10
   }
   ```

5. Write the updated JSON back. The existing `SessionStart` hooks (if any) are **preserved byte-for-byte** — only the new entry is appended.
6. Confirm: "Guardian hook added to .claude/settings.json. It will fire at the next session start."

### Removing the project-scoped guardian hook

When the user asks to remove the guardian hook from `.claude/settings.json`:

1. Read `.claude/settings.json`. Parse as JSON.
2. Find entries in `hooks.SessionStart[*].hooks[*]` whose `command` contains `adr-guardian`. If none found: print "Guardian hook not found in .claude/settings.json" and stop.
3. Remove exactly those entries. Leave all sibling hooks untouched.
4. If the containing `hooks` array becomes empty after removal, remove the empty array (but keep the parent `SessionStart` entry if other entries exist in other groups).
5. Write the updated JSON back.
6. Confirm: "Guardian hook removed from .claude/settings.json."

**Safety invariant:** Never remove or modify any hook entry that does not contain `adr-guardian` in its `command`. This is the cozempic lesson — a remove that also clobbers unrelated hooks is worse than not removing at all.

### Adding .adr-kit-state.json to .gitignore

After adding the guardian hook (project-scoped or as part of `/adr-kit:init`):

```bash
echo "docs/adr/.adr-kit-state.json" >> .gitignore
```

Verify it is not already present first (idempotent). The state file is per-machine and must never be committed.

## CI gates — offer the shipped workflow templates

The git hook judges one commit. Two gates that a hook cannot cover ship as
copyable workflows in `templates/github-workflows/`; offer them, do not install
them silently, because a workflow file is the project's business:

- **`adr-judge.yml`** — judges the whole branch on every pull request. This is
  what the reviewer is actually being asked to accept, and it uses the CI-sized
  diff budget so raising it never weakens the commit-time gate.
- **`adr-readiness.yml`** — refuses to merge implementation that is linked to a
  Proposed decision nobody accepted.
- **`adr-guardian-audit.yml`** — the weekly staleness sweep, reported into one
  tracking issue.
- **`adr-index-check.yml`** — fails when the generated indexes no longer match
  the ADRs. The commit hook can only warn about this, because it reads the
  worktree while the commit is the staged snapshot; CI checks out the commit
  itself, so it is the only place the block is honest.

Copy on request into `.github/workflows/`, and tell the user the checkout must
use `fetch-depth: 0` or the diff has only one side.

Note for Claude Code users: the branch is also judged *before* the pull request
exists, by the pre-tool guard on `gh pr create`. The workflow remains worth
installing anyway - it covers pushes from a laptop, a different client, and
anyone not working through an agent at all.

## Constraints

- **Never silently overwrite a pre-existing user hook.** Always detect, show, ask.
- **Set `core.hooksPath` only when needed.** If the user already has it pointing at a custom dir, propose a symlink rather than redirecting their config.
- **Idempotent in both directions.** Re-running install when already installed is a no-op. Re-running uninstall when nothing is installed is a no-op (with a warning).
- **`chmod +x`** the hook after writing — without the executable bit, git silently ignores it.
- **Do not commit the hook.** The hook lives in `.githooks/`, which the project may or may not have in `.gitignore`. Don't add it to git here; the user decides whether to track it.
