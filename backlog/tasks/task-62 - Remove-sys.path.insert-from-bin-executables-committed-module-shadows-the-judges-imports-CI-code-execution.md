---
id: TASK-62
title: >-
  Remove sys.path.insert from bin/ executables: committed module shadows the
  judge's imports (CI code execution)
status: Done
assignee: []
created_date: '2026-07-30 18:31'
updated_date: '2026-07-30 21:25'
labels:
  - security
  - judge
  - ci
  - review-finding
dependencies: []
references:
  - .full-review/02-security-performance.md
  - .github/actions/adr-judge/action.yml
modified_files:
  - bin/adr-judge
  - .github/workflows/adr-judge-self.yml
  - .github/actions/adr-judge/action.yml
  - tests/test_adr_judge_security.py
priority: high
ordinal: 67500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found by the Phase 2 security audit, reproduced end to end, and the CI vector independently confirmed by reading the workflow and action. See `.full-review/02-security-performance.md` finding F1. CWE-427 (Uncontrolled Search Path Element), CWE-94.

`bin/adr-judge:53-55` prepends its own directory to `sys.path` ahead of the standard library and site-packages:

```python
_BIN_DIR = Path(__file__).resolve().parent
if str(_BIN_DIR) not in sys.path:
    sys.path.insert(0, str(_BIN_DIR))
```

Every import the judge performs then resolves from that directory first, including the lazy `import jsonschema` at `:101`. If `_BIN_DIR` is a directory an attacker can commit into, a committed module shadowing any imported name executes as code. This is on the ALWAYS-ON declarative path, not gated behind `judge.llm_enabled`.

**Reachability is the whole finding.** `_BIN_DIR` is the directory of the running `adr-judge`, not the repository under test.

- Standard downstream install: the hook resolves the judge to the plugin cache (`.githooks/pre-commit:84-136`), so a downstream repo's `bin/jsonschema.py` is NOT on the path. Reproduced: payload did not execute. Downstream is safe from this vector.
- Self-hosted, vendored, or fork-CI: `_BIN_DIR` is the repository's own `bin/`. Reproduced end to end: a committed `bin/jsonschema.py` wrote its marker and returned a stub validator while the judge ran normally and exited on the real violation, so nothing looks unusual.

**The CI vector, verified in this repository:**

1. `.github/workflows/adr-judge-self.yml` triggers on `pull_request` targeting `main` — every PR, including from forks.
2. `actions/checkout@v4` with `fetch-depth: 0` checks out the PR code.
3. `.github/actions/adr-judge/action.yml:63` sets `JUDGE="${GITHUB_ACTION_PATH}/../../../bin/adr-judge"` — the judge FROM THE PR CHECKOUT.
4. That judge inserts the PR's own `bin/` at `sys.path[0]`.
5. A PR adding `bin/jsonschema.py` gets it imported during Enforcement validation, executing attacker code on the runner.

The attacker here is anyone who can open a pull request — an external, lower-trust actor, not a committer. That is why this outranks the other findings. Blast radius is bounded because `pull_request` (not `pull_request_target`) runs with a read-only token and without secrets for forks, which is why it is High rather than Critical. It still means arbitrary code on the runner and a forgeable judge verdict, which makes the self-dogfood check meaningless.

Any downstream repository that vendors `bin/` or uses `uses: ./.github/actions/adr-judge` inherits the same vector.

**It also defeats CPython's own mitigation.** Reproduced under `python -P` / `PYTHONSAFEPATH=1`: the payload still executes, because the explicit `sys.path.insert` re-adds the directory that `-P` removed.

**Scope.** This is the house pattern: roughly 16 of the executables in `bin/` do the same thing, because the extensionless scripts cannot be imported and this is the stdlib-only way to share sibling `adr_*.py` modules. The fix should cover the pattern, not just `adr-judge`.

**Remediation (stdlib-only).** Load sibling modules by explicit file location so the directory never becomes importable:

```python
import importlib.util
from pathlib import Path

_BIN_DIR = Path(__file__).resolve().parent

def _load_sibling(mod_name):
    spec = importlib.util.spec_from_file_location(mod_name, _BIN_DIR / f"{mod_name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
```

Ten test files already use `importlib.util.spec_from_file_location` for extensionless siblings, so the mechanism is proven in this codebase. If the flat `sys.path` approach must stay, at minimum use `append` rather than `insert(0, ...)` so stdlib and site-packages win, and never allow an optional dependency name to be shadowed from the judge's own directory.

