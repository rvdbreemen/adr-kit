---
name: supersede
description: Guided supersession of an existing Architecture Decision Record. Shows the target's dependency graph first, drafts the superseding ADR via the adr-generator subagent (Status Proposed, back-linked), and only after explicit user approval flips the old ADR's Status line to "Superseded by ADR-M", appends status_history entries on both sides, and wires Related Decisions both ways. Verifies the chain with bin/adr-related and bin/adr-lint. Refuses to overwrite an existing supersession that points at a different ADR.
argument-hint: "[ADR id to supersede; e.g. \"ADR-007\"]"
license: MIT
disable-model-invocation: true
allowed-tools: [Read, Bash, Edit, Write, Task]
---

# adr-kit supersede

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

## Step 3 - Flip the old ADR (only after approval)

Only after the user has approved the new ADR-NEW:

1. On the OLD ADR, exactly two edits and nothing else:
   - Change its `## Status` line to: `Superseded by ADR-NEW, YYYY-MM-DD.`
   - Append one entry to its `status_history` YAML block:

     ```yaml
       - date: YYYY-MM-DD
         status: Superseded
         changed_by: <user>
         reason: Superseded by ADR-NEW (<new title>)
         changed_via: adr-kit /adr-kit:supersede
     ```

   Do NOT touch Context, Decision, Alternatives, Consequences, References,
   or Enforcement of the old ADR. Do not edit earlier status_history entries.

2. Wire Related Decisions both ways:
   - New ADR already carries `Supersedes ADR-OLD` (from Step 2).
   - Add to the OLD ADR's `## Related Decisions`? No: the old ADR is
     immutable beyond the two edits above. The back-pointer lives in its
     Status line (`Superseded by ADR-NEW`), which bin/adr-related reads as a
     `superseded-by` outbound edge. That is the wiring.
   - If inbound ADRs from Step 1 reference the OLD decision in their
     `## Related Decisions`, list them for the user and offer to add a note
     pointing at ADR-NEW. Apply only the entries the user approves.

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
  flip and the appended status_history entry. Everything else is read-only.
- **Conflict guard.** An existing `Superseded by` pointing at a different ADR
  is a stop-the-line conflict. Surface it; never overwrite.
- **No auto-accept.** The new ADR starts as Proposed and a human approves it.
  Do not flip it to Accepted on your own initiative.
- **No silent edits to third ADRs.** Updating inbound referencers happens
  only per-entry with user approval.
- **Verification is part of the job.** Do not declare the supersession done
  before Step 4 is clean.
