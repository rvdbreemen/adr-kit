---
id: "ADR-005"
title: "Use Selectable ADR Body Profiles with MADR as the Default"
status: "Accepted"
date: "2026-07-18"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes:
  - "ADR-003"
superseded_by: null
format: "madr"
topics:
  - "body profile"
  - "template"
  - "format registry"
aliases:
  - "MADR default"
  - "selectable profile"
  - "semantic roles"
components:
  - "adr"
  - "adr-lint"
  - "adr-migrate"
---
# ADR-005 Use Selectable ADR Body Profiles with MADR as the Default

## Status

Accepted, 2026-07-18.

## Status History

```yaml
status_history:
  - date: 2026-07-18
    status: Proposed
    changed_by: Codex
    reason: User approved the researched MADR switch and selectable-format implementation for TASK-26
    changed_via: adr-kit lifecycle
  - date: 2026-07-18
    status: Accepted
    changed_by: Codex
    reason: User approved the MADR-default selectable-format decision and expanded TASK-26 execution
    changed_via: adr-kit lifecycle
  - date: 2026-07-18
    status: Accepted
    changed_by: Codex
    reason: ADR-005 replaces the canonical-only storage contract with selectable profiles
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR-003 made the existing adr-kit seven-section template the only storage
format and treated MADR and Nygard as import formats. That kept parsers simple,
but made `template.profile` informational and forced teams to rewrite otherwise
valid records before using strict lint, lifecycle, context, or enforcement.

TASK-26 asks adr-kit to switch to an agent-friendly default and make formats
selectable. The research in
`docs/research/adr-format-evaluation.md` compares the common lightweight
formats and the materially relevant formal alternatives. Public evidence does
not provide a global usage census. It does show Nygard and MADR as the two
leading lightweight families, and a 2026 empirical comparison selected those
two as its expert-screened finalists.

Terminology used below: ADR (Architecture Decision Record), MADR (Markdown
Architectural Decision Records), CLI (command-line interface), LLM (large
language model), ISO (International Organization for Standardization), and
TASK (Backlog task identifier).

Nygard optimizes concision. MADR makes the problem, drivers, considered options,
outcome, rationale, consequences, and confirmation explicit. Those semantic
slots lower ambiguity for an agent that drafts, retrieves, reviews, or enforces
a decision. adr-kit still needs invariant machine-readable status, history,
relationships, references, and Enforcement regardless of body vocabulary.

## Decision Drivers

* Preserve deterministic, stdlib-only local operation.
* Give agents explicit problem, driver, option, outcome, and consequence slots.
* Preserve human readability and a concise selectable profile.
* Avoid rewriting existing adr-kit records during upgrade.
* Keep lifecycle, reciprocal supersession, indexing, retrieval, and enforcement
  behavior identical across formats.
* Fail safely and actionably for unsupported or ambiguous hybrid documents.

## Considered Options

* MADR-only storage.
* Nygard-only storage.
* Keep the ADR-003 canonical-only contract.
* Selectable MADR, Nygard, and legacy canonical profiles behind one semantic
  parser contract.
* Support every researched template, including Y-Statements, Tyree/Akerman,
  arc42, and ISO-oriented records.

## Decision Outcome

Chosen option: **support selectable `madr`, `nygard`, and `canonical` body
profiles through one semantic format registry, and make `madr` the default for
new records and projects.**

1. Body profiles map headings to semantic roles. Engines consume roles rather
   than hard-coded heading names.
2. YAML-subset frontmatter remains invariant and gains an optional `format`
   discriminator. `## Status`, `## Status History`, `## Related Decisions`,
   `## References`, and optional `## Enforcement` remain common extension
   sections in every adr-kit profile.
3. A per-file supported `format` value is authoritative. Without it, tools use
   deterministic, fence-aware heading detection. Conflicting unlabelled
   families are `hybrid`; unrecognized shapes are `unknown`. Strict lint rejects
   both with remediation, while tolerant read/enforcement paths continue to use
   invariant metadata where safe.
4. `template.profile` becomes an operational creation default. The default is
   `madr`; `--profile` can override it for a single creation or migration.
5. The Nygard template keeps its four core sections and includes small adr-kit
   extension sections for alternatives, relationships, references, history,
   and enforcement so all four verification gates remain available.
6. Existing canonical ADRs stay valid without a rewrite. Migration between
   supported profiles is explicit, dry-run by default, content-preserving,
   deterministic, and idempotent.
7. Y-Statements are supported as concise summaries, not full storage profiles.
   Tyree/Akerman, arc42, ISO-oriented, and custom formats remain evaluated
   migration inputs; shipping them as built-in profiles would add parsing
   surface without enough routine value.

### Confirmation

The decision is confirmed when focused fixtures prove create, detect, lint,
mutate, index, retrieve, enforce, relate, retire, and migrate behavior for all
three profiles; generated client payloads are synchronized; and the full test
suite passes on the supported Python runtime.

## Consequences

### Positive

* New users get the most explicit agent-oriented structure by default.
* Teams that value brevity can select Nygard without losing lifecycle or
  enforcement metadata.
* Existing adr-kit repositories upgrade without forced content changes.
* One semantic registry prevents each engine from inventing its own heading
  aliases.
* Explicit unsupported/hybrid behavior replaces silent misclassification.

### Negative

* The shared parser and templates add more maintained surface than ADR-003's
  single-storage-format decision.
* Nygard records used with strict adr-kit gates include extension sections
  beyond Nygard's minimal four headings.
* A MADR default uses more tokens than Nygard. Bounded index and context
  extraction must continue to select only the decision outcome, not the full
  record.
* Projects with heavily customized headings still need an explicit migration
  or `template.required_sections`; arbitrary schemas are not auto-inferred.

## Pros and Cons of the Options

### MADR-only storage

* Good, because every new record has explicit agent-friendly structure.
* Bad, because existing canonical and Nygard repositories require rewrites.

### Nygard-only storage

* Good, because it is concise, familiar, and backed by the largest dedicated
  CLI adoption signal.
* Bad, because alternatives, drivers, evidence, and confirmation are implicit.

### Keep canonical-only storage

* Good, because current parsers remain simple.
* Bad, because format selection stays cosmetic and adoption requires migration.

### Select three profiles through semantic roles

* Good, because it balances explicit defaults, concise choice, and backward
  compatibility.
* Good, because shared roles keep engine behavior deterministic.
* Bad, because profile detection, migration, and cross-profile tests become
  permanent maintenance obligations.

### Support every researched format

* Good, because almost any team could keep its house style unchanged.
* Bad, because Y-Statements lack full gate semantics and formal templates add
  high ceremony and many optional fields.
* Bad, because the parser/test matrix would grow faster than demonstrated use.

## Related Decisions

* Supersedes ADR-003: selectable profiles replace its canonical-only storage
  contract.
* Related to ADR-001: format parsing stays deterministic and never enables an
  LLM or network call.
* Related to ADR-004: every profile exposes the same semantic decision and
  enforcement roles to the bounded context-injection layers.

## References

* `docs/research/adr-format-evaluation.md`
* https://arxiv.org/abs/2604.27333
* https://adr.github.io/madr/
* https://github.com/adr/madr
* https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
* https://github.com/npryce/adr-tools
* https://adr.github.io/adr-templates/
* https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html
* https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record

## Enforcement

```json
{
  "require_pattern": [
    {
      "pattern": "\"default\"\\s*:\\s*\"madr\"",
      "path_glob": "schemas/adr-kit-config.schema.json",
      "message": "The project config schema must expose MADR as the selectable default."
    }
  ]
}
```