Consider also hardening the CI path independently: pin the action to a released ref rather than `./`, or run the judge from a trusted checkout rather than the PR's.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A committed `bin/jsonschema.py` in a repository under test is never imported by the judge, in the self-hosted, vendored and CI shapes
- [ ] #2 The fix covers the shared pattern across bin/ executables, not only bin/adr-judge
- [ ] #3 The payload does not execute under a normal invocation NOR under python -P / PYTHONSAFEPATH=1
- [ ] #4 Sibling adr_*.py modules still load correctly from every invocation path: repo checkout, plugin cache, and the pre-commit hook's resolved root
- [ ] #5 A regression test asserts that a shadowing module placed next to the executable is not imported
- [ ] #6 The CI exposure is addressed: either the workflow runs the judge from a trusted checkout, or the action is pinned to a released ref, or the import fix is verified sufficient on its own with a test
- [ ] #7 Tests pass on Python 3.10 and 3.12, on Windows and Linux
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
19 files in `bin/` converted to explicit sibling loading, plus two shadowing paths the conversion alone would not have closed. New `tests/test_bin_import_safety.py` with 123 tests, proven to fail on HEAD.

**Three files the enumeration missed, and they were worse.** `adr-readiness`, `adr-readiness-ci` and `adr-grill-signal` had no `sys.path.insert` at all — which is why they were not in the estimate — but they resolved siblings purely through CPython's implicit `sys.path[0]`, so they were more exposed rather than less. `python -P bin/adr-readiness --help` failed outright before the change and is clean after.

**`bin/adr_schema.py` was partially undoing adr-judge's own fix.** It carried its own `sys.path.insert(0, _BIN_DIR)` behind an `if str(_BIN_DIR) not in sys.path` guard that does not short-circuit under `-P`, nor on Python 3.10 where `sys.path[0]` is relative rather than absolute. Because `bin/adr-judge` loads `adr_schema` through `_load_sibling`, the shared module re-added the very directory commit ebdbbf6 had removed. Replaced with the same explicit loader. This is the finding I would have missed by treating the task as "grep for the insert and convert".

**Removing the insert is not sufficient for `adr-lint`.** CPython places the script's directory at `sys.path[0]` regardless, and `adr-lint` is the only executable importing a third-party name (`jsonschema`) through the path — the exact name the original finding used as its payload. Reproduced with a hostile module: plain invocation executed it, `-P` did not. `adr-judge` escapes this only because ebdbbf6 made jsonschema deep-only; `adr-lint` cannot. Closed with a scoped import that masks the bin entry and restores it. A global scrub was rejected deliberately: fourteen test modules load these executables in-process via `SourceFileLoader` and nine more put `bin/` on the path on purpose.

**`adr-doctor` had a second shadowing shape.** It inserted three roots, of which only `ROOT/bin` was the target; `ROOT` and `ROOT/scripts` must stay importable because its modules reach real packages there. Those are now appended rather than prepended. Probing found a different working payload: a committed `bin/adr_settings.py` shadowed `scripts/adr_settings.py` and executed. Masked during the import block and restored after.

**Verification** went beyond `--help`, which argparse would pass even on an unconverted file: `python3 -P` on all 18 executables with real invocations, and a hostile-module probe across 15 executables × {plain, `-P`} × four payload names, all clean. `adr-lint --strict docs/adr` output is byte-identical to HEAD. Startup A/B over 7 samples: −23 ms to +18 ms, noise against the 500–600 ms budgets.

**The agent caused a CRLF incident and reported it.** Its conversion script used `Path.write_text`, which translates to CRLF on Windows, rewriting 15 files against `.gitattributes`' `bin/* text eol=lf` pin. Caught via a git warning, normalised back to LF, re-verified, exec bits intact. Worth knowing given TASK-57 is the same surface. Separately observed and explicitly not claimed: `bin/adr-renumber` and `bin/bump-version` already carry CRLF and were never touched.

**Python 3.10 remains unverified** — not installed on this machine. That is the axis that matters most here, because 3.10 gives a relative `sys.path[0]`, which is exactly why `adr_schema.py`'s guard failed to short-circuit there. `_is_bin_dir()` compares resolved paths for that reason, but CI's 3.10 leg is the real check.

Deliberately skipped: `bin/adr-judge` and `bin/adr-mcp` (owned by concurrent agents), `bin/adr-judge-precommit` (subprocess wrapper, no imports), `bin/adr-renumber` and `bin/bump-version` (no sibling imports, no insert). The `codex/` and `copilot/` mirrors are untouched and were byte-compared as in sync.
<!-- SECTION:FINAL_SUMMARY:END -->
