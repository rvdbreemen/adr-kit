---
name: setup
description: "Set up ADR Kit project guidance without an architecture audit. Use for managed CLAUDE.md guidance, the local ADR guide, or lightweight setup."
argument-hint: "[no arguments]"
disable-model-invocation: true
allowed-tools: [Read, Write, Edit, Bash]
---

# adr-kit setup

`$ARGUMENTS` should be empty. Reject unknown arguments instead of changing the
setup scope.

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
   Decision indexes: @docs/adr/ADR-INDEX.md is the compact session map; `docs/adr/ADR-INDEX.json` is the agent metadata and relationship graph. Regenerate both with `bin/adr-index docs/adr`; open source Markdown ADRs before applying constraints.

   Authoring: `/adr-kit:adr` (or the `adr-generator` subagent).
   Pre-commit verification: `bin/adr-judge` runs declarative `Enforcement` rules at commit time. ADRs with `llm_judge: true` are reviewed in-session via `/adr-kit:judge`.
   Edit-tier injection: when an `[adr-inject] ADR-NNN ... governs <file>` block appears before an edit, treat the quoted Decision as a binding constraint for that file and comply with it.
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
