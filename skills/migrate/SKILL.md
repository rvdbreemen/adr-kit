---
name: migrate
description: Preview and migrate legacy or supported ADR body profiles. Adds canonical metadata and converts between MADR, Nygard, and legacy canonical headings without rewriting decision prose.
argument-hint: "[file or directory; defaults to docs/adr/]"
disable-model-invocation: true
allowed-tools: [Read, Edit, Glob, Grep]
---

# adr-kit migrate

You are running `/adr-kit:migrate`. The user wants to add invariant adr-kit
metadata or convert between the supported `madr`, `nygard`, and `canonical`
body profiles. This is a write skill: preview first, show the result, obtain
confirmation, then apply it.

Start with the shared read-only discovery report:

```text
python bin/adr-migrate --plan <path>
```

The plan detects MADR, Nygard, canonical, conservative Y-Statement,
Tyree/Akerman, and arc42 markers, including recognizable files that do not yet
use an `ADR-NNN-...md` filename. It reports an exact deterministic preview
when metadata and filename normalization are safe. Ambiguous, hybrid, and
semantically lossy formats are routed to this guided workflow. `--plan` never
writes, and detection never authorizes migration.

Use the deterministic CLI whenever the source is already a supported profile:

```text
python bin/adr-migrate --dry-run --to-profile madr <path>
python bin/adr-migrate --to-profile madr <path>
python bin/adr-migrate --check --to-profile madr <path>
```

Use `--from-profile` only to disambiguate an `unknown` or `hybrid` record after
reading it. The same source and target is an idempotent no-op. Existing
frontmatter, Status History, relationships, references, and Enforcement remain
unchanged. Use the guided patterns below only for genuinely legacy shapes that
cannot be converted by semantic headings alone.

## Inputs

- **No argument**: migrate ADRs in `docs/adr/` (the whole tree).
- **A directory path**: migrate ADRs under that directory.
- **A file path**: migrate that one file.

If the path does not exist or contains no ADR files, say so plainly and stop.

## Cardinal rules

1. **Read-then-confirm.** Always read every target file before proposing edits. Always show the proposed restructure (file by file, summarised) and ask for explicit confirmation before calling Edit. Silent writes are forbidden.
2. **No fabrication.** If a target-profile section is missing and the source contains no content that maps to it, do not invent a decision. The deterministic CLI inserts an explicit TODO or `None` extension; guided migration uses a `<!-- TODO: populate -->` placeholder.
3. **Preserve content.** The migration restructures shape, not substance. Bullet points, prose, examples, and links from the source must appear in the target unchanged. Reorder; do not rewrite.
4. **Idempotent.** Running migration when the record already uses the selected target profile is a no-op.
5. **Skip files that opt out.** A file with `<!-- adr-kit-lint: skip -->` is left untouched. A file with `<!-- adr-kit-lint: advisory -->` gets a warning ("this file is currently in advisory mode; migrating will make the marker meaningless") and a confirmation prompt.

## Workflow

### Step 1: read the policy

Look for `docs/adr/.adr-kit.json` (relative to project root, or the directory
passed). If `template.profile` is set, use it as the target unless the user
selected another profile. `template.required_sections` describes a custom
shape and requires guided migration. The default target is MADR. Every profile
keeps `Status`, `Status History`, `Related Decisions`, `References`, and
`Enforcement`. The semantic choice headings are:

| Profile | Context | Alternatives | Decision |
| --- | --- | --- | --- |
| MADR | `Context and Problem Statement` | `Considered Options` | `Decision Outcome` |
| Nygard | `Context` | `Alternatives Considered` | `Decision` |
| Canonical | `Context` | `Alternatives Considered` | `Decision` |

MADR also requires `Decision Drivers`. Use the shared registry and selected
template as the ordering contract instead of assuming canonical headings.

### Step 2: classify each input file

For each file, determine:

- **Already on the selected profile** (required semantic sections present) -> skip, report as "no changes needed".
- **Marker says skip** -> skip, report as "skipped per marker".
- **Marker says advisory** -> ask "advisory marker is on this file; migrate anyway?"
- **Migratable** -> identify which patterns apply (see next section).

### Step 3: identify patterns

The skill body below documents the patterns observed in real-world legacy ADRs. Apply each pattern that fits, in this order. Do not invent new transformations.

#### Pattern A: inline status promotion

Source:

