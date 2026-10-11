---
id: TASK-232
title: The doctor's live MCP check starts the command each client registered
status: Done
assignee: []
created_date: '2026-10-11 17:07'
updated_date: '2026-10-11 17:09'
labels:
  - doctor
  - mcp
  - interpreter
dependencies: []
ordinal: 76000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
bin/adr_doctor_probes.py:88-89 started the MCP server for the live check as [sys.executable, <plugin-root>/bin/adr-mcp], the doctor's own interpreter. A client starts the command its .mcp.json registers. On a PATH with python3 and no python, the doctor for a Codex install with the repository's bare python reported mcp-launcher stale and mcp-live healthy for the same server, which the client could not start (DEF-33, observed). The live result proves only that the doctor can run the server.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The live check runs, per client, the argv that client's registered command resolves to
- [x] #2 A client whose registered command does not resolve gets a failed live check that names the command
- [x] #3 Tests run the doctor's deep probe against the repository's own .mcp.json on a PATH without python, and fail on the old code
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced first: all three changed or new tests in tests/test_client_doctor.py fail on the old code, which produced one common mcp-live check started with sys.executable.

resolve_launcher_target now also returns the whole argv: the resolved command, then each argument with the plugin-root variables expanded and path arguments resolved. The healthy launcher check records it. run_deep_extensions adds one mcp-live check per client whose launcher was examined. When the launcher resolved, it runs that argv. Otherwise the check fails, names the command, and carries the launcher's repair action. Each check keeps the launcher's required flag.

End to end on a PATH with python3 and no python, the doctor from this checkout against a Codex 0.59.1 install with the repository's bare python reported mcp-launcher stale and mcp-live failed ('codex cannot start the MCP server: python does not resolve'). Against the install whose installer pinned /usr/bin/python3.13 it reported both healthy, and ran exactly that interpreter with the installed bin/adr-mcp.
<!-- SECTION:NOTES:END -->
