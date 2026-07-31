---
id: TASK-71
title: >-
  bump-version does not read the version-site registry, so declared sites are
  verified but never written
status: To Do
assignee: []
created_date: '2026-07-30 23:47'
labels:
  - release
  - bug
  - adr-013
dependencies: []
references:
  - 'bin/bump-version:182-193'
  - packaging/version-sites.json
  - tests/test_version_sites.py
  - >-
    docs/adr/ADR-013-declare-version-sites-in-one-registry-and-bump-by-writing.md
modified_files:
  - bin/bump-version
  - tests/test_version_sites.py
priority: high
ordinal: 76500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ADR-013 is titled "Declare version sites in one registry and bump by writing". The registry exists at `packaging/version-sites.json` and the verifier reads it — but **the writer does not**. `bin/bump-version` carries its own hard-coded `required_paths` tuple (`bin/bump-version:182-193`) listing 10 files, and never opens the registry at all.

The two are already out of sync. The registry declares 10 sites; `required_paths` covers 8 of them and omits both `README.md` entries:

```json
{"path": "README.md", "kind": "regex_all", "pattern": "(adr-judge@v)(\\d+\\.\\d+\\.\\d+)", "label": "README composite-action pin"}
{"path": "README.md", "kind": "regex_all", "pattern": "(rev: v)(\\d+\\.\\d+\\.\\d+)", "label": "README pre-commit rev pin"}
```

**Reproduced 2026-07-31** running `bin/bump-version 0.43.0`. It reported nine files written, README.md not among them, then:

```
FAILED tests/test_version_sites.py::test_repository_is_version_consistent
FAILED tests/test_version_sites.py::test_bump_version_check_passes_for_the_current_version
  - README composite-action pin (README.md) = '0.42.0', expected '0.43.0'
  - README pre-commit rev pin (README.md) = '0.42.0', expected '0.43.0'
```

Those are the two copy-paste snippets users are told to paste into their own `.github/workflows` and `.pre-commit-config.yaml`, so a stale pin ships a wrong version to every new consumer.

**Why it matters beyond these two entries.** The failure is not that README was forgotten once. It is that adding a site to the registry gives you verification without writing, and the gap only surfaces as a red test during a release — the moment you least want to be debugging the release tool. Any site added in future inherits the same trap silently.

The verifier working correctly is the only reason this was caught rather than shipped, which is worth noting in favour of ADR-013's design; the defect is that half of it was never implemented.

**Fix direction.** Drive the writer from the registry so the two cannot diverge: `bump-version` reads `packaging/version-sites.json`, writes every declared site by its declared `kind`, and fails loudly on a `kind` it does not implement rather than skipping it. `required_paths` then becomes a derived existence check rather than a second source of truth. Note the registry already distinguishes kinds (`regex_all` for the README pins versus JSON manifests), so the writer needs a small dispatch, not a rewrite.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `bin/bump-version` reads `packaging/version-sites.json` and writes every site declared there; the hard-coded path tuple is no longer a second source of truth
- [ ] #2 A site kind the writer does not implement causes a loud failure, not a silent skip
- [ ] #3 Adding a new entry to the registry is sufficient to have it bumped, proven by a test that adds a temporary site and asserts the writer updates it
- [ ] #4 `tests/test_version_sites.py` passes immediately after a bump, with no manual follow-up edit
- [ ] #5 The existing atomic write and rollback behaviour is preserved: a failure part way through leaves no file half-bumped
<!-- AC:END -->
