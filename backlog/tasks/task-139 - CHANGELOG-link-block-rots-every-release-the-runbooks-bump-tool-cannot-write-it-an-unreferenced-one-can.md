---
id: TASK-139
title: >-
  CHANGELOG link block rots every release: the runbook's bump tool cannot write
  it, an unreferenced one can
status: To Do
assignee: []
created_date: '2026-08-06 05:58'
labels:
  - release
  - tooling
  - defect
  - changelog
dependencies: []
references:
  - 'scripts/bump-version.py:41'
  - 'bin/bump-version:184'
  - 'bin/bump-version:248'
  - packaging/version-sites.json
  - 'docs/RELEASING.md:78'
  - 'docs/RELEASING.md:82'
  - >-
    docs/adr/ADR-013-declare-version-sites-in-one-registry-and-bump-by-writing.md
priority: medium
ordinal: 110500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`docs/RELEASING.md` step 1 instructs `python scripts/bump-version.py X.Y.Z` and states it "writes EVERY version site" and is "the only place a version is typed". Neither claim covers the CHANGELOG link block at the bottom of the file, and the block therefore goes stale on every release.

**Two bump tools exist with different capabilities, and the runbook names the weaker one.**

- `scripts/bump-version.py` (5,793 bytes) — the one the runbook uses. It knows the `## [Unreleased]` heading (`UNRELEASED` regex at `:41`) and the sites declared in `packaging/version-sites.json`. It has no link-block logic at all.
- `bin/bump-version` (10,828 bytes) — referenced nowhere in `docs/RELEASING.md`. It has `_update_changelog_links(changelog, current, new)` at `:184`, called from `main` at `:248`, which writes exactly the two lines that go missing:
  - `[Unreleased]: https://github.com/rvdbreemen/adr-kit/compare/v{new}...HEAD`
  - `[{new}]: https://github.com/rvdbreemen/adr-kit/compare/v{current}...v{new}`

`packaging/version-sites.json` declares 11 sites; the link block is not one of them. So the registry that ADR-013 makes authoritative does not know the block exists, and the tool that could maintain it is not the tool the runbook runs.

**Observed cost, measured on 2026-08-06.** After cutting v0.46.0 the block still read `[Unreleased]: ...compare/v0.45.0...HEAD` with no `[0.46.0]` target. Copilot review caught it on the merge-back PR. Checking the whole block rather than the one line found seven further headings with no link target at all: 0.38.0, 0.39.0, 0.40.0, 0.41.0, 0.42.0, 0.44.0 and 0.44.1. All were backfilled by hand in commit a31cb04 on `sync/v0.46.0-to-dev`.

Hand-backfilling is not a fix. The next release reproduces the gap, and it now also risks conflicting with `bin/bump-version` if anyone ever runs that one instead.

**Deciding which tool is canonical is part of this task, not a precondition.** `scripts/client_generation_model.py` sets `COPY_EXCLUSIONS = {"bin/bump-version"}`, so `bin/bump-version` is deliberately withheld from the client trees — consistent with it being maintainer tooling, but not evidence it is current. Two files that both claim to bump the version is itself the defect underneath this one.

Found while refreshing the C4 architecture documentation; the `bin/bump-version:281-290` citation in `c4-code-bin-cli-migration.md` points past that file's 270 lines, which is what led here.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 One tool is named canonical for bumping the version, and the other is either deleted or reduced to a thin delegation — two independent implementations of the same release step do not survive this task
- [ ] #2 The canonical tool writes the CHANGELOG link block: `[Unreleased]` retargeted to the new version and a `[X.Y.Z]` compare link added
- [ ] #3 The link block is declared in `packaging/version-sites.json` so `scripts/check-release-version.py` fails the release when it disagrees with the tag, the same way every other site does (ADR-013)
- [ ] #4 `docs/RELEASING.md` names the canonical tool and no longer claims coverage the tool does not have
- [ ] #5 A test cuts a fake version against a fixture CHANGELOG and asserts both link lines are written, so the gap cannot reopen silently
- [ ] #6 Every existing `## [X.Y.Z]` heading has a matching link target — verified by a check, not by inspection; 65 headings had 58 targets before the manual backfill in a31cb04
<!-- AC:END -->
