---
name: supersede
description: "Supersede an Accepted ADR while preserving history and links. Use for replacing a decision, successor ADRs, or changed architecture."
argument-hint: "[ADR id to supersede; e.g. \"ADR-007\"]"
license: MIT
disable-model-invocation: true
allowed-tools: [Read, Bash, Edit, Write, Task]
---

# adr-kit supersede

Use `$ARGUMENTS` as the required ADR id. Ask for the id when it is empty and
never infer a destructive target.

You are running `/adr-kit:supersede`. Purpose: replace an existing decision
with a new one without rewriting history. The old ADR's reasoning stays
immutable; only its Status line changes and its Status History grows by one
entry. Everything else lands in the new ADR.

Resolve the plugin path once and reuse it:

```bash
ADR_KIT=$(ls -d ~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/ | sort -V | tail -1)
```

## Step 1 - Identify the target and show its graph

1. Take the ADR id from the argument; if absent, ask which ADR to supersede.
2. Run the graph tool on it and show the user the result:

   ```bash
   python "$ADR_KIT/bin/adr-related" ADR-OLD --format json
   ```

   Present inbound edges explicitly: these are the ADRs that point at the
   target and may need their Related Decisions updated after supersession.
   Flag any dangling references already present.

3. **Conflict guard (hard stop).** Read the old ADR. If its Status line
   already says `Superseded by ADR-X` where X is NOT the ADR you are about to
   create, stop and surface the conflict to the user verbatim. Never
   overwrite an existing supersession pointer; the user must resolve the
   chain (perhaps the right move is superseding ADR-X instead).

4. Confirm with the user: "Supersede ADR-OLD (<title>) with a new ADR about
   <reason>?" Do not proceed without a yes.

## Step 2 - Draft the superseding ADR (Proposed)

Before drafting, run `/adr-kit:grill --revalidate ADR-OLD`. Revalidation covers
changed forces, alternatives, migration, consequences, new evidence, and impact
on related ADRs. It supports unchanged, Proposed successor, reject-candidate,
and explicit defer outcomes. Never rewrite Accepted prose.

Determine the next free ADR number (highest existing + 1, no gaps, no reuse).
Invoke the `adr-generator` subagent with:

- The user's stated reason for the change as Context input.
- The old ADR's Decision text as background (what is being replaced and why
  it no longer holds).
- An explicit instruction to include in `## Related Decisions`:
  `- **ADR-OLD (<old title>)**: Supersedes ADR-OLD.`
- `Status: Proposed` with today's date, and a `status_history` entry:

  ```yaml
  status_history:
    - date: YYYY-MM-DD
      status: Proposed
      changed_by: <user>
      reason: Drafted to supersede ADR-OLD
      changed_via: adr-kit /adr-kit:supersede
  ```

Show the draft to the user. **Never auto-accept it.** The user reviews and
may iterate; the new ADR is only flipped to `Accepted` (by the user or on
their explicit instruction) before the old one is touched.

Show the complete acceptance packet and require an explicit `yes` in this
active session before invoking `adr accept`. A failure or interruption stops
before `adr supersede`, leaving the old ADR and reciprocal links unchanged.

## Step 3 - Supersede transactionally (only after approval)

Only after the user has approved the new ADR-NEW:

1. Ensure ADR-NEW is Accepted through `python "$ADR_KIT/bin/adr" accept
   ADR-NEW --adr-dir docs/adr`. Acceptance is blocked unless all verification
   gates pass.
2. Run the only supported reciprocal mutation:

   ```bash
   python "$ADR_KIT/bin/adr" supersede ADR-OLD --by ADR-NEW \
     --adr-dir docs/adr --changed-by "<user>" \
     --reason "Superseded by ADR-NEW (<new title>)"
   ```

   The command rejects illegal or conflicting chains before mutation. It
   atomically updates both ADRs and all generated index views, and restores
   their original bytes if any write or index refresh fails. Never reproduce
   these edits manually.
3. If inbound ADRs from Step 1 reference the old decision, list them and offer
   a note pointing at ADR-NEW. Apply only entries the user approves.

## Step 4 - Verify the chain

Run all three and show the results:

```bash
python "$ADR_KIT/bin/adr-related" ADR-OLD --format json
python "$ADR_KIT/bin/adr-related" ADR-NEW --format json
python "$ADR_KIT/bin/adr-lint" docs/adr/
```

The chain is clean when:

- ADR-OLD shows outbound `superseded-by -> ADR-NEW` and ADR-NEW shows
  outbound `supersedes -> ADR-OLD` (and inbound mirrors of each other).
- Neither graph reports dangling references.
- adr-lint reports no FAIL on either file.

If any check fails, fix the link wiring (not the old ADR's prose) and re-run
until clean. Report the final state to the user.

## Boundaries

- **Immutability.** The only allowed edits to the old ADR are the Status line
  flip and appended status history performed by the lifecycle command.
- **Conflict guard.** An existing `Superseded by` pointing at a different ADR
  is a stop-the-line conflict. Surface it; never overwrite.
- **No auto-accept.** The new ADR starts as Proposed and a human approves it.
  Do not flip it to Accepted on your own initiative.
- **No silent edits to third ADRs.** Updating inbound referencers happens
  only per-entry with user approval.
- **Verification is part of the job.** Do not declare the supersession done
  before Step 4 is clean.
