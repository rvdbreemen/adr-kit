---
id: TASK-48
title: >-
  Fix installer: re-point Claude marketplace on version bump (prepared-dir
  source)
status: Done
assignee:
  - '@claude'
created_date: '2026-07-22 18:46'
updated_date: '2026-07-22 19:54'
labels:
  - bug
  - installer
dependencies: []
priority: high
ordinal: 49500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
install-agent-envs.py did not advance Claude Code from 0.36.0 to 0.37.0. Root cause: clients/installer/native.py claude_marketplace_source_matches() returned True for ANY directory/local marketplace whenever the new prepared source carried the PREPARED_MARKER, even when the registered marketplace pointed at an older version directory (.../marketplaces/0.36.0). install_claude therefore skipped the remove+add re-point, so 'claude plugin update' pulled from the stale 0.36.0 directory and the version never advanced. This is the mechanism behind 'no auto-update to 0.37'. Fix: only use the marker fallback when the registration exposes no comparable path; a path mismatch is authoritative so a version bump re-points.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 claude_marketplace_source_matches re-points when the registered directory path differs from the new prepared source
- [x] #2 Path-less directory registration still matches via the prepared marker (existing behavior preserved)
- [x] #3 Regression test covers the version-bump re-point case
- [x] #4 Installer test suite green (except pre-existing codex adapter drift, tracked separately)
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed claude_marketplace_source_matches(): the prepared-marker fallback matched ANY directory-backed marketplace, so install_claude never re-pointed Claude from an older version directory and plugin update kept pulling the stale payload (0.36.0 did not advance to 0.37.0). A path mismatch is now authoritative; the marker fallback applies only when the registration exposes no path. Regression test added. Verified live on the 0.38.0 release: Claude re-pointed to marketplaces
<!-- SECTION:FINAL_SUMMARY:END -->
