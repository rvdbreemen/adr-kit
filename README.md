# adr-kit

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/tag/rvdbreemen/adr-kit?label=release&sort=semver)](https://github.com/rvdbreemen/adr-kit/releases)

A complete Architecture Decision Record (ADR) toolkit for AI coding agents. Drop into any project to give Claude Code, Claude Cowork, Cursor, GitHub Copilot, OpenAI Codex CLI, or any agent that supports the [Agent Skills](https://agentskills.io/) format a shared, enforceable ADR workflow.

> **Pre-1.0**: the toolkit is functional and in use, but the API and conventions may change before v1.0.0. Pin to a specific tag if you need stability across upgrades. Latest release: see the badge above.

## What it does

Five coordinated operating modes, since v0.18.0:

- **Init** (`/adr-kit:init`, since v0.12.0): one-shot project bootstrap. Hooks the kit into `CLAUDE.md` (slim stub + canonical guide at `.claude/adr-kit-guide.md`), runs `bin/adr-audit` to enumerate decision-shaped artefacts in source + documentation, walks the user through batched approval to generate `Accepted` ADRs, and installs the pre-commit hook. Use once per project.
- **Per-commit verification** (`bin/adr-judge` + pre-commit hook, since v0.12.0): every `git commit` runs declarative `Enforcement` rules from each Accepted ADR against the staged diff. Fast, deterministic, key-free. Default-on after init.
- **On-demand** (`/adr-kit:adr`, `/adr-kit:judge`, since v0.12.0 for judge): author a new ADR mid-session, or interactively review a staged diff against existing ADRs (declarative + in-session LLM review for `llm_judge: true` ADRs).
- **Observability** (`bin/adr-status`, `bin/adr-quality`, `bin/adr-context`, since v0.14.0): repository-wide health dashboard, per-ADR quality scoring (A–D grade), and semantic ADR ranking for task context.
- **Guardian** (`bin/adr-guardian` + `/adr-kit:guardian`, v0.18.0+): periodic ADR-set health detector. Fires at Claude Code SessionStart when a health tier is due. Cheap tier daily (drift + retire + lint, free); LLM tier bi-weekly (suggest + audit, asks before spending). Mix-by-finding-type in-session responses. No background processes.

### Components

- **Skill** (`skills/adr/SKILL.md`): the comprehensive ADR guide. Anti-rationalization guards, the four verification gates (Completeness, Evidence, Clarity, Consistency), supersession workflow.
- **Agent** (`agents/adr-generator.md`): the subagent for *creating* a new ADR. Includes a decision tree ("when do I need an ADR?"), proposes an `## Enforcement` block when the ADR has a code surface, and runs a post-decision quality check.
- **Init skill** (`/adr-kit:init`, v0.12.0+): umbrella project bootstrap (audit + ADR generation + hook install). Checks for Python 3.9+ and guides installation if absent.
- **Judge runner** (`bin/adr-judge`, v0.12.0+): declarative diff-vs-ADR engine. Parses fenced JSON `## Enforcement` blocks; applies `forbid_pattern` / `forbid_import` / `require_pattern` rules to the staged diff with file:line citations. `--profile` for timing, `--dry-run-enforcement ADR-NNN` for single-ADR testing.
- **Judge skill** (`/adr-kit:judge`, v0.12.0+): on-demand interactive judge. Runs `bin/adr-judge --llm` for `llm_judge: true` ADRs in-session. LLM judging at commit time is opt-in (see `judge.llm_enabled`); `/adr-kit:judge` always fires the LLM pass regardless of that config.
- **Suggestion runner** (`bin/adr-suggest`, v0.16.0+): the **advisory** counterpart to the judge. Where `adr-judge` *enforces* existing ADRs and can block a commit, `adr-suggest` runs one LLM pass over the staged diff to detect whether the change introduces a *new* architectural / contract / dependency decision **not yet covered by any ADR**, then prints a one-line nudge to run `/adr-kit:adr`. It is wired into the pre-commit hook (since v0.16.0) and **never blocks the commit** — a missing `claude` CLI, a timeout, a malformed response, or "no decision detected" all resolve to a silent skip and exit 0. Opt-in as of v0.17.0: enable per-project via `suggest.enabled: true` in `.adr-kit.json`, or per-commit with `ADR_KIT_SUGGEST=1`.
- **Audit runner** (`bin/adr-audit`, v0.12.0+): deterministic candidate scanner used by init.
- **Hook installer** (`/adr-kit:install-hooks`, v0.12.0+): installs/uninstalls the pre-commit hook. Default-on after init or upgrade.
- **Upgrade skill** (`/adr-kit:upgrade`, v0.12.0+): guided v0.11 → v0.12 migration without re-running the heavy audit.
- **Lint skill + CLI** (`/adr-kit:lint`, `bin/adr-lint`, since v0.7.0 / v0.10.0): validates ADR file content against the four gates. Policy gate (`--gates policy`) validates Enforcement JSON schema and regex safety. Quality gate (`--gates quality`) detects vague language and missing evidence.
- **Retirement audit** (`/adr-kit:retire`, `bin/adr-retire`, v0.14.0+): ranks review candidates using four deterministic signals without changing ADRs.
- **Health dashboard** (`bin/adr-status`, v0.14.0+): repository-wide ADR statistics — total count, status breakdown, average age, enforcement health, retirement candidates. Outputs JSON, Markdown, or table.
- **Quality scorer** (`bin/adr-quality`, v0.14.0+): grades each ADR A–D via four weighted gates (Completeness 40%, Evidence 20%, Clarity 20%, Consistency 20%). Returns structured JSON with per-gate issue codes. Exits 1 when grade < B.
- **Context ranker** (`bin/adr-context`, v0.14.0+): ranks ADRs by relevance to a task query using five weighted heuristic signals (keyword match, domain tag, related decisions, acceptance status, recency). Used by the agent to inject relevant context before authoring.
- **Script generator** (`bin/adr-generate-scripts`, v0.14.0+): produces standalone `validate.py` and `validate.sh` scripts from ADR Enforcement blocks. Scripts run without adr-kit as a dependency — embed in any CI pipeline.
- **Migrate skill** (`/adr-kit:migrate`, since v0.11.0): guided rewrite of legacy-shaped ADRs into the canonical seven-section template.
- **Setup skill** (`/adr-kit:setup`, since v0.4.0; rewritten in v0.12.0): lighter cousin of `init`. Drops the canonical guide and writes the slim CLAUDE.md stub.
- **Instructions** (`instructions/`): per-developer rules (`adr.coding.md`) and the seven-check code-review checklist (`adr.review.md`).
- **Templates** (`templates/`, v0.12.0+): canonical project-side guide (`adr-kit-guide.md`), ADR template with optional Enforcement section (`adr-template.md`), pre-commit hook template (`githooks/pre-commit`), and standalone validation script templates.

The pieces work together: `init` bootstraps the project, the hook + `bin/adr-judge` guard every commit deterministically, `/adr-kit:judge` handles in-session LLM review on demand, the agent + `/adr-kit:adr` author new ADRs, `bin/adr-quality` grades them, `bin/adr-status` shows the health of the whole repository, and `lint` and `migrate` keep the existing record clean.

## Why ADRs

Architecture Decision Records are short markdown files that capture *why* a system is built the way it is: the problem, the chosen solution, the alternatives that were rejected, the consequences accepted. They live in the repo (`docs/adr/`) alongside the code they describe.

ADRs are the antidote to "why does this exist?" archaeology three years after the fact. They are also the antidote to silent architectural drift: when the next change conflicts with a documented ADR, the conflict surfaces in code review instead of in a postmortem.

This toolkit adds two patterns to the basic ADR tradition:

- **Anti-rationalization guards**: a table of excuses agents (and humans) use to skip writing an ADR ("it's obvious", "I'll do it later", "the code speaks for itself"), with counter-arguments. Pre-flight discipline.
- **Verification gates**: four named gates an ADR must pass before its Status can flip from `Proposed` to `Accepted`. Reviewer can block on a single named gate ("this fails the Evidence gate, please add measurements").

## Install

### Claude Code (recommended): four slash commands

```
/plugin marketplace add rvdbreemen/adr-kit
/plugin install adr-kit@rvdbreemen-adr-kit
/reload-plugins
/adr-kit:init
```

The first three install the plugin: marketplace registration, plugin install, plugin reload. The fourth is the one-shot per-project bootstrap (since v0.12.0): it hooks `CLAUDE.md` (slim stub + canonical guide at `.claude/adr-kit-guide.md`), runs `bin/adr-audit` to enumerate decision-shaped artefacts in your source and docs, walks you through batched approval to generate `Accepted` ADRs for decisions already in effect, and installs the pre-commit hook. Idempotent on re-run.

If your project already had a v0.11 footprint (inline `## ADR Kit Rules` in `CLAUDE.md`, no Enforcement blocks, no hook), use `/adr-kit:upgrade` instead of `/adr-kit:init`. Upgrade skips the heavy audit and just migrates the layout + offers Enforcement-block backfill ADR-by-ADR.

For a lighter touch (no audit, no hook): `/adr-kit:setup` writes only the CLAUDE.md stub + canonical guide, leaving everything else for you to wire up later.

Optional follow-ups:
- `/adr-kit:lint [path]` — validate existing ADRs against the four gates.
- `/adr-kit:judge` — interactively review a staged diff against existing ADRs (handles both declarative `Enforcement` rules and `llm_judge: true` ADRs in-session).
- `/adr-kit:migrate [path]` — rewrite legacy-shaped ADRs into the canonical template.

Claude Cowork shares the `.claude/` convention; the same plugin commands work once your workspace is connected to a repo.

### Other AI coding tools: copy the files

For Cursor, GitHub Copilot, OpenAI Codex CLI, and any other agent that reads skills from its own directory layout, see [INSTALL.md](INSTALL.md). It documents the per-tool target paths and includes a one-shot install script that lays everything down in one command.

## File map

```
adr-kit/
├── README.md                       # this file
├── LICENSE                         # MIT
├── INSTALL.md                      # per-tool install (manual route)
├── .claude-plugin/
│   ├── plugin.json                 # Claude Code plugin manifest (hooks: SessionStart guardian, v0.18+)
│   ├── marketplace.json            # marketplace listing
│   └── hooks/
│       ├── hooks.json              # SessionStart hook declaration (v0.18+)
│       ├── run-hook.cmd            # cross-platform polyglot runner (v0.18+)
│       └── session-start           # bash hook script invoking bin/adr-guardian check (v0.18+)
├── skills/
│   ├── adr/SKILL.md                # the comprehensive ADR guide
│   ├── init/SKILL.md               # /adr-kit:init: one-shot project bootstrap (v0.12+)
│   ├── judge/SKILL.md              # /adr-kit:judge: in-session diff review (v0.12+)
│   ├── install-hooks/SKILL.md      # /adr-kit:install-hooks: pre-commit hook installer (v0.12+)
│   ├── upgrade/SKILL.md            # /adr-kit:upgrade: v0.11 -> v0.12 migration (v0.12+)
│   ├── setup/SKILL.md              # /adr-kit:setup: lighter CLAUDE.md+guide hookup
│   ├── lint/SKILL.md               # /adr-kit:lint: validates ADRs against the four gates
│   ├── migrate/SKILL.md            # /adr-kit:migrate: rewrite legacy ADRs into canonical
│   ├── retire/SKILL.md             # /adr-kit:retire: rank retirement candidates (v0.14+)
│   └── guardian/SKILL.md           # /adr-kit:guardian: ADR-set health sweep (v0.18+)
├── agents/
│   └── adr-generator.md            # subagent: create a new ADR (proposes Enforcement blocks v0.12+)
├── bin/
│   ├── adr-lint                    # deterministic gate validator (policy + quality gates v0.14+)
│   ├── adr-judge                   # diff vs Enforcement-block runner (v0.12+)
│   ├── adr-suggest                 # advisory: detect a new decision needing an ADR (v0.16+)
│   ├── adr-audit                   # candidate scanner used by init (v0.12+)
│   ├── adr-retire                  # retirement-candidate audit (v0.14+)
│   ├── adr-status                  # repository health dashboard (v0.14+)
│   ├── adr-quality                 # per-ADR quality scorer, grade A-D (v0.14+)
│   ├── adr-context                 # semantic ADR relevance ranker (v0.14+)
│   ├── adr-generate-scripts        # standalone validate.py / validate.sh generator (v0.14+)
│   └── adr-guardian                # ADR-set staleness detector: check/stamp/state (v0.18+)
├── templates/
│   ├── adr-template.md             # ADR template with optional Enforcement section (v0.12+)
│   ├── adr-kit-guide.md            # canonical project-side guide; copied to .claude/ (v0.12+)
│   ├── githooks/pre-commit         # pre-commit hook template (v0.12+)
│   ├── validate_adr_template.py    # reference template for generated Python validator (v0.14+)
│   ├── validate_adr_template.sh    # reference template for generated shell validator (v0.14+)
│   └── cc-settings/
│       └── guardian-hook-entry.json # project-scoped SessionStart hook JSON fragment (v0.18+)
├── schemas/
│   ├── adr-kit-config.schema.json  # .adr-kit.json schema (judge.* v0.12+, suggest.* v0.16+, guardian.* v0.18+)
│   └── adr-enforcement.schema.json # ADR Enforcement block schema (v0.12+)
├── instructions/
│   ├── adr.coding.md               # ADR rules during coding
│   └── adr.review.md               # ADR checks during PR review (seven checks since v0.12)
├── tests/                          # pytest end-to-end tests for adr-lint, adr-judge, adr-audit
└── examples/
    └── ADR-template.md             # legacy template (kept for backwards compat; new template is in templates/)
```

## Slash commands reference

After `/plugin install adr-kit@rvdbreemen-adr-kit` + `/reload-plugins`, your Claude Code session exposes the commands below. `/adr` and `/adr-kit:adr` invoke the same skill; the others are independent.

| Command | Type | Auto-invocable | When to use |
|---|---|---|---|
| `/adr [title]` | knowledge / guide | yes | Author or review an ADR. Loads the comprehensive ADR guide (anti-rationalization guards, four verification gates, supersession workflow). Same skill as `/adr-kit:adr`. |
| `/adr-kit:adr [title]` | knowledge / guide | yes | Identical to `/adr`. The prefix form is canonical; the root form is a shortcut Claude Code exposes when a skill allows model-invocation. Use whichever fits your typing. |
| `/adr-kit:setup` | one-time write | no | Run once per project after install. Appends an "ADR Kit Rules" section to your project's `CLAUDE.md` so future sessions know about the skill, the agent, and the path-specific instructions. Idempotent: re-running reports "Already set up" rather than duplicating. |
| `/adr-kit:lint [path]` | deliberate check | no | Validate existing ADRs against the four gates with file:line citations. Reads `docs/adr/.adr-kit.json` if present. Default target is `docs/adr/`; pass a directory or file as argument to scope. Read-only. Three result tiers: PASS, ADVISORY (informational), FAIL (action required). |
| `/adr-kit:migrate [path]` | guided rewrite | no | Bring a legacy-shaped ADR into the canonical-seven-section template. Read-then-confirm: prints a per-file plan first, applies after explicit yes. Six named patterns (Status promotion, Alternatives lift, Related-to-Related-Decisions split, TODO placeholders for genuine content gaps). Default target is `docs/adr/`. |
| `/adr-kit:retire [path]` | deliberate check | no | Rank Accepted ADRs for possible retirement using deterministic status-age, technology-removal, supersession, and policy signals. Read-only. |

### Auto-invocable vs user-only

- **Auto-invocable** (`/adr`, `/adr-kit:adr`): Claude can also load this skill in the background when context calls for it (e.g. you ask "should I document this decision?"). The skill body activates without you typing the slash command. Knowledge / reference skills sit here.
- **User-only** (`/adr-kit:setup`, `/adr-kit:lint`, `/adr-kit:migrate`, `/adr-kit:retire`): only fires when you explicitly type the slash command. Set via `disable-model-invocation: true` in the skill frontmatter. Write actions and deliberate checks sit here so Claude does not surprise you by triggering them.

This is a deliberate design pattern. Knowledge skills should be cheap to auto-trigger; write-and-check skills should be costly enough that you have to ask.

### Companion CLI: `bin/adr-lint`

`/adr-kit:lint` runs in your Claude Code session. For unattended use (CI / pre-commit / batch validation) the toolkit ships a deterministic Python CLI at `bin/adr-lint`. Same gate logic, exit-code-based, runs anywhere with Python 3.8+. See the [CI integration section](#ci-integration-binadr-lint-since-v0100) below for a copy-paste GitHub Actions snippet.

The CLI defaults to the deterministic gates (Completeness, Consistency); the heuristic gates (Evidence, Clarity) are opt-in via `--gates` because they need judgement that a regex cannot reliably provide. That judgement is where the slash-command form remains canonical.

## Quickstart

Once installed in your project:

1. **First time setup**: run `/adr-kit:setup` to wire the rules into your project's `CLAUDE.md`.
2. **First-time analysis**: ask your agent to "analyze this codebase for undocumented architectural decisions". Use the workflow in `SKILL.md` (Initial Codebase Analysis section) to retroactively document existing patterns at `Status: Accepted`.
3. **For new work**: when about to make an architecturally significant change, the coding instructions (`adr.coding.md`) point at the agent. The agent (`agents/adr-generator.md`) writes the ADR. The verification gates from the skill validate it. You can also invoke `/adr <short title>` directly.
4. **In code review**: the review instructions (`adr.review.md`) walk through six named checks. The reviewer cites a check by name when blocking a PR.
5. **Audit existing ADRs**: `/adr-kit:lint` runs the four verification gates over every ADR in `docs/adr/` and reports per-file, per-gate pass/fail. Useful right after install and before merging ADR-touching PRs.
6. **Bring legacy ADRs into shape**: `/adr-kit:migrate` rewrites legacy-shaped ADRs into the canonical-seven-section template, read-then-confirm. Pair with `/adr-kit:lint` afterwards to verify the result.

## ADR conventions

The toolkit defaults to:

- **Filename**: `ADR-XXX-kebab-case-title.md` with uppercase prefix and 3-digit zero-padded number, stored in `docs/adr/`.
- **Heading**: `# ADR-XXX Title`.
- **Sections** in order: Status, Context, Decision, Alternatives Considered, Consequences, Related Decisions, References.
- **Status values**: `Proposed`, `Accepted`, `Deprecated`, `Superseded by ADR-YYY`, `Amended by ADR-YYY`.
- **Date format**: `YYYY-MM-DD`.

### Status history (v0.14.0+)

New ADRs include an append-only `## Status History` YAML block. Each transition
records `date`, `status`, `changed_by`, `reason`, and `changed_via`.
`bin/adr-lint` checks a present history with its deterministic `audit` gate,
including chronological dates and agreement with `## Status`.

```yaml
status_history:
  - date: 2026-05-26
    status: Proposed
    changed_by: author@example.com
    reason: Initial proposal
    changed_via: adr-kit v0.14.0
```

Existing v0.13 ADRs remain readable without modification. To deliberately add
an initial history entry to legacy ADRs, run:

```bash
python bin/adr-judge --adr-dir docs/adr --migrate-status-history
```

Migration is explicit because ordinary pre-commit judging must remain
read-only and must not introduce unstaged edits while evaluating a staged diff.

You can change the convention if your project already has a different one (some teams use `adr-NNNN-` lowercase 4-digit, or `0001-` with no prefix). Edit the `## Project Conventions` section in the skill and the agent definition; the rest of the toolkit follows from there.

## Configuration (since v0.9.0)

Established projects often have a long history of ADRs that predate the four canonical gates. Linting them under strict rules produces noise rather than actionable feedback. Two opt-in mechanisms let a project apply the gates surgically: strict on new ADRs, advisory on legacy ones.

### Project-level config: `docs/adr/.adr-kit.json`

Drop this file at `docs/adr/.adr-kit.json` to set the project's lint policy. Skipped if absent (defaults: everything strict, exact match to v0.7.x output).

```json
{
  "strict_from": "ADR-042",
  "ignore": ["ADR-001", "ADR-007"],
  "severity": {
    "completeness": "advisory_before_strict_from",
    "audit": "always_strict",
    "evidence": "advisory_before_strict_from",
    "clarity": "always_advisory",
    "consistency": "always_strict"
  },
  "template": {
    "required_sections": ["## Status", "## Context", "## Decision", "## Consequences"]
  }
}
```

- `strict_from` is the first ADR id (inclusive) on which the gates are enforced strictly. ADRs with a lower number are linted in advisory mode.
- `ignore` lists ADR ids (or filenames) to skip entirely.
- `severity` overrides the per-gate behaviour. Legal values: `always_strict`, `always_advisory`, `advisory_before_strict_from`. Audit and consistency stay strict by default because invalid status chains, filename / heading mismatches, and duplicate numbers are real bugs regardless of when the ADR was written.
- `template.required_sections` overrides the canonical seven sections with your project's actual template.

A fully annotated copy lives at [`examples/.adr-kit.sample.json`](examples/.adr-kit.sample.json).

### Per-commit LLM judging: `judge.llm_enabled` (opt-in since v0.17.0)

The pre-commit hook always runs the **declarative** Enforcement gate (fast, free, no LLM). The **LLM pass** — which evaluates `llm_judge: true` ADRs via Claude Sonnet — is opt-in as of v0.17.0. Previously the hook hard-coded `--llm`; that was changed to reduce surprise cost.

Enable per-project:

```json
{
  "judge": {
    "llm_enabled": true
  }
}
```

Enable for a single commit: `ADR_KIT_LLM=1 git commit ...`
Disable for a single commit: `ADR_KIT_NO_LLM=1 git commit ...`

- `judge.llm_enabled` (default `false` since v0.17.0): user-facing master switch for the per-commit LLM pass.
- `judge.llm_default` (legacy, kept for CI back-compat): equivalent alternative to `llm_enabled`; prefer `llm_enabled` for the per-commit hook.
- `judge.llm_model` (default `claude-sonnet-4-6`): switch to `claude-haiku-4-5` for higher throughput at lower cost.
- `judge.llm_timeout_seconds` (default `120`): per-call timeout.

**Concurrency guard (v0.17.0):** the hook uses `flock` (when available) to serialize the LLM passes across parallel commits. Under lock contention the cheap declarative gate still runs; the LLM passes are suppressed for that commit rather than piling up concurrent `claude -p` calls.

LLM review is always available on demand regardless of config: `/adr-kit:judge` in a Claude Code session always runs the full LLM pass.

### Advisory ADR-suggestion: `suggest.*` (since v0.16.0)

The pre-commit hook can also run `bin/adr-suggest` — the **advisory** counterpart to `adr-judge`. It runs one LLM pass over the staged diff to detect whether the change introduces a *new* architectural / contract / dependency decision not yet covered by any ADR, then prints a one-line nudge to run `/adr-kit:adr`. It **never blocks the commit**: missing CLI, timeout, malformed response, or "no decision" all resolve to a silent skip and exit 0.

As of v0.17.0 the suggest pass is **opt-in** (default off). Enable it per-project or per-commit:

```json
{
  "suggest": {
    "enabled": true,
    "llm_model": "claude-sonnet-4-6",
    "llm_timeout_seconds": 120
  }
}
```

- `suggest.enabled` (default `false` since v0.17.0): set `true` to enable the suggestion pass project-wide, or use `ADR_KIT_SUGGEST=1` for a single commit.
- `suggest.llm_cmd` / `suggest.llm_model`: override the model for the suggestion pass. Both fall back to the `judge.*` equivalents when absent, so a project that already configured the judge LLM gets the same model for suggestions for free. Repo-tracked `llm_cmd` binaries are validated against the same Claude-CLI allowlist as `judge.llm_cmd`.
- `suggest.llm_timeout_seconds` (default `120`): per-call timeout; falls back to `judge.llm_timeout_seconds`.

Enable for a single commit: `ADR_KIT_SUGGEST=1 git commit ...`.

### ADR Guardian: periodic health detection (v0.18.0+)

The ADR Guardian is a SessionStart staleness detector that nudges the in-session model when an ADR health tier is due. It has no background processes, never runs an LLM in the hook, and always exits 0. The heavy sweep runs in-session via `/adr-kit:guardian`.

**Two-tier cadence:**

| Tier | Default | Tools | Cost |
|---|---|---|---|
| cheap | Daily (`drift_stale_days: 1`) | `adr-judge` (declarative drift), `adr-retire`, `adr-lint`/`adr-status` | Free |
| llm | Bi-weekly (`llm_stale_days: 14`) | `adr-suggest` (missing-ADR), `adr-judge --llm` (full audit) | ~$0.10–0.30 |

When a tier is due, `bin/adr-guardian check` emits an `[adr-guardian] ... DUE` block as `additionalContext` into the Claude Code session. The in-session model sees it and offers to run `/adr-kit:guardian`.

**Hook install paths:**

- **Plugin-level (default, frictionless):** the adr-kit plugin declares the `SessionStart` hook in `.claude-plugin/plugin.json`. It auto-registers when the plugin is enabled globally. The `bin/adr-guardian check` binary self-guards: it no-ops silently unless the current directory has `docs/adr/` with ADRs.
- **Project-scoped (explicit):** `/adr-kit:install-hooks` can add/remove the guardian hook entry from the project's `.claude/settings.json` using JSON-structural editing (never clobbers sibling hooks).

**Config block** in `docs/adr/.adr-kit.json`:

```json
{
  "guardian": {
    "enabled": true,
    "drift_stale_days": 1,
    "llm_stale_days": 14,
    "nudge_cooldown_hours": 24,
    "llm_autorun": false
  }
}
```

- `enabled` (default `true`): set `false` to disable all guardian nudges.
- `drift_stale_days` (default `1`): cheap tier cadence in days.
- `llm_stale_days` (default `14`): LLM tier cadence in days.
- `nudge_cooldown_hours` (default `24`): minimum hours between successive nudges.
- `llm_autorun` (default `false`): set `true` to let the skill run the LLM tier without asking (not recommended for most projects — keeps the opt-in posture from ADR-001).

**State file:** `docs/adr/.adr-kit-state.json` (gitignored, per-machine). Added to `.gitignore` by `/adr-kit:init`.

**Team mode (v0.22.0+):** the guardian works at two levels that coexist. The SessionStart nudge is per-developer: each machine keeps its own gitignored state file (atomic writes, safe across parallel Claude Code sessions, last-writer-wins). For shared team visibility, copy `templates/github-workflows/adr-guardian-audit.yml` into your repo's `.github/workflows/`. It runs the free cheap tier only (lint + retire + status), maintains a single "ADR guardian audit" tracking issue, never fails the build, and never runs an LLM. The LLM tier stays local and opt-in (ADR-001).

**Mix-by-finding-type responses** (in-session, via `/adr-kit:guardian`):

| Finding | Response |
|---|---|
| Drift — code violates an Accepted ADR | Surface prominently. List violations with file:line + ADR id. Offer to fix or create a task. |
| Missing ADR — new decision not recorded | Passive. List candidates; offer to author via `adr-generator`. User picks. |
| Stale ADR — tech removed / superseded / policy drift | Draft retirement/supersession skeleton for review. Never auto-apply. |
| ADR-set health — gate failures, broken chains | Report PASS/ADVISORY/FAIL. Offer to fix FAILs via `adr-generator`. |

### Per-ADR markers

For one-off grandfathering without a project-wide config, drop one of these HTML comments anywhere in an ADR file:

```html
<!-- adr-kit-lint: skip -->
<!-- adr-kit-lint: skip completeness, evidence -->
<!-- adr-kit-lint: advisory -->
```

`skip` (no args) skips the file entirely; `skip <gate>[, <gate>...]` skips specific gates; `advisory` runs all gates in advisory mode on this file. A worked example lives at [`examples/ADR-sample-003-grandfathered-legacy.md`](examples/ADR-sample-003-grandfathered-legacy.md).

### Result tiers

`/adr-kit:lint` now reports three tiers: PASS, ADVISORY (a finding that does not block but is reported), and FAIL. The aggregate's "next step" line always points at a FAIL, never an ADVISORY: ADVISORY is informational, FAIL is what you act on.

## CI integration: `bin/adr-lint` (since v0.10.0)

The `/adr-kit:lint` skill is for human-in-the-loop review (judgement-based gates rely on Claude). For CI / pre-commit / batch validation, v0.10.0 ships a deterministic Python CLI at `bin/adr-lint`. It runs Completeness, Audit, and Consistency by default; Evidence and Clarity remain available behind `--gates`. It reads the same `.adr-kit.json` policy and exits with a status code that makes blocking a PR trivial.

### Quick start

```bash
# Lint your project's ADRs (default: docs/adr/, gates: completeness,audit,consistency)
python bin/adr-lint

# Limit to one gate, JSON output for tooling
python bin/adr-lint --gates completeness --format json

# Override the strict_from boundary on the command line
python bin/adr-lint --strict-from ADR-100

# Lint a different directory or a single file
python bin/adr-lint docs/decisions/
python bin/adr-lint docs/adr/ADR-042-foo.md
```

Exit codes: `0` = no FAIL (PASS / ADVISORY counts may be non-zero), `1` = at least one FAIL, `2` = config or input error.

### Drop-in GitHub Actions snippet

Add this job to your `.github/workflows/<ci>.yml` to block PRs that introduce a FAIL:

```yaml
adr-lint:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: '3.11' }
    - name: Fetch adr-lint
      run: |
        curl -fsSL -o /tmp/adr-lint \
          https://raw.githubusercontent.com/rvdbreemen/adr-kit/main/bin/adr-lint
        chmod +x /tmp/adr-lint
    - name: Lint ADRs
      run: python /tmp/adr-lint docs/adr/
```

The script is stdlib-only, so no `pip install` is needed in CI. `jsonschema` is auto-detected if installed and used for deeper config validation; absence is non-fatal.

### Periodic retirement audit (v0.14.0+)

`bin/adr-retire` is a read-only ranked audit. It averages four signals and
reports `RETIRE` (score >= 0.8), `REVIEW` (>= 0.6), `MONITOR` (>= 0.4), or
`KEEP`. A recommendation still requires human review before an ADR is
superseded.

```bash
python bin/adr-retire docs/adr --repo-root . --threshold 0.4 --format markdown
```

The shipped `.github/workflows/adr-retire-audit.yml` demonstrates a weekly
Monday audit that opens an issue only when candidates meet the monitor
threshold.

### Help text

```
$ adr-lint --help
usage: adr-lint [-h] [--strict-from ADR-NNN] [--gates GATES]
                [--format {human,json}] [--config PATH] [-v] [--version]
                [path]

Deterministic CLI for the four adr-kit verification gates.

positional arguments:
  path                  File or directory to lint (default: docs/adr/)

options:
  --strict-from ADR-NNN
                        First ADR id (inclusive) on which gates are strict; overrides config.
  --gates GATES         Comma-separated gates to run. Default:
                        completeness,audit,consistency. All:
                        completeness,audit,evidence,clarity,consistency
  --format {human,json}
                        Output format (default: human)
  --config PATH         Override .adr-kit.json location.
  -v, --verbose         Show ADVISORY and SKIPPED details too
```

### When to use which

- `/adr-kit:lint` (skill, in Claude Code): nuanced review, all four gates, judgement on Evidence and Clarity.
- `bin/adr-lint` (CLI, in CI): deterministic completeness, status-history audit, and consistency checks by default; exit-code based and suitable as a PR merge gate.

The two are designed to agree on Completeness, Audit, and Consistency. They can disagree on Evidence and Clarity by design: Claude's judgement is structurally better at those.

## CI integration: `bin/adr-judge` (since v0.19.0)

`bin/adr-judge` enforces the Accepted ADRs' `## Enforcement` blocks against a diff.
In a PR workflow, pipe the full PR diff into it and block the merge on exit 1.

### Composite GitHub Action (recommended)

The toolkit ships a reusable composite action at `.github/actions/adr-judge/`.
Add it to a PR workflow in your project:

```yaml
# .github/workflows/adr-judge.yml
name: ADR enforcement

on:
  pull_request:
    branches: [main]

jobs:
  adr-judge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # required: both sides of the diff must be available
      - uses: rvdbreemen/adr-kit/.github/actions/adr-judge@v0.19.0
        with:
          adr-dir: docs/adr/   # adjust if your ADR directory differs
```

Declarative-only by default: no `--llm` flag, no secrets, no API key.
Exit codes: `0` = no violations, `1` = at least one Enforcement violation, `2` = config error.

### Opt-in LLM pass in CI (advanced)

The `--llm` pass (which evaluates `llm_judge: true` ADRs via Claude Sonnet) shells out
to the `claude` CLI. An `ANTHROPIC_API_KEY` environment variable alone is **not**
sufficient — the runner must have the `claude` CLI installed and authenticated.
The recommended setup is to install `claude` in a CI step and point `judge.llm_cmd`
at it in `docs/adr/.adr-kit.json`. This is an advanced, optional path; the declarative
pass is the supported and key-free default.

### Inline snippet (no action dependency)

If you prefer not to use the composite action, the same behaviour without the
action dependency:

```yaml
adr-judge:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with: { fetch-depth: 0 }
    - uses: actions/setup-python@v5
      with: { python-version: '3.11' }
    - name: Fetch adr-judge
      run: |
        curl -fsSL -o /tmp/adr-judge \
          https://raw.githubusercontent.com/rvdbreemen/adr-kit/main/bin/adr-judge
        chmod +x /tmp/adr-judge
    - name: Run adr-judge against PR diff
      run: |
        git fetch --no-tags origin "$GITHUB_BASE_REF"
        git diff --unified=0 "origin/${GITHUB_BASE_REF}...HEAD" \
          | python /tmp/adr-judge --diff - --adr-dir docs/adr/
```

### `pre-commit` framework support (v0.19.0+)

Teams using the [`pre-commit`](https://pre-commit.com) framework can register
`adr-judge` without writing a native git hook. Add this to your
`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/rvdbreemen/adr-kit
    rev: v0.19.0
    hooks:
      - id: adr-judge
```

The hook runs `git diff --cached --unified=0` internally via the
`bin/adr-judge-precommit` wrapper and pipes the result to `bin/adr-judge`.
Declarative-only (no LLM, no API key). Fails the commit on any Enforcement
violation; passes on a clean staging area.

Note: the `pre-commit` framework downloads and caches the hook repository.
The wrapper resolves the sibling `bin/adr-judge` via its own file path, so
it works regardless of PATH or how `pre-commit` places the files.

## MCP server: `bin/adr-mcp` (since v0.21.0)

A deliberately thin MCP server (stdio, newline-delimited JSON-RPC 2.0, Python stdlib only, zero dependencies) that exposes the adr-kit guardrails to any MCP client: Cursor, Cline, Windsurf, Copilot, or Claude Code itself. Four tools, all key-free (no LLM calls, no API keys):

| Tool | Arguments | Wraps |
| --- | --- | --- |
| `adr_context` | `query` (string), `limit?` (int) | `adr-context --format json` |
| `adr_judge` | `diff` (string) | `adr-judge --json` (declarative pass only) |
| `adr_status` | none | `adr-status --format json` |
| `adr_quality` | `adr_id?` (string) | `adr-quality --format json` per ADR |

The project root the tools operate on is resolved from `--root`, then the `PROJECT_ROOT` environment variable, then the server's working directory. ADRs are read from `<root>/docs/adr` unless `--adr-dir` says otherwise.

### Claude Code

```bash
claude mcp add adr-kit -- python /path/to/adr-kit/bin/adr-mcp --root "$(pwd)"
```

### Cursor / Cline / other stdio clients

Generic stdio configuration (`.cursor/mcp.json`, Cline MCP settings, etc.):

```json
{
  "mcpServers": {
    "adr-kit": {
      "command": "python",
      "args": ["/path/to/adr-kit/bin/adr-mcp", "--root", "/path/to/your/project"]
    }
  }
}
```

On Windows use `python` from your PATH or an absolute interpreter path; the server invokes its sibling `bin/` scripts with the same interpreter, so no shebang support is needed.

Why only 4 tools? Contrast is the feature: the 73-tool approach already exists elsewhere. adr-kit ships the smallest surface that carries the guardrails (context injection, enforcement, health, quality) and nothing that needs an API key.

## FAQ

**Where are ADRs stored?**

Under `docs/adr/` in your project, one file per decision, named `ADR-XXX-kebab-case-title.md`. The numbering is sequential and zero-padded to three digits. The skill assumes this layout but documents how to override it.

**How do I customize the conventions?**

Open `skills/adr/SKILL.md` (or the installed copy in your tool's skills directory) and edit the `## Project Conventions` section. The agent and the instructions read from that section, so a single edit propagates. Some teams prefer `adr-NNNN-` lowercase 4-digit; some prefer `0001-...` without a prefix; both work as long as you commit to one.

**What if my project already has ADRs in a different format?**

Two options. (1) Migrate the existing files to the adr-kit conventions in one pass; the most common change is the filename casing. (2) Override the conventions in `SKILL.md` to match what you have, so future ADRs use the same format. Migration is cleaner long-term; override is faster short-term.

**Does the skill auto-create ADRs without me asking?**

No. The main skill activates when you author or review ADRs, but it does not write files on its own. The `adr-generator` subagent writes a file only when you ask it to. The `setup` skill writes once to `CLAUDE.md` and only when you run `/adr-kit:setup`. All file mutations are user-triggered.

**Is this an Anthropic product?**

No. `adr-kit` is an independent open-source toolkit. It happens to install cleanest in Claude Code because Claude Code's plugin system is the most mature option for this kind of multi-file bundle, but the same files run in Cursor, Copilot, and Codex.

## Comparison

A plain ADR template gives you a markdown file with sections to fill in. `adr-kit` adds three things on top:

| Concern | Plain ADR template | adr-kit |
|---|---|---|
| Format | yes (one file) | yes (one file plus a generator agent) |
| Pre-flight discipline | absent | **anti-rationalization guards**: a 9-row excuse / counter-argument table that fires before you reach for "this is too obvious to document" |
| Acceptance bar | "fill it in" | **four named verification gates** (Completeness, Evidence, Clarity, Consistency) that must pass before Status flips from Proposed to Accepted |
| Code-review integration | absent | six named checks plus review-comment templates, ready to paste into a PR review |
| Tool integration | none | drop-in skill, agent, and instructions for Claude Code, Claude Cowork, Cursor, GitHub Copilot, OpenAI Codex CLI |
| Onboarding | "read this template" | one-time setup command that wires the rules into your project's `CLAUDE.md` |

The patterns themselves (anti-rationalization, verification gates) are not novel; both predate this toolkit. What `adr-kit` contributes is the **packaging**: a plug-and-play installation in any major AI coding tool, with the patterns wired into the place they need to be (the agent's pre-flight, the reviewer's checklist, the project's standing instructions).

If your team is happy with a plain template and the discipline lives in your culture, you do not need this toolkit. If you want the discipline to be enforceable by an AI agent reviewing a PR, this is what `adr-kit` does.

## Credits

Based on [Michael Nygard's ADR format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

The two distinguishing patterns of this toolkit, **anti-rationalization guards** and **verification gates**, were first combined into a single ADR skill by [Jim van den Breemen's adr-skill](https://github.com/Jvdbreemen/adr-skill). That combination is what turns a plain ADR template into a discipline tool: the guards catch the excuses *before* a decision goes undocumented, and the gates catch the gaps *before* a `Proposed` ADR flips to `Accepted`. Without that pairing, this toolkit would be a thicker template, not a workflow.

The original sources of the two patterns:

- Anti-rationalization guards: [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills).
- Verification gates: [trailofbits/skills](https://github.com/trailofbits/skills).

`adr-kit` builds on that combination by adding a focused creator agent (`adr-generator`), path-specific instructions for coding and review work, and per-tool install paths for Claude Code, Claude Cowork, Cursor, GitHub Copilot, and OpenAI Codex CLI.

## Project resources

- [ROADMAP.md](ROADMAP.md): direction, v1.0.0 criteria, deliberate non-goals.
- [MIGRATING-FROM-ADR-SKILL.md](MIGRATING-FROM-ADR-SKILL.md): switching from or co-installing alongside Jim van den Breemen's adr-skill.
- [CHANGELOG.md](CHANGELOG.md): release history in Keep a Changelog format.
- [CONTRIBUTING.md](CONTRIBUTING.md): dev loop, add-a-skill, version-bump, release procedure, code style.
- [SECURITY.md](SECURITY.md): security disclosure policy.
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md): community standards (Contributor Covenant 2.1 by reference).

## License

MIT. See [LICENSE](LICENSE).

## Contributing

Issues and PRs welcome. The skill is intentionally domain-agnostic; project-specific examples should stay in your own copy of `SKILL.md`, not upstream.