```markdown
# ADR-NNN Title

**Status:** Accepted
**Date:** 2026-04-25
**Supersedes:** ADR-XXX (optional)
```

Target:

```markdown
# ADR-NNN Title

## Status

Accepted, 2026-04-25. Supersedes ADR-XXX (optional).
```

If only `**Status:**` exists with no `**Date:**`, the Status section reads `Accepted` (without date).

#### Pattern B: alternatives inside Context

Source has a `### Alternatives considered:` (or `### Alternatives considered and rejected`) heading nested inside `## Context`. Target: lift the entire block out, change `### ` to `## `, and place the new top-level `## Alternatives Considered` heading between `## Decision` and `## Consequences`. Preserve content verbatim; only the heading level and position change.

#### Pattern C: alternatives inside Consequences

Same as Pattern B but the source nests alternatives inside `## Consequences`. Target: same restructure, place between Decision and Consequences.

#### Pattern D: Related to Related Decisions + References split

Source: a `## Related` section that mixes ADR/TASK references with file paths, PR links, vendor doc URLs, internal docs.

Target: rename to `## Related Decisions`. Move pure-external references (files, URLs, PRs that are not ADR or TASK identifiers) to a new `## References` section that follows. Keep ADR-NNN and TASK-NNN entries in `## Related Decisions`.

Heuristic for splitting:
- Lines starting with `ADR-`, `TASK-`, or referencing those identifiers -> `## Related Decisions`.
- Lines starting with backticks (file path), URL, or `PR `/`Issue ` references -> `## References`.
- When ambiguous, leave in `## Related Decisions` (safer default).

#### Pattern E: missing References with no inline content

If after Pattern D there are no external references to populate `## References`, create the section with a placeholder:

```markdown
## References

<!-- TODO: populate from inline citations or external sources cited in the body. -->
```

Never invent references. The placeholder makes it clear to a human reviewer that this is a known gap.

#### Pattern F: missing Alternatives Considered with no source

If the source legitimately has no alternatives discussion anywhere, create the section with a placeholder:

```markdown
## Alternatives Considered

<!-- TODO: document at least 2 alternatives that were considered and rejected, with reasoning. -->
```

This is a real gap a human should fill, but the skill must not fabricate.

#### Guided Pattern G: unsupported MADR variant

Source is a MADR-shaped ADR (madr.github.io): YAML frontmatter carrying
`status:` / `date:`, plus `## Context and Problem Statement`,
`## Considered Options`, `## Decision Outcome`, and often
`## Pros and Cons of the Options` and `### Positive Consequences` /
`### Negative Consequences` subsections. Standard MADR records are supported
directly and should use `bin/adr-migrate --to-profile ...`. Use this mapping
only for an `unknown` or `hybrid` MADR variant that the semantic registry
cannot convert safely.

Mapping to semantic roles (content moves verbatim; target headings come from
the selected profile):

| MADR source | Semantic target |
| --- | --- |
| frontmatter `status:` + `date:` (or inline `* Status:` lines) | invariant `Status`; preserve and complete frontmatter |
| `## Context and Problem Statement` plus `## Decision Drivers` | `context` and `drivers` roles |
| `## Considered Options` plus `## Pros and Cons of the Options` | `alternatives` role; keep the chosen option marked |
| `## Decision Outcome` ("Chosen option: ..., because ...") | `decision` role |
| positive/negative consequence subsections or bullets | `consequences` role |
| `## Links` / `## More Information` | split per Pattern D: ADR identifiers to `## Related Decisions`, external links to `## References` |

If the source has no Related Decisions or References content, apply
Patterns E / F TODO placeholders. Never invent rejection reasons that the
Pros and Cons section does not state; if an option has no documented cons,
carry it over with `<!-- TODO: state why this option was rejected -->`.

#### Guided Pattern H: minimal or unsupported Nygard variant

Source is a Nygard / adr-tools ADR: exactly `## Status`, `## Context`,
`## Decision`, `## Consequences`, nothing else. Standard Nygard records are a
supported source profile. Prefer the deterministic CLI, which preserves those
four sections and adds the selected profile's explicit extension placeholders.

The four sections map directly to semantic roles and their content is
preserved verbatim. Missing target-profile sections are created with explicit
TODO or `None` placeholders:

- `## Alternatives Considered` between Decision and Consequences, via
  Pattern F's placeholder.
- `## Related Decisions` after Consequences, with `- None.` unless the
  Status or Context text references other ADRs (e.g. "Supersedes ADR-9"),
  in which case those references move here.
