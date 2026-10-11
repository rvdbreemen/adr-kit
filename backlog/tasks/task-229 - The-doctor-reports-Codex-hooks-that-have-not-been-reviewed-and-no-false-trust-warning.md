---
id: TASK-229
title: >-
  The doctor reports Codex hooks that have not been reviewed, and no false trust
  warning
status: Done
assignee: []
created_date: '2026-10-11 16:54'
updated_date: '2026-10-11 16:56'
labels:
  - doctor
  - codex
dependencies: []
ordinal: 73000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Codex 0.162.1 runs a plugin's hooks only after the user reviews them with /hooks ('hooks need review before they can run'), and records each trusted hook in $CODEX_HOME/config.toml as [hooks.state."adr-kit@<marketplace>:hooks/hooks.json:<event>:<group>:<handler>"] with trusted_hash. Before the review there is no such table, and app-server hooks/list reports trustStatus untrusted (observed). bin/adr_doctor_probes.py:45-47 reports trust-pending only when the plugin-list output contains 'trust' or 'review', which Codex never prints, so a fresh install with every hook inactive reads healthy (DEF-32, observed in the doctor run). The same substring test runs over every installed plugin's id and installPath in Claude's and Copilot's listings, so a plugin such as code-review@claude-plugins-official turns the check into trust-pending for a client that has no plugin trust state. Only app-server hooks/list, an experimental API, can tell a trusted hook from one an update modified; the file shows only whether a review happened.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A Codex install whose config.toml records no trusted ADR Kit hook reports trust-pending, with an action that names /hooks
- [x] #2 A Codex install with trusted ADR Kit hooks reports healthy, and the evidence names the trusted events
- [x] #3 Another plugin's trusted hooks, or an ADR Kit table without trusted_hash, do not count
- [x] #4 No client turns trust-pending because a plugin id or path contains trust or review
- [x] #5 Tests use the config.toml shapes Codex wrote, and fail on the old code
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced first: all 7 new tests in tests/test_client_doctor.py fail on the old code. The never-reviewed install read healthy, and a Claude or Copilot listing with code-review@claude-plugins-official read trust-pending.

The probe no longer looks for the words trust or review in a plugin listing. For Codex it reads $CODEX_HOME/config.toml, or ~/.codex/config.toml, and counts the ADR Kit hooks that have a hooks.state table with a trusted_hash. It uses patterns, not tomllib, for the 3.10 floor. With none it reports trust-pending and names /hooks, the command Codex 0.162.1 itself points to ('Use /hooks to view and manage lifecycle hooks'). Otherwise the evidence lists the trusted events.

End to end with Codex 0.162.1 and the doctor from this checkout, the untrusted home reads trust-pending, and the home whose app-server hooks/list said trusted reads healthy with six events.

Limits: the file shows that a review happened, not that the hooks still match it. A hook that an update changed needs a new review, and only the app-server's experimental hooks/list reports that (trustStatus modified). A partial review also reads healthy.
<!-- SECTION:NOTES:END -->
