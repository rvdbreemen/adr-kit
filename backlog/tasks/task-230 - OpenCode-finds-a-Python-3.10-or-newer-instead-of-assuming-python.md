---
id: TASK-230
title: OpenCode finds a Python 3.10 or newer instead of assuming python
status: Done
assignee: []
created_date: '2026-10-11 17:00'
updated_date: '2026-10-11 17:02'
labels:
  - opencode
  - interpreter
dependencies: []
ordinal: 74000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
opencode/plugin.ts:289 defaults the interpreter to 'python' when neither the python option nor ADR_KIT_PYTHON is set. macOS and most Linux distributions ship python3 and no python, so the plugin registers an MCP server that cannot start and spawns hooks that fail open into silence (DEF-35). macOS's own python3 from the Command Line Tools is 3.9, below the 3.10 floor. ADR-044 fixes the order: ADR_KIT_PYTHON, then the interpreter an installer pinned (here the python option), then the first of python3, python and, on Windows, py -3 that runs Python 3.10 or newer.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 With neither the option nor ADR_KIT_PYTHON, the plugin uses the first of python3, python and (on Windows) py -3 that runs 3.10 or newer, for the MCP server and for every hook
- [x] #2 An interpreter older than 3.10 is skipped
- [x] #3 ADR_KIT_PYTHON wins over the python option, as ADR-044 orders them
- [x] #4 Tests run the plugin on a PATH with only python3, with only python, and with a python3 that is too old, and fail on the old code
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced first with the real client: OpenCode 1.19.0, the plugin loaded from this checkout and a PATH with python3 and no python. opencode mcp list printed 'adr-kit failed: Executable not found in $PATH: "python"'. With the fix it prints 'adr-kit connected', running .../python3 bin/adr-mcp. In tests/test_opencode_plugin.py the python3-only case and the precedence test fail on the old code. The python-only and too-old python3 cases guard the new resolver: a resolver that took python3 without the version probe fails the too-old case.

The plugin now resolves the interpreter once at load, in ADR-044's order: ADR_KIT_PYTHON, then the python option, then the first of python3, python and, on Windows, py -3 whose probe 'sys.exit(sys.version_info < (3, 10))' exits 0. Bun.which gives the absolute path. The MCP server and every hook use the result. With no candidate it falls back to the first name, so OpenCode reports the failed server instead of the plugin failing silently. The command templates still render the procedures' bare python; the <python> placeholder in clients/workflows.json is TASK-231.
<!-- SECTION:NOTES:END -->
