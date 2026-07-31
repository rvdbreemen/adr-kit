---
id: TASK-71
title: >-
  bump-version does not read the version-site registry, so declared sites are
  verified but never written
status: Done
assignee: []
created_date: '2026-07-30 23:47'
updated_date: '2026-07-31 05:41'
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
  - scripts/bump-version.py
  - scripts/version_sites.py
  - packaging/version-sites.json
  - tests/test_bump_version.py
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
- [x] #1 `bin/bump-version` reads `packaging/version-sites.json` and writes every site declared there; the hard-coded path tuple is no longer a second source of truth
- [x] #2 A site kind the writer does not implement causes a loud failure, not a silent skip
- [x] #3 Adding a new entry to the registry is sufficient to have it bumped, proven by a test that adds a temporary site and asserts the writer updates it
- [x] #4 `tests/test_version_sites.py` passes immediately after a bump, with no manual follow-up edit
- [x] #5 The existing atomic write and rollback behaviour is preserved: a failure part way through leaves no file half-bumped
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Done. **This task's stated cause was half wrong, and the half that was wrong is mine.**

There are two bump writers. `scripts/bump-version.py` is the one ADR-013 designates (ADR-013:101 and :167) and that `docs/RELEASING.md:78` and `.claude/commands/release-adr-kit.md:25` both prescribe — and it **already read the registry and already wrote both README pins correctly**. I verified this against HEAD rather than taking the report's word for it. `bin/bump-version` appears in none of those three documents; it is the pre-ADR-013 predecessor.

So the red tests I hit came from running the wrong tool, not from a broken writer. I wrote this task describing "the writer" as not reading the registry. That was inaccurate, and the description is left standing as the record of what I believed at the time.

The defect is still real, and worth the fix: `bin/bump-version` sits in `bin/` alongside every other command, has the obvious name, and silently did partial work. That is exactly why I reached for it.

**What changed**

- `scripts/version_sites.py` — one write engine, plan-then-apply. `plan_writes()` computes every post-image before the first byte and collects *all* errors in one pass (ADR-013's "report everything"), folding sites that share a path through one working image. That fold is load-bearing: planning each site against disk independently discards the first of README's two pin edits.
- `bin/bump-version` — rewritten as a front end over that registry; the ten path constants and the `required_paths` tuple are gone. Two guards stay because the registry cannot express them: all client manifests must carry the same plugin name, and the positional pointer `/plugins/0/version` must hit our entry.
- `packaging/version-sites.json` — declares `.githooks/pre-commit`. That is the **inverse** gap: it carries `ADR_KIT_WRAPPER_VERSION`, was written only by `bin/bump-version`, and was declared nowhere, so nothing verified it. `bin/adr-guardian:297-313` compares that stamp against the plugin version and reports STALE. Simply switching to the sanctioned writer would have let this repository's own hook go quietly stale. Registry is now 11 sites over 10 unique paths.
- `scripts/bump-version.py` — **a second real defect, in the sanctioned writer.** `ensure_changelog_heading()` wrote CHANGELOG directly and only then called `write_all()`. On a mid-run failure the canonical source announced a release that nothing else carried, with no rollback. The heading is now planned, not written, and its bytes travel in the same transaction.

**Verified by running, in scratch copies of the repo:**

| Check | Result |
|---|---|
| `bin/bump-version 0.44.0` | 11 files written, README among them (was 9 without it) |
| README pins afterwards | both at 0.44.0 |
| `scripts/check-release-version.py --expect 0.44.0` | all publish surfaces agree |
| Rollback: site 9 made read-only, then bump | exit 1, **zero** files at the new version, no stray `.tmp` |
| CHANGELOG orphan, sanctioned writer, same failure | 0.98.0 appears nowhere — transaction held |

The rollback and orphan checks are the ones that mattered, so I reproduced both myself rather than accepting them: a release tool that leaves half the manifests bumped, or a CHANGELOG announcing a version nothing carries, fails exactly when it is least convenient.

Full suite after the change: **1224 passed, 11 skipped, 0 failed** (baseline was 1200; the delta is 12 new tests here plus the other agent's additions). Mirrors need no generator run — `bin/bump-version` is in `COPY_EXCLUSIONS`, and `scripts/`, `packaging/` and `tests/` are outside `COPY_ROOTS`.

**Left open, deliberately, for a decision rather than a patch:** both writers still exist, with different CLIs and different CHANGELOG behaviour (`bin/` maintains the compare links, `scripts/` writes a TODO section). They now share one engine so they can no longer disagree about *which* sites get written, but a maintainer still has to know both exist. The relationship is documented in `bin/bump-version`'s docstring, pointing at `scripts/bump-version.py` as ADR-013's designated writer. Removing `bin/bump-version` outright means porting the compare-link logic first.</finalSummary>
<!-- SECTION:FINAL_SUMMARY:END -->
