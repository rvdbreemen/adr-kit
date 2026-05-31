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

## Step 0 — Verify Python 3

adr-kit requires Python 3.9 or later. Before doing anything else, verify it is available.

### Detection

Run these checks in order:

```bash
python3 --version 2>/dev/null || python --version 2>/dev/null || py --version 2>/dev/null
```

Parse the output. Acceptable: any Python 3.9+ version string. Not acceptable: Python 2.x, command not found, or no output.

**If Python 3 is found:** print `[adr-kit] Python OK: <version>` and continue to Step 1.

**If Python 3 is NOT found:** offer installation. Detect the platform:

```bash
uname -s 2>/dev/null || echo "windows"
```

Then present platform-specific installation guidance:

---

### macOS — Python not found

```bash
# Option A (recommended): Install via Homebrew
brew install python3

# Option B: Install Xcode Command Line Tools (includes python3)
xcode-select --install

# Option C: Download from python.org
# https://www.python.org/downloads/macos/
```

Ask the user: `Run 'brew install python3' now? (Y/n)`
- If yes: run `brew install python3` via Bash. After it completes, verify again with `python3 --version`. If successful: confirm and continue.
- If no: print the install instructions and tell the user to re-run `/adr-kit:init` after installing.

---

### Linux (Debian/Ubuntu)

```bash
sudo apt-get update && sudo apt-get install -y python3 python3-pip
```

Ask: `Run this command now? (Y/n)`
- If yes: run it. Verify after. Continue if successful.

### Linux (Red Hat/Fedora/CentOS)

```bash
sudo dnf install python3   # Fedora/RHEL 8+
# or: sudo yum install python3
```

### Linux (Arch)

```bash
sudo pacman -S python
```

For generic Linux, detect the distro from `/etc/os-release` and present the matching command. If uncertain, present all three and ask the user to choose.

---

### Windows — Python not found

Present these options in order:

**Option A (recommended): Windows Package Manager (winget)**
```powershell
winget install Python.Python.3.12
```
Ask: `Run this in a terminal now? (Y/n)` — if yes, run it via PowerShell.

**Option B: Microsoft Store**
Open: `ms-windows-store://pdp/?ProductId=9NCVDN91XZQP`
(or search "Python 3" in the Microsoft Store)

**Option C: python.org installer**
Download from: https://www.python.org/downloads/windows/
Instruct: Check "Add Python to PATH" during installation.

After any Windows installation, verify:
```powershell
python --version
```

**IMPORTANT for Windows users:** After installation, a new terminal session may be needed to pick up the updated PATH. Tell the user to close and reopen the terminal, then re-run `/adr-kit:init`.

---

### All platforms — After successful installation

1. Verify the installed version: `python3 --version` (or `python --version` on Windows).
2. Confirm the version is 3.9+. If it is 3.8 or earlier, warn: `[adr-kit] WARN: Python 3.8 detected. adr-kit recommends 3.9+. Some features may not work.`
3. Print: `[adr-kit] Python 3.x.y installed. Continuing setup...`
4. Continue to Step 1.

If the user declines installation and Python is unavailable: print the error below and stop.

```
[adr-kit] ERROR: Python 3 is required but not installed.
Install Python 3.9+ from https://www.python.org/downloads/ and re-run /adr-kit:init.
```

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
Pre-commit verification: `bin/adr-judge` runs declarative `Enforcement` rules at commit time (free). The Claude LLM pass for `llm_judge: true` ADRs is opt-in (enable in `docs/adr/.adr-kit.json`, or review in-session via `/adr-kit:judge`).
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

## Step 4 — Hook installation

Run the `install-hooks` skill (or do its work inline if delegating is awkward):

1. Resolve the plugin's `templates/githooks/pre-commit` path (same plugin path as step 1a).
2. Read it. Write to project `.githooks/pre-commit`. Make it executable (`chmod +x .githooks/pre-commit`).
3. If the project already has a `.githooks/pre-commit`, do NOT overwrite. Read both. Tell the user the existing hook content. Ask: `prepend adr-kit check before existing hook | replace | abort install`. On `prepend`, write a wrapper that runs adr-kit then exec's the original (saved as `.githooks/pre-commit.adr-kit-saved`).
4. Run `git config core.hooksPath .githooks` once. Confirm with `git config --get core.hooksPath`.

