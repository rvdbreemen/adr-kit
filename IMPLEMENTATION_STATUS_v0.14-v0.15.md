# adr-kit v0.14-v0.15 Implementation Status

Status: Phase 1 implemented on `v0.14-dev`; later-phase scaffolding is not
accepted as complete without functional tests.
Date: 2026-05-26
Target release: v0.14.0 for Phase 1

## Phase 1: v0.14.0

### Feature 1: Append-Only Status History

Implemented:

- `templates/adr-template.md` includes a documented `status_history` YAML list.
- `bin/adr-judge` implements `parse_status_history()` and
  `append_to_status_history()`.
- `bin/adr-judge --migrate-status-history` deliberately migrates legacy ADRs
  by appending an initial transition.
- `bin/adr-lint` runs the additive `audit` gate by default for ADRs that have
  a status history; legacy ADRs without the block continue to pass.
- `tests/test_adr_status_history.py` supplies real behavioral and budget tests.

Safety decision:

- Migration is explicit rather than silently performed during normal judge
  runs. A pre-commit checker must remain read-only; otherwise it could inspect
  staged content while leaving unstaged ADR edits behind.

### Feature 2: Automated Retirement Detection

Implemented:

- `bin/adr-retire` evaluates four bounded deterministic signals: status age,
  explicit backticked technology removal, broken supersession references, and
  risky Enforcement patterns.
- Scores are averaged into `RETIRE`, `REVIEW`, `MONITOR`, or `KEEP`
  recommendations and emitted as JSON, Markdown, or text.
- `skills/retire/SKILL.md` exposes a read-only guided audit.
- `.github/workflows/adr-retire-audit.yml` demonstrates weekly issue creation
  when candidates reach the reporting threshold.
- `tests/test_adr_retire.py` covers detectors, formats, filtering, errors, and
  the 30-ADR performance target.

## Later Phases

The earlier parallel-delivery commit introduced scaffolding for Features 3-8.
Those files are not considered completed features until their Backlog
acceptance criteria are implemented and verified with non-placeholder tests.

## Verification Targets

- Status-history parse loop over 30 ADRs: below 50 ms.
- Status-history append: below 100 ms.
- Retirement audit over 30 ADRs: below 2 seconds.
- Existing v0.13 test suite remains passing.

Branch: `v0.14-dev`
