---
name: setup
description: One-time project setup for adr-kit. Hooks `CLAUDE.md` (slim stub with @-import) and drops the canonical guide at `.claude/adr-kit-guide.md`. v0.11-style inline `## ADR Kit Rules` sections are detected and left untouched (run `/adr-kit:upgrade` to migrate them). Idempotent across re-runs. The lighter cousin of `/adr-kit:init` — `setup` does not run a codebase audit or install the pre-commit hook.
disable-model-invocation: true
allowed-tools: [Read, Write, Edit, Bash]
---

# adr-kit setup

You are running the one-time project setup for the adr-kit plugin. Your job is to:

1. Drop the canonical guide at `.claude/adr-kit-guide.md` (copied from the plugin's `templates/adr-kit-guide.md`).
2. Append a slim ADR-kit stub to the project's `CLAUDE.md` so future Claude Code sessions auto-load the guide.

This is the lightweight counterpart to `/adr-kit:init`. Use `setup` when the user has an existing project, already understands their architecture, and just wants the kit registered. Use `init` when the user wants the kit to also audit the codebase and propose ADRs.

## Backwards compatibility (v0.11 footprint)

A project that ran v0.11 `/adr-kit:setup` has an inline `## ADR Kit Rules` section in `CLAUDE.md`. This skill detects that footprint and leaves it untouched — telling the user to run `/adr-kit:upgrade` to migrate to the v0.12 marker-bracketed stub + external guide layout. **Do not silently rewrite a v0.11 footprint.** The upgrade skill exists for that explicit migration.

## Steps

1. **Resolve the plugin path.**

   ```bash
   ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1)
   ```

   If empty, abort: the plugin install is broken; tell the user to reinstall via `/plugin install adr-kit@rvdbreemen-adr-kit`.

2. **Locate `CLAUDE.md`.** It lives at the project root (`pwd`). The user is expected to run `/adr-kit:setup` from there. Read it if it exists.

3. **Detect existing footprint.** Three cases:

   - **v0.11 inline `## ADR Kit Rules` section present.** Stop and tell the user: `Detected v0.11 ADR Kit Rules section in CLAUDE.md at line <N>. Run /adr-kit:upgrade to migrate to v0.12 (slim stub + external guide). /adr-kit:setup is leaving the v0.11 footprint untouched.` Exit without changes.
   - **v0.12 `<!-- ADR-KIT STUB START --> ... <!-- ADR-KIT STUB END -->` block present.** Read it. If its content matches the canonical stub below, no-op. If it differs (e.g., from a partial earlier run, or a manual edit), refresh just the block contents — do not touch surrounding CLAUDE.md content. Confirm with `Refreshed v0.12 ADR-kit stub in CLAUDE.md at line <N>.`
   - **No ADR-kit footprint.** Proceed to step 4 (write the v0.12 stub) and step 5 (write the guide).

4. **Append the v0.12 stub to `CLAUDE.md`.** If CLAUDE.md exists, append the block below at the end with one blank line of separation. If it does not exist, create it containing only the block.

   Stub:

   ```markdown
   <!-- ADR-KIT STUB START -->
   <!-- DO NOT regenerate manually. Updated by `/adr-kit:init`, `/adr-kit:upgrade`, `/adr-kit:setup`. -->
   ## ADR Kit

   This project uses [adr-kit](https://github.com/rvdbreemen/adr-kit). All architectural decisions live as ADRs in `docs/adr/`. Full guide: @.claude/adr-kit-guide.md

   Authoring: `/adr-kit:adr` (or the `adr-generator` subagent).
   Pre-commit verification: `bin/adr-judge` runs declarative `Enforcement` rules at commit time. ADRs with `llm_judge: true` are reviewed in-session via `/adr-kit:judge`.
   <!-- ADR-KIT STUB END -->
   ```

5. **Drop the canonical guide.** Copy `$ADR_KIT/templates/adr-kit-guide.md` to project `.claude/adr-kit-guide.md` (mkdir `.claude/` if needed). Three sub-cases:

   - **No project guide.** Write the plugin template verbatim.
   - **Project guide exists, byte-identical to plugin template.** No-op.
   - **Project guide exists and differs.** Read both. Show the user a unified diff (3 context lines) and ask: `keep project version | replace with plugin version | merge by hand`. Apply.

   The first line of the plugin template is `<!-- adr-kit-guide vX.Y.Z -->` — preserve it so future `/adr-kit:upgrade` runs can detect freshness.

6. **Confirm.** One line summarising both writes:

   ```
   Setup complete.
   - CLAUDE.md: <created | appended at line N | refreshed stub at line N>
   - .claude/adr-kit-guide.md: <created | refreshed | unchanged>
   ```

## Constraints

- **Two coordinated writes.** v0.12 setup writes both the stub AND the guide file. Either-or is incomplete.
- **Never silently migrate v0.11.** A v0.11 footprint requires explicit `/adr-kit:upgrade`. Leave v0.11 alone here.
- **Idempotent.** Re-running on a v0.12 project where everything is current is a no-op.
- **Read before write.** Always read `CLAUDE.md` and `.claude/adr-kit-guide.md` before editing.
- **Preserve surrounding content.** Only the marker-bracketed stub and the guide file may be touched. Everything else stays byte-exact.
- **No em dashes** in any text the skill writes (per adr-kit style).

## When the user is in the wrong directory

If `pwd` lacks all of `CLAUDE.md`, `.git/`, and a recognisable project manifest (`package.json`, `pyproject.toml`, `Cargo.toml`, `platformio.ini`, etc.), stop and ask: `I do not see a project root here (no CLAUDE.md, no .git, no manifest). Confirm you want to set up adr-kit in <pwd>?` Do not silently create files in unexpected locations.

## Cross-references

- `/adr-kit:init` — full bootstrap including audit and hook installation.
- `/adr-kit:upgrade` — migrate v0.11 → v0.12 footprint without re-auditing.
- `/adr-kit:install-hooks` — install the pre-commit hook independently.
