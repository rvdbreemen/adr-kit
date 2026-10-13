<!-- ADR-KIT CLAUDE START -->
## ADR Kit

Read `.adr-kit/ADR-guide.md` before architectural changes. Architecture decisions live in `docs/adr/`. Use `/adr-kit:context` before implementation, `/adr-kit:adr` for new decisions, and `/adr-kit:judge` before commit.
<!-- ADR-KIT CLAUDE END -->

## Backlog.md

This repository uses Backlog.md (`backlog/`) as the source of truth for work.

- Search for an existing task before starting any meaningful implementation or
  design work.
- If no task exists, create one before editing code or docs.
- Prefer the Backlog MCP tools for reading, searching, creating, and updating
  tasks. Use the `backlog` CLI only as a fallback.
- Keep tasks small enough to complete in one focused pass.
- Do not edit files in `backlog/tasks/` directly.

## Working in this repo

- Reproduce the cause a backlog task names before you design a fix; correct the record afterwards. In two sweeps the recorded cause held for 3 of 4 and 4 of 12 tasks respectively. Also check the severity estimate and the completeness of any enumeration, not only the stated cause.
- `python -m pytest -q` takes ~11 minutes and is mandatory before a merge or release. Targeted runs miss guards in files your change does not touch: a module split broke a check in `tests/test_setup_project_command.py`.
- Never switch branches during a test run. A run that starts on branch A and ends on B reports failures that are artifacts of the checkout.
- Make all changes in canonical files first, then regenerate once with `python scripts/build-client-adapters.py`, and confirm with `--check` (expect `changed=0`). Never edit `codex/` or `copilot/` by hand.
- `python bin/adr relate ADR-A --to ADR-B` writes both sides; ADR-028's gate does not let a one-sided link pass lint. `python bin/adr accept ADR-N` refuses without `--confirm`: acceptance puts a name into an immutable history and must be explicitly requested.
- ADR-010 caps lines per file, enforced in `tests/test_release_allowlist.py`: entrypoints in `scripts/` at most 300 lines, support modules 400. Split along the seam the docstring already describes and add the new module to that list.
- `main` and `dev` are protected with `enforce_admins: true`, so `gh pr merge --admin` does not bypass the required `validate` check. Use `--auto`: it weakens nothing and merges once the checks pass. Merging to `main` is the maintainer's action.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
