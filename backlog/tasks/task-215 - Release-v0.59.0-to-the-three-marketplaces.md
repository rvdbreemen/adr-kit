---
id: TASK-215
title: Release v0.59.0 to the three marketplaces
status: Done
assignee: []
created_date: '2026-10-03 20:51'
updated_date: '2026-10-03 21:26'
labels: []
dependencies: []
priority: high
type: chore
ordinal: 59000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Minor release. TASK-212 and TASK-213 are fixes, but a consumer can observe two behaviour changes. adr-retire now scans only what git versions, so files git ignores no longer count as uses of a technology. /adr-kit:lint now runs bin/adr-lint through Bash. Also: adr-doctor no longer regenerates adapters in a source checkout, lifecycle writes keep CRLF, and release.py's preflight continues a prepared release.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Tag v0.59.0 created by release-publish.yml resolves to origin/main
- [x] #2 Sync-back PR into dev merged
- [x] #3 Per-client versions read back as 0.59.0
- [x] #4 npm dist-tags.latest names 0.59.0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The whole release ran in one driver invocation after the notes were written. Preflight accepted the prepared tree ('continuing a prepared release: 25 release file(s) changed'), which is the TASK-213 fix working on its first real use; no --only was needed. Verify: version consistency, adapter drift, adr-lint --strict and adr-index --check all passed. The full local suite gave 1956 passed, 12 skipped, with no failures: the adr-retire ceiling now passes (TASK-212).

Land: release PR #175 merged into main with all 14 checks green. Tag v0.59.0 resolves to 7857f42, equal to origin/main. The 'ADR Kit release publish' run completed with success. Release page: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.59.0 (not a draft, not a prerelease, published 2026-10-03T21:13:13Z). Syncback: PR #176 merged; v0.59.0 is an ancestor of origin/dev, and check-branch-sync reports in sync. Install: all three clients report 0.59.0.

Open: npm. dist-tags.latest still reads 0.58.0, and approval needs the maintainer's 2FA.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
v0.59.0 is released, a minor bump: adr-retire now ignores git-ignored files, and the lint skill runs its CLI through the shell. The driver ran end to end in one invocation, with preflight accepting the prepared tree (TASK-213); the full suite was clean. Release PR #175 merged with 14/14 checks green. Tag v0.59.0 resolves to 7857f42, equal to origin/main. Release page: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.59.0. Sync-back PR #176 merged, and the branches are in sync. All three clients report 0.59.0. npm dist-tags.latest is 0.59.0, approved by the maintainer. Driver --status reports every phase done.
<!-- SECTION:FINAL_SUMMARY:END -->
