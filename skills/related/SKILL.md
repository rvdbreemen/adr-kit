---
name: related
description: "Show inbound and outbound links for one ADR. Use for related decisions, dependencies, dangling ADR links, supersession, or retirement. Read-only."
argument-hint: "[ADR id; e.g. \"ADR-007\" or \"7\"]"
license: MIT
allowed-tools: [Read, Bash]
---

# adr-kit related

Use `$ARGUMENTS` as the required ADR id. Ask for the id when it is empty.

You are running `/adr-kit:related`. Purpose: show who an ADR points at and who
points back at it, before anyone changes its status. This is read-only; it
never edits ADRs.

## Procedure

1. Take the ADR id from the argument. If none was given, ask the user which
   ADR to inspect (id or title fragment is enough; resolve a title fragment by
   listing `docs/adr/ADR-*.md` and matching).

2. Resolve the plugin path and run the bundled graph tool from the project
   root:

   ```bash
   ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1)
   python "$ADR_KIT/bin/adr-related" ADR-NNN --format json
   ```

   - Use `--adr-dir <path>` if the project keeps ADRs somewhere other than
     `docs/adr/`.
   - Exit code 2 means the id is unknown or the directory is missing; relay
     the stderr message and stop.

3. Present the graph readably, not as raw JSON:

   - **`ADR-NNN <title>`** (status, file path)
   - **Outbound**: one line per edge, `-> ADR-MMM [kind] <title> (<status>)`.
     Kinds: `related`, `supersedes`, `superseded-by`, `amended-by`.
   - **Inbound**: one line per edge, `<- ADR-MMM [kind] <title> (<status>)`.
     Inbound also surfaces `mention` edges: plain ADR-id occurrences outside
     any declared relationship.

4. If the `dangling` list is non-empty, call it out explicitly: these are
   references to ADR ids that do not exist in the set. Suggest fixing the
   stale link (typo) or restoring the missing ADR; do not fix it yourself in
   this skill.

5. One closing sentence of interpretation: e.g. "Nothing depends on this ADR;
   superseding it is low-risk" or "Three Accepted ADRs reference this one;
   superseding it requires updating their Related Decisions."

## Boundaries

- Read-only. Never modify ADRs, statuses, or links during a graph load.
- Matching is whole-token: ADR-043 is never inferred from ADR-0430. Trust the
  tool's edges; do not add speculative relationships the files do not state.
- A `mention` edge is weak evidence, not a declared dependency. Say so when it
  is the only inbound edge.
- If the user wants to act on the graph (supersede, retire), hand off to
  `/adr-kit:supersede` or `/adr-kit:retire` instead of editing here.
