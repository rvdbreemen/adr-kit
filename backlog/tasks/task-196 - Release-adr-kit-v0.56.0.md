---
id: TASK-196
title: Release adr-kit v0.56.0
status: In Progress
assignee: []
created_date: '2026-08-27 05:13'
updated_date: '2026-08-27 05:14'
labels: []
dependencies:
  - TASK-195
references:
  - docs/RELEASING.md
  - >-
    docs/adr/ADR-042-drive-the-release-from-the-maintainer-s-machine-and-create-the-tag-from-the-merge.md
  - >-
    docs/adr/ADR-012-release-to-the-three-coding-agent-marketplaces-from-the-public-repository.md
priority: high
type: chore
ordinal: 40000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Release adr-kit v0.56.0 to the three certified coding-agent marketplaces and stage the OpenCode npm package, following docs/RELEASING.md and ADR-012 as amended by ADR-042.

A minor bump rather than a patch, for two reasons. ADR-042's tag-from-the-merge is a new capability, not a fix. And issue #118 changes behaviour a consumer can observe: frontmatter inference now leaves an unreadable status undetermined instead of defaulting to "Proposed", so adr-migrate reports and refuses where it previously rewrote the record with an invented status.

FIRST RELEASE UNDER ADR-042. The tag must NOT be created by hand. release-publish.yml now triggers on a push to main, reads the canonical CHANGELOG version, and creates the tag on the commit that carries it before publishing in the same run. This release is that mechanism's first real exercise, so verifying it is part of the work: after the merge, the peeled tag must equal origin/main, and the tag must have been created by the workflow rather than by a person.

Contents: ADR-042 accepted and its first half implemented; the #118 and #119 lifecycle fixes; the documentation sweep from TASK-190; the marketplace description refresh from TASK-189; two new version sites in the registry.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The CHANGELOG carries a 0.56.0 section written to release-note quality
- [ ] #2 Every publish surface reports 0.56.0, written by bump-version.py rather than by hand
- [ ] #3 build-client-adapters.py --check reports changed=0
- [ ] #4 adr-lint --strict, adr-index --check and the full pytest suite pass on the release commit
- [ ] #5 The PR into main is green on all four required checks and merged
- [ ] #6 The tag is created by release-publish.yml rather than by a person, and the peeled tag equals origin/main
- [ ] #7 release-publish.yml completes green and the Release body is the 0.56.0 CHANGELOG section
- [ ] #8 main is merged back into dev and check-branch-sync.py reports in sync
- [ ] #9 The local prepared-directory marketplace is advanced and each client reports 0.56.0
- [ ] #10 npm dist-tags.latest names 0.56.0 after the maintainer approves the staged package
<!-- AC:END -->
