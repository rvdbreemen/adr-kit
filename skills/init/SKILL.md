---
name: init
description: "Initialize ADR Kit in a project. Use for adr-kit init, first-time ADR setup, architecture audit, managed guidance, and the pre-commit gate."
argument-hint: "[no arguments]"
disable-model-invocation: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Task]
---

# adr-kit init

`$ARGUMENTS` is reserved for future init options and should normally be empty.
Reject unknown arguments instead of guessing.

You are running the one-shot project bootstrap for adr-kit. Your job is to take a project that has either no ADRs or only legacy-shaped ADRs and:

1. Hook the kit into the project's `CLAUDE.md` and drop the canonical guide at `.claude/adr-kit-guide.md`.
   New ADRs use MADR unless `docs/adr/.adr-kit.json` selects
   `template.profile: "nygard"` or `"canonical"`.
2. Discover decision-shaped artefacts in the source and documentation, create a starter work queue of Proposed ADRs, and confirm each decision independently.
3. Install the pre-commit hook so future commits are guarded against ADR drift.
4. Lint everything to confirm the resulting ADR set passes the four verification gates.

This is a deep, one-shot operation. Do not skip steps. Do interact with the user — batched approval beats silent autopilot every time.

## Step 0 — Verify Python 3

adr-kit requires Python 3.10 or later. Before doing anything else, verify it is available.

### Detection

Run these checks in order:

```bash
python3 --version 2>/dev/null || python --version 2>/dev/null || py --version 2>/dev/null
```

Parse the output. Acceptable: any Python 3.10+ version string. Not acceptable: Python 2.x, Python 3.9 or earlier, command not found, or no output.

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
2. Confirm the version is 3.10+. If it is 3.9 or earlier, warn: `[adr-kit] WARN: Python 3.9 or earlier detected. adr-kit requires 3.10+. Some features will not work.`
3. Print: `[adr-kit] Python 3.x.y installed. Continuing setup...`
4. Continue to Step 1.

If the user declines installation and Python is unavailable: print the error below and stop.

```
[adr-kit] ERROR: Python 3 is required but not installed.
Install Python 3.10+ from https://www.python.org/downloads/ and re-run /adr-kit:init.
```

## Step 1 — Project hookup

### 1a. Drop the canonical guide

Locate the plugin's `templates/adr-kit-guide.md`. The plugin is loaded under `~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/<version>/`; resolve the latest version with:

```bash
ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1
```

If `docs/adr/` already exists, inspect its formats before creating or changing
records:

```bash
ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1)
python3 "$ADR_KIT/bin/adr-migrate" --plan docs/adr/
```

Show the notices, but do not migrate automatically. Continue initialization;
the user can approve deterministic preview commands or invoke
`/adr-kit:migrate` for guided mappings afterward.

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
Decision indexes: @docs/adr/ADR-INDEX.md is the compact session map; `docs/adr/ADR-INDEX.json` is the agent metadata and relationship graph. Regenerate both with `bin/adr-index docs/adr`; open source Markdown ADRs before applying constraints.

