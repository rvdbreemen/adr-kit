---
name: install-hooks
description: Install or uninstall the adr-kit pre-commit hook in the current project. Copies templates/githooks/pre-commit into .githooks/pre-commit, makes it executable, and runs `git config core.hooksPath .githooks`. Idempotent. Used internally by /adr-kit:init and /adr-kit:upgrade; also exposed standalone for users who want to add or remove the hook independently.
argument-hint: "[--uninstall]"
disable-model-invocation: true
allowed-tools: [Read, Write, Edit, Bash]
---

# adr-kit install-hooks

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
```

## Uninstall behaviour: `--uninstall`

When invoked as `/adr-kit:install-hooks --uninstall`:

1. Read `.githooks/pre-commit`. Verify it is the adr-kit hook (look for the line `# adr-kit pre-commit hook` near the top). If it is NOT the adr-kit hook, refuse — tell the user the hook in place isn't ours and we won't touch it.
2. Three paths:
   - **No saved original** (`.githooks/pre-commit.adr-kit-saved` does not exist). Remove `.githooks/pre-commit`. If `.githooks/` is now empty, remove it too. Run `git config --unset core.hooksPath`.
   - **Saved original exists.** Restore: rename `.githooks/pre-commit.adr-kit-saved` → `.githooks/pre-commit`. Leave `core.hooksPath` set to `.githooks`.
   - **`.githooks/pre-commit.backup-<timestamp>` exists** (from a prior `replace` install). Tell the user the backup is there and ask whether to restore that instead. Apply choice.
3. Confirm with one line: `Pre-commit ADR judge uninstalled. (restored prior hook | removed .githooks/ | unset core.hooksPath)`

## Constraints

- **Never silently overwrite a pre-existing user hook.** Always detect, show, ask.
- **Set `core.hooksPath` only when needed.** If the user already has it pointing at a custom dir, propose a symlink rather than redirecting their config.
- **Idempotent in both directions.** Re-running install when already installed is a no-op. Re-running uninstall when nothing is installed is a no-op (with a warning).
- **`chmod +x`** the hook after writing — without the executable bit, git silently ignores it.
- **Do not commit the hook.** The hook lives in `.githooks/`, which the project may or may not have in `.gitignore`. Don't add it to git here; the user decides whether to track it.
