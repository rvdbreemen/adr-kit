# Changelog

All notable changes to `adr-kit` are documented in this file. The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Layered ADR context injection (ADR-004).** A documented model for feeding ADR knowledge into agent work through three fail-open injection tiers plus the one fail-closed pre-commit floor, modeled on the OpenWolf inject/freshen/enforce loop. New surfaces:
  - **`bin/adr-index`** generates `docs/adr/ADR-INDEX.md`, a compact one-row-per-ADR map (id, status, scope, one-line decision) that `CLAUDE.md` `@`-imports so every session is ADR-aware at a fixed low token cost. Deterministic and timestamp-free; a new `adr-index-check` CI workflow diffs the committed index against a fresh regenerate. The init/setup stubs now include the `@docs/adr/ADR-INDEX.md` import.
  - **Edit-tier injector** (`bin/adr-watch --pre-edit`), wired as a `PreToolUse` hook for `Edit|MultiEdit|Write` in `.claude-plugin/plugin.json`. Before an edit it injects the single top-ranked governing Accepted ADR's `## Decision` text (bounded to `inject.max_tokens`, default 400) as `hookSpecificOutput.additionalContext`, so the agent honours the decision *as it writes* rather than after. Reuses the existing adr-watch matcher and a separate `inject` cooldown key in `.adr-kit-state.json`. Advisory only, always exits 0. New `inject` config block added to `schemas/adr-kit-config.schema.json`.
  - **`bin/adr-status` floor coverage buckets**: the summary now reports how many Accepted ADRs are covered by declarative rules vs. manual review (`{"llm_judge": false}`) vs. no Enforcement block, in text and markdown, so the deterministic floor's coverage is visible without false-positiving the documented manual-review pattern.
  - Canonical fields are pinned (scope = Enforcement `path_glob`; status = `## Status` reconciled with the latest `status_history` entry) and shared by all readers; a no-drift regression test locks `bin/adr-index`'s readers to `bin/adr-watch`'s. Covered by `tests/test_adr_index.py`, new `TestPreEditInject` cases in `tests/test_adr_watch.py`, and `TestFloorBuckets` in `tests/test_adr_status_coverage.py`.
- **Lint consistency gate now flags one-directional (dangling) supersession.** `bin/adr-lint`'s consistency gate already FAILed *concurrent* supersession (2+ Accepted ADRs claiming one target); it now also catches the single-claimant case where an Accepted ADR claims `Supersedes ADR-X` but the target's Status line does not name it back as successor. This is the common drift where the successor lands but the superseded ADR is never flipped, so it still reads as live and the audit trail is one-way. A claim against a target absent from the directory is deliberately left to the broken-reference detectors (`bin/adr-retire`) to avoid flagging prose mentions of unknown ADR numbers; clean bidirectional supersessions are unaffected. The finding flows through the normal consistency-gate severity policy, so projects can tune it via their severity config. Covered by three new tests in `tests/test_adr_lint_supersession.py`.

## [0.30.5] - 2026-06-14

### Fixed

