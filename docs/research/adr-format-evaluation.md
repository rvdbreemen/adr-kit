# ADR Format Evaluation for Agent-Friendly Decision Records

Date: 2026-07-18

## Executive conclusion

adr-kit should use **MADR 4** as the default body format for newly created
records, while supporting **Nygard** and the existing **canonical adr-kit**
format as selectable profiles.

The recommendation is not a claim that MADR is the most common format by a
measured global usage count. No authoritative census of ADR files or templates
exists. Public evidence instead supports two dominant lightweight families:

- Nygard is the original, concise format and has the largest dedicated CLI
  ecosystem signal through `adr-tools`.
- MADR is the actively maintained structured format, is the default template
  in Log4brains, and explicitly records drivers, options, rationale, and
  confirmation.

A 2026 empirical comparison screened Tyree/Akerman, Nygard, arc42,
Y-Statements, and MADR. Nygard and MADR were the two expert-screened finalists;
Nygard scored better overall with student participants because it was concise,
while MADR better supported structural detail and specific architectural
requirements. For adr-kit's use case, the extra structure is valuable: an
agent can identify the problem, drivers, option set, chosen outcome, and
trade-offs without inferring them from prose.

## Sources and adoption signals

Adoption signals are directional proxies, not exact usage counts.

| Source | Signal and relevance |
| --- | --- |
| [Nygard's original ADR article](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) | Defines the influential Status, Context, Decision, Consequences structure and immutable supersession model. |
| [adr-tools](https://github.com/npryce/adr-tools) | Mature Nygard-oriented CLI with about 5.6k GitHub stars and 631 forks when checked on 2026-07-18. Its latest listed release is from 2018, but the format remains widely referenced. |
| [MADR project](https://adr.github.io/madr/) and [repository](https://github.com/adr/madr) | Maintained structured template with full, minimal, annotated, and bare variants; about 2.2k GitHub stars and 461 forks when checked. MADR 4.0.0 was released in 2024. |
| [Log4brains](https://github.com/thomvaill/log4brains) | ADR publishing/management tool with about 1.5k stars; its customizable template defaults to MADR. |
| [ADR template catalog](https://adr.github.io/adr-templates/) | Community catalog identifies MADR, Nygard, Y-Statements, and other templates, and explains why MADR includes explicit trade-off analysis. |
| [2026 empirical comparison](https://arxiv.org/abs/2604.27333) | Compares Tyree/Akerman, Nygard, arc42, Y-Statements, and MADR. Nygard and MADR were the top expert-screened templates. |
| [AWS ADR process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html) | Requires at least context, decision, and consequences, plus a Proposed-to-Accepted lifecycle and immutable supersession. |
| [Azure Well-Architected ADR guidance](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) | Recommends problem context, options, outcome, trade-offs, confidence, status, append-only history, and reciprocal supersession. |
| [arc42 architecture decisions](https://docs.arc42.org/section-9/) | Treats ADRs as one possible form within a larger architecture-documentation structure; useful, but not a distinct lightweight file contract for adr-kit. |

## Formats considered

### MADR 4

Core semantics are Context and Problem Statement, Decision Drivers, Considered
Options, Decision Outcome, Consequences, and Confirmation. Status and date can
be metadata. Explicit drivers and option-level pros/cons reduce the amount of
reasoning an agent must reconstruct. The cost is more headings and therefore
more authoring and token overhead.

### Nygard / adr-tools

Core semantics are Status, Context, Decision, and Consequences. This is the
lowest-ceremony full ADR format, is easy to scan, and has the strongest public
tool-popularity signal. Its deliberately small shape does not require explicit
decision drivers, rejected alternatives, evidence, related decisions, or
verification. adr-kit must add small optional extension sections when strict
four-gate governance is desired.

### Existing adr-kit canonical format

The current seven-section format adds Alternatives Considered, Related
Decisions, and References to Nygard's core, with invariant frontmatter, Status
History, and optional Enforcement. It already supports adr-kit's gates well,
but is a project-specific shape with less external recognition than MADR.
Keeping it avoids forced rewrites and makes upgrades safe.

### Y-Statement

The compact sentence records context, concern, chosen option, desired quality,
accepted downside, and optionally rejected options/rationale. It is excellent
as an index summary or decision synopsis. As a complete storage profile it is
too compressed for deterministic checks of evidence, multiple alternatives,
status history, references, and enforcement without surrounding it with enough
extension sections that it stops being meaningfully compact.

### Tyree/Akerman

This detailed enterprise template captures issue, decision, status, group,
assumptions, constraints, positions, argument, implications, and related
decisions. It is strong for formal review and evidence but high-ceremony,
verbose, and more expensive for routine agent context.

### arc42

arc42 provides a place and guidance for architecture decisions inside a larger
architecture description and explicitly allows ADRs, lists, tables, or
sections. It is an important documentation ecosystem, but not one stable
single-record Markdown grammar for adr-kit to parse.

### ISO/IEC/IEEE 42010-oriented records

ISO 42010 supplies architecture-description concepts and rationale/traceability
expectations. It is not a standard four-heading ADR file format. An
ISO-oriented profile would add stakeholders, concerns, viewpoints, and formal
traceability that exceed adr-kit's lightweight scope.

### Tool-specific and custom formats

Log4brains is a tool and defaults to MADR; it is not a separate semantic
format. Large template collections and bespoke organizational templates are
valuable migration inputs, but their diversity makes them unsuitable as
built-in deterministic profiles. They remain `unknown` unless a project maps
headings through `template.required_sections` or migrates them.

## Weighted evaluation

Scores are 1 (poor) to 5 (strong). Weights reflect adr-kit's purpose: reliable
human/agent authoring, deterministic local parsing, and enforceable lifecycle
governance. The scoring is an adr-kit engineering evaluation informed by the
sources above, not a result reported by those sources.

| Criterion | Weight | MADR | Nygard | canonical | Y-Statement | Tyree/Akerman | arc42 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Agent reliability: explicit semantic slots | 22% | 5 | 3 | 4 | 2 | 4 | 3 |
| Evidence/options/trade-off quality | 18% | 5 | 2 | 4 | 2 | 5 | 4 |
| Deterministic parseability | 15% | 5 | 5 | 5 | 4 | 4 | 3 |
| Human readability and adoption ease | 12% | 4 | 5 | 4 | 4 | 3 | 3 |
| Adoption/tooling signal | 10% | 4 | 5 | 2 | 2 | 2 | 3 |
| Token efficiency | 8% | 3 | 5 | 3 | 5 | 1 | 1 |
| Status/history compatibility | 7% | 4 | 4 | 5 | 2 | 4 | 3 |
| Enforcement extensibility | 5% | 5 | 4 | 5 | 2 | 4 | 3 |
| Migration safety for adr-kit | 3% | 4 | 5 | 5 | 4 | 2 | 2 |
| **Weighted score / 5** | **100%** | **4.52** | **3.90** | **4.09** | **2.83** | **3.64** | **2.93** |

## Compatibility model

All profiles vary only the human-facing body headings. These machine contracts
remain invariant:

- adr-kit YAML-subset frontmatter, with an optional `format` discriminator;
- `## Status` and append-only `## Status History`;
- `## Related Decisions` and `## References`;
- optional `## Enforcement` fenced JSON;
- ADR identifiers, filenames, and reciprocal supersession metadata.

Tools consume semantic roles (`context`, `decision`, `alternatives`,
`consequences`, and so on) through one shared profile registry. A declared
per-file format wins. Otherwise, deterministic heading detection is used.
Conflicting unlabelled heading families are `hybrid` and fail strict lint with
an actionable message. Unknown formats remain readable by tolerant status and
enforcement paths but cannot pass strict profile validation.

## Selected profiles

1. `madr` — default for new records and new projects.
2. `nygard` — concise option, with adr-kit extension sections for alternatives,
   related decisions, references, history, and enforcement.
3. `canonical` — backward-compatible name for the existing adr-kit template.

Y-Statements remain useful as generated one-line summaries, but are not a
storage profile. Tyree/Akerman, arc42, ISO-oriented, and custom templates remain
documented migration inputs rather than built-in profiles.

## Migration strategy

- Existing records are not rewritten during upgrade.
- Missing `template.profile` means legacy-compatible detection; existing
  canonical records keep working.
- New projects and `adr new` default to MADR unless configuration selects
  another supported profile.
- A dry-run migration can convert headings between supported profiles while
  preserving frontmatter, history, prose, related links, references, and
  Enforcement byte-for-byte where their semantic role is unchanged.
- Re-running the same migration is a no-op.
- Unsupported or hybrid records require an explicit source profile or manual
  mapping; adr-kit does not guess destructively.
