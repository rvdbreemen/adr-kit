---
id: TASK-173
title: Release v0.51.0 to the three marketplaces
status: In Progress
assignee: []
created_date: '2026-08-10 22:07'
labels:
  - release
dependencies: []
priority: high
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ships TASK-171: a declared timeout on a call that starts a client CLI is now a real upper bound.

`subprocess.run(timeout=N)` bounds nothing once a descendant outlives the direct child - its own handler kills the child and then drains the pipes unbounded, and on Windows that kill is `TerminateProcess` on a single handle. Behind a `.CMD` shim, which is what an npm-installed client CLI is, the grandchild survives holding the pipe. Measured: `subprocess.run` returned after 25.22s on a `timeout=1` call; the new runner after 1.65s with the tree gone.

ADR-010 (Accepted, binding) describes these calls as bounded. The claim was made true rather than softened, so no ADR changes.

Minor rather than patch: all three paths that start a client CLI or packaged runtime now spawn through a different runner that kills the process tree on timeout - the hook smoke test, the installer runner, and the deep-doctor probe.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 bump-version.py moved every version site and the client trees were regenerated
- [ ] #2 CHANGELOG has a release-quality 0.51.0 section naming what changes for a user
- [ ] #3 All five local gates pass
- [ ] #4 PR into main is green and handed to the maintainer
- [ ] #5 Tag pushed, release-publish.yml green, GitHub Release created
- [ ] #6 Release merged back into dev
- [ ] #7 Local prepared-directory marketplace advanced and the three clients report 0.51.0
<!-- AC:END -->
