---
id: TASK-240
title: Certify OMP as the fourth native client (ADR-050)
status: To Do
assignee: []
created_date: '2026-10-21T20:05:00Z'
labels:
  - omp
  - client
  - certification
dependencies: []
references:
  - >-
    docs/adr/ADR-050-certify-omp-as-a-fourth-native-client-through-a-thin-extension.md
  - docs/clients/omp.md
priority: high
ordinal: 82000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ADR-050 (Accepted 2026-10-21) makes omp-cli the fourth certified client, amending ADR-010's client list. v0.61.0 ships the native extension (omp/extension.ts) and the omp-cli judge host; this task adds the certification so v0.62.0 can claim it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 omp-cli is registered in clients/capabilities.json with all ADR-010 required outcomes and event mappings
- [ ] #2 Late pre-edit context is declared as an edit-governance degradation (reason, user effect, backstop) and plan exit is mapped as no native event
- [ ] #3 client-capabilities and client-certification schemas, client_certification.py and client_evidence.py accept omp-cli
- [ ] #4 install-agent-envs.py detects omp and installs, updates, rolls back, disables and removes ADR Kit through omp plugin commands without clobbering user state
- [ ] #5 adr-doctor fast and deep cover omp-cli: registration, extension load, MCP handshake, hook smoke
- [ ] #6 A passing native record tests/certification/omp/windows-native.json binds to the candidate commit and payload, and the release gate accepts it
- [ ] #7 The generated support matrix, README and docs/clients/omp.md claim OMP certification only per platform with a passing record (ADR-048)
<!-- AC:END -->
