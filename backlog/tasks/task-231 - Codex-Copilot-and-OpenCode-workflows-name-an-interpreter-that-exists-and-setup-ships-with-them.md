---
id: TASK-231
title: >-
  Codex, Copilot and OpenCode workflows name an interpreter that exists, and
  setup ships with them
status: Done
assignee: []
created_date: '2026-10-11 17:04'
updated_date: '2026-10-11 17:06'
labels:
  - skills
  - interpreter
  - setup
dependencies: []
ordinal: 75000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
clients/workflows.json:35,48,73,126,136,189,204 tell the agent to run 'python <plugin-root>/...'. The generator copies that into every Codex and Copilot skill, and the OpenCode plugin copies it into every command template. Where python is missing (macOS, most Linux distributions) each of those steps fails first (DEF-34). The setup workflow names <plugin-root>/scripts/setup-project.py, which scripts/client_generation_model.py does not mirror into codex/ or copilot/, so an installed Codex or Copilot skill points at a file its tree does not have. tests/test_setup_project_command.py runs the checkout's copy, so it never noticed. Claude's skills carry runnable bash snippets with the same defect; a placeholder there would parse as a redirection, so they need a runnable resolver and are left for the ADR-044 launcher work.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Workflow procedures write <python> where they ran python, and every generated skill defines <python> in ADR-044's order
- [x] #2 OpenCode command templates substitute the interpreter the plugin resolved
- [x] #3 codex/ and copilot/ ship scripts/setup-project.py, and the documented setup command runs from each tree
- [x] #4 Tests fail on the old code
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced first: all ten new or changed assertions fail on the old code. The workflows ran a bare python, codex/scripts/setup-project.py and copilot/scripts/setup-project.py did not exist, and the OpenCode lint template read 'python <root>/bin/adr-lint'.

The seven procedures now write <python>. A generated skill whose procedure uses it says, next to <plugin-root>, that <python> is the first of python3, python or, on Windows, py -3 that runs Python 3.10 or newer, which is ADR-044's order. The other skills keep the old sentence. The OpenCode plugin substitutes the interpreter it resolved (TASK-230) and quotes it when the path has a space. scripts/setup-project.py is mirrored into both trees: it imports only adr_settings and project_setup, which were already mirrored, and reads instructions/ and templates/ from its own tree. Run from codex/ for real in a scratch project, it wrote the guide, AGENTS.md and the codex tree's pre-commit hook.

Not done here: Claude's skills run a bare python in runnable bash snippets, where a <python> placeholder would parse as a redirection. They need a runnable resolver, which belongs with ADR-044's launcher.
<!-- SECTION:NOTES:END -->