Authoring: `/adr-kit:adr` (or the `adr-generator` subagent).
Pre-commit verification: `bin/adr-judge` runs declarative `Enforcement` rules at commit time (free). The Claude LLM pass for `llm_judge: true` ADRs is opt-in (enable in `docs/adr/.adr-kit.json`, or review in-session via `/adr-kit:judge`).
Guardian: when an `[adr-guardian] ... DUE` block appears at session start, proactively offer to run the due tier via `/adr-kit:guardian`. Confirm cost before the LLM tier. Apply mix-by-finding-type responses: drift violations surfaced prominently; missing-ADR suggestions passive; stale ADRs drafted for review; health issues reported with fix offer.
Edit-tier injection: when an `[adr-inject] ADR-NNN ... governs <file>` block appears before an edit, treat the quoted Decision as a binding constraint for that file and comply with it.
<!-- ADR-KIT STUB END -->
```

Confirm to the user with one line naming the action (`created` / `appended` / `replaced v0.11 inline rules` / `refreshed stub`) and the line number.

## Step 1b — The signer: propose, never assume

Do this before Step 3, because that is where `bin/adr new` first runs and it
refuses to write an unsigned Status History entry. Discovering that refusal
halfway through a batch of reconstructed ADRs is the worst moment to meet it.

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
- **Nothing found** — ask for the name outright rather than guessing.

**Bot and CI identities are deliberately not offered.** `github-actions[bot]`,
`runner`, a bare `user`: those are configured values that name a machine, and R8
asks for evidence of which *human* accepted a decision.

The value is machine-local by design (`docs/adr/.adr-kit.local.json`, gitignored)
because writing one person's name into the tracked config would sign every
teammate's acceptances.

## Step 2 — Candidate discovery

Run `bin/adr-discover` to scan the project. Use `--output` to drop the result next to the existing ADRs:

```bash
$ADR_KIT/bin/adr-discover --root . --output docs/adr/.adr-kit-init-candidates.json
```

(`$ADR_KIT` is the plugin path resolved in step 1a.)

The output is a JSON file with:
- `tooling-*` candidates (build system, CI, runtime markers)
- `deps-*` candidates (one per dependency manifest found)
- `doc-quote-*` candidates (one per documentation file containing decision-narrative phrases, with up to 5 example snippets)
- `history-*` candidates from the git log: commit subjects that announce a
  change of direction, the files rewritten far more often than the rest, and
  the order in which tooling and dependencies arrived.

**Every candidate carries `source`, and the difference matters.** `source:
"tree"` is a fact about a file that exists. `source: "history"` is a claim
someone typed once, in a hurry, possibly about a decision that was reversed
three commits later — those candidates carry a `why_this_is_weak` note saying
so. Never write an ADR from a history candidate without confirming it against
the code as it stands now. Do surface them: the *why* of an existing codebase
lives in its history, which is exactly what a working-tree scan cannot see.

`history.available: false` means the scan could not read a history (no git, no
commits, not a repository). Say so plainly rather than presenting a tree-only
scan as complete.

Open the file. Tell the user the headline counts: `<N total candidates: <X>
tooling, <Y> dependency, <Z> documented, <H> from history>`.

## Step 3 — Deep LLM curation

Read every candidate's evidence file(s) (or relevant section), plus the project's `README.md`, root `AGENTS.md`/`CLAUDE.md`, and the existing `docs/adr/ADR-*.md` files. Your job: decide for each candidate whether it warrants an ADR and dedupe against ADRs that already exist.

For each candidate, classify:
- **`keep`** — material architectural decision; needs an ADR.
- **`merge with ADR-NNN`** — already documented in an existing ADR; no new file needed.
- **`drop`** — not architecturally significant (e.g., a casual doc phrase that didn't actually drive a decision).

Process candidates in **batches of 5–10**. For each batch:

1. Print a numbered list with: candidate id, your proposed classification, your reasoning (one sentence), and (for `keep`) the proposed ADR title and decision_type.
2. Ask the user: `Approve all [yes] | reject specific (list ids) | drop classification suggestion (id → drop) | refine title/type (id → ...)`.
3. Apply the user's choices. For every `keep` candidate, create the record with
   the lifecycle command, **named explicitly**:

   ```bash
   $ADR_KIT/bin/adr new "<Title>" --adr-dir docs/adr
   ```

   Do not write the file with the Write tool. `bin/adr new` allocates the next
   number, honours `template.profile`, writes `Status: Proposed, <today>`, and
   regenerates all three indexes inside one transaction. A hand-written file
   gets none of that, and the index it leaves behind is stale from the moment
   it lands.

   Include an `## Enforcement` block when the rule is declarative,
   `llm_judge: true` when it is not, or omit the section when no code surface
   exists.

   **When the decision is already shipped, record that.** An init scan is
   reconstructing decisions the code already implements, so set
   `documents_shipped: true` and list the concrete evidence in `verified_in`
   (the candidate's `evidence_files` are exactly that). Use:

   ```bash
   $ADR_KIT/bin/adr document ADR-NNN --verified-in <path> [--verified-in <path>]
   ```

   This is not a shortcut to acceptance; it is the honest metadata, and it is
   what makes step 3b's supported path available at all.
4. Explain and select grill depth per candidate:
   - **compact confirmation** only when chosen decision, rationale,
     alternatives, and consequences each have direct cited evidence;
   - **deep grill** when any of those fields, ownership, or conflict resolution
     is missing or inferred.
   Resolve duplicates and conflicts by merging, linking, rejecting, or
   escalating before acceptance.
5. Confirm each ADR separately. A batch response may select candidates but
   cannot accept multiple decisions. On interruption, retain valid Proposed
   records, Open Questions, a consistent index, and one
   `/adr-kit:grill ADR-NNN` resume command per unfinished record.

Do not race ahead. Wait for the user's response per batch.

## Step 3b — Acceptance, and what "never silently accept" actually forbids

Reconstructing a decision the code already implements is documentation, not
authorisation: nobody is being asked to approve a new direction, they are being
asked to confirm that the record matches what already ships. That is why the
kit has an auto-accept path at all, and init is what it exists for.

What "never silently accept" forbids is the *silently*, not the accepting. So:

1. Show the user the batch of records and what each one documents.
2. Ask once, explicitly, for that batch:
   `Accept these <N> as documentation of shipped behaviour? [yes / grill first / list ids to hold back]`
3. On `yes`, accept each through the supported path:

   ```bash
   $ADR_KIT/bin/adr accept ADR-NNN --auto --auto-mode auto --repo-root .
   ```

   `--auto` is not a bypass. It re-runs every acceptance gate and additionally
   demands `documents_shipped: true`, at least one `verified_in` pointer, no
   unresolved Open Questions, and a quality score above the configured
   threshold. A record that fails any of those refuses to accept and tells you
   which one. That refusal is the point: it is the difference between "the user
   approved this batch" and "the record is good enough to stand".
4. Anything held back, or anything `--auto` refused, stays `Proposed` and gets
   `/adr-kit:grill ADR-NNN`.

Never accept without step 2's question, and never accept a record the user has
not seen. Batch approval selects *which* records; each still passes its own
gates on its own.

When all candidates are processed, summarise: `<created N new ADRs, accepted A
as shipped documentation, held B for grilling, merged M, dropped K>`.

## Step 3c — Verify the index rather than assuming it

Every lifecycle command regenerates the indexes in its own transaction, so
after a clean run this passes. Run it anyway, because "should have" is not a
guarantee and a stale index misinforms every later reader and every agent:

```bash
$ADR_KIT/bin/adr-index docs/adr --check
```

Exit 0 means the three generated artefacts match the ADRs. **Init does not
finish while this is non-zero.** On failure, run `$ADR_KIT/bin/adr-index
docs/adr` to regenerate, then re-run the check and say what was stale — a
record written outside the lifecycle command is the usual cause, and the user
should know it happened.

## Step 4 — Hook installation

Run the `install-hooks` skill (or do its work inline if delegating is awkward):

1. Resolve the plugin's `templates/githooks/pre-commit` path (same plugin path as step 1a).
2. Read it. Write to project `.githooks/pre-commit`. Make it executable (`chmod +x .githooks/pre-commit`).
3. If the project already has a `.githooks/pre-commit`, do NOT overwrite. Read both. Tell the user the existing hook content. Ask: `prepend adr-kit check before existing hook | replace | abort install`. On `prepend`, write a wrapper that runs adr-kit then exec's the original (saved as `.githooks/pre-commit.adr-kit-saved`).
4. Run `git config core.hooksPath .githooks` once. Confirm with `git config --get core.hooksPath`.

### 4a — Choose the judge backend (ADR-017)

The declarative Enforcement gate is always-on, deterministic and free. The LLM pass is **on by default** and needs one decision from the user: which model reviews their commits.

Print this notice first, verbatim. Do not shorten the cost paragraph and do not name a specific model — no model is pinned any more.

```
[adr-kit] The pre-commit judge runs two passes.

  Declarative gate  always on, regex and globs, no model, no cost.
  LLM pass          on by default, for ADRs you mark `llm_judge: true`.

What the LLM pass costs: ONE model call per llm_judge ADR, on every commit that
touches its scope, every time. The calls are deliberately isolated from each
other -- a shared prompt let one ADR's text flip another ADR's verdict -- so the
cost is LINEAR in the number of opted-in ADRs and is not amortised across them.
No ADR carries `llm_judge: true` until an author adds it, so a fresh project
pays nothing until someone opts a decision in.

Where that call goes is your choice:

  1. host        the CLI of the agent you already use. No model flag is passed,
                 so your own configured model answers, and no extra credential
                 is needed beyond the agent you are already signed in to.
  2. openrouter  any model, over HTTPS. Needs OPENROUTER_API_KEY in your
                 environment. adr-kit will never store a key in the repository.
  3. ollama      a local model. Nothing leaves the machine. Measured at ~3.4s
                 per call on a 12B model, so commits get noticeably slower.
  4. openai-compatible
                 any endpoint that speaks the OpenAI chat API -- LM Studio,
                 vLLM, a self-hosted gateway. Nothing leaves the machine when
                 the endpoint is local.

Any backend that is unavailable degrades to declarative-only and never blocks a
commit.
```

Then ask: `Judge backend? [1] host  [2] openrouter  [3] ollama  [4] openai-compatible  [5] turn the LLM pass off (1)`

Apply the answer with the kit's own command — do **not** hand-write the JSON, because the command validates what it wrote and refuses an incomplete choice. Resolve the plugin path first if it is not already in scope from step 1a:

```bash
ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1)
```

- **host** — you know which client you are running in, because you are reading this client's copy of this skill. Pass that id:
  ```bash
  "$ADR_KIT/bin/adr-judge" --adr-dir docs/adr --set-backend host --host-client claude-code-cli
  ```
  Each client's copy of this skill names its own id: this one is `claude-code-cli`. The judge cannot work this out at commit time — a `git commit` happens whether or not any agent is running — which is why it is recorded now, into the gitignored `docs/adr/.adr-kit.local.json`, while it is known with certainty.
- **openrouter** — ask for a `provider/model` slug (e.g. `anthropic/claude-sonnet-4.5`), then:
  ```bash
  "$ADR_KIT/bin/adr-judge" --adr-dir docs/adr --set-backend openrouter --model <slug>
  ```
  **Never ask the user for their API key and never write one anywhere.** `docs/adr/.adr-kit.json` is committed, so a key written there is a published key; the judge refuses one outright. Tell the user to export `OPENROUTER_API_KEY` in their own shell profile.
- **ollama** — run `ollama list` and offer the tags it actually reports; a tag that is not pulled fails on first use. Then:
  ```bash
  "$ADR_KIT/bin/adr-judge" --adr-dir docs/adr --set-backend ollama --model <tag>
  ```
- **openai-compatible** — ask for the base URL and the model the endpoint serves. LM Studio's default is `http://127.0.0.1:1234/v1`; its model list is on its Developer tab. Then:
  ```bash
  "$ADR_KIT/bin/adr-judge" --adr-dir docs/adr --set-backend openai-compatible     --base-url http://127.0.0.1:1234/v1 --model <model the endpoint serves>
  ```
  The two values land in different files on purpose: which model judges is a team decision and goes into the committed `docs/adr/.adr-kit.json`, while the base URL is a fact about this machine and goes into the gitignored local file. The command refuses an incomplete choice rather than writing a config the judge would then silently degrade on. If the endpoint needs a key, tell the user to export `ADR_KIT_OPENAI_API_KEY` in their own shell profile — never write one anywhere.
- **off** — merge `{"judge": {"llm_enabled": false}}` into `docs/adr/.adr-kit.json`. Say plainly that the declarative gate still runs and that `/adr-kit:judge` still gives LLM review on demand.

Ignore the local file in version control (idempotent):

```bash
grep -q "\.adr-kit\.local\.json" .gitignore 2>/dev/null || echo "docs/adr/.adr-kit.local.json" >> .gitignore
```

Then ask one more question (default No): `Enable per-commit ADR-suggest nudges (a second model call per commit, advisory only)? (y/N)` and merge `{"suggest": {"enabled": <true|false>}}`.

Confirm by showing the resolved configuration rather than by asserting it:

```bash
"$ADR_KIT/bin/adr-judge" --adr-dir docs/adr --show-config
```

Print the final one-liner: `Pre-commit ADR judge installed (declarative gate always-on; LLM pass on <backend>). Disable a single commit with ADR_KIT_HOOK_DISABLE=1 git commit ...; skip the LLM pass for one commit with ADR_KIT_NO_LLM=1 git commit ...; change the backend later with /adr-kit:judge settings; remove permanently with /adr-kit:install-hooks --uninstall.`

## Step 5 — Final lint

Run the kit's lint binary on the freshly populated ADR directory:

```bash
$ADR_KIT/bin/adr-lint docs/adr/
```

Report the result: `<N PASS, M ADVISORY, K FAIL>`. If any FAIL: list them with the gate name and ask the user whether to fix now (re-invoke `adr-generator` for the offending ADR) or defer to a follow-up.

## Step 5b — Guardian setup (new in v0.18.0)

After the hook and LLM opt-in are configured, offer the ADR Guardian.

Print this notice:

```
[adr-guardian] The ADR Guardian is a SessionStart staleness detector (v0.18.0).
It checks ADR health at session start and nudges when a sweep is due:
  - cheap tier (drift + retire + lint): daily, free
  - LLM tier   (suggest + audit):      bi-weekly, asks before spending (~$0.10–0.30)
Two registration paths:
  A. Plugin-level (default, recommended): auto-registers when the adr-kit plugin is enabled.
     The guardian self-guards (no-ops silently in non-ADR projects).
  B. Project-scoped: adds a SessionStart entry to .claude/settings.json (explicit, contained).
```

Ask two questions (default A/No):

1. `Enable guardian? (Y/n)` — Write `{"guardian": {"enabled": true}}` into `docs/adr/.adr-kit.json` (merge if present). If No: write `{"guardian": {"enabled": false}}` and skip the rest of this step.
2. `Register project-scoped SessionStart hook in .claude/settings.json? (y/N)` — If yes, follow the instructions in `skills/install-hooks/SKILL.md` under "Adding the project-scoped guardian hook". If no, remind the user the plugin-level hook is used by default.

Add `.adr-kit-state.json` to the project's `.gitignore` (idempotent):

```bash
grep -q "\.adr-kit-state\.json" .gitignore 2>/dev/null || echo "docs/adr/.adr-kit-state.json" >> .gitignore
```

Confirm: `[adr-guardian] enabled (<path>); state file gitignored.`

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
- llm:      backend <host|openrouter|ollama|off>, suggest <enabled|disabled>
- guardian: <enabled|disabled> (plugin-level | project-scoped | disabled)
- lint:     <P> PASS, <A> ADVISORY, <F> FAIL
- scripts:  generated | skipped (user declined)
```

Suggest a first commit: `git add docs/adr/ .claude/adr-kit-guide.md CLAUDE.md .githooks/pre-commit && git commit -m "chore(adr-kit): bootstrap v0.12"`. Do not run the commit yourself; let the user inspect first.

## Constraints

- **Do not skip steps.** Each step has an idempotency story; running them in order produces a consistent project state.
- **Batch selection, individual gates.** Do not silently mass-generate or
  accept ADRs. Five to ten candidates may be triaged per round; the user
  approves a batch, and every record still passes its own acceptance gates on
  its own through `bin/adr accept --auto`. A record the user has not seen is
  never accepted, and a record that fails a gate is never accepted regardless
  of what the batch answer was.
- **Reconstruction is documentation, not authorisation.** Init records
  decisions the code already implements, which is why `--auto` exists and why
  it demands `documents_shipped: true` and a `verified_in` pointer before it
  will run. A decision that is *not* already shipped is a new decision: it goes
  through `/adr-kit:grill` and ordinary acceptance, never `--auto`.
- **Resolve the plugin path dynamically.** The kit lives at `~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/<version>/`. Use the `ls | sort -V | tail -1` resolver above; do not hardcode a version.
- **Preserve user CLAUDE.md content.** Only the marked stub block (or a v0.11-style `## ADR Kit Rules` section being replaced) may be modified. Everything else stays byte-exact.
- **Re-runnable.** A second invocation on a project where init already succeeded should detect the existing footprint and either skip or refresh, not regenerate.
