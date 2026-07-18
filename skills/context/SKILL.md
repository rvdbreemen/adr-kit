---
name: context
description: Loads the Architecture Decision Records most relevant to a task before you implement it, so existing decisions are considered without burning context on the whole ADR set. Give it a topic (e.g. "mqtt discovery", "heap allocation", "caching") and it returns the 3-5 most relevant ADRs as readable context: title, one-line decision, file path, and relevance score. Accepted ADRs rank higher, but Proposed records can also appear in v0.33.0, so verify status in the source file. Read-only and safe to call from parallel subagents.
argument-hint: "[topic or task description; e.g. \"mqtt discovery\"]"
license: MIT
allowed-tools: [Read, Bash]
---

# adr-kit context

You are running `/adr-kit:context`. Purpose: surface the ADRs that constrain the
task at hand **before** writing code, so you implement within existing decisions
instead of rediscovering or contradicting them. This is read-only — it never
edits ADRs or code, so it is safe to call from parallel subagents.

## Procedure

1. Take the topic from the argument. If none was given, ask the user for a short
   topic or task description (one phrase is enough).

2. Run the bundled deterministic ranker from the project root. Request JSON so
   you get the relevance signals, and keep the default limit of 5:

   ```bash
   python <adr-kit-plugin-path>/bin/adr-context --format json --limit 5 "<topic>"
   ```

   - Use `--adr-dir <path>` if the project keeps ADRs somewhere other than
     `docs/adr/`.
   - Use `--min-score <0-1>` to tighten or loosen the relevance cutoff
     (default `0.1`).

3. **If the result is an empty list (`[]`)**: tell the user plainly —
   *"No ADRs match '<topic>'; all existing ADRs may apply, or none constrain
   this work."* Do not invent relevance. Stop here.

4. **Otherwise**, for each returned ADR, `Read` the file and present it as
   readable context, not just a filename:

   - **`ADR-NNN — <title>`** (relevance: `<score>`)
   - one-line summary of its semantic decision (`## Decision Outcome` for
     MADR, `## Decision` for Nygard/canonical; paraphrase rather than dumping)
   - file path, so the user can open the full record

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
- Loading context is not approval to violate a decision. If the task conflicts
  with an Accepted ADR, surface the conflict and use `/adr-kit:judge` or
  `/adr-kit:adr` to resolve it.
