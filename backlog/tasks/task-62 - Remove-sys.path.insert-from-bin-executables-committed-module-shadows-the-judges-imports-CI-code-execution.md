---
id: TASK-62
title: >-
  Remove sys.path.insert from bin/ executables: committed module shadows the
  judge's imports (CI code execution)
status: To Do
assignee: []
created_date: '2026-07-30 18:31'
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
