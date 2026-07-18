---
id: "ADR-003"
title: "Canonical Template Stays the Storage Format; MADR and Nygard Are Import Formats"
status: "Superseded"
date: "2026-07-18"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: "ADR-005"
---
# ADR-003 Canonical Template Stays the Storage Format; MADR and Nygard Are Import Formats

## Status

Superseded by ADR-005, 2026-07-18.

## Status History

```yaml
status_history:
  - date: 2026-06-12
    status: Proposed
    changed_by: robert@vandenbreemen.net
    reason: Input-contract decision for MADR / Nygard compatibility (task-5)
    changed_via: adr-kit v0.21.0
  - date: 2026-06-12
    status: Accepted
    changed_by: robert@vandenbreemen.net
    reason: Implemented with template-profile detection, migrate patterns G/H, fixtures, and tests
    changed_via: adr-kit v0.21.0
  - date: 2026-07-18
    status: Superseded
    changed_by: Codex
    reason: ADR-005 replaces the canonical-only storage contract with selectable profiles
    changed_via: adr-kit lifecycle
```

## Context

adr-kit validates ADRs against a canonical seven-section template
(`templates/adr-template.md`, enforced by `bin/adr-lint`). The two dominant
formats in the wild are different: MADR (madr.github.io, ~2.2k stars) uses
`## Context and Problem Statement`, `## Considered Options`,
`## Decision Outcome`, and YAML frontmatter status; Nygard / adr-tools
(~5.5k stars) uses only `## Status`, `## Context`, `## Decision`,
`## Consequences`. A project adopting adr-kit with an existing MADR or
Nygard ADR set sees every file FAIL lint, which is a high switching cost
and the main adoption blocker identified in backlog task-5.

The question is the input contract: does adr-kit accept multiple storage
formats, or one storage format with import mappings?

## Decision

Keep the canonical seven-section template as the only storage format.
MADR and Nygard are import formats, handled in three advisory layers:

1. **Detection is heuristic and advisory.** `bin/adr-audit` classifies each
   file in `docs/adr/` as `canonical`, `madr`, `nygard`, or `unknown`
   (`detect_template_profile`) and emits a `template_profile` finding for
   MADR / Nygard files, pointing at `/adr-kit:migrate`. It never blocks.
2. **Mapping lives in the migrate skill.** `skills/migrate/SKILL.md` gains
   two named patterns: "MADR mapping" (Pattern G: Context and Problem
   Statement to Context, Considered Options plus Pros and Cons to
   Alternatives Considered, Decision Outcome to Decision plus Consequences,
   frontmatter status to `## Status`) and "Nygard lift" (Pattern H: the four
   Nygard sections map 1:1; Alternatives Considered, Related Decisions, and
   References are created with TODO placeholders). Read-then-confirm
   posture is unchanged.
3. **The declared profile is informational.** `.adr-kit.json` gains an
   optional `template.profile` ("canonical" | "madr" | "nygard") in
   `schemas/adr-kit-config.schema.json`. It annotates audit findings and
   hints migrate; lint keeps validating against the canonical sections or
   `template.required_sections` exactly as before.

## Alternatives Considered

- **Multi-format lint (teach adr-lint to validate MADR and Nygard
  natively).** Rejected: every downstream tool (judge, context, retire,
  status-history) parses the canonical sections; supporting three storage
  formats triples the parsing surface and forks the gate semantics
  (Nygard has no Alternatives Considered for the completeness gate to
  check).
- **A separate bin/adr-import converter.** Rejected for now: the migrate
  skill already owns legacy-shape rewriting with a read-then-confirm
  posture and human judgment for content mapping (e.g. which pros and cons
  become rejection reasons). A deterministic converter would either
  fabricate content or produce worse output than the guided skill.
- **Do nothing (document manual conversion only).** Rejected: the switching
  cost stays where it is, and audit stays blind to the most common reason a
  fresh adr-kit install fails lint.

## Consequences

**Positive:**

- One storage format: all gates, judges, and parsers keep a single
  contract.
- Existing MADR / Nygard sets get a guided, lint-clean migration path,
  documented by the `tests/fixtures/madr-migrated/` and
  `tests/fixtures/nygard-migrated/` fixtures.
- Detection is free and advisory; no new blocking behavior anywhere.

**Negative:**

- Detection is heuristic: hybrid or heavily customized templates classify
  as `unknown` and still need manual review.
- The MADR mapping is lossy in shape (frontmatter and per-option
  subsections are folded into prose sections), so a round-trip back to
  MADR is not supported.

## Related Decisions

- ADR-001 (Make Per-Commit LLM Gates Opt-In): same advisory-first posture;
  detection nudges, it does not block.

## References

- MADR template: https://adr.github.io/madr/
- Nygard's original post: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- adr-tools: https://github.com/npryce/adr-tools
- Implementation: `bin/adr-audit` (`detect_template_profile`,
  `scan_template_profiles`), `skills/migrate/SKILL.md` (Patterns G and H),
  `schemas/adr-kit-config.schema.json` (`template.profile`)
- Fixtures and tests: `tests/fixtures/madr/`, `tests/fixtures/nygard/`,
  `tests/test_template_profiles.py`
- Backlog: task-5 (MADR / Nygard format compatibility)
