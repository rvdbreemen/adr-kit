# adr-kit v0.14.0

> First major feature release since v0.13.x. Delivers Phase 1–4 of the v0.14–v0.15 roadmap: governance backbone, intelligence layer, enforcement quality tools, and observability.

## What's new

### Phase 1 — Governance backbone

- **Append-only status history**: `bin/adr-judge` now parses and appends immutable `status_history` YAML entries to ADRs. Each transition records `date`, `status`, `changed_by`, `reason`, and `changed_via`. Run `--migrate-status-history` to backfill legacy ADRs. `bin/adr-lint` validates histories via a new `audit` gate (on by default), keeping unmigrated v0.13 ADRs compatible.
- **Automated retirement detection**: new `bin/adr-retire` tool and `/adr-kit:retire` skill score retirement candidates on four signals: staleness, technology disappearance, broken supersession references, and risky policy patterns. Optional `adr-retire-audit.yml` GitHub Actions workflow runs weekly.

### Phase 2 — Intelligence layer

- **Profiling and dry-run**: `bin/adr-judge --profile` emits per-ADR timing breakdowns. `--dry-run-enforcement ADR-NNN` tests a single ADR against a staged diff without blocking.
- **Semantic relevance ranking**: new `bin/adr-context` tool ranks ADRs for a task query using five weighted heuristic signals: keyword match (40%), domain tag (25%), related decisions (15%), acceptance status (10%), recency (10%). Weights configurable in `.adr-kit.json`. Injected into `agents/adr-generator.md` context-loading step.

### Phase 3 — Enforcement quality

- **Policy block validation**: `bin/adr-lint` gains `--gates policy` and `--gates quality` (both opt-in). The policy gate validates Enforcement JSON against `schemas/adr-enforcement.schema.json`, compiles all regex patterns, and warns on anti-patterns. The quality gate flags vague language, missing metrics, and too few alternatives.
- **Standalone validation script generation**: new `bin/adr-generate-scripts` produces self-contained `validate.py` (Python stdlib only) and `validate.sh` scripts — embed in any CI pipeline without adr-kit as a dependency.

### Phase 4 — Observability and agent guidance

- **ADR health dashboard**: new `bin/adr-status` reports total count, status breakdown, average age, enforcement health per ADR, and top retirement candidates. `--format json|markdown|table`.
- **Quality scoring**: new `bin/adr-quality` grades each ADR A–D via four weighted gates: Completeness (40%), Evidence (20%), Clarity (20%), Consistency (20%). Returns structured JSON with per-gate issue codes. Exits 1 when grade < B.
- **Agent decision tree**: `agents/adr-generator.md` gains "When to Create an ADR" decision tree and post-decision quality check.

### Cross-cutting

- **Python 3 availability check**: `skills/init/SKILL.md` and the pre-commit hook both check for Python 3.9+ and provide guided installation for macOS (Homebrew), Linux (apt/dnf/pacman), and Windows (winget).
- **`.adr-kit.json`** extended with `context.weights`, `retirement.*`, and timeout fields.
- **222 tests passing**, 2 skipped.

## Upgrade

No breaking changes from v0.13.x. Existing ADRs without `status_history` blocks remain compatible — the new `audit` gate in `bin/adr-lint` only validates blocks that are present, and skips files that don't have one yet.

To add status history to existing ADRs:
```bash
python bin/adr-judge --adr-dir docs/adr --migrate-status-history
```
