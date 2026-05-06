---
name: init
description: One-shot project bootstrap for adr-kit. Hooks the kit into CLAUDE.md (via a slim stub + a copy of templates/adr-kit-guide.md → .claude/adr-kit-guide.md), runs bin/adr-audit to enumerate decision-shaped artefacts in source + documentation, walks the user through batch approval to generate Accepted ADRs via the adr-generator subagent, installs the pre-commit hook, and finally lints. Idempotent across re-runs. User-invocable only — this is a side-effecting operation.
argument-hint: "[no arguments]"
disable-model-invocation: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Task]
---

# adr-kit init

You are running the one-shot project bootstrap for adr-kit. Your job is to take a project that has either no ADRs or only legacy-shaped ADRs and:

1. Hook the kit into the project's `CLAUDE.md` and drop the canonical guide at `.claude/adr-kit-guide.md`.
2. Discover decision-shaped artefacts in the source and documentation, propose a starter set of ADRs reflecting decisions already in effect, and let the user accept them in batches.
3. Install the pre-commit hook so future commits are guarded against ADR drift.
4. Lint everything to confirm the resulting ADR set passes the four verification gates.

This is a deep, one-shot operation. Do not skip steps. Do interact with the user — batched approval beats silent autopilot every time.

## Step 1 — Project hookup

### 1a. Drop the canonical guide

Locate the plugin's `templates/adr-kit-guide.md`. The plugin is loaded under `~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/<version>/`; resolve the latest version with:

```bash
ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1
```

Copy `templates/adr-kit-guide.md` from that path to the project's `.claude/adr-kit-guide.md` (relative to `pwd`, which the user is expected to set to the project root before invoking).

- If `.claude/adr-kit-guide.md` does not exist: write the file.
- If it exists and is byte-identical to the template: skip (no-op).
- If it exists and differs: read both, show the user a unified diff (3 lines of context), ask `keep project version | replace with plugin version | merge by hand`. Apply the chosen action. Default on re-run with no edits is `replace`.

The first line of the plugin template is `<!-- adr-kit-guide vX.Y.Z -->` — preserve that line so future `/adr-kit:upgrade` runs can detect freshness.

### 1b. Append the slim stub to CLAUDE.md

Locate `CLAUDE.md` at the project root. Three cases:

- **CLAUDE.md does not exist.** Create it containing only the stub below.
- **CLAUDE.md exists, no ADR-kit footprint.** Append the stub at the end of the file with one blank line of separation.
- **CLAUDE.md exists, v0.11-style `## ADR Kit Rules` section present.** Replace the entire `## ADR Kit Rules` section (from its heading down to the next `## ` heading or EOF) with the v0.12 stub. Leave everything else in CLAUDE.md untouched.
- **CLAUDE.md exists with an `<!-- ADR-KIT STUB START --> … <!-- ADR-KIT STUB END -->` block.** Replace just the block, preserving its position in the file. Idempotent.

The stub:

```markdown
<!-- ADR-KIT STUB START -->
<!-- DO NOT regenerate manually. Updated by `/adr-kit:init`, `/adr-kit:upgrade`, `/adr-kit:setup`. -->
## ADR Kit

This project uses [adr-kit](https://github.com/rvdbreemen/adr-kit). All architectural decisions live as ADRs in `docs/adr/`. Full guide: @.claude/adr-kit-guide.md

Authoring: `/adr-kit:adr` (or the `adr-generator` subagent).
Pre-commit verification: `bin/adr-judge` runs declarative `Enforcement` rules at commit time. ADRs with `llm_judge: true` are reviewed in-session via `/adr-kit:judge`.
<!-- ADR-KIT STUB END -->
```

Confirm to the user with one line naming the action (`created` / `appended` / `replaced v0.11 inline rules` / `refreshed stub`) and the line number.

## Step 2 — Candidate discovery

Run `bin/adr-audit` to scan the project. Use `--output` to drop the result next to the existing ADRs:

```bash
$ADR_KIT/bin/adr-audit --root . --output docs/adr/.adr-kit-init-candidates.json
```

(`$ADR_KIT` is the plugin path resolved in step 1a.)

The output is a JSON file with:
- `tooling-*` candidates (build system, CI, runtime markers)
- `deps-*` candidates (one per dependency manifest found)
- `doc-quote-*` candidates (one per documentation file containing decision-narrative phrases, with up to 5 example snippets)

Open the file. Tell the user the headline counts: `<N total candidates: <X> tooling, <Y> dependency, <Z> documented>`.

