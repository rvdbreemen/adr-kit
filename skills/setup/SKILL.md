---
name: setup
description: "The one entry point for installing ADR Kit in a project (R19). Modes: register (default), adopt (audit + propose ADRs, /adr-kit:init), hooks (/adr-kit:install-hooks), upgrade (/adr-kit:upgrade)."
argument-hint: "[adopt|hooks|upgrade]"
disable-model-invocation: true
allowed-tools: [Read, Write, Edit, Bash]
---

# adr-kit setup

Setting up ADR Kit is one deterministic act (spec R19) with four modes. An
empty `$ARGUMENTS` runs the default **register** mode below. A mode name
routes to the procedure that owns it -- follow that skill file and nothing
else; each is a mode of this entry point, not a separate product:

| `$ARGUMENTS` | Mode | Procedure |
|---|---|---|
| *(empty)* | **register** -- write the managed guidance layout | this file, below |
| `adopt` | audit the codebase and propose ADRs, then register | `skills/init/SKILL.md` (`/adr-kit:init`) |
| `hooks` | install or remove the pre-commit gate only | `skills/install-hooks/SKILL.md` (`/adr-kit:install-hooks`) |
| `upgrade` | refresh copied artifacts, migrate a v0.11 footprint | `skills/upgrade/SKILL.md` (`/adr-kit:upgrade`) |

Reject any other argument instead of guessing a mode.

You are running the one-time project setup for the adr-kit plugin (register
mode). Your job is to:

1. Write the project's instruction layout with `scripts/setup-project.py`, which owns every file in it.
2. Leave everything outside its managed markers byte-exact.

This is the lightweight counterpart to `/adr-kit:init`. Use `setup` when the user has an existing project, already understands their architecture, and just wants the kit registered. Use `init` when the user wants the kit to also audit the codebase and propose ADRs.

## Backwards compatibility (v0.11 footprint)

A project that ran v0.11 `/adr-kit:setup` has an inline `## ADR Kit Rules` section in `CLAUDE.md`. This skill detects that footprint and leaves it untouched — telling the user to run `/adr-kit:upgrade` to migrate to the v0.12 marker-bracketed stub + external guide layout. **Do not silently rewrite a v0.11 footprint.** The upgrade skill exists for that explicit migration.

## Steps

1. **Resolve the plugin path.**

   ```bash
   ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1)
   ```

   If empty, abort: the plugin install is broken; tell the user to reinstall via `/plugin install adr-kit@rvdbreemen-adr-kit`.

2. **Check for a v0.11 footprint first.** Read `CLAUDE.md` if it exists. If it
   carries an inline `## ADR Kit Rules` section, stop and tell the user:
   `Detected v0.11 ADR Kit Rules section in CLAUDE.md at line <N>. Run
   /adr-kit:upgrade to migrate. /adr-kit:setup is leaving the v0.11 footprint
   untouched.` Exit without changes. A v0.11 footprint requires an explicit
   migration; this command never performs one silently.

3. **Run the writer.** Do not hand-write the instruction block or the guide.
   `scripts/setup-project.py` owns the layout, and it is the only thing that
   knows all of it: `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`
   and `.adr-kit/ADR-guide.md`. Prose in this skill describing an older layout is
   how the three clients drifted apart in the first place -- Codex and Copilot
   delegated here while this file still wrote a guide under `.claude/` and a
   stub block that `scripts/project_setup.py` classifies as legacy.

   Preview first, then apply:

   ```bash
   python3 "$ADR_KIT/scripts/setup-project.py" --client claude-code-cli --project-root . --dry-run
   python3 "$ADR_KIT/scripts/setup-project.py" --client claude-code-cli --project-root .
   ```

   The command is idempotent: re-running it on a current project changes
   nothing. It writes only inside its managed markers, so user content around
   them stays byte-exact, and it never touches `.adr-kit/ADR-guide.local.md`.

   `--client` also accepts `codex-cli` and `github-copilot-cli`, and `--clients`
   takes a comma-separated list when a project uses more than one.

4. **Report what it did.** The command prints one line per change. Relay them,
   and say plainly when there was nothing to do -- a no-op is the expected
   outcome of a second run, not a failure.

## Constraints

- **Two coordinated writes.** v0.12 setup writes both the stub AND the guide file. Either-or is incomplete.
- **Never silently migrate v0.11.** A v0.11 footprint requires explicit `/adr-kit:upgrade`. Leave v0.11 alone here.
- **Idempotent.** Re-running on a v0.12 project where everything is current is a no-op.
- **Read before write.** Preview with `--dry-run` before applying; the writer reads every file it touches.
- **Preserve surrounding content.** Only the marker-bracketed stub and the guide file may be touched. Everything else stays byte-exact.
- **No em dashes** in any text the skill writes (per adr-kit style).

## When the user is in the wrong directory

If `pwd` lacks all of `CLAUDE.md`, `.git/`, and a recognisable project manifest (`package.json`, `pyproject.toml`, `Cargo.toml`, `platformio.ini`, etc.), stop and ask: `I do not see a project root here (no CLAUDE.md, no .git, no manifest). Confirm you want to set up adr-kit in <pwd>?` Do not silently create files in unexpected locations.

## Cross-references

- `/adr-kit:setup adopt` (alias `/adr-kit:init`) — full bootstrap including audit and hook installation.
- `/adr-kit:setup upgrade` (alias `/adr-kit:upgrade`) — migrate v0.11 → v0.12 footprint without re-auditing.
- `/adr-kit:setup hooks` (alias `/adr-kit:install-hooks`) — install the pre-commit hook independently.

## Step 4c — The signer: propose, never assume

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
