---
id: TASK-139
title: >-
  CHANGELOG link block rots every release: the runbook's bump tool cannot write
  it, an unreferenced one can
status: Done
assignee: []
created_date: '2026-08-06 05:58'
updated_date: '2026-08-06 18:33'
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
- [x] #1 One tool is named canonical for bumping the version, and the other is either deleted or reduced to a thin delegation — two independent implementations of the same release step do not survive this task
- [x] #2 The canonical tool writes the CHANGELOG link block: `[Unreleased]` retargeted to the new version and a `[X.Y.Z]` compare link added
- [x] #3 The link block is declared in `packaging/version-sites.json` so `scripts/check-release-version.py` fails the release when it disagrees with the tag, the same way every other site does (ADR-013)
- [x] #4 `docs/RELEASING.md` names the canonical tool and no longer claims coverage the tool does not have
- [x] #5 A test cuts a fake version against a fixture CHANGELOG and asserts both link lines are written, so the gap cannot reopen silently
- [x] #6 Every existing `## [X.Y.Z]` heading has a matching link target — verified by a check, not by inspection; 65 headings had 58 targets before the manual backfill in a31cb04
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed on `fix/backlog-todo-sweep` (commit 2ec18f1).

**AC#1 — `scripts/bump-version.py` is canonical; `bin/bump-version` is now a four-line delegation.** ADR-013 and the runbook already named the former, so the deciding question was which implementation to keep, not which name. `bin/bump-version` is kept rather than deleted because it is what people have in shell history; it implements nothing. Its two preflight validations moved across, since only the *unnamed* tool performed them: the client manifests must agree on the plugin name, and every marketplace pointer must resolve to that plugin's entry — the runbook's tool could previously bump a tree where those disagreed.

**AC#2.** The canonical writer writes both lines: `[Unreleased]` retargeted, and a `[X.Y.Z]` compare link added. Re-running for the same version does not add a second target.

**The clobber that would have made AC#3 a silent no-op.** `main` planned the CHANGELOG and the registry separately, then did `changes[CHANGELOG] = changelog_bytes` — discarding any registry-computed bytes for that file. Harmless while nothing declared the CHANGELOG; a silent no-op the moment something did, which is exactly what AC#3 asks for. `plan_writes` now takes an `overrides` pre-image and the CHANGELOG is folded through **one** image in order: heading → links → declared sites.

**AC#3.** The `[Unreleased]` link is declared in `packaging/version-sites.json` as a `regex` site. Verified end to end: a real bump to 0.47.0 wrote both lines and `check-release-version.py --expect 0.47.0` passed listing the new site; staling the link by hand made it exit 1 with `CHANGELOG Unreleased compare link (CHANGELOG.md) = '0.45.0', expected '0.47.0'`. Trial bump reverted.

The `[X.Y.Z]` target is an *existence* property, not a substitution, so it fits no kind in `SITE_KINDS` and is covered by AC#6's check instead — declaring an unwritable kind is the verified-but-never-written failure ADR-013 exists to stop.

**AC#4.** `docs/RELEASING.md` names `scripts/bump-version.py` as canonical, says `bin/bump-version` forwards and implements nothing, and now lists the link block and the two preflight validations among what it writes.

**AC#5 and AC#6.** Seven tests in `tests/test_version_sites.py`: both link lines written, idempotent re-run, a CHANGELOG with no block gets one, the site is declared, the declared pattern actually matches the real file (a pattern matching nothing is verified-but-never-written), heading↔target parity, and `bin/bump-version` carries no second implementation. Parity is scoped to semver so the genuine `## [0.2.0-attribution]` heading is not dragged into the contract. It passes today.

**Contract differences resolved in the canonical writer's favour, each now asserted rather than assumed:** usage errors exit 2 (argparse, matching every other adr-kit CLI) rather than 1; a leading `v` is accepted and stripped, matching the tag spelling and `check-release-version.py`, where `bin/bump-version` rejected it; and the release section is a TODO placeholder rather than promotion of the Unreleased body — the behaviour that has been shipping.

`test_bump_writes_every_registry_site` checked staleness by scanning for the old version string. CHANGELOG.md is a declared site now and the old version legitimately survives in it — in the previous release heading, and inside the new `v0.30.0...v0.31.0` compare link, which is the entire point of a compare link. It now checks the declared value through the engine.
<!-- SECTION:FINAL_SUMMARY:END -->