### 4a — Interactive LLM opt-in (new in v0.17.0)

The hook installs, but the per-commit LLM passes are **OFF by default**. The declarative regex/glob gate is always-on and free.

Print this notice first:

```
[adr-kit] Per-commit LLM judging (claude-sonnet-4-6) adds up to 2 Sonnet calls
per commit (adr-judge + adr-suggest), each with a 120s timeout. Estimated cost:
$0.10–$0.30 per commit on a typical project. The declarative Enforcement gate is
always-on and costs nothing. LLM review is always available on demand via
/adr-kit:judge and `adr-judge --llm`.
```

Then ask two questions (default No for both):

1. `Enable per-commit LLM judging (claude-sonnet-4-6) for llm_judge:true ADRs? (y/N)`
2. `Enable per-commit ADR-suggest nudges? (y/N)`

Write the answers into `docs/adr/.adr-kit.json` (create if absent, merge if present):

```json
{
  "judge": { "llm_enabled": <true|false> },
  "suggest": { "enabled": <true|false> }
}
```

Write the file even when both are declined (both `false`) — explicit configuration is better than absent-and-defaulting. Tell the user:

```
[adr-kit] LLM judging: <enabled|disabled>. Suggest: <enabled|disabled>.
LLM review is always available on demand: /adr-kit:judge or ADR_KIT_LLM=1 git commit ...
```

Print the final one-liner: `Pre-commit ADR judge installed (declarative gate always-on; LLM passes opt-in). Disable a single commit with ADR_KIT_HOOK_DISABLE=1 git commit ...; enable LLM for one commit with ADR_KIT_LLM=1 git commit ...; remove permanently with /adr-kit:install-hooks --uninstall.`

## Step 5 — Final lint

Run the kit's lint binary on the freshly populated ADR directory:

```bash
$ADR_KIT/bin/adr-lint docs/adr/
```

Report the result: `<N PASS, M ADVISORY, K FAIL>`. If any FAIL: list them with the gate name and ask the user whether to fix now (re-invoke `adr-generator` for the offending ADR) or defer to a follow-up.

## Step 6 — Generate standalone validation scripts (optional)

Ask the user: "Generate standalone validation scripts for CI/CD pipelines? (Y/n)"

If yes:

```bash
ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1)
"$ADR_KIT/bin/adr-generate-scripts" --lang shell --output .generated/
```

This generates shell scripts in `.generated/<ADR-NNN>/validate.sh` that validate code against ADR Enforcement rules without requiring adr-kit. Useful for CI/CD pipelines that run outside Claude Code.

If the user says no (or presses Enter on the default), skip silently. If `.generated/` already contains scripts from a previous run, the generator overwrites them — this is idempotent.

## Wrap-up

Print a final summary in this exact shape:

```
adr-kit init complete:
- guide:    .claude/adr-kit-guide.md (created | refreshed | unchanged)
- stub:     CLAUDE.md (created | appended | replaced | refreshed)
- audit:    <N> candidates → <X> kept, <Y> merged, <Z> dropped
- ADRs:     <N> created, <M> already present
- hook:     installed (or already present + reason)
- llm:      per-commit judging <enabled|disabled>, suggest <enabled|disabled>
- lint:     <P> PASS, <A> ADVISORY, <F> FAIL
- scripts:  generated | skipped (user declined)
```

Suggest a first commit: `git add docs/adr/ .claude/adr-kit-guide.md CLAUDE.md .githooks/pre-commit && git commit -m "chore(adr-kit): bootstrap v0.12"`. Do not run the commit yourself; let the user inspect first.

## Constraints

- **Do not skip steps.** Each step has an idempotency story; running them in order produces a consistent project state.
- **Batch user approval.** Do not silently mass-generate ADRs. Five to ten candidates per round, one round at a time.
- **Resolve the plugin path dynamically.** The kit lives at `~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/<version>/`. Use the `ls | sort -V | tail -1` resolver above; do not hardcode a version.
- **Preserve user CLAUDE.md content.** Only the marked stub block (or a v0.11-style `## ADR Kit Rules` section being replaced) may be modified. Everything else stays byte-exact.
- **Re-runnable.** A second invocation on a project where init already succeeded should detect the existing footprint and either skip or refresh, not regenerate.