- `## References` last, via Pattern E's placeholder.

Nygard Status sections often contain supersession links ("Superseded by
[ADR-12]"). Keep them in `## Status` as prose and mirror the ADR identifier
into `## Related Decisions`.

### Step 4: present the plan

Before applying any edit, show the user a per-file summary:

```
Proposed migration plan (3 files):

ADR-007-timer-based-task-scheduling.md
  Pattern A: inline `**Status:**` -> `## Status` heading
  Pattern D: `## Related` -> `## Related Decisions` + new `## References`

ADR-029-simple-xhr-ota-flash.md
  Pattern A: inline `**Status:**` -> `## Status` heading
  Pattern F: missing `## Alternatives Considered`, will create with TODO placeholder

ADR-058-nonblocking-pic-command-response.md
  Pattern A: inline `**Status:**` -> `## Status` heading
  Pattern F: missing `## Alternatives Considered`, will create with TODO placeholder
  Pattern E: missing `## References`, will create with TODO placeholder
  No `## Related Decisions` content found in source; will create with `- None.`

Confirm to apply (y/n)?
```

If the user declines, stop without writing.

### Step 5: apply edits

After confirmation, apply each transformation via Edit. One Edit per logical change, so the diff is reviewable. Report what was changed per file.

### Step 6: post-migration verification

After all edits, suggest the user run `/adr-kit:lint <path>` to confirm the migrated files now PASS strictly. Do NOT run lint yourself: that is a separate skill the user invokes.

## What you do not do

- You do not modify the body content of sections. Headings move; prose stays.
- You do not auto-fabricate Alternatives Considered or References content. Use TODO placeholders.
- You do not rename ADR files (Consistency-gate filename FAILs). Out of scope.
- You do not edit ADRs that already PASS strict.
- You do not invoke `/adr-kit:lint` after migration. The user decides when to verify.

## Reporting format

Single-file migration:

```
ADR-007-timer-based-task-scheduling.md migrated.
  Applied: Pattern A (Status promotion), Pattern D (Related split).
  Run /adr-kit:lint on this file to verify.
```

Directory migration:

```
Migrated 3 of 80 candidate files. 1 already on the target profile (skipped). 76 deferred (no patterns matched, manual review needed).

Applied:
  ADR-007 (A, D)
  ADR-029 (A, F)
  ADR-058 (A, F, E, no Related content)

Skipped:
  ADR-022 (already on the target profile)

Deferred (manual review): 76 files.
  Reason: complex shape that did not match any of patterns A through H. Inspect by hand.

Run /adr-kit:lint docs/adr/ to confirm overall result.
```

The aggregate's bottom line tells the user one concrete next step (run lint), never invents a status the migration did not actually achieve.

## Edge cases

- **Multiple inline metadata lines**: source has `**Status:**`, `**Date:**`, `**Supersedes:**`, `**Amended by:**`, etc. Fold all into the new `## Status` section as a comma-separated sentence. Order: Status, date, supersedes/amended.
- **Empty Related section**: source has `## Related` with no body or only whitespace. Target: `## Related Decisions` with `- None.` body.
- **Anchor comments inline at top**: source has a `Renumbered from ADR-XXX ...` line before `**Date:**`. Fold into the new `## Status` section as a trailing sentence: "Renumbered from ADR-XXX on YYYY-MM-DD to resolve duplicate numbering. Content unchanged."
- **Body has Markdown that confuses heading-detection**: e.g. a `## ` inside a fenced code block. The skill treats only headings *outside* code fences as semantic sections. If unsure, ask the user.
- **Source uses `## Pros and Cons` or `## Decision drivers`**: if the file matches the MADR shape, Pattern G consumes these (`## Pros and Cons of the Options` feeds `## Alternatives Considered`, `## Decision Drivers` folds into `## Context`). Otherwise do not rename these; they are project-specific and the user can address custom subsections in a follow-up pass.

## Anti-patterns to refuse

If the migration would require any of these, refuse and explain:

- Renaming ADR files. Out of scope; surfaces commit / cross-ref breakage.
- Modifying body prose ("the Decision section reads better if reorganised..."). Restructure shape only.
- Fabricating Alternatives or References. TODO placeholder is the answer.
- Skipping the user confirmation. Read-then-confirm is non-negotiable.
- Running `/adr-kit:lint` automatically after migration. The user decides.
