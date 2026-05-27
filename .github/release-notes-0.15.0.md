# adr-kit v0.15.0

> Quality release: 37 findings from a multi-agent security, performance, and architecture review of v0.14.0, all resolved.

## Security fixes

- **`llm_cmd` allowlist** (`bin/adr-judge`): `judge.llm_cmd` in `.adr-kit.json` is now validated against an allowlist of known Claude CLI binaries. A repo-committed malicious `llm_cmd` no longer silently executes arbitrary binaries on every contributor's commit. Env var `ADR_KIT_LLM_CMD` and `--llm-cmd` CLI flag remain unrestricted (operator-controlled).
- **ReDoS guard** (`bin/adr-judge`): ADR-controlled regex patterns are now executed inside a 1-second `threading.Timer` timeout. A crafted pattern that would hang the pre-commit hook indefinitely now produces an ADVISORY finding instead.
- **Path traversal** (`bin/adr-judge`): `require_pattern` rules now validate that diff-derived file paths resolve under the repository root. Absolute paths and `..` sequences are rejected.
- **LLM debug output gated** (`bin/adr-judge`): verbose LLM error payloads (which could contain prompt contents including staged diffs) are now hidden behind `ADR_KIT_DEBUG=1`. Default messages are generic.
- **Generated shell script — ERE validation** (`bin/adr-generate-scripts`): `validate.sh` now tests each regex pattern against POSIX ERE at startup and warns loudly if any pattern is incompatible, rather than silently passing all lines.
- **Generated shell script — `printf` fix** (`bin/adr-generate-scripts`): replaced `echo "$line"` with `printf '%s\n' "$line"` to avoid backslash interpretation on `xpg_echo` shells.
- **Pre-commit hook glob** (`templates/githooks/pre-commit`): replaced `ls -d | sort -V` path resolution with a bash `nullglob` array, closing a path-with-spaces injection vector.
- **`adr-retire` symlink traversal** (`bin/adr-retire`): replaced unbounded `rglob('*')` with `os.walk(followlinks=False)` and a 50,000-file cap.

## Performance improvements

- **`glob_to_regex` caching** (`bin/adr-judge`): module-level cache eliminates O(ADRs × rules × files × globs) redundant `re.compile()` calls — up to 100,000 per commit on a large repo.
- **JSON schema singleton** (`bin/adr-judge`, `bin/adr-lint`): `schemas/adr-enforcement.schema.json` is compiled into a `Draft7Validator` once per process instead of once per ADR.
- **Section regex precompilation** (`bin/adr-lint`, `bin/adr-quality`): `REQUIRED_SECTIONS` heading patterns compiled at module load.
- **`adr-status` single-pass parsing**: new `AdrRecord` dataclass means each ADR is read once; all formatters reuse the cached record. Eliminates 500–700 redundant regex scans on a 100-ADR repository.
- **Pre-commit diff streaming**: replaced `DIFF=$(git diff ...)` buffering with direct pipe to `adr-judge` — no intermediate memory allocation for large diffs.
- **`validate.sh` single-pass grep**: rewritten from O(lines × rules × subprocess_spawn) to O(rules) spawns via a single-pass `grep -nE` per rule.
- **`adr-context` compiled regexes**: domain inference and metadata extraction now use module-level compiled patterns instead of per-ADR inline `re.search()`.
- **`adr-quality` compiled gate patterns**: section presence/body patterns and acronym regex compiled at module load.

## Architecture improvements

- **Structured quality issues** (`bin/adr-quality`): `gate_*()` functions return `QualityIssue` dataclasses with stable `code`, `detail`, `severity` fields. JSON output now includes machine-readable issue codes (`MISSING_SECTION`, `NO_REFERENCES`, `VAGUE_LANGUAGE`, etc.).
- **Unified vague-language list**: `bin/adr-lint` and `bin/adr-quality` now share an identical 8-word canonical set — same feedback from both tools.
- **Quality gate boundary documented**: `agents/adr-generator.md` and `bin/adr-lint`'s docstring now clearly state that `adr-lint` and `bin/adr-quality` run different gate sets. Passing one does not guarantee passing the other.
- **Schema extended**: `schemas/adr-kit-config.schema.json` now documents the `context` and `retirement` top-level config blocks introduced in v0.14.0.
- **`adr-status` — "amended" status**: `by_status` histogram now correctly buckets ADRs with `Amended by ADR-NNN` status. `CANONICAL_STATUSES` constant added.
- **`adr-context` — silent errors fixed**: `except Exception: pass` replaced with a `stderr` warning so malformed ADRs surface rather than silently disappearing from rankings.
- **CLI consistency**: `bin/adr-retire` default format changed from `json` to `text`; `bin/adr-lint` accepts `text` as an alias for `human`.

## Testing

- **3 new `@pytest.mark.slow` wall-clock tests**: adr-judge on 50 ADRs (<3 s), adr-status on 50 ADRs (<500 ms), adr-context on 50 ADRs (<600 ms).
- **`pytest.ini`** added to register the `slow` marker.
- **225 tests passing**, 2 skipped (Windows shell-script execution).

## Upgrade

No breaking changes from v0.14.0. The `QualityIssue` JSON format change in `bin/adr-quality` is additive — the new fields (`code`, `severity`) are additions alongside the existing `message` field.

One opt-in cleanup: if you were using `min_relevance_threshold` in `.adr-kit.json` for `bin/adr-context`, rename it to `min_score`.
