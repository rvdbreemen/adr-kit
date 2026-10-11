---
id: "ADR-044"
title: "Resolve the interpreter and the engine through one resolver at every entry point"
status: "Accepted"
date: "2026-10-11"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-004"
  - "ADR-006"
  - "ADR-008"
  - "ADR-045"
topics:
  - "engine resolution"
  - "python interpreter"
  - "commit gate"
  - "mcp launcher"
  - "fail closed"
aliases:
  - "ADR_KIT_ROOT"
  - "adr-judge binary not found in plugin cache"
  - "Executable not found in $PATH"
  - "python3 only"
components:
  - "templates/githooks/pre-commit"
  - "hooks/run-hook.cmd"
  - ".mcp.json"
  - "scripts/project_setup.py"
symbols:
  - "_patch_mcp_python"
  - "_plugin_roots"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-044 Resolve the interpreter and the engine through one resolver at every entry point

## Status

Accepted, 2026-10-11.

## Status History

```yaml
status_history:
  - date: 2026-10-11
    status: Proposed
    changed_by: "User: Claude"
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted decision after all four verification gates passed
    changed_via: adr-kit lifecycle
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: "ADR-044 amends ADR-008: adds ADR_KIT_ROOT and a setup-recorded root to the version-ranked candidate set"
    changed_via: adr-kit lifecycle
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-006
    changed_via: adr-kit lifecycle
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-004
    changed_via: adr-kit lifecycle
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-045
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

Every ADR Kit entry point has to find two things before it can do anything: a
Python 3.10 or newer, and the engine (`bin/` with its modules). Today four entry
points find them four different ways, and they fail four different ways.

| Entry point | Finds Python by | Finds the engine by | When nothing resolves |
| --- | --- | --- | --- |
| Commit gate, `templates/githooks/pre-commit` | probing for a 3.10+ (`:60-95`) | three client plugin caches, plus the repository itself when it is an ADR Kit checkout (ADR-008, `:100-120`) | exit 0, "skipping pre-commit ADR check" (`:93`, `:161-163`) |
| Hooks, `hooks/run-hook.cmd` | `ADR_KIT_PYTHON`, an embedded path, `python3`, `python` (`:29-43`) | the `bin/` beside `hooks/` (`hooks/adr_hook_core.py:27`) | exit 0 through `\|\| true` (`:43`) |
| MCP server, `.mcp.json` and the `codex/` and `copilot/` copies | a bare `python` (`.mcp.json:4`); only the installer pins an absolute interpreter (`clients/installer/payload.py:145-153`) | `${CLAUDE_PLUGIN_ROOT}` or `${PLUGIN_ROOT}` | the host reports a failed connection |
| Ten skills (`skills/*/SKILL.md`) | `python` | `ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ \| sort -V \| tail -1` | the skill aborts by its own instruction |

The 2026-10-11 defect sweep reproduced the consequences against commit
`f2f6fe2` (TASK-222):

* **The documented client-neutral setup enforces nothing.**
  `scripts/setup-project.py`, run from a checkout as INSTALL-AGENT.md section 6
  prescribes, installs a hook that finds no engine on a machine without a plugin
  cache. A violating commit then succeeds with exit 0. ADR-004 promises "one
  fail-closed floor"; on this path the floor is absent and the only sign is a
  stderr line.
* **The MCP server does not start where only `python3` exists.** Claude Code
  2.1.296 loads the kit with `--plugin-dir` and reports
  `plugin:adr-kit:adr-kit ✔ Connected` when `python` is on PATH. On a PATH with
  `python3` and no `python`, which is the default on macOS 12.3 and later and on
  stock Debian and Ubuntu, it reports
  `✘ Failed to connect — ENOENT: Executable not found in $PATH`. The README's
  quick install (`/plugin marketplace add` plus `/plugin install`) never runs
  the installer that would have pinned the interpreter.
* **The skills fail outside the Claude plugin cache.** Their resolver also uses
  GNU `sort -V`, which TASK-216 and TASK-220 removed from the pre-commit hook and
  the guardian entry as non-portable (issue #155). The skills were not in that
  enumeration.

ADR-006 named this cause: "Windows commonly provides `python.exe`, while macOS
and Linux installations may expose only `python3`. Static manifests cannot
select the interpreter that actually launched the installer." It fixed the
installer-driven install and recorded "Unix installations no longer depend on a
command literally named `python`". That consequence holds for the installer path
only.

How should every entry point find a Python 3.10+ and the engine, and what should
each do when either is missing?

## Decision Drivers

* ADR-004's fail-closed floor must not disappear without a refusal.
* The same engine answers at the hook, the commit gate, the MCP server and the
  skills, ranked by manifest version as ADR-008 decided.
* Nothing may require a command literally named `python` (ADR-006).
* A machine's facts stay machine-local (ADR-025); no interpreter or engine path
  enters tracked configuration.
* A contributor who does not have ADR Kit installed must still be able to commit,
  with a one-line instruction and a documented escape.

## Considered Options

* One resolver, with failure behaviour set by the entry point's ADR-004 tier.
* Patch each entry point separately.
* Make the installer the only supported install path.
* Do nothing.

## Decision Outcome

Chosen option: **one resolver, used by every entry point, with the failure
behaviour set by that entry point's ADR-004 tier**, because the four defects
share one cause, and patching them separately is how the same `sort -V` defect
survived in ten skills after TASK-216 and TASK-220.

The resolver tries the candidates in this order:

* **Interpreter:** `ADR_KIT_PYTHON`, then an interpreter pinned by the installer,
  then `python3`, then `python`, then `py -3` on Windows. It takes the first
  candidate that reports Python 3.10 or newer.
* **Engine root:** `ADR_KIT_ROOT`, then a root that setup records in the
  machine-local `docs/adr/.adr-kit.local.json` (ADR-025), then the client plugin
  caches, then the checkout. All candidates are ranked by manifest version, as
  ADR-008 decided.

The failure behaviour depends on the tier:

* **Commit gate (the fail-closed floor).** A project with at least one Accepted
  ADR that carries an Enforcement block has something to enforce. If nothing
  resolves in such a project, the gate refuses the commit. It prints one line
  naming what is missing, the repair command, and the existing
  `ADR_KIT_HOOK_DISABLE=1` escape. A project without such a block keeps today's
  exit 0 (Open Question 1).
* **MCP server.** Each client tree ships a launcher script that applies the
  interpreter order, as `hooks/run-hook.cmd` already does for the hooks. It
  ships only after `windows-latest` proves it, because starting a `.cmd`
  without a shell is the Windows risk. The installer keeps pinning the absolute
  interpreter (Open Question 2).
* **Injection hooks (fail-open tiers).** They still exit 0. Reporting a missing
  engine once per session is a fix under ADR-021 and ADR-004, not part of this
  decision.
* **Skills.** They resolve `<plugin-root>` from the installed skill, as the
  Codex and Copilot trees already do, with no client cache path and no `sort -V`.

**Proposed by:** Claude (agent) at the request of User: Robert van den Breemen,
from the 2026-10-11 defect sweep. **Decision Maker:** User: Robert van den
Breemen settled both human decisions on 2026-10-11, taking the recommended
option each time. The gate refuses when nothing resolves (Open Question 1), and
the MCP server starts through a probing launcher (Open Question 2).

### Confirmation

* An end-to-end test runs setup from a checkout with an empty `HOME`; a violating
  commit is refused with the repair line.
* Claude Code `--plugin-dir <kit> mcp list` reports `✔ Connected` on a PATH with
  only `python3`, on a PATH with only `python`, and on `windows-latest`.
* A test asserts that no `skills/*/SKILL.md` contains a client cache path or
  `sort -V`.
* The sweep checks DEF-02, DEF-21 and DEF-25 report `reproduced=False`.

## Decision Contract

### Must

* Every entry point resolves the interpreter and the engine root through the
  shared order above.
* The commit gate refuses with a named reason, the repair command and the escape
  when a project with an Accepted Enforcement block has no resolvable interpreter
  or engine.
* Setup records the engine root machine-locally only.

### Must Not

* Ship a launcher configuration that needs a command literally named `python`.
* Hard-code a client plugin-cache path, or use `sort -V`, in a skill.
* Write an interpreter or engine path into tracked configuration.

### Exceptions

* A project without an Accepted Enforcement block keeps exit 0 when nothing
  resolves, because it has nothing to enforce.

### Verification

* `tests/test_pre_commit_e2e.py` and `tests/test_skill_resolver.py`, both added
  with the implementation.
* `tests/test_packaging_contract.py` and the client certification tests.
* The two `forbid_pattern` rules below, once this record is Accepted.

## Consequences

### Positive

* The floor ADR-004 promises exists on every install path, including the one
  INSTALL-AGENT.md documents.
* The MCP tools work after the README's quick install on macOS, Debian and
  Ubuntu.
* "Which engine ran?" has one answer in one place.

### Negative

* A contributor without ADR Kit, in a project with Accepted enforcement, is
  refused until they install it or use the escape. Mitigation: the refusal names
  both, and CI remains the authoritative control.
* A launcher adds a file to each client tree, and it has to pass certification
  on three platforms (ADR-010).
* A recorded engine root can go stale when a checkout moves. Mitigation: the
  resolver falls through to the caches and the checkout, ranked by version.

## Pros and Cons of the Options

### One resolver with tier-specific failure behaviour

* Good, because it removes the shared cause of DEF-02, DEF-21 and DEF-25.
* Bad, because it touches four entry points in one change.

### Patch each entry point separately

* Good, because each change is small.
* Bad, because four resolvers keep drifting; `sort -V` survived in ten skills
  after it was fixed in two other places.

### Make the installer the only supported install path

* Good, because the installer already pins the interpreter.
* Bad, because it removes the four-command quick install, while every client
  marketplace keeps serving the unpatched manifest.

### Do nothing

* Good, because nothing changes.
* Bad, because the documented client-neutral setup keeps enforcing nothing, and
  MCP stays absent where only `python3` exists.

## Open Questions

- [x] When a project has an Accepted ADR with an Enforcement block, and no Python 3.10+ or no engine resolves at commit time, does the commit gate refuse the commit (recommended), or keep exiting 0 with a warning? — **Answered 2026-10-11 by User: Robert van den Breemen:** Refuse. When a project has an Accepted ADR with an Enforcement block and no Python 3.10+ or no engine resolves at commit time, the gate refuses the commit with one line naming what is missing, the repair command, and the ADR_KIT_HOOK_DISABLE=1 escape. A project without such a block keeps exit 0. The same principle settles ADR-045 item 3: a non-empty diff the parser cannot read is refused.
- [x] Which mechanism starts the MCP server on a direct marketplace install: a launcher script that probes the interpreter order (recommended, proven on windows-latest before it ships), `python3` as the configured command, or `python` kept with a SessionStart notice and the installer documented as the reliable path? — **Answered 2026-10-11 by User: Robert van den Breemen:** A launcher script in each client tree that probes python3, then python, then py -3, in the order hooks/run-hook.cmd already uses for the hooks. It ships only after windows-latest proves it, because starting a .cmd without a shell is the Windows risk. The installer keeps pinning the absolute interpreter.

## Related Decisions

* Amends ADR-008 (Resolve the enforcement engine from a version-ranked root set
  including the checkout): adds `ADR_KIT_ROOT` and a setup-recorded root to the
  candidate set. The ranking rule is unchanged.
* ADR-004 (Layered ADR context injection): the fail-closed floor this protects,
  and the tiers that set each entry point's failure behaviour.
* ADR-006 (Prepare platform-local marketplaces for native installs): extends its
  interpreter fix beyond the installer-driven install.
* ADR-025 (Separate what tracked configuration may select from what only a
  machine may introduce): where the recorded root lives.
* ADR-010 (Certify three native CLI clients through one outcome contract): the
  launcher must pass certification on all three clients.

## References

* `templates/githooks/pre-commit:88-95`, `:100-120`, `:161-163`.
* `hooks/run-hook.cmd:29-43`; `hooks/adr_hook_core.py:27-31`.
* `.mcp.json:4`, `codex/.mcp.json:5`, `copilot/.mcp.json:5`;
  `clients/installer/payload.py:145-153` (`_patch_mcp_python`).
* `skills/review/SKILL.md:35` and nine other skills.
* INSTALL-AGENT.md section 6; README "Install"; TASK-216; TASK-220; issue #155.
* 2026-10-11 defect sweep (TASK-222): DEF-02, DEF-21, DEF-25.

## Enforcement

```json
{
  "forbid_pattern": [
    {
      "pattern": "~/\\.claude/plugins/cache/rvdbreemen-adr-kit",
      "path_glob": "skills/**/SKILL.md",
      "message": "Resolve the plugin root from the installed skill, not from one client's cache path (ADR-044)."
    },
    {
      "pattern": "sort -V",
      "path_glob": "skills/**/SKILL.md",
      "message": "GNU sort -V is not portable; let the shared resolver rank versions (ADR-044, TASK-216)."
    }
  ],
  "forbid_import": [],
  "require_pattern": []
}
```
