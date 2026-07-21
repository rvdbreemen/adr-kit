# ADR lifecycle analysis for grilling

## Analysis model

Every candidate statement used during grilling is classified as one of:

- **Observed** — directly supported by repository, diff, history, configuration,
  or another cited source.
- **Human-stated** — supplied or explicitly confirmed by the engineer or
  architect.
- **Inferred** — a reasoned interpretation that remains subject to confirmation.
- **Unknown** — required information that neither the repository nor the user
  has resolved.

Only observed and human-stated information may be presented as settled.
Inferences must remain labelled. Unknowns become explicit open questions.

## Lifecycle opportunity matrix

| Lifecycle moment | Value of grilling | Trigger and outcome |
|---|---|---|
| Qualify a new subject | High | `/adr-kit:adr <subject>` determines whether the subject is consequential and difficult to reverse. |
| Author a Proposed ADR | High | Resolve context, forces, decision, alternatives, consequences, evidence, scope, and ownership one question at a time. |
| Reconstruct from code or chat | High | Extract observed facts first, then ask for rationale that cannot be recovered. |
| `adr-kit:init` | High | Create candidates as Proposed and adapt interview depth to the completeness of direct evidence. |
| Branch or PR review | High | Convert a likely undocumented decision or linked Proposed ADR into an explicit decision workflow. |
| Judge an Accepted ADR conflict | Medium | Enforcement stays deterministic; grilling helps decide whether code changes or a successor ADR is appropriate. |
| Lint a Proposed ADR | Medium | Translate actionable lint and readiness findings into the next human question. |
| Accept an ADR | High | Present an acceptance packet, request explicit confirmation, then call `adr accept`. |
| Guardian session start | Medium | Rank at most three unfinished decisions and route the user to `/adr-kit:grill`. |
| Supersede | High | Reassess changed forces, migration, consequences, and reciprocal history. |
| Retire or revalidate | High | Confirm that the original constraints no longer apply or record a successor. |
| Pre-commit hook | Low | Never interview; emit a short advisory and exact command. |
| Pull request CI | Medium | Produce deterministic readiness evidence; block only an explicitly linked, implemented Proposed ADR. |

## Proposed is active decision work

`Proposed` must not become a permanent parking state. A grill should drive each
proposal to one of three explicit outcomes:

- **Accepted** — the decision is complete, passes all gates, and the engineer
  confirms the acceptance packet.
- **Rejected** — the candidate is not the chosen architecture or is not an ADR.
- **Deferred** — the record remains Proposed with named open questions, a reason,
  and a future re-evaluation condition or date.

Guardian should prioritize shipped-but-Proposed and ready-for-confirmation
records before merely old proposals.

## Acceptance interaction

The final interaction is deliberately narrow:

1. Readiness reports no unresolved mechanical or human findings.
2. The agent shows the chosen decision, primary rationale, alternatives,
   consequences, evidence, scope, conflicts, and lifecycle effect.
3. The engineer explicitly answers `yes` in the active session.
4. The workflow invokes the existing `adr accept` command.
5. Existing lifecycle validation remains able to refuse the transition.

An affirmative statement recovered from a chat log, PR body, commit message, or
previous session cannot substitute for step 3.

## Automation boundaries

### Hooks

Hooks must be fast, deterministic, non-interactive, and fail-open for new
advisory behavior. They may suggest a grill command but may not start one or
perform a full readiness sweep.

### Continuous integration

CI performs deterministic analysis only:

- an architectural-looking change without an ADR remains advisory;
- an explicitly linked Proposed ADR that the same pull request demonstrably
  implements fails the readiness gate;
- Accepted ADR enforcement remains separate and authoritative;
- output goes to Step Summary and annotations, not an automatically posted PR
  comment.

### MCP

MCP exposes readiness as a read-only tool. It does not expose acceptance or
another lifecycle mutation.

## Failure and abuse analysis

- **Rubber-stamping:** prevented by a structured acceptance packet and explicit
  same-session confirmation.
- **Question overload:** prevented by one-question interaction and repository
  grounding.
- **Hallucinated rationale:** prevented by evidence classification.
- **Prompt injection:** source material is treated as untrusted data and cannot
  alter the workflow.
- **Endless Proposed status:** addressed by guardian ranking, deferral metadata,
  and explicit terminal outcomes.
- **False CI blocks:** prevented by restricting blocking to explicit,
  inspectable implementation links.
- **Performance regression:** prevented by keeping model and full scans out of
  hooks, sharing parsed state, and certifying dedicated budgets.
- **Lifecycle weakening:** prevented by routing every transition through
  existing lifecycle commands and gates.
