---
name: context
description: "Find ADRs relevant to a task before implementation. Use for ADR context, governing decisions, architecture constraints, or why a design exists. Read-only."
argument-hint: "[topic or task description; e.g. \"mqtt discovery\"]"
license: MIT
allowed-tools: [Read, Bash]
---

# adr-kit context

Use `$ARGUMENTS` as the task topic. If empty, use the current user request or
ask for one short topic when the request does not identify one.

You are running `/adr-kit:context`. Purpose: surface the ADRs that constrain the
task at hand **before** writing code, so you implement within existing decisions
instead of rediscovering or contradicting them. This is read-only — it never
edits ADRs or code, so it is safe to call from parallel subagents.

## Procedure

1. Take the topic from the argument. If none was given, ask the user for a short
   topic or task description (one phrase is enough).

2. Treat schema-v2 `docs/adr/ADR-INDEX.json` as the generated local query
   database. Never treat it as the decision authority or edit it by hand; source
   Markdown remains authoritative. Run the shared deterministic query engine
   from the project root and keep the default limit of 5:

   ```bash
   python <adr-kit-plugin-path>/bin/adr-context --format json --limit 5 "<topic>"
   ```

   - Use `--adr-dir <path>` if the project keeps ADRs somewhere other than
     `docs/adr/`.
   - Use `--min-score <0-1>` to tighten or loosen the relevance cutoff
     (default `0.1`).
   - Include known `--paths`, `--components`, `--symbols`, or `--topics`.
     Filter with `--status` or `--authority`; use `--history` only when the
     task needs Rejected, Superseded, or Deprecated rationale.
   - Keep governing Accepted and advisory Proposed results separate.
   - If the JSON graph is missing or stale, report the fallback and
     `python bin/adr-index docs/adr` as the repair command. Use
     `--strict-index` when fallback would be unsafe.

3. **If the result is an empty list (`[]`)**: tell the user plainly —
   *"No ADRs match '<topic>'; all existing ADRs may apply, or none constrain
   this work."* Do not invent relevance. Stop here.

4. **Otherwise**, for each returned ADR, `Read` the file and present it as
   readable context, not just a filename:

   - **`ADR-NNN — <title>`** (relevance: `<score>`)
   - returned status and format;
   - returned decision summary, authority, role, and matched signals;
   - declared related ADR ids when they explain the match;
   - file path, then `Read` that source ADR before stating a binding constraint.

   Order by relevance (highest first), most relevant ADR last in your message so
   it stays closest to the work that follows.

5. Briefly state the net constraint: in one or two sentences, what these
   decisions require or forbid for the task. Then proceed with (or hand back to)
   the implementation.

## Boundaries

- Read-only. Never modify ADRs, code, or status during a context load.
- Report relevance honestly — a low score means "weakly related", not "must
  comply". Do not inflate scores to seem thorough.
- The ranker is a heuristic. If the user mentions a decision you do not see in
  the results, widen with a different topic or lower `--min-score` rather than
  assuming no ADR exists.
- Query the index first and open only returned sources; do not scan every ADR
  merely to discover relevance.
- Loading context is not approval to violate a decision. If the task conflicts
  with an Accepted ADR, surface the conflict and use `/adr-kit:judge` or
  `/adr-kit:adr` to resolve it.
