# adr-kit v0.10.0

Adds `bin/adr-lint`, a deterministic Python CLI that pairs with the `/adr-kit:lint` Claude Code skill. The skill is for human-in-the-loop review (judgement-based gates rely on Claude). The CLI is for CI / pre-commit / batch validation: it runs unattended, exits with a status code, and reads the same `.adr-kit.json` policy.

## What is new

### `bin/adr-lint`

Single-file Python 3.8+ CLI. Stdlib only by default; `jsonschema` auto-detected for deeper config validation. Read-only by design.

```bash
python bin/adr-lint                        # docs/adr/, default gates: completeness,consistency
python bin/adr-lint --gates all-gates      # opt into evidence and clarity (heuristic)
python bin/adr-lint --strict-from ADR-100  # override config strict_from
python bin/adr-lint --format json          # machine-readable output
```

Exit codes:

- `0`: no FAIL (PASS / ADVISORY counts may be non-zero).
- `1`: at least one FAIL.
- `2`: config or input error (malformed `.adr-kit.json`, unknown gate, missing path).

### `schemas/adr-kit-config.schema.json`

JSON Schema (draft-07) for `docs/adr/.adr-kit.json`. Pattern-validates `strict_from`, enum-validates severity values, validates `template.required_sections` heading shape. Used by the CLI when `jsonschema` is installed; basic checks fall back when it is not.

### Test suite

`tests/test_adr_lint.py` runs 15 subprocess-based tests against fixtures in `tests/fixtures/`. Each test exercises a known FAIL or marker pattern and asserts on JSON output plus exit code. Run via `pytest tests/`.

Fixture coverage: `canonical/`, `missing-headings/`, `bad-filename/`, `heading-mismatch/`, `marker-skip/`, `marker-advisory/`, `marker-skip-gate/`, `with-policy/` (strict_from boundary), `bad-config/`.

### CI workflow

`.github/workflows/adr-lint-self.yml` runs both the pytest suite and a smoke test against `examples/` on every push and pull request to `main`. Demonstrates the GitHub Actions pattern downstream users can copy.

The existing `.github/workflows/validate.yml` was extended to require `bin/adr-lint`, `schemas/adr-kit-config.schema.json`, and `tests/test_adr_lint.py` in the file presence check, so future contributors cannot accidentally remove them without CI noticing.

### README "CI integration" section

New section between "Configuration" and "FAQ" with a copy-paste-ready GitHub Actions snippet that fetches `bin/adr-lint` from this repo's `main` branch and runs it as a PR merge gate. Stdlib-only means no `pip install` needed.

## Smoke test

Validated end-to-end against a representative real-world ADR set (87 files, mixed legacy + canonical, with a `.adr-kit.json` policy that sets `strict_from` mid-range):

```
$ bin/adr-lint /path/to/your-project/docs/adr/
PASS strictly:  7
ADVISORY only: 80
FAIL:           0
exit 0
```

Matches the skill's output on the same set exactly. JSON format `--format json` parseable by `jq` for downstream tooling.

## Skill vs CLI

| | Skill (`/adr-kit:lint`) | CLI (`bin/adr-lint`) |
|---|---|---|
| Where it runs | Claude Code session | Anywhere with Python 3.8+ |
| Default gates | All four (Completeness, Evidence, Clarity, Consistency) | Two deterministic ones (Completeness, Consistency) |
| Evidence and Clarity | Judgement-based, nuanced | Heuristic, opt-in via `--gates`, may produce false positives |
| Use case | Code review, ADR drafting | CI gate, pre-commit hook, batch validation |
| Output | Markdown human-readable | Human or JSON (`--format`) |

The two are designed to agree on Completeness and Consistency. They can legitimately disagree on Evidence and Clarity by design.

## Backwards compatibility

The CLI is additive. Existing users of `/adr-kit:lint` see no change. The `.adr-kit.json` policy file from v0.9.0 is consumed by both tools.

## Out of scope (future work)

- `/adr-kit:migrate` interactive helper for mass-rewriting legacy ADRs into the canonical template. Conceptually different work; planned as a separate release.
- Pre-commit hook YAML example (a thin wrapper around the GH Actions snippet; can land in v0.10.x).
- Pip-installable package (`pyproject.toml`); single-file script first, package later if demand surfaces.

## Install / upgrade

Existing installations:

```
/plugin marketplace remove rvdbreemen-adr-kit
/plugin marketplace add rvdbreemen/adr-kit
/plugin install adr-kit@rvdbreemen-adr-kit
/reload-plugins
```

The CLI lives in the cloned plugin directory at `bin/adr-lint`; you can symlink it onto your `PATH` or invoke it as `python /path/to/cache/bin/adr-lint`.

## Refs

- Backlog task: TASK-422 (adr-lint standalone CLI).
- Pairs with: TASK-420 (v0.9.0 scoped lint with grandfathering); the CLI consumes the same policy file.