- **Config schema rejected the `judge.*` performance-budget knobs (#10).** `schemas/adr-kit-config.schema.json` declares the `judge` object with `additionalProperties: false` but omitted the TASK-712 performance-bounded-hooks fields that adr-kit's own dogfood `.adr-kit.json` (and downstream projects) already set: `pre_commit_timeout_ms`, `pre_push_timeout_ms`, `llm_timeout_ms`, `warn_on_exceed`. Config validation therefore failed with `'pre_commit_timeout_ms' was unexpected` before any ADR was evaluated, including against this repo's own config. The four knobs are now declared as permissive, documented properties; the change is additive, so previously-valid configs stay valid.

## [0.30.4] - 2026-06-13

### Fixed

- **`bin/bump-version` now also stamps the guide template's version line.** `templates/adr-kit-guide.md` opens with `<!-- adr-kit-guide vX.Y.Z -->`, which `/adr-kit:upgrade` uses to decide whether a project's copied guide is fresh; the line had been frozen at v0.18.0 because no release step updated it, so the freshness check would have reported every guide as stale forever. Found by running `/adr-kit:upgrade` on this repo itself. Covered by a lockstep test (template line must equal `plugin.json` version) and a bump fixture test.

### Changed

- **This repo now carries its own adr-kit footprint** (dogfooding): `CLAUDE.md` stub and the pre-commit wrapper at `.githooks/pre-commit` with `core.hooksPath` set, so Enforcement violations are caught locally before CI. ADR-003 deliberately carries no Enforcement block (process decision, no code surface).

## [0.30.3] - 2026-06-13

### Fixed

- **markdownlint failure in `skills/install-hooks/SKILL.md` (MD029).** The JSON hook-entry example sat unindented inside an ordered list, splitting the list and failing the `validate` workflow on main. The block is now indented as a continuation of list item 4; numbering is valid again and CI is green.

## [0.30.2] - 2026-06-13

### Changed

- **README rewritten around the decision lifecycle (capture, guard, maintain).** The old README grew feature-by-feature across eleven releases and read as a changelog with a table of contents. The new structure leads with what the toolkit is for (architecture decisions that AI coding agents actually follow), puts the agentic install paths first (Claude Code four-command install up top; Codex CLI, Cursor, Copilot, Cowork and the MCP server right after), and makes the upgrade story explicit: plugin updates flow automatically, copied artifacts are stamp-checked by the guardian and refreshed by `/adr-kit:upgrade`, and existing MADR / Nygard ADR sets import via `/adr-kit:migrate`. All 14 skills and the CLI engines are described in terms of what they do for a software project rather than when they shipped. Reference detail that moved out of the README (full config keys, hook internals) lives on in the project guide, INSTALL.md, and the CHANGELOG. No behavioural changes.

## [0.30.1] - 2026-06-13

### Fixed

- **`bin/bump-version` rewritten in pure stdlib Python (was bash).** The bash version shelled out to `python3` for each file edit. On Windows the `python3` command resolves to the Microsoft Store alias, which routes through the Python Install Manager; that launcher scans argv for a script file and dispatches on THAT file's shebang. Step 4 passed the bash-shebanged `templates/githooks/pre-commit` as an argument, so the launcher warned `shebang 'bash' ... treated as an arbitrary command` and executed bash instead of python, which crashed with cygheap fork errors during the v0.27.0 through v0.29.0 releases (stamps were applied by hand each time; the lockstep tests caught nothing missed). The rewrite spawns no child processes at all, so there is nothing for a launcher to misroute; it also needs no Git Bash, resolves the repo root from its own location (worktree-safe), and matches every other bin in this repo. Same CLI, same output, same exit codes. Invoke as `bin/bump-version X.Y.Z` (or `python bin/bump-version X.Y.Z` on Windows). 8 tests in `tests/test_bump_version.py`, including a structural guard that the script never gains a child-process call.

## [0.30.0] - 2026-06-12

### Added

- **MADR / Nygard format compatibility (task-5).** Lowers the switching cost for projects with existing ADR sets in the two dominant community formats.
  - `bin/adr-audit` now classifies every file in `docs/adr/` by template profile (`canonical` | `madr` | `nygard` | `unknown`) via a linear, fence-aware heuristic (`detect_template_profile`) and emits a new `template_profile` finding for MADR / Nygard shaped ADRs, pointing at `/adr-kit:migrate`. Advisory only; never blocks.
  - `/adr-kit:migrate` gains two named patterns: **Pattern G "MADR mapping"** (Context and Problem Statement to Context; Considered Options plus Pros and Cons to Alternatives Considered; Decision Outcome to Decision plus Consequences; frontmatter status to `## Status`) and **Pattern H "Nygard lift"** (the four Nygard sections map 1:1; TODO placeholders for Alternatives Considered, Related Decisions, References). Read-then-confirm posture unchanged.
  - Optional `template.profile` ("canonical" | "madr" | "nygard") in `.adr-kit.json` (`schemas/adr-kit-config.schema.json`): informational declaration of a project's source profile, surfaced in audit findings. Lint behaviour is unchanged.
  - Fixtures `tests/fixtures/madr/` and `tests/fixtures/nygard/` plus hand-migrated, lint-clean counterparts in `tests/fixtures/madr-migrated/` and `tests/fixtures/nygard-migrated/`; covered by `tests/test_template_profiles.py` (13 tests).
  - `docs/adr/ADR-003-template-profile-compatibility.md` records the input contract: the canonical seven-section template stays the only storage format; MADR and Nygard are import formats; detection is heuristic and advisory.

## [0.29.0] - 2026-06-12

### Added

- **`bin/adr-status`: Enforcement coverage metric (task-4).** The summary now reports `coverage_pct` (percent of Accepted ADRs carrying a parseable `## Enforcement` block with at least one rule) and `llm_judge_pct` (percent of Accepted ADRs whose Enforcement includes `llm_judge: true`). Present in all three output formats (json, markdown, table). Additive only: all existing field names are unchanged. 12 tests in `tests/test_adr_status_coverage.py`.
- **`bin/adr-guardian`: trend history (task-4).** `adr-guardian stamp` now appends an entry to a new append-only `trend` list in `.adr-kit-state.json`: `{date, tier, total_adrs, drift_violations, retire_candidates, suggest_hits, audit_findings, coverage_percent}`. Fields for the tier that did not run are carried from the last known values (or null). Capped at 52 entries (roughly a year of weekly sweeps; oldest dropped). New `stamp --coverage PCT` flag records the coverage percent that the guardian skill reads from `adr-status --format json`. Corrupt trend data degrades silently. When at least two sweeps have been stamped, the SessionStart nudge block adds a one-line delta vs the previous sweep, e.g. `trend: drift 2 -> 0, retire 1 -> 2, coverage 40% -> 45%`: the guardian becomes a KPI with memory instead of a snapshot.

## [0.28.0] - 2026-06-12

### Added

- **`bin/adr-related`: read-only ADR dependency graph CLI (task-3).** `adr-related ADR-NNN [--adr-dir docs/adr] [--format human|json]` prints outbound edges (Related Decisions entries, Supersedes claims, Superseded by / Amended by status refs) and inbound edges (every other ADR referencing the target, with reference kind: related, supersedes, superseded-by, amended-by, mention). Whole-token id matching (ADR-043 never matches inside ADR-0430). Dangling references are flagged. Exit 0 on success, 2 on unknown id or missing directory. Stdlib-only, linear regexes. 24 tests in `tests/test_adr_related.py`.
- **`/adr-kit:related` skill (task-3):** thin read-only wrapper around `bin/adr-related`. Model-invocable; safe from parallel subagents.
- **`/adr-kit:supersede` skill (task-3):** guided supersession workflow (`disable-model-invocation: true`). Shows the target's dependency graph first, drafts the superseding ADR via the adr-generator subagent (Status: Proposed, back-linked), and only after user approval flips the old ADR's Status line to `Superseded by ADR-M` and appends status_history entries on both sides. Verifies the chain with `bin/adr-related` + `bin/adr-lint`. Hard-stops when the target already carries a `Superseded by` pointer at a different ADR (never overwrites an existing supersession; same invariant the adr-lint consistency gate enforces since v0.25.0). Never auto-accepts the new ADR.

## [0.27.0] - 2026-06-12

### Added

- **Copied-artifact staleness detection (task-15).** Plugin-level hooks refresh automatically when the plugin updates, but artifacts copied into a project freeze at install time: the git pre-commit wrapper and the project-scoped guardian entry in `.claude/settings.json` keep resolving the newest engines, yet their own feature surface lags until refreshed. The templates now carry version stamps (`ADR_KIT_WRAPPER_VERSION="X.Y.Z"` in `templates/githooks/pre-commit`, `_wrapper_version` in `templates/cc-settings/guardian-hook-entry.json`) that `bin/bump-version` keeps in lockstep with the release. `bin/adr-guardian check` compares the stamps against the installed plugin version with pure file reads (no subprocesses) and adds a `wrapper: ... STALE -> /adr-kit:upgrade` line to the SessionStart nudge; a stale wrapper counts as a due item, so it surfaces even when both sweep tiers are fresh, riding the existing nudge cooldown. Staleness rules avoid false positives: an up-to-date stamp is silent, a non-adr-kit pre-commit hook is never reported, and an unstamped settings entry is reported present but never stale (it self-resolves engines). New `adr-guardian artifacts [--format json]` subcommand exposes the same report for skills and manual inspection. 17 tests in `tests/test_adr_guardian_artifacts.py`, including lockstep guards that fail when a release bump misses the template stamps.

### Changed

- **`/adr-kit:upgrade` generalized into the artifact refresh driver (task-15).** Previously a one-shot v0.11 to v0.12 migration. New Step 0 runs `adr-guardian artifacts` and refreshes each stale artifact idempotently: the git wrapper is replaced from the current template (diff-and-ask when locally edited), the settings guardian entry is rewritten with JSON-structural editing (sibling hooks untouched), and an outdated `.claude/adr-kit-guide.md` is refreshed. Artifacts the plugin cannot reach (GitHub Action `@vX` pins, `pre-commit` framework `rev:`) are reported with the right tool to bump them (Dependabot/Renovate, `pre-commit autoupdate`). The legacy v0.11 to v0.12 migration remains as the one-time path.

## [0.26.0] - 2026-06-12

### Added

- **`/adr-kit:review` skill (`skills/review/SKILL.md`): PR/branch-level ADR audit (task-14).** Audits the COMMITTED work of a branch or PR (merge-base with the base ref, default `origin/main`; `gh pr view` supplies the base and PR metadata when available) in two passes. Enforcement: the range diff is piped through `bin/adr-judge --diff` (declarative-only, key-free; identical verdicts to the pre-commit hook and the CI action), with the three `/adr-kit:judge` resolution paths offered per violation. Discovery: detects NEW architectural decisions the range introduces that no ADR documents yet, using both the headless `bin/adr-suggest` detector and an in-session vigilance pass over the diff PLUS the stated intent (commit subjects/bodies, PR title/body), because decisions are often confessed in prose while the diff looks like plumbing. Candidates are deduped against the existing set via `bin/adr-context`; the user picks which findings to act on; picked decisions are drafted via the `adr-generator` subagent with `Status: Proposed` and never auto-accepted. Degrades honestly: no `gh` means git-log intent only, no `claude` CLI means enforcement-only plus the in-session pass.
- **`bin/adr-suggest --intent-file <path>` (task-14).** Appends the change author's stated intent (commit messages, PR description) to the decision-detector prompt as untrusted data inside the same content-derived sentinel fences introduced by the task-12 hardening: evidence of what the change intends, never instructions to the model (PR bodies are author-controlled). Content is truncated at 8000 chars. Without the flag the prompt is byte-identical to the no-intent form; the response schema, advisory posture, and opt-in gate are unchanged. A bad path is a usage error (exit 2), matching `--diff`. Four new tests in `tests/test_adr_suggest.py`.

## [0.25.0] - 2026-06-12

### Security

- **Prompt-injection hardening for the LLM judge and suggest passes (task-12).** Diff and ADR content in `bin/adr-judge` and `bin/adr-suggest` prompts are now wrapped in unique sentinel data fences (`<<<ADR-KIT-DATA-<sha256-prefix> BEGIN/END>>>`), with an explicit instruction that fenced content is untrusted data and any instructions inside it must be ignored. The fence token is derived from a SHA-256 of the fenced content, so a diff cannot pre-place a matching END marker: embedding any guessed token changes the token. The ADR fence token depends only on the ADR set, preserving the prompt-cache prefix.
- **Enforcement blocks are schema-validated before use (task-12).** `bin/adr-judge` now structurally validates every Enforcement block (known rule kinds only, required non-empty string `pattern`, optional `path_glob`/`message`, boolean `llm_judge`; mirrors `schemas/adr-enforcement.schema.json`, stdlib-only with jsonschema as optional deeper layer) BEFORE any rule is compiled as a regex or lands in an LLM prompt. Invalid blocks are reported as ADVISORY `enforcement_config` findings and never silently used; malformed JSON syntax keeps the existing exit-2 contract. Tests in `tests/test_adr_judge_security.py`, including a forged-END-marker test and a 4-way parallel-run concurrency test.

### Added

- **Judge override audit trail (task-10).** A pre-commit FAIL can now be overridden for ONE named ADR per commit via `ADR_KIT_OVERRIDE="ADR-NNN: <reason>" git commit ...`. The override downgrades only that ADR's violations to loudly printed warnings (other ADRs still block), refuses an empty reason, and appends a record (timestamp, ADR id, reason, git user, SHA-256 of the judged diff) to the untracked log `docs/adr/.adr-kit-overrides.jsonl` (excluded via `.git/info/exclude`). Judging stays read-only: no tracked file is touched while a staged diff is evaluated. Convention: the commit message SHOULD carry a matching `ADR-Override: ADR-NNN <reason>` trailer. New modes: `adr-judge --check-override` (validate the env var) and `adr-judge --audit-overrides [--json]` (read-only reconciliation of the local log against commit trailers).
- **Concurrent-supersession detection (task-10)** in the adr-lint consistency gate. Two or more Accepted ADRs declaring `Supersedes ADR-NNN` for the same target now FAIL, with every claimant file named; the message reports whether the target's Status line names a successor. A single clean supersession still passes. Tests in `tests/test_adr_judge_override.py` and `tests/test_adr_lint_supersession.py`.

## [0.24.0] - 2026-06-12

### Added

- **`bin/adr-watch`: in-flight ADR guidance for just-edited files (task-6).** New stdlib-only Python bin that closes the guidance gap between SessionStart context injection (guardian) and pre-commit enforcement (adr-judge). Given one or more edited file paths it prints at most three compact one-line nudges naming the Accepted ADRs that likely apply. Two signals: Enforcement-block `path_glob` match (strongest, reuses the adr-judge glob translator including `**` and `{a,b}` brace expansion) and adr-context-style keyword relevance of the path against ADR title + Decision text. Deterministic, key-free, no LLM, no network; each ADR file is read exactly once and all regexes are precompiled and linear-time. Always exits 0 (advisory, never blocks). Self-guards: silent no-op when the working directory has no `docs/adr/` with ADRs.
- **PostToolUse hook wiring (plugin-level, task-6).** `.claude-plugin/plugin.json` now declares a `PostToolUse` hook (matcher `Edit|MultiEdit|Write`) invoking the new `.claude-plugin/hooks/post-tool-use` bash script via the existing `run-hook.cmd` cross-platform polyglot. In `--hook` mode adr-watch extracts `tool_input.file_path` from the payload and emits the nudges as a `hookSpecificOutput.additionalContext` envelope under Claude Code, or plain text elsewhere. Degrades silently (exit 0) when Python, the bin, or the payload is missing or malformed.
- **Per-session nudge cooldown (task-6).** The same ADR+file pair is not nudged again within `watch.cooldown_hours` (default 4). State lives under a separate `watch` key in `docs/adr/.adr-kit-state.json`, written atomically via `os.replace`; sibling guardian keys are preserved and corrupt state is tolerated as empty. New `watch` config block (`enabled`, `cooldown_hours`) in `schemas/adr-kit-config.schema.json`. 23 tests in `tests/test_adr_watch.py`.

## [0.23.0] - 2026-06-12

### Added

- **`bin/adr-renumber`: safely renumber one ADR for the merge-collision workflow (task-8).** Dry-run by default (prints the full plan: file rename, heading rewrite, and every cross-reference rewrite with file:line); `--apply` executes. `--to ADR-NNN` is optional and defaults to the next free number (max in use + 1; gaps are not reused so retired numbers stay retired). Updates Related Decisions entries, "Superseded by" and "Amended by" status strings, Status History mentions, and plain ADR-NNN references across all ADRs in the directory. Whole-token matching only: renumbering ADR-043 never touches ADR-0430. Refuses (exit 2) when the target number is taken, the source is missing, or the source number is ambiguous (duplicates: pass the file path). Stdlib-only, linear regexes. Tests in `tests/test_adr_renumber.py`.

### Changed

- **`bin/adr-lint`: the duplicate-number consistency finding now names every file sharing the number and points at `bin/adr-renumber` as the fix.** Detection itself pre-existed and already failed CI (consistency is `always_strict` regardless of `strict_from`); this release adds the post-merge regression tests and the actionable message.

## [0.22.0] - 2026-06-12

### Added

- **Guardian team mode (task-9).** New weekly CI-cron sweep workflow `.github/workflows/adr-guardian-audit.yml` runs the cheap tier only (`adr-lint` + `adr-retire` + `adr-status`), aggregates one markdown report, and maintains a single "ADR guardian audit" tracking issue (created on findings, body updated on later runs, closed when clean). Report-only: never fails the build, never runs an LLM (ADR-001 posture), no secrets beyond `GITHUB_TOKEN`. A copy-paste variant for downstream projects ships in `templates/github-workflows/adr-guardian-audit.yml`. The guardian skill (`skills/guardian/SKILL.md`) documents the split: SessionStart nudge = per-developer freshness, CI cron = shared team visibility.

### Fixed

- **Multi-session-safe guardian state (task-9).** `bin/adr-guardian` now writes `.adr-kit-state.json` via a unique per-process temp file plus `os.replace` (atomic on POSIX and Windows), tolerates corrupt or partial state files on read (treated as empty state, one stderr warning, file overwritten by the next stamp), and takes a best-effort non-blocking advisory lock (`fcntl`/`msvcrt`, guarded by `ImportError`) around writes. Last-writer-wins semantics are documented in the script header; the state file is per-machine advisory data, not a ledger. Tests in `tests/test_adr_guardian_state.py`.

## [0.21.0] - 2026-06-12

### Added

- **`bin/adr-mcp`: thin Model Context Protocol server over stdio (task-7).** Hand-rolled JSON-RPC 2.0 on the Python stdlib only (no `mcp` package), newline-delimited messages. Exposes 4 key-free tools that wrap the existing CLIs via subprocess: `adr_context` (heuristic ADR ranking), `adr_judge` (declarative Enforcement pass on a diff, never `--llm`), `adr_status` (repository health JSON), `adr_quality` (per-ADR grades). `adr-suggest` is deliberately not exposed: it is LLM-only and the MCP server stays key-free. Project root via `--root`, `PROJECT_ROOT` env, or cwd; ADR directory via `--adr-dir` (default `<root>/docs/adr`). Brings the same guardrails to Cursor, Cline, Windsurf, and Copilot without the skills format. Tests in `tests/test_adr_mcp.py` (14 end-to-end stdio tests).

## [0.20.1] - 2026-06-07

### Fixed

- **`bin/bump-version` now also bumps `.claude-plugin/marketplace.json`.** The helper previously updated only `plugin.json` and `CHANGELOG.md`, leaving the marketplace manifest to be edited by hand. `marketplace.json` `plugins[].version` is the field the Claude Code plugin update system compares against, so a bump that misses it ships to the repo but is never picked up by clients (the propagation gap behind the "fixed but still serving the old version" reports, e.g. issue #6). The script now updates the marketplace entry whose `name` matches `plugin.json`, and errors out if no such entry exists rather than bumping silently. Documented and staging hint updated to include `marketplace.json`.

## [0.20.0] - 2026-06-07

### Added

- **`/adr-kit:context` skill (`skills/context/SKILL.md`) — load the relevant ADRs before implementing (issue #7).** Projects with many ADRs make it expensive for an agent to know which decisions apply before starting work: loading all of them burns the context window, loading none means existing decisions get ignored. This skill takes a topic (e.g. `"mqtt discovery"`, `"caching"`) and drives the existing `bin/adr-context` ranker (`--format json --limit 5`), then reads the top hits and presents them as readable context — `ADR-NNN — title`, a one-line paraphrase of the `## Decision`, the file path, and the relevance score — followed by a one-or-two-sentence statement of the net constraint. Empty results are reported honestly ("No ADRs match '<topic>'; all existing ADRs may apply, or none constrain this work") rather than silently. Read-only and safe to call from parallel subagents; no MCP server required (unlike the `adr_planning_context` MCP tool in the `kschlt/adr-kit` fork, which has a known subagent-blocking issue). The `bin/adr-context` CLI and its 20 tests already shipped; this release adds the missing slash-command wrapper that exposes it in Claude Code.

## [0.19.2] - 2026-06-07

### Fixed

- **Catastrophic regex backtracking (ReDoS) in `## Enforcement` parsing — remaining tools (issue #9 follow-up).** v0.19.1 fixed the nested lazy quantifier `(?:.*?\n)*?` in `bin/adr-retire` only. The identical pattern lived on in three sibling tools that also parse `## Enforcement` blocks: `bin/adr-judge` (the pre-commit / CI enforcement gate), `bin/adr-generate-scripts`, and `bin/adr-lint`. A fence-less `## Enforcement` section (heading with prose but no ` ```json ` block) therefore still hung those tools — most importantly `adr-judge`, which runs on every commit. De-nested the quantifier (`(?:.*?\n)*?` → `.*?`); a single lazy quantifier under `re.DOTALL` is linear and behaviour-identical on properly-fenced ADRs. `bin/adr-status` already used a single non-nested `.*?` and was unaffected. Added `tests/test_enforcement_redos.py` — a parametrized guard across all three tools asserting linear runtime, no nested quantifier in the pattern, and continued matching of fenced blocks.

## [0.19.1] - 2026-06-05

### Fixed

- **`bin/adr-retire` hung on ADRs with a fence-less `## Enforcement` section (#9).** `ENFORCEMENT_BLOCK_RE` used a nested lazy quantifier `(?:.*?\n)*?` under `re.DOTALL`. When an ADR had a `## Enforcement` heading but no ` ```json ` fenced block to anchor on, the regex backtracked catastrophically (~0.75s for a single 7.5KB ADR, growing with file size), stacking into a multi-minute hang across a real ADR set (observed on a 123-ADR project where 4 ADRs carried prose-only "manual review" Enforcement notes). Replaced with the linear, lookahead-anchored `extract_section("Enforcement")` plus a simple non-nested `JSON_FENCE_RE`. Behaviour is preserved (a fence-less Enforcement section yields no rules and `policy_mismatch` 0.0, identical to the previous non-match path); the unused `ENFORCEMENT_BLOCK_RE` is removed. Regex work drops from a timeout to 0.118s over 128 ADRs, with verified capture parity against all properly-fenced ADRs. Added regression test `test_enforcement_without_json_fence_scores_zero_quickly`.

## [0.19.0] - 2026-05-31

### Added

- **`.github/actions/adr-judge/action.yml` — reusable composite GitHub Action for PR-level enforcement.** Computes the PR diff via `git diff --unified=0 origin/<base>...HEAD` (using `GITHUB_BASE_REF`), fetches the base branch explicitly so shallow clones work, downloads `bin/adr-judge` from the same tag the action was loaded from, and pipes the diff to `adr-judge --diff - --adr-dir`. **Declarative-only by default** — no `--llm` flag, no API key, no `claude` CLI required in the runner. Exits 1 on any Enforcement-block violation, 0 on a clean diff, 2 on config/input error.
- **`.github/workflows/adr-judge-self.yml` — self-dogfood workflow.** Runs the composite action against adr-kit's own `docs/adr/` on every PR targeting `main`. Trigger is `pull_request` only (`push` excluded because `GITHUB_BASE_REF` is empty on push commits and the PR diff collapses to nothing). Confirms declarative-only enforcement gates work with no secrets.
- **`bin/adr-judge-precommit` — thin Python wrapper for the `pre-commit` framework.** The framework passes staged filenames to hooks, but `bin/adr-judge` needs the diff on stdin. This wrapper: (1) runs `git diff --cached --unified=0`, (2) pipes the result to the sibling `bin/adr-judge` resolved via `Path(__file__).resolve().parent`, (3) propagates the exit code. Sibling-resolution means it works regardless of PATH, consistent with how the native pre-commit hook resolves `bin/adr-judge` via the plugin cache.
- **`.pre-commit-hooks.yaml` — pre-commit framework hook declaration.** Declares an `adr-judge` hook (`id: adr-judge`, `language: script`, `pass_filenames: false`, `stages: [pre-commit]`, `minimum_pre_commit_version: "2.18.0"`) that invokes `bin/adr-judge-precommit`. Declarative-only by default. Enables teams already using the `pre-commit` framework to register enforcement without writing a native git hook.
- **README "CI integration" section extended.** New sub-section "PR-level enforcement: `bin/adr-judge`" (after the existing `adr-lint` section) with: a copy-paste GitHub Actions workflow snippet for downstream projects; a pre-commit framework usage snippet (`.pre-commit-config.yaml`); honest documentation of the opt-in LLM path (requires the `claude` CLI authenticated in the runner — an `ANTHROPIC_API_KEY` alone is not sufficient; declarative-only is the supported default).
- **`tests/test_adr_judge_precommit.py` — four pytest tests** covering: exit 1 on a staged violation, exit 0 on a clean staging area, exit 0 on an empty staging area, and static verification that `bin/adr-judge` exists at the expected sibling path.

### Notes

- Both features are declarative-only and key-free by default, consistent with the v0.17.0 LLM opt-in posture.
- No ADR authored for v0.19.0: CI enforcement and pre-commit delivery are additive tooling within the existing `bin/adr-judge` contract, not new interfaces, dependencies, or NFR shifts. The roadmap explicitly targets an ADR for v0.22.0 (MADR/Nygard format compatibility) and v0.18.0 (guardian), not v0.19.0.

## [0.18.0] - 2026-05-31

### Added

- **`bin/adr-guardian` -- ADR-set health detector.** New stdlib-only Python bin with three subcommands: `check` (the SessionStart hook entry point; read-only, always exit 0, never spawns), `stamp <cheap|llm>` (records sweep completion in `.adr-kit-state.json`), and `state` (inspect current state). The `check` subcommand computes due tiers vs. the two-tier clocks, applies `nudge_cooldown_hours` throttle, and emits the `[adr-guardian]` block as Claude Code `hookSpecificOutput.additionalContext` JSON when a tier is due.
- **`/adr-kit:guardian` skill** (`skills/guardian/SKILL.md`) -- the in-session ADR-set health sweep. Orchestrates `adr-judge` (declarative drift), `adr-retire` (stale detection), `adr-lint`/`adr-status` (health), `adr-suggest` (missing-ADR detection, LLM tier), and `adr-judge --llm` (full audit, LLM tier). Applies mix-by-finding-type responses (drift = prominent; missing ADR = passive; stale = autonomous draft; health = report). Confirms cost before any LLM-tier phase. Stamps state when done. Accepts optional argument `cheap | llm | all`.
- **Two-tier cadence**: cheap tier (drift + retire + lint) runs daily (`guardian.drift_stale_days: 1`, free); LLM tier (suggest + audit) runs bi-weekly (`guardian.llm_stale_days: 14`, costs ~$0.10-0.30). Each tier stamped independently so the clocks do not interfere.
- **Mix-by-finding-type responses**: drift violations surfaced prominently (highest signal); missing-ADR suggestions passive (user picks); stale ADRs get an autonomous draft for review (never auto-applied); ADR-set health reported with fix offer. Per spec 6.
- **Both hook-install paths shipped** (spec 7): plugin-level (`hooks` key in `.claude-plugin/plugin.json` + `.claude-plugin/hooks/`) auto-registers when the plugin is enabled globally; project-scoped instructions added to `skills/install-hooks/SKILL.md` for JSON-structural add/remove of the SessionStart entry in `.claude/settings.json` (idempotent, never clobbers sibling hooks).
- **`guardian` config block** in `schemas/adr-kit-config.schema.json` with full descriptions and defaults: `enabled` (default `true`), `drift_stale_days` (default 1), `llm_stale_days` (default 14), `nudge_cooldown_hours` (default 24), `llm_autorun` (default `false`, consistent with ADR-001 opt-in posture).
- **Gitignored state file**: `docs/adr/.adr-kit-state.json` added to `.gitignore` (per-machine, never committed). `/adr-kit:init` adds it to the project gitignore during setup.
- **Guardian section in `templates/adr-kit-guide.md`** (v0.18.0 header bump): documents the two-tier cadence, mix-by-finding-type table, config block, both hook-install paths, and in-session model behaviour for the `[adr-guardian] ... DUE` block.
- **`/adr-kit:init` Step 5b** -- guardian setup step offering `enabled` toggle, project-scoped hook install, and gitignore update.
- **`docs/adr/ADR-002-adr-guardian-session-start-staleness-detector.md`** -- dogfood ADR recording the guardian design decision (Status: Proposed).
- **`tests/test_adr_guardian.py`** -- 29 tests covering due/not-due logic across both clocks, cwd-guard no-op, `nudge_cooldown_hours` throttle, retire-candidate state display, `stamp` updates, `state` round-trip, always-exit-0 under corrupt state/config, and JSON envelope format (Claude Code `hookSpecificOutput` path).

### Changed

- `.claude-plugin/plugin.json`: description updated to mention guardian; `hooks` key added declaring the SessionStart hook; version bumped to 0.18.0.

## [0.17.0] - 2026-05-31

### Changed (BREAKING DEFAULT)

- **Per-commit LLM judge is now OPT-IN.** The pre-commit hook no longer hard-codes `--llm`. Existing users who relied on automatic per-commit LLM judging must set `judge.llm_enabled: true` in `docs/adr/.adr-kit.json` to restore the old behaviour. One-liner migration: `echo '{"judge":{"llm_enabled":true}}' > docs/adr/.adr-kit.json`. Enable for a single commit: `ADR_KIT_LLM=1 git commit ...`. On-demand LLM review is always available via `/adr-kit:judge` and `adr-judge --llm` — these are unaffected by this change.
- **`suggest.enabled` default flipped `true` → `false` (opt-in).** The per-commit `adr-suggest` nudge pass is now off by default. Enable per-project: `suggest.enabled: true` in `.adr-kit.json`. Enable per-commit: `ADR_KIT_SUGGEST=1 git commit ...`.

### Added

- **`judge.llm_enabled` config switch** (default `false`): user-facing master switch for the per-commit LLM pass. `/adr-kit:init` now interactively asks whether to enable it and writes the choice to `docs/adr/.adr-kit.json`. The legacy `judge.llm_default` key is preserved for CI / direct-CLI back-compat.
- **Flock concurrency guard in the pre-commit hook.** When `flock` is available, the hook takes a non-blocking advisory lock (`$ROOT/.git/adr-kit-judge.lock`). Under lock contention (rapid or parallel commits) the cheap declarative gate still runs; LLM passes are suppressed via `ADR_KIT_NO_LLM` for that commit instead of piling up concurrent `claude -p` calls. Degrades gracefully to no-lock on bare Windows cmd.exe where `flock` is absent.
- **`/adr-kit:init` interactive LLM opt-in.** After hook install the skill now prints a cost/latency notice (up to 2 Sonnet calls per commit, 120s timeout each, ~$0.10–$0.30 per commit) and asks two questions (both defaulting to No): enable per-commit LLM judging, enable per-commit ADR-suggest. Writes the chosen booleans to `docs/adr/.adr-kit.json`. Adds a `llm:` line to the wrap-up summary.

### Fixed

- **`bin/adr-suggest` now honors `suggest.enabled`** (previously documented but never read — latent no-op). The opt-in check fires before any diff reading or LLM invocation, mirroring the judge LLM opt-in pattern.

## [0.16.0] - 2026-05-29

### Added

- **`bin/adr-suggest` — advisory ADR-needed detector.** A new bin, distinct from `bin/adr-judge`. Where `adr-judge` *enforces* existing Accepted ADRs and can block a commit, `adr-suggest` runs one LLM pass over the staged diff to detect whether the change introduces a *new* architectural / contract / dependency decision **not yet covered by any ADR**, and prints a one-line nudge to run `/adr-kit:adr`. It **never blocks the commit**: the advisory path always exits 0. A missing `claude` CLI, a timeout, a non-zero exit, a malformed response, or a docs/lockfile-only diff all resolve to a silent skip. CLI: `adr-suggest [--diff PATH|-] [--adr-dir DIR] [--config PATH] [--llm-cmd CMD] [--llm-timeout SECS] [--json] [--repo-root ROOT]`.
  - Reuses the same LLM-command resolution as `adr-judge` (`--llm-cmd` > `ADR_KIT_LLM_CMD` env > `.adr-kit.json` `suggest.llm_cmd`/`suggest.llm_model` > `judge.llm_cmd`/`judge.llm_model` > default `claude -p --model claude-sonnet-4-6`), including the repo-config binary allowlist (SEC-HIGH).
  - Existing ADR ids + titles + one-line decisions are passed to the model so it does not suggest a duplicate of a decision already recorded.
  - Advisory output goes to **stderr** only (stdout stays pipe-clean); `--json` emits the parsed result object `{needs_adr, confidence, reason, suggested_title, category}` to stdout.
- **Pre-commit hook: advisory suggestion section** (`templates/githooks/pre-commit`). A third section runs `adr-suggest` after the `adr-judge` pass, piping `git diff --cached --unified=0` to it. Its exit status is swallowed (`|| true`) so it can never fail a commit. Gated by `ADR_KIT_SUGGEST_DISABLE` (runs by default; set `=1` to skip).
- **Config: `suggest.*` block** in `.adr-kit.json` (`schemas/adr-kit-config.schema.json`). Optional, back-compatible (absent block = defaults): `suggest.enabled` (bool, default true), `suggest.llm_cmd` / `suggest.llm_model` (fall back to `judge.*`), `suggest.llm_timeout_seconds` (default 120).
- **Tests**: `tests/test_adr_suggest.py` — fake-`claude` binary approach mirroring `tests/test_adr_judge_llm.py`. Covers high-confidence advisory, needs_adr=false silence, low-confidence silence, docs-only / lockfile / empty-diff skips (no LLM call), missing CLI, malformed JSON, `--json` output, fenced-JSON parsing, and assertions that existing ADR titles reach the prompt.

## [0.15.0] - 2026-05-27

### Fixed / Improved (37 review findings from multi-agent code review)

#### Security

- **llm_cmd allowlist** (`bin/adr-judge`): `judge.llm_cmd` from `.adr-kit.json` is now validated against an explicit allowlist of known Claude CLI binaries. Unknown binaries trigger a warning and fall back to the default; `ADR_KIT_LLM_CMD` env and `--llm-cmd` CLI flag remain unrestricted (operator-controlled).
- **ReDoS guard** (`bin/adr-judge`): ADR-controlled regex patterns are now executed inside a `threading.Timer`-based 1-second timeout per pattern. A timed-out pattern produces an ADVISORY finding instead of hanging the pre-commit hook indefinitely.
- **Path traversal in require_pattern** (`bin/adr-judge`): diff-derived file paths are validated to resolve under `repo_root` before reading. Absolute paths and `..` sequences are rejected.
- **LLM stderr info disclosure** (`bin/adr-judge`): verbose LLM error output is now gated behind `ADR_KIT_DEBUG=1`; default messages are generic.
- **Generated shell script — ERE validation** (`bin/adr-generate-scripts`): generated `validate.sh` now tests each pattern with a `printf | grep` preflight at startup and warns loudly if any pattern is not valid POSIX ERE.
- **Generated shell script — echo/printf** (`bin/adr-generate-scripts`): replaced `echo "$line"` with `printf '%s\n' "$line"` to avoid xpg_echo backslash interpretation.
- **Pre-commit hook glob expansion** (`templates/githooks/pre-commit`): replaced `ls -d | sort -V | tail -1` path resolution with a bash nullglob array, eliminating the ls-parsing vulnerability.
- **adr-retire symlink traversal** (`bin/adr-retire`): replaced unbounded `rglob('*')` with `os.walk(followlinks=False)` and a 50,000-file cap.

#### Performance

- **glob_to_regex caching** (`bin/adr-judge`): module-level `_GLOB_PATTERN_CACHE` eliminates O(ADRs × rules × files × globs) redundant `re.compile()` calls.
- **JSON schema singleton** (`bin/adr-judge`, `bin/adr-lint`): `schemas/adr-enforcement.schema.json` is now loaded and compiled into a `Draft7Validator` once per process instead of once per ADR.
- **Section regex precompilation** (`bin/adr-lint`, `bin/adr-quality`): `REQUIRED_SECTIONS` heading patterns precompiled at module load.
- **adr-status single-pass parsing** (`bin/adr-status`): introduced `AdrRecord` dataclass and `parse_adr()` — each ADR is read and all fields extracted exactly once. All formatters consume the cached record, eliminating 500-700 redundant regex scans on 100-ADR sets.
- **Pre-commit hook streaming** (`templates/githooks/pre-commit`): replaced `DIFF=$(git diff ...)` buffering with direct pipe streaming to `adr-judge`.
- **Generated validate.sh** (`bin/adr-generate-scripts`): rewritten from O(lines × rules × subprocess_spawn) to O(rules) subprocess spawns via single-pass `grep -nE` per rule.
- **adr-context domain inference** (`bin/adr-context`): replaced ~125 `in text_lower` substring checks per ADR with per-domain compiled word-boundary regexes.
- **adr-context metadata extraction** (`bin/adr-context`): 6 inline `re.search()` calls per ADR replaced with module-level compiled constants.
- **adr-quality gate regexes** (`bin/adr-quality`): section presence/body patterns and acronym regex precompiled at module level.
- **Diff size check** (`bin/adr-judge`): `len(diff_text)` replaces `len(diff_text.encode("utf-8"))`.
- **Dry-run shortcut** (`bin/adr-judge`): `--dry-run-enforcement ADR-NNN` now globs only the target ADR directly.

#### Architecture

- **Structured quality issues** (`bin/adr-quality`): `gate_*()` functions now return `QualityIssue` dataclasses with stable `code`, `detail`, `severity` fields instead of raw strings. JSON output includes `code`, `detail`, `severity`, `message` per issue.
- **Unified vague-language list** (`bin/adr-lint`, `bin/adr-quality`): both tools now share a canonical 8-word set (`appropriate`, `somehow`, `maybe`, `possibly`, `might`, `could`, `should consider`, `might consider`).
- **Quality gate boundary documented** (`bin/adr-lint`, `agents/adr-generator.md`): `check_quality_gate()` docstring and Step 3 in `agents/adr-generator.md` now explicitly state that `adr-lint` and `bin/adr-quality` run different gate sets with different thresholds.
- **Schema extended** (`schemas/adr-kit-config.schema.json`): `context` and `retirement` top-level config blocks now documented with full property schemas.
- **Legacy config key removed** (`bin/adr-context`): `min_relevance_threshold` fallback removed; canonical key is `min_score`.
- **adr-status — amended status** (`bin/adr-status`): `by_status` histogram now buckets "amended" correctly; `CANONICAL_STATUSES` constant defined.
- **adr-status — no-op flags removed** (`bin/adr-status`): `--show-enforcement` and `--show-retirement` flags (shipped as no-ops in v0.14.0) removed.
- **adr-context — bare except fixed** (`bin/adr-context`): silent `except Exception: pass` replaced with stderr warning.
- **adr-context — infer_task_domain returns Optional** (`bin/adr-context`): returns `None` instead of "backend" when no domain matches; scoring skips domain_tag credit for unknown domains.
- **CLI format consistency** (`bin/adr-retire`, `bin/adr-lint`): adr-retire default changed from `json` to `text`; adr-lint accepts `text` as alias for `human`.
- **adr-generate-scripts cleanup** (`bin/adr-generate-scripts`): extracted `_make_executable()` helper, removed duplicated chmod blocks and unused `import os`.

#### Testing

- **Wall-clock performance tests** (`tests/test_adr_performance.py`): 3 new `@pytest.mark.slow` tests assert timing budgets on 50-ADR synthetic suites for adr-judge (<3s), adr-status (<500ms), adr-context (<600ms).
- **pytest.ini**: registered `slow` marker to eliminate PytestUnknownMarkWarning.
- **225 tests passing**, 2 skipped (Windows shell-script execution).

## [0.14.0] - 2026-05-27

### Added

#### Phase 1 — Governance backbone (TASK-710, TASK-711)

- **Append-only status history**: `bin/adr-judge` parses and appends immutable
  `status_history` YAML entries; `--migrate-status-history` migrates legacy ADRs.
  `bin/adr-lint` validates histories via a new `audit` gate (default-on) while
  keeping unmigrated v0.13 ADRs compatible.
- **Automated retirement detection**: new `bin/adr-retire` tool and
  `/adr-kit:retire` skill score candidates by staleness, technology disappearance,
  broken supersession references, and risky policy patterns. Optional
  `adr-retire-audit.yml` GitHub Actions workflow runs weekly.

#### Phase 2 — Intelligence layer (TASK-712, TASK-713)

- **Profiling and dry-run**: `bin/adr-judge --profile` emits per-ADR timing
  breakdowns; `--dry-run-enforcement ADR-NNN` tests a single ADR against staged
  diffs without blocking the commit.
- **Semantic relevance ranking**: new `bin/adr-context` tool ranks ADRs for a
  task query using five weighted heuristic signals (keyword match, domain tag,
  related decisions, acceptance status, recency). Configurable weights in
  `.adr-kit.json`. Injected into `agents/adr-generator.md` context-loading step.

#### Phase 3 — Enforcement quality (TASK-714, TASK-715)

- **Policy block validation**: `bin/adr-lint` gains `--gates policy` and
  `--gates quality` (both opt-in). The policy gate validates Enforcement JSON
  against `schemas/adr-enforcement.schema.json`, compiles all regex patterns, and
  warns on anti-patterns (unescaped dots, excessive wildcards, broad globs). The
  quality gate flags vague language, missing metrics, and too few alternatives.
- **Standalone validation script generation**: new `bin/adr-generate-scripts` tool
  produces self-contained `validate.py` (Python stdlib only) and `validate.sh`
  scripts in `.generated/`. Scripts enforce the same rules as `adr-judge` without
  requiring adr-kit as a dependency, suitable for embedding in foreign CI
  pipelines.

#### Phase 4 — Observability and agent guidance (TASK-716, TASK-717)

- **ADR health dashboard**: new `bin/adr-status` tool reports total count, status
  breakdown, average age, enforcement health per ADR, and top retirement
  candidates. Output in `--format json|markdown|table`.
- **Quality scoring**: new `bin/adr-quality` tool grades each ADR A–D via four
  weighted gates (completeness 40%, evidence 20%, clarity 20%, consistency 20%).
  Returns structured JSON or human-readable text; exits 1 when grade is below B.
- **Agent decision tree**: `agents/adr-generator.md` gains a "When to Create an
  ADR" decision tree and post-decision quality check section.

#### Cross-cutting improvements

- **Python 3 availability check**: `skills/init/SKILL.md` now checks for Python
  3.9+ before any installation step, with guided installation instructions for
  macOS (Homebrew), Linux (apt/dnf/pacman) and Windows (winget). The pre-commit
  hook template (`templates/githooks/pre-commit`) also checks for Python 3 at
  hook runtime and exits gracefully with installation hints if absent.
- **`.adr-kit.json`**: new `context.weights`, `context.default_limit`,
  `context.min_score`, `retirement.*`, and timeout fields
  (`pre_commit_timeout_ms`, `pre_push_timeout_ms`, `llm_timeout_ms`,
  `warn_on_exceed`).
- **222 tests passing**, 2 skipped (Windows shell-script execution).

## [0.13.3] - 2026-05-25

### Fixed

- **`bin/adr-judge` Windows encoding (#LLM-pass)**: two Windows-specific bugs prevented the LLM judge pass from running on Windows machines.
  - **`subprocess.run` cp1252 encoding error**: when the diff or ADR content contained non-ASCII characters (e.g. `≤`), `subprocess.run` with `text=True` but no explicit `encoding` used the Windows console code page (cp1252), causing `UnicodeEncodeError` when writing the prompt to `claude`'s stdin. Fixed by passing `encoding="utf-8"` to `subprocess.run`.
  - **`sys.stdin.buffer` on Windows**: `sys.stdin.read()` uses the console code page; switching to `sys.stdin.buffer.read().decode("utf-8", errors="replace")` ensures the diff is always read as UTF-8 regardless of the active console code page.
  - **`shlex.split` path mangling**: `shlex.split` in POSIX mode (the Python default) treats backslashes as escape characters, mangling Windows paths passed via `--llm-cmd` (e.g. `C:\Users\...` → `C:Users...`). The `shutil.which` check then failed to find the binary and the LLM pass was silently skipped. Fixed by a new `_split_cmd` helper that uses `posix=False` on Windows and strips surrounding quote pairs.
  - **Test fixtures**: fake `claude` binaries in `tests/test_adr_judge_llm.py` were bash scripts, which are not directly executable on Windows. Rewrote all fixtures as Python scripts (always available) and added a `_fake_cmd(path)` helper to produce correctly-quoted `--llm-cmd` strings.

## [0.13.2] - 2026-05-25

### Fixed

- **`templates/githooks/pre-commit`**: two shell bugs caused the hook to exit 1 on clean commits (no ADR violations), effectively blocking every commit and forcing users to set `ADR_KIT_HOOK_DISABLE=1` as a workaround.
  - **`grep -avE` false-positive exit 1**: when `adr-judge` output consists entirely of advisory lines, `grep -avE` finds nothing to print and exits 1. Under `set -e` this killed the script before the actual violation check. Fixed by appending `|| true`.
  - **Missing `exit 0`**: `[ "$ADR_EXIT" -ne 0 ] && exit "$ADR_EXIT"` — when `ADR_EXIT=0` the test returns 1 (false), `&&` short-circuits, and that 1 became the script's exit code because no `exit 0` followed. Fixed by adding an explicit `exit 0` at the end of the script.

## [0.13.1] - 2026-05-08

### Fixed

- **`templates/githooks/pre-commit`**: suppress per-ADR `llm_judge` advisory lines that repeat once for every ADR with `llm_judge: true` and produce very noisy output on projects with many ADRs (e.g. 57 identical lines on OTGW-firmware). The hook now captures `adr-judge` output and filters lines matching `^  ADVISORY ` and `ADR has llm_judge:true` before printing. Violations and the summary line (`[adr-judge] OK N violations, M advisory`) are preserved. Uses `grep -a` to handle multi-byte emoji in the summary line.

## [0.13.0] - 2026-05-07

### Added — Claude Sonnet LLM judge, default-on at hook time

`bin/adr-judge` gains a `--llm` flag that runs an LLM pass for `llm_judge: true` ADRs alongside the v0.12 declarative pass. The pre-commit hook template enables it by default. ADRs with `llm_judge: true` no longer produce just an advisory — Sonnet evaluates the staged diff against the ADR's `## Decision` section and the hook blocks on a `VIOLATION` verdict.

- **`bin/adr-judge` `--llm` mode**: collects all `llm_judge: true` Accepted ADRs, batches them into ONE `claude -p --model claude-sonnet-4-6` call (single round-trip per commit), parses the JSON verdict object Sonnet returns, and emits a `violation` finding for each `{verdict: "VIOLATION", reason: ...}` entry. ADRs with `OK` or unrecognised verdicts produce no finding.
- **`bin/adr-judge` `--llm-cmd "..."`**: override the CLI invocation (model, flags, or substitute a different binary). Tests inject a fake claude binary this way; users can switch to Haiku or Opus by passing a different `--model`.
- **`bin/adr-judge` `--llm-timeout SECS`**: per-call timeout, default 120s. Configurable via `judge.llm_timeout_seconds` in `.adr-kit.json`.
- **`templates/githooks/pre-commit`**: now invokes `adr-judge --llm`. Two new env knobs documented at the top: `ADR_KIT_NO_LLM=1` for per-commit LLM opt-out (declarative checks still run), `ADR_KIT_HOOK_DISABLE=1` for full hook bypass.
- **`schemas/adr-kit-config.schema.json`**: extended with `judge.llm_default` (run LLM pass even without --llm), `judge.llm_model` (default `claude-sonnet-4-6`), `judge.llm_cmd` (full invocation override), `judge.llm_timeout_seconds`.
- **`tests/test_adr_judge_llm.py`**: 10 new tests using a fake `claude` binary fixture. Cover: violation blocks the commit, OK passes through, fenced JSON / prose-wrapped responses parse correctly, unparseable LLM output falls back gracefully, missing CLI falls back gracefully, no `llm_judge` targets means no LLM call, `ADR_KIT_NO_LLM=1` env disables the pass, and verifying the implementation truly batches (one call across N targets, not N calls).

### Behaviour changes

- **Pre-commit hook on a v0.13+ project**: `llm_judge: true` ADRs that were previously informational at commit time are now actively enforcing. A diff that semantically conflicts with such an ADR will be blocked with a one-sentence reason from the model. To opt out per commit: `ADR_KIT_NO_LLM=1 git commit ...`. To opt out persistently: remove the hook via `/adr-kit:install-hooks --uninstall` and reinstall a custom variant, or override `judge.llm_cmd` in `.adr-kit.json` to point at a no-op shell script.
- **`/adr-kit:judge` skill**: rewritten to delegate the entire LLM evaluation to `bin/adr-judge --llm` rather than reasoning in-session. Same engine, same prompt, same verdicts as the hook. The skill's value is now the **resolution loop** (write a new ADR / supersede / fix code) — the evaluation step is shared.
- ADRs without an `## Enforcement` block are still skipped silently. ADRs with declarative-only rules behave exactly as in v0.12. Pure additive change for the `llm_judge: true` set.

### Cost / performance shape

For OTGW-firmware (56 `llm_judge: true` ADRs, typical small commit):
- ~30–40 K input tokens per commit (with prompt caching the per-commit cost drops as ADRs become cached).
- ~5–10 second latency.
- Roughly $0.10–0.30 per commit on Sonnet 4.6.

Configurable downgrade to Haiku 4.5 (~3–5× cheaper, slightly lower fidelity) by setting `judge.llm_model: "claude-haiku-4-5"` in `.adr-kit.json`.

### Backwards compatibility

- v0.12 hooks already in place keep working (they don't pass `--llm`, so the v0.12 advisory behaviour is preserved). To pick up the LLM pass, refresh the hook via `/adr-kit:install-hooks` after upgrading to v0.13.
- Existing tests: 37/37 pass byte-exact (no regressions in the declarative pass, lint, or audit).
- Missing `claude` CLI is non-fatal — judge prints a `WARN` line and falls through to declarative-only. A user who hasn't installed Claude Code locally still gets the v0.12 declarative protection without setup.

### Notes

- **Why batched into one call.** Calling `claude -p` per ADR would multiply latency and cost by N. The single-batch design with the ADR set BEFORE the diff in the prompt also lets Anthropic's prompt cache hit on repeat commits where the ADR set is stable.
- **Why `claude -p` over the SDK.** The CLI reuses the user's Claude Code auth (no `ANTHROPIC_API_KEY` env-var setup), and the spawn overhead (~200ms) is dwarfed by the model latency. Tests can override via `--llm-cmd` for full isolation.
- **Why Sonnet 4.6 and not 4.7.** Quality is indistinguishable for this task, and prompt caching is more mature on 4.6. Override via `judge.llm_model`.

## [0.12.2] - 2026-05-07

### Fixed

- **`bin/adr-judge` and `bin/adr-audit`**: `glob_to_regex` now expands brace-alternation `{a,b,c}` → `(?:a|b|c)`. Without it, real-world Enforcement-block path_globs like `src/**/*.{ino,cpp,h}` or `src/{MQTTstuff,OTGW-Core,SAT*}.ino` silently matched nothing. **Real-world impact**: OTGW-firmware's ADR-049 (no String class in protocol paths) and ADR-042 (no ArduinoJson) ship with brace-style path_globs that were dead code under v0.12.0/v0.12.1 — now correctly enforce. Each alternative inside the brace is itself a valid sub-glob (so `**`, `*`, `?` work inside).
- Unclosed braces and nested braces are treated literally (escape-and-leave) rather than crashing or fabricating a regex.

### Tests

- 3 new tests in `tests/test_adr_judge.py` covering: simple brace-expanded `path_glob` matches the listed alternatives, paths NOT in the alternatives are correctly skipped, and `**` combined with brace alternation in extensions (`src/**/*.{ino,cpp,h}`).

### Notes

- Pure parser improvement, additive only. ADRs already on v0.12 with brace-style path_globs gain enforcement after a plugin re-fetch — no project-side changes required.
- `bin/adr-audit`'s default skip list (`node_modules/**`, `vendor/**`, `docs/adr/**`, etc.) does not use braces today, so its behaviour is unchanged. The fix is preventative for users who add `--skip` patterns containing braces.

## [0.12.1] - 2026-05-06

### Fixed

- **`bin/adr-judge`**: parser now recognises `**Status:** Accepted` (bold-inline) and `**Status: Accepted**` (fully bracketed) status formats in addition to the canonical `## Status\n\nAccepted` heading. **Real-world impact**: a project with 67 legacy bold-inline ADRs (OTGW-firmware) had every Accepted ADR show up as `unknown` to the judge after upgrading to v0.12.0, silently disabling diff-vs-Enforcement coverage on every commit. The judge now correctly classifies these — the project gets enforcement before it has time to migrate via `/adr-kit:migrate`.
- `adr-lint` is intentionally left strict on this point (the Completeness gate still requires a `## Status` heading, nudging users toward canonical format via `/adr-kit:migrate`). Different responsibilities: lint says "your ADR shape is wrong", judge says "is this Accepted, yes or no, what should I enforce?".

### Tests

- 3 new tests in `tests/test_adr_judge.py` covering the three bold-inline formats: `**Status:** Accepted` (rules enforce), `**Status:** Proposed` (rules ignored), `**Status: Accepted**` (rules enforce).

### Notes

- Pure parser improvement, additive only. No false positives — ADRs without an `## Enforcement` block continue to be skipped silently regardless of format.
- v0.12.0 users who hit this trap (judge reports `0 ADR(s) checked` on a project they expect to have rules) should re-fetch with `/plugin install adr-kit@rvdbreemen-adr-kit` to pick up the fix without changing anything else in their project.

## [0.12.0] - 2026-05-06

### Added — three-mode workflow

The kit now operates in three coordinated modes that match how an AI coding agent engages with a codebase: one-shot project init, automatic per-commit verification, and on-demand authoring/review during a session. v0.11 covered only the third mode.

- **`/adr-kit:init`** (`skills/init/SKILL.md`): umbrella one-shot project bootstrap. Hooks `CLAUDE.md` (slim stub + `@`-import to `.claude/adr-kit-guide.md`), copies the canonical project-side guide, runs `bin/adr-audit` to enumerate decision-shaped artefacts in source + documentation, walks the user through batched approval to generate Accepted ADRs via the `adr-generator` subagent, and installs the pre-commit hook. User-invocable only (`disable-model-invocation: true`).
- **`/adr-kit:judge`** (`skills/judge/SKILL.md`): on-demand interactive judge of a staged git diff against existing ADRs. Runs the deterministic `bin/adr-judge` for declarative `Enforcement` rules, then evaluates `llm_judge: true` ADRs **in the active Claude Code session** (no `claude -p` shell-out, no extra API key). On violation, walks three resolution paths (write a new ADR, supersede an existing ADR, fix the code) — each delegates to existing primitives.
- **`/adr-kit:install-hooks`** (`skills/install-hooks/SKILL.md`): installs or uninstalls the pre-commit hook. Supports `--uninstall` (restores any saved prior hook). Default-on after init/upgrade.
- **`/adr-kit:upgrade`** (`skills/upgrade/SKILL.md`): guided v0.11 → v0.12 migration without re-running the heavy init audit. Detects v0.11 inline `## ADR Kit Rules` block and replaces with the v0.12 marker-bracketed stub, copies the guide file, installs the hook, and walks Accepted ADRs offering Enforcement-block backfill proposals one at a time.
- **`bin/adr-judge`**: declarative diff-vs-ADR engine. Parses fenced JSON `Enforcement` blocks from each Accepted ADR; applies `forbid_pattern` / `forbid_import` / `require_pattern` rules to the staged diff with file:line citations. ADRs with `llm_judge: true` and no declarative rules emit advisory entries (non-blocking). Exit codes mirror `bin/adr-lint` (0 / 1 / 2). Fast (sub-second on typical diffs), key-free, runs in any environment.
- **`bin/adr-audit`**: deterministic candidate scanner used by `/adr-kit:init`. Walks `src/` and `docs/`, emits a JSON list of decision-shaped artefacts (top-level dependencies, framework markers, build/CI tooling, documented decision narratives in README/AGENTS/CLAUDE/docs). One candidate per file (deduped) with up to 5 example snippets. Skips `docs/adr/`, `backlog/`, and the usual non-source directories by default.
- **`templates/adr-kit-guide.md`**: canonical project-side guide. Copied to `.claude/adr-kit-guide.md` by init/upgrade/setup. Plain markdown without Claude-Code-specific syntax — readable by any agent, hook, CI script, or evaluator. Includes the four verification gates, three operating modes, slash-command index, Enforcement-block grammar with examples, supersession workflow, and the seven review checks.
- **`templates/adr-template.md`**: the canonical ADR template with the optional `## Enforcement` section pre-stubbed.
- **`templates/githooks/pre-commit`**: pre-commit hook template. Resolves the latest installed plugin version dynamically (no hard-coded paths), so plugin upgrades don't break the hook. Degrades gracefully when the plugin cache is missing — never blocks a commit due to tooling drift. Honors `ADR_KIT_HOOK_DISABLE=1` for per-commit opt-out.
- **`schemas/adr-enforcement.schema.json`**: JSON Schema (draft-07) for the optional `## Enforcement` block in an ADR. Validated by `bin/adr-judge` when `jsonschema` is installed; basic shape checks always run.
- **`tests/test_adr_judge.py`**: 9 end-to-end tests covering violation detection, advisory entries for `llm_judge:true`-only ADRs, status-form parsing (period vs comma), path-glob filtering, malformed JSON handling, and clean-diff pass.
- **`tests/test_adr_audit.py`**: 7 end-to-end tests covering tooling marker detection, dependency extraction across manifest formats, doc decision-phrase grouping (one candidate per file, not per match), skip-glob behaviour, and `--output` writing.

### Changed

- **`skills/setup/SKILL.md`**: rewritten for v0.12. Detects v0.11-style inline `## ADR Kit Rules` and explicitly leaves it untouched (telling the user to run `/adr-kit:upgrade`). On fresh installs, writes the slim marker-bracketed stub to `CLAUDE.md` AND drops the canonical guide at `.claude/adr-kit-guide.md`. Idempotent across re-runs.
- **`agents/adr-generator.md`**: adds Step 3b — propose an `## Enforcement` block when the ADR has a code surface. Three patterns: declarative rules, `llm_judge: true`, or omit-with-explanation. Template extended with the optional Enforcement section. Cross-references expanded to point at new templates and the judge runner.
- **`instructions/adr.coding.md`**: adds rule 5 — Accepted ADRs SHOULD include an `## Enforcement` block when the rule is mechanically expressible.
- **`instructions/adr.review.md`**: header now reads "seven checks" (was "six"). Adds **Check 7**: Enforcement block is set appropriately on any new Accepted ADR with a code surface. Adds the "Missing Enforcement block" review-comment template. Adds the corresponding Definition-of-Done item.
- **`skills/adr/SKILL.md`**: adds "Companion skills and runners (v0.12+)" section indexing init/judge/install-hooks/upgrade/lint/migrate, plus an "Enforcement blocks (v0.12+)" section. Cross-links to `bin/adr-judge` as the canonical runner. Verification gates and supersession workflow remain the source of truth — every other skill delegates to them.
- **`schemas/adr-kit-config.schema.json`**: extended with a top-level `judge` object holding `skip_files` (project-wide path-glob exclusions for the judge), `advisory_only` (downgrade declarative violations to advisory during early adoption), and `max_diff_bytes` (skip pathologically large diffs).
- **`.claude-plugin/plugin.json`**: version bumped to 0.12.0; description rewritten to reflect the three modes.
- **`.claude-plugin/marketplace.json`**: plugin entry version bumped to 0.12.0; description updated.

### Backwards compatibility

- All v0.11 commands (`/adr-kit:adr`, `/adr-kit:lint`, `/adr-kit:migrate`, `/adr-kit:setup`) keep working unchanged. Existing tests pass byte-exact (15/15 baseline preserved).
- ADRs without an `## Enforcement` block are skipped silently by `bin/adr-judge` — zero false positives on legacy ADR sets.
- The pre-commit hook is opt-in: not installed unless the user runs `/adr-kit:init`, `/adr-kit:upgrade`, or `/adr-kit:install-hooks`.
- v0.11 inline `## ADR Kit Rules` sections in `CLAUDE.md` are detected and explicitly preserved by the new `/adr-kit:setup`. Migration to the v0.12 footprint is via `/adr-kit:upgrade` (explicit, never silent).
- Plugin re-fetch via `/plugin install adr-kit@rvdbreemen-adr-kit` upgrades to v0.12 without a marketplace re-add.

### Notes

- **Hook is default-on from v0.12 onwards.** `/adr-kit:init` and `/adr-kit:upgrade` install the pre-commit hook automatically — no prompt. Per-commit opt-out via `ADR_KIT_HOOK_DISABLE=1`. Permanent removal via `/adr-kit:install-hooks --uninstall`.
- **LLM judge is in-session-only.** The pre-commit hook is purely deterministic. ADRs with `llm_judge: true` produce advisory output at hook time; deeper review happens via `/adr-kit:judge` inside a Claude Code session, using the model already loaded for the user's work. No API-key plumbing in the hook environment.
- **Audit is one-shot, deep.** `/adr-kit:init` scans source + documentation in a single pass and walks the user through batches of 5–10 candidates. ADRs are generated with `Status: Accepted` because they reflect decisions already in effect. The user remains the gatekeeper — `init` never fabricates, never auto-approves.

## [0.11.0] - 2026-04-25

### Added

- **`/adr-kit:migrate`** (`skills/migrate/SKILL.md`): guided rewrite skill that brings legacy-shaped ADRs into the canonical-seven-section template enforced by `/adr-kit:lint`. User-only invocable (`disable-model-invocation: true`); never silent. Six named transformation patterns:
  - **Pattern A**: inline `**Status:** ...` / `**Date:** ...` / `**Supersedes:** ...` lines folded into a top-level `## Status` heading.
  - **Pattern B**: `### Alternatives considered` nested inside Context promoted to top-level `## Alternatives Considered` between Decision and Consequences.
  - **Pattern C**: `### Alternatives considered and rejected` nested inside Consequences promoted to top-level before Consequences.
  - **Pattern D**: `## Related` renamed to `## Related Decisions`, with external file paths / URLs / PR references split off into a new `## References` section.
  - **Pattern E**: missing `## References` section with no source content gets a `<!-- TODO: populate -->` placeholder. Never fabricates.
  - **Pattern F**: missing `## Alternatives Considered` with no source discussion gets a `<!-- TODO: document at least 2 alternatives -->` placeholder. Never fabricates.
- README "What it does" section gains entries for `/adr-kit:lint`, `bin/adr-lint`, and `/adr-kit:migrate`. The single-paragraph "the pieces work together" closing now mentions all four roles (skill, agent, lint, migrate, instructions).
- `.github/workflows/validate.yml` required-files set extended with `skills/migrate/SKILL.md`.

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.11.0.
- `.claude-plugin/marketplace.json` plugin entry version bumped to 0.11.0.

### Notes

- The skill is **read-then-confirm**: it always prints a per-file plan first ("Pattern A on ADR-007: promote inline Status to heading") and asks for explicit user confirmation before writing. No silent edits.
- The skill is **idempotent**: running migrate on an already-canonical ADR is a no-op.
- The skill **respects markers**: files with `<!-- adr-kit-lint: skip -->` are left untouched. Files with `<!-- adr-kit-lint: advisory -->` get a warning before migration (the marker becomes meaningless once the file is canonical-shaped).
- The skill **respects `template.required_sections`** in `.adr-kit.json`. If a project has codified a different template, migrate targets that.
- Out of scope on purpose: filename renaming (Consistency-FAILs), body-prose rewriting, auto-fabricating Alternatives or References content, deterministic Python CLI variant. Migration is judgement-heavy; same reasoning that put Evidence and Clarity gates as opt-in for `bin/adr-lint`.

## [0.10.1] - 2026-04-25

### Fixed

- `skills/lint/SKILL.md`: added `disable-model-invocation: true` to the frontmatter so the lint skill follows the same user-only invocation discipline as `skills/setup/SKILL.md`. Before this fix, `/lint` (without plugin prefix) appeared in Claude Code's autocomplete at the root namespace, and the skill was auto-invocable by Claude. With the fix, only the canonical `/adr-kit:lint` form is registered, matching `/adr-kit:setup` and giving the plugin a uniform invocation pattern. Lint is a deliberate user action (a checking tool, not a background helper), so disabling auto-invocation is the right discipline.

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.10.1.
- `.claude-plugin/marketplace.json` plugin entry version bumped to 0.10.1.

### Notes

- No skill body change. The lint logic (severity model, gate evaluation, output format) is identical to v0.10.0.
- No `bin/adr-lint` change. The deterministic CLI is independent of the skill's invocation discipline.

## [0.10.0] - 2026-04-25

### Added

- **`bin/adr-lint`**: standalone Python 3.8+ CLI for CI / pre-commit integration. Mirrors the deterministic gates of `/adr-kit:lint` (Completeness, Consistency by default; Evidence and Clarity available behind `--gates`). Reads the same `.adr-kit.json` policy, supports per-ADR markers, and produces both human-readable and JSON output. Exit codes: `0` (no FAIL), `1` (FAIL detected), `2` (config or input error). Stdlib-only; `jsonschema` auto-detected for deeper config validation.
- `schemas/adr-kit-config.schema.json`: JSON Schema (draft-07) for `docs/adr/.adr-kit.json`. Pattern-validates `strict_from` (`^ADR-\d{3}$`), enum-validates `severity` values, validates `template.required_sections` heading shape. Used by `bin/adr-lint` when `jsonschema` is installed; falls back to basic checks otherwise.
- `tests/`: pytest suite with 15 tests covering every FAIL pattern and severity combination. Subprocess-based: each test runs `adr-lint --format json` and asserts on the JSON output, so the public interface is exercised, not internal helpers. Fixtures: `canonical/`, `missing-headings/`, `bad-filename/`, `heading-mismatch/`, `marker-skip/`, `marker-advisory/`, `marker-skip-gate/`, `with-policy/` (strict_from boundary), `bad-config/`.
- `.github/workflows/adr-lint-self.yml`: dual job that runs `pytest` and a smoke test against `examples/`. Runs on push and pull request to `main`.
- `README.md` "CI integration" section between "Configuration" and "FAQ", with a copy-paste-ready GitHub Actions snippet that downstream users can drop into their own workflow to block PRs on FAIL.

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.10.0.
- `.claude-plugin/marketplace.json` plugin entry version bumped to 0.10.0.

### Notes

- The CLI does not replace the skill. The skill stays canonical for nuanced review; the CLI is for unattended CI gates. They are designed to agree on Completeness and Consistency. They can legitimately disagree on Evidence and Clarity, where Claude's judgement is structurally better than a regex.
- Smoke-tested locally against a representative 87-ADR real-world project (the same set used in the v0.9.0 smoke test): produces 7 PASS / 80 ADVISORY / 0 FAIL with exit code 0 and parseable JSON. Matches the skill's output exactly.
- Future work: `/adr-kit:migrate` (interactive helper to rewrite legacy ADRs into the canonical template) is still planned for a later release; v0.10.0 is scoped to the CLI alone.

## [0.9.0] - 2026-04-25

### Added

- **Scoped lint with grandfathering.** `/adr-kit:lint` now reads an optional project-level config file at `docs/adr/.adr-kit.json` and per-file HTML-comment markers inside individual ADRs. The two mechanisms together let a project apply the four gates surgically: strict on new ADRs, advisory on legacy ones, ignored on archived ones.
- `skills/lint/SKILL.md`:
  - New "Configuration" section documenting the `.adr-kit.json` schema (`strict_from`, `ignore`, `severity` per-gate overrides, `template.required_sections` override).
  - New "Per-ADR markers" subsection: `<!-- adr-kit-lint: skip -->` / `skip <gates>` / `advisory` tell the linter how to treat a single ADR without a project-wide config.
  - New "Severity decision tree" (Graphviz block) that documents the precedence rules: ignore beats markers, markers beat config, and within config the precedence is `always_strict` > `always_advisory` > `advisory_before_strict_from`.
  - Output format gains an ADVISORY tier between PASS and FAIL. Single-file output reports each finding with the reason it was downgraded (e.g. "ADVISORY: ADR predates strict_from=ADR-042"). Directory-tree output groups files into PASS strictly / ADVISORY only / FAIL / SKIPPED counts.
  - Reporting section: the bottom-line "next step" sentence now always points at a FAIL, never an ADVISORY. ADVISORY is informational; FAIL is what the user is asked to act on.
  - Completeness gate now respects `template.required_sections` when set in the config; otherwise the canonical seven still apply.
- `examples/.adr-kit.sample.json`: fully annotated example config with `_comment` keys explaining each field.
- `examples/ADR-sample-003-grandfathered-legacy.md`: a worked legacy-template ADR using the `<!-- adr-kit-lint: advisory -->` marker, demonstrating how a pre-canonical ADR coexists with strict gating on newer ADRs.
- `README.md` gains a "Configuration" section between "ADR conventions" and "FAQ" covering both mechanisms with copy-paste-ready snippets.
- `.github/workflows/validate.yml` required-files set extended with the two new example files.

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.9.0.
- `.claude-plugin/marketplace.json` plugin entry version bumped to 0.9.0.

### Notes

- Backwards compatible: when no `.adr-kit.json` and no per-ADR markers are present, behaviour is identical to v0.8.0 (everything strict, FAIL on any gate failure).
- Defaults are safe: Consistency stays `always_strict` by default even when `strict_from` is set, because filename / heading mismatches and duplicate numbers are real bugs regardless of when the ADR was written.
- Future work: `/adr-kit:migrate` (v0.10.0) will help projects mass-rewrite legacy ADRs into the canonical template; `severity_profile` presets (v0.11.0) will offer named bundles instead of per-gate configuration.

## [0.8.0] - 2026-04-25

### Added

- `schemas/plugin.json.schema.json`: hand-curated JSON Schema (draft-07) for `.claude-plugin/plugin.json`. Validates the documented field types and rejects the historical bug pattern that broke install in v0.7.2 (`repository` as object). The schema's top-level `description` field documents which historical bugs each constraint prevents.
- `schemas/marketplace.json.schema.json`: JSON Schema (draft-07) for `.claude-plugin/marketplace.json`. Required fields: `name`, `description`, `owner` (object with `name`), `plugins` (non-empty array). Each plugin entry requires `name`, `source`, `version`, `description`. The schema's top-level description references the v0.7.1 missing-manifest incident.
- `.github/workflows/validate.yml`: two new CI steps that run `ajv-cli` (draft-07, with `ajv-formats`) against both manifests on every push and pull request. The workflow now fails the build on schema violations, not just JSON syntax errors. `marketplace.json` was added to the required-files set; `schemas/plugin.json.schema.json` and `schemas/marketplace.json.schema.json` are now also required (so a future contributor cannot accidentally remove the schemas without CI noticing). `skills/lint/SKILL.md` was also added to the required-files list (was missing since v0.7.0).
- `CONTRIBUTING.md` "Pre-release smoke test" section: a 5-step manual checklist that release authors run in a fresh Claude Code session before tagging. Steps cover `claude --plugin-dir`, `/plugin`, `/help`, `/adr-kit:setup` (idempotency check), and `/adr-kit:lint`. Schema validation catches manifest field-type bugs; the smoke test catches the install-path bugs schema validation cannot reach.

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.8.0.
- `.claude-plugin/marketplace.json` plugin entry version bumped to 0.8.0 (also corrects the v0.7.1/v0.7.2 drift where the marketplace manifest still listed 0.7.1 while the plugin manifest had advanced to 0.7.2).
- `CONTRIBUTING.md` "Validation" section now mentions the new schema validation step alongside the existing `jq empty` and required-files checks.

### Notes

- This release closes the post-mortem from the v0.7.1 and v0.7.2 install-side regressions. The schemas are sized to current manifest fields only; they are not a substitute for the official Claude Code plugin manifest spec, which (when published) will replace this hand-curated pair. The schemas are best-effort regression tests for the bugs we have actually shipped.

## [0.7.2] - 2026-04-25

### Fixed

- **`plugin.json` `repository` field rejected by Claude Code plugin manifest schema.** Versions v0.1.0 through v0.7.1 declared `repository` as an object (`{ "type": "git", "url": "..." }`), borrowing the convention from npm's `package.json`. Claude Code's plugin manifest schema instead expects a plain URL string for `repository`. Result: after fixing the marketplace.json issue in v0.7.1, `/plugin install adr-kit@rvdbreemen-adr-kit` failed with `Validation errors: repository: Invalid input: expected string, received object`.
- Changed `repository` to a plain URL string: `"https://github.com/rvdbreemen/adr-kit.git"`.
- The CI workflow added in v0.5.0 catches JSON syntax errors via `jq empty` but does not validate the manifest schema. A follow-up task (post-v1.0.0) will add schema validation against the official Claude Code plugin manifest spec.

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.7.2.

## [0.7.1] - 2026-04-25

### Fixed

- **Plugin install via marketplace was incomplete in v0.1.0 through v0.7.0.** The repo had `.claude-plugin/plugin.json` (the per-plugin manifest) but lacked `.claude-plugin/marketplace.json` (the marketplace manifest). Without the marketplace manifest, `/plugin marketplace add rvdbreemen/adr-kit` could not register the marketplace under the `rvdbreemen-adr-kit` name, and the subsequent `/plugin install adr-kit@rvdbreemen-adr-kit` failed with "Unknown command" errors when users tried `/adr-kit:setup` afterwards.
- Adds `.claude-plugin/marketplace.json` declaring `name: "rvdbreemen-adr-kit"`, owner metadata, and one plugin entry (`adr-kit`, source `./`, version 0.7.1).
- After upgrading: existing installations should remove and re-add the marketplace, then re-install:
  ```
  /plugin marketplace remove rvdbreemen-adr-kit
  /plugin marketplace add rvdbreemen/adr-kit
  /plugin install adr-kit@rvdbreemen-adr-kit
  /reload-plugins
  /adr-kit:setup
  ```

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.7.1.

## [0.7.0] - 2026-04-25

### Added

- `skills/lint/SKILL.md`: new `/adr-kit:lint` slash command. Reads every `ADR-*.md` in `docs/adr/` (or a single file or directory passed as argument) and reports per-file, per-gate pass/fail against the four verification gates with file:line citations for failures. Read-only (`allowed-tools: [Read, Glob, Grep]`). Lifts the gates from "documented" to "programmatically enforced" against existing ADRs.
- `ROADMAP.md`: documents Status, criteria for v1.0.0 (90 days field time, 5 unrelated installs, gate-based PR block in real review, migration guide), Planned features (signals not commitments), Out-of-scope non-goals (multi-language, visualisation, bundling, Anthropic-specific features, framework wrapping), and how decisions get made (the maintainer eats the dog food).
- `MIGRATING-FROM-ADR-SKILL.md`: guide for users of Jim van den Breemen's adr-skill explaining the overlap (same gates, same template, same patterns), the differences (skill-only vs full toolkit), and three migration paths (replace, co-install, stay). Slash commands are namespaced by plugin prefix so co-installation does not cause conflicts.
- README: optional fifth slash command (`/adr-kit:lint`) added to the Install section. New Quickstart bullet for "Audit existing ADRs". New "Project resources" section linking to ROADMAP, MIGRATING, CHANGELOG, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT.
- `plugin.json` keywords add `lint`. Description expanded to mention the lint and setup commands.

## [0.6.0] - 2026-04-25

### Added

- `.github/ISSUE_TEMPLATE/bug.yml`: structured bug-report form with fields for tool/version, adr-kit version, reproduction steps, expected vs actual behaviour.
- `.github/ISSUE_TEMPLATE/feature_request.yml`: structured feature-request form that requires alternatives-considered (mirroring the same discipline the skill asks of an ADR).
- `.github/pull_request_template.md`: PR checklist that explicitly references the four verification gates (Completeness, Evidence, Clarity, Consistency) and the CHANGELOG-update requirement.
- `SECURITY.md`: minimal security-disclosure policy (no secrets handled, file-write scope is constrained, reports go to maintainer email).
- `CODE_OF_CONDUCT.md`: short adoption-by-reference of Contributor Covenant 2.1, with reporting email and scope; full canonical text lives at the upstream URL.
- `examples/ADR-sample-001-postgresql-for-event-store.md`: worked-example ADR that passes all four verification gates. Fictional but realistic decision (PostgreSQL vs Kafka vs EventStoreDB for an event store) with concrete measurements, alternatives, and risks-with-mitigations.
- `examples/ADR-sample-002-evidence-gate-before-after.md`: same decision (sync vs async webhook delivery) written twice, once failing the Evidence gate and once passing. Illustrates what "replace bare adjectives with measurements" looks like in practice.
- `README.md` FAQ section: where ADRs are stored, how to customize the conventions, what to do if the project already has ADRs in another format, whether the skill auto-creates ADRs, whether this is an Anthropic product.
- `README.md` Comparison section: short table contrasting `adr-kit` with a plain ADR template along format, pre-flight discipline, acceptance bar, code-review integration, tool integration, and onboarding axes.

## [0.5.0] - 2026-04-25

### Added

- `.github/workflows/validate.yml`: GitHub Actions CI that validates `plugin.json` (`jq empty`), enforces the required-files set, asserts that `plugin.json` version matches the top entry of `CHANGELOG.md`, and runs `markdownlint` over skills, agents, instructions, and examples.
- `CONTRIBUTING.md`: dev loop (`claude --plugin-dir .`), how to add a skill or agent, version-bump and release procedure, code style (no em dashes, English, kebab-case file names), validation, and issue-reporting guidelines.
- `argument-hint: "[short title of the decision]"` on `skills/adr/SKILL.md` so users see the expected slash-command syntax in the picker.
- `allowed-tools: [Read, Write, Edit]` on `skills/setup/SKILL.md` so the one-time `/adr-kit:setup` does not prompt for tool permission.
- `homepage` (already present), enriched `keywords` list (covers Claude Cowork, Cursor, Copilot, Codex, agent-skills, AI coding assistant, decision-records, verification-gates, anti-rationalization), and an empty `dependencies: []` placeholder in `.claude-plugin/plugin.json`.

## [0.4.0] - 2026-04-25

### Added

- `CHANGELOG.md` in Keep a Changelog format. Retroactively documents v0.1.0, v0.2.0, and v0.3.0.
- `.gitignore` with sensible defaults for Claude Code plugin development (OS files, editor metadata, common cache directories).

### Changed

- Adopted the `adr-kit--vX.Y.Z` git tag convention that `claude plugin tag` expects. Existing legacy tags (`v0.1.0`, `v0.2.0`, `v0.3.0`) remain in place so pinned installs do not break; they are also mirrored to the new naming on the same commits, and the new convention applies from v0.4.0 forward.

## [0.3.0] - 2026-04-25

### Added

- `/adr-kit:setup` slash command via `skills/setup/SKILL.md`. One-time per project, idempotent: appends an "ADR Kit Rules" section to the project's `CLAUDE.md`, creates `CLAUDE.md` if it does not exist, skips if the section is already present.
- The install flow in `README.md` and `INSTALL.md` now lists four slash commands (`marketplace add`, `install`, `reload-plugins`, `setup`).

## [0.2.0] - 2026-04-25

### Added

- Native Claude Code plugin support via `.claude-plugin/plugin.json` manifest.
- Plugin install path: `/plugin marketplace add rvdbreemen/adr-kit` + `/plugin install adr-kit@rvdbreemen-adr-kit` + `/reload-plugins`.

### Changed

- **Breaking for non-Claude-Code tools**: `SKILL.md` source path moved from `adr-kit/SKILL.md` to `adr-kit/skills/adr/SKILL.md` to match the Claude Code plugin layout. Destination paths in `.claude/`, `.cursor/`, `.github/`, `.codex/` are unchanged. `INSTALL.md` and the bundled install script updated accordingly.

## [0.2.0-attribution] - 2026-04-25

### Changed

- `README.md` Credits section and `SKILL.md` credit paragraphs now name [Jim van den Breemen's adr-skill](https://github.com/Jvdbreemen/adr-skill) explicitly as the source where the anti-rationalization guards and verification gates patterns were first combined into a single ADR skill. The original pattern sources (`addyosmani/agent-skills`, `trailofbits/skills`) remain credited as upstream.

## [0.1.0] - 2026-04-25

### Added

- Initial public release of `adr-kit`.
- `SKILL.md`: comprehensive ADR guide with anti-rationalization guards (a 9-row excuse / counter-argument table) and four named verification gates (Completeness, Evidence, Clarity, Consistency).
- `agents/adr-generator.md`: focused subagent for authoring a complete ADR file given a decision and context.
- `instructions/adr.coding.md`: ADR rules during coding work, including implementation checklist and supersession workflow.
- `instructions/adr.review.md`: six named ADR checks for code review with concrete review-comment templates.
- `examples/ADR-template.md`: clean template to copy into new ADRs.
- `INSTALL.md`: per-tool install paths for Claude Code, Claude Cowork, Cursor, GitHub Copilot, and OpenAI Codex CLI, plus a one-shot helper script and a generic fallback.
- `README.md`, `LICENSE` (MIT).

### Credits

The anti-rationalization guards pattern is adapted from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills). The verification gates pattern is adapted from [trailofbits/skills](https://github.com/trailofbits/skills). Both patterns were first combined into a single ADR skill by [Jim van den Breemen's adr-skill](https://github.com/Jvdbreemen/adr-skill); `adr-kit` builds on that combination.

[Unreleased]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.11.0...HEAD
[0.11.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.10.1...adr-kit--v0.11.0
[0.10.1]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.10.0...adr-kit--v0.10.1
[0.10.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.9.0...adr-kit--v0.10.0
[0.9.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.8.0...adr-kit--v0.9.0
[0.8.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.7.2...adr-kit--v0.8.0
[0.7.2]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.7.1...adr-kit--v0.7.2
[0.7.1]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.7.0...adr-kit--v0.7.1
[0.7.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.6.0...adr-kit--v0.7.0
[0.6.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.5.0...adr-kit--v0.6.0
[0.5.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.4.0...adr-kit--v0.5.0
[0.4.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.3.0...adr-kit--v0.4.0
[0.3.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.1.0
