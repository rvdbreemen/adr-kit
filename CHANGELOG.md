# Changelog

All notable changes to `adr-kit` are documented in this file. The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