## Step 3 — Deep LLM curation

Read every candidate's evidence file(s) (or relevant section), plus the project's `README.md`, root `AGENTS.md`/`CLAUDE.md`, and the existing `docs/adr/ADR-*.md` files. Your job: decide for each candidate whether it warrants an ADR and dedupe against ADRs that already exist.

For each candidate, classify:
- **`keep`** — material architectural decision; needs an ADR.
- **`merge with ADR-NNN`** — already documented in an existing ADR; no new file needed.
- **`drop`** — not architecturally significant (e.g., a casual doc phrase that didn't actually drive a decision).

Process candidates in **batches of 5–10**. For each batch:

1. Print a numbered list with: candidate id, your proposed classification, your reasoning (one sentence), and (for `keep`) the proposed ADR title and decision_type.
2. Ask the user: `Approve all [yes] | reject specific (list ids) | drop classification suggestion (id → drop) | refine title/type (id → ...)`.
3. Apply the user's choices. For `keep` candidates: invoke the `adr-generator` subagent with the title, decision context (drawn from the evidence files), and at least two alternatives. The agent assigns the next sequential ADR number, writes `docs/adr/ADR-NNN-<kebab-title>.md` with `Status: Accepted, <today>`, and runs the four verification gates. Per ADR, **prompt the agent to include an `## Enforcement` block** if the rule can be expressed declaratively, or `llm_judge: true` if it cannot, or omit the section if the decision has no code surface.

Do not race ahead. Wait for the user's response per batch.

When all candidates are processed, summarise: `<created N new ADRs, merged M, dropped K>`.

## Step 4 — Hook installation (default-on)

Run the `install-hooks` skill (or do its work inline if delegating is awkward):

1. Resolve the plugin's `templates/githooks/pre-commit` path (same plugin path as step 1a).
2. Read it. Write to project `.githooks/pre-commit`. Make it executable (`chmod +x .githooks/pre-commit`).
3. If the project already has a `.githooks/pre-commit`, do NOT overwrite. Read both. Tell the user the existing hook content. Ask: `prepend adr-kit check before existing hook | replace | abort install`. On `prepend`, write a wrapper that runs adr-kit then exec's the original (saved as `.githooks/pre-commit.adr-kit-saved`).
4. Run `git config core.hooksPath .githooks` once. Confirm with `git config --get core.hooksPath`.

Print a one-liner: `Pre-commit ADR judge installed. Disable a single commit with ADR_KIT_HOOK_DISABLE=1 git commit ...; remove permanently with /adr-kit:install-hooks --uninstall.`

Hook is **default-on** as of v0.12 — no prompt for installation. The user can opt out per-commit with the env var or remove the hook with the `--uninstall` flag on the install-hooks skill.

## Step 5 — Final lint

Run the kit's lint binary on the freshly populated ADR directory:

```bash
$ADR_KIT/bin/adr-lint docs/adr/
```

Report the result: `<N PASS, M ADVISORY, K FAIL>`. If any FAIL: list them with the gate name and ask the user whether to fix now (re-invoke `adr-generator` for the offending ADR) or defer to a follow-up.

## Wrap-up

Print a final summary in this exact shape:

```
adr-kit init complete:
- guide:    .claude/adr-kit-guide.md (created | refreshed | unchanged)
- stub:     CLAUDE.md (created | appended | replaced | refreshed)
- audit:    <N> candidates → <X> kept, <Y> merged, <Z> dropped
- ADRs:     <N> created, <M> already present
- hook:     installed (or already present + reason)
- lint:     <P> PASS, <A> ADVISORY, <F> FAIL
```

Suggest a first commit: `git add docs/adr/ .claude/adr-kit-guide.md CLAUDE.md .githooks/pre-commit && git commit -m "chore(adr-kit): bootstrap v0.12"`. Do not run the commit yourself; let the user inspect first.

## Constraints

- **Do not skip steps.** Each step has an idempotency story; running them in order produces a consistent project state.
- **Batch user approval.** Do not silently mass-generate ADRs. Five to ten candidates per round, one round at a time.
- **Resolve the plugin path dynamically.** The kit lives at `~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/<version>/`. Use the `ls | sort -V | tail -1` resolver above; do not hardcode a version.
- **Preserve user CLAUDE.md content.** Only the marked stub block (or a v0.11-style `## ADR Kit Rules` section being replaced) may be modified. Everything else stays byte-exact.
- **Re-runnable.** A second invocation on a project where init already succeeded should detect the existing footprint and either skip or refresh, not regenerate.
