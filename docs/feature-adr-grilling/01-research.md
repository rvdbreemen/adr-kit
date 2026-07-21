# Research: grilling techniques for ADR Kit

Date consulted: 2026-07-20

## Sources

- Matt Pocock, [grill-with-docs: Align Before You
  Build](https://www.aihero.dev/grill-with-docs)
- Matt Pocock, [The /grilling
  Skill](https://www.aihero.dev/skills-grilling)

This document paraphrases and analyses the sources. It does not copy their
skill implementation or long passages.

## What the source techniques contribute

The underlying `grilling` technique is a decision-tree interview. It descends
through dependent decisions one branch at a time. Each question is asked
separately, includes the agent's recommended answer, and is delayed until
earlier answers have established the context needed to ask it well.

Questions that can be answered from the codebase should be answered by
inspection rather than delegated to the user. The interactive part is reserved
for intent, trade-offs, ownership, risk tolerance, and other information that
cannot be recovered deterministically.

`grill-with-docs` adds durable outputs. It writes resolved vocabulary and
hard-to-reverse decisions while the interview progresses so that alignment does
not disappear with the chat session. It deliberately treats ADRs as rare:
reversible implementation choices should not be promoted to architecture
records merely because they were discussed.

## Transferable principles

ADR Kit should adopt the following principles:

1. Ask one question at a time.
2. Traverse decisions in dependency order.
3. Answer repository-factual questions by inspecting the repository.
4. Include a recommended answer and its evidence with each question.
5. Record answers as they resolve instead of reconstructing them at the end.
6. Keep unresolved terms and questions explicit.
7. Create an ADR only for a consequential, difficult-to-reverse trade-off.
8. Require shared understanding before executing an irreversible lifecycle
   transition.
9. Preserve a durable paper trail that can be resumed in a later session.

## Where ADR Kit must be stricter

The source techniques are interaction patterns, not a complete ADR governance
system. ADR Kit already has stronger invariants that must remain in control:

- schema and profile validation;
- evidence and quality gates;
- explicit lifecycle transitions;
- reciprocal supersession links;
- deterministic indexes;
- Accepted ADR enforcement;
- pre-commit and CI behavior;
- cross-client generated artifacts;
- bounded hook and command performance.

Consequently, ADR Kit should use grilling as an authoring and decision-support
layer. It must not replace lint, readiness, lifecycle commands, or deterministic
enforcement.

## Vocabulary and context files

The source workflow writes resolved terminology to `CONTEXT.md`. ADR Kit should
use an existing `CONTEXT.md` when a project already maintains one, because
inconsistent vocabulary reduces ADR quality. ADR Kit should not require or
automatically create that file as part of the first implementation. Vocabulary
management remains optional and subordinate to the project's existing context
conventions.

## Resulting hypothesis

Grilling adds the most value at moments where repository evidence is available
but human intent is still required:

- qualifying a subject as an architectural decision;
- filling missing rationale or alternatives;
- reconstructing why shipped code exists;
- resolving review findings into a Proposed ADR;
- completing or rejecting an old Proposed ADR;
- confirming a successor or retirement decision.

It adds little value inside non-interactive hooks and deterministic CI. Those
surfaces should detect and route work to an explicit grill command instead.
