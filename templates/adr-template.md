# ADR-NNN Short Imperative Title

## Status

Proposed, YYYY-MM-DD.

<!-- When accepted: replace with `Accepted, YYYY-MM-DD.`. When superseded: `Superseded by ADR-MMM, YYYY-MM-DD.`. Do not edit other sections of an Accepted/Deprecated ADR; write a new superseding ADR instead. -->

## Context

<!-- The problem this ADR resolves and the constraints driving the decision. Cite evidence: incidents, profiling data, requirements, prior ADRs, code paths, dependencies. The Evidence verification gate looks here for at least one concrete reference. Avoid hand-waving ("scalability", "best practice"); state the actual force. -->

## Decision

<!-- The chosen approach, in imperative voice. One paragraph or a short bulleted list. The Clarity gate looks here for: a single concrete decision (not a survey of options), no hedging language ("we should perhaps consider"), and traceable identifiers (file paths, function names, config keys) where applicable. -->

## Alternatives Considered

<!-- At least two alternatives, each with a one-line rejection reason. The Completeness gate requires this section to be non-empty and to contain ≥ 2 distinct alternatives. "Do nothing" counts as an alternative if it was actually weighed. -->

- **Alternative A.** Rejection reason.
- **Alternative B.** Rejection reason.

## Consequences

<!-- Both directions: what gets easier, what gets harder, what new constraints fall out. The Completeness gate requires both positive and negative consequences (or an explicit note that one direction is empty). -->

**Positive:**
- Consequence 1.

**Negative:**
- Consequence 1.

## Related Decisions

<!-- Other ADRs this one depends on, supersedes, is superseded by, or relates to. Use ADR-NNN identifiers. If none, write "- None." -->

- None.

## References

<!-- External evidence supporting the decision: links to incidents, RFCs, papers, vendor docs, profiling reports, code paths, prior PRs. The Evidence gate looks here for at least one concrete external reference. -->

- ...

## Enforcement

<!--
OPTIONAL section, introduced in adr-kit v0.12.0. Machine-readable rules that bin/adr-judge applies to staged git diffs at commit time.

If the rule can be expressed as a regex / glob, prefer declarative rules (fast, deterministic, no LLM round-trip in the hook).

If the rule is too nuanced for regex, set "llm_judge": true. The pre-commit hook will treat the ADR as advisory; deeper review happens in-session via /adr-kit:judge.

If the ADR is "manual review only" (e.g., a process or governance decision with no code surface), delete this entire section. ADRs without an Enforcement block are skipped silently by the judge.

Schema: schemas/adr-enforcement.schema.json
-->

```json
{
  "forbid_pattern": [
    { "pattern": "\\bForbiddenSymbol\\b", "path_glob": "src/**/*.py", "message": "Use AllowedSymbol instead (see Decision above)." }
  ],
  "forbid_import": [
    { "pattern": "^import\\s+legacy_module\\b", "path_glob": "src/**/*.py" }
  ],
  "require_pattern": [],
  "llm_judge": false
}
```
