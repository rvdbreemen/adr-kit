# adr-kit v0.11.0

Adds `/adr-kit:migrate`, a guided rewrite skill that brings legacy-shaped ADRs into the canonical-seven-section template enforced by `/adr-kit:lint`. Closes the loop opened by v0.9.0's scoped lint with grandfathering: v0.9.0 lets you tolerate legacy shape; v0.11.0 lets you fix it.

## What is new

### `/adr-kit:migrate` skill

User-only invocable (`disable-model-invocation: true`); never silent. Always shows a per-file plan first, asks for explicit confirmation, then applies via Edit.

Six named transformation patterns observed in real-world legacy ADRs:

- **Pattern A**: inline `**Status:** ...` / `**Date:** ...` / `**Supersedes:** ...` lines fold into a top-level `## Status` heading.
- **Pattern B**: `### Alternatives considered` nested inside Context promoted to top-level `## Alternatives Considered` between Decision and Consequences.
- **Pattern C**: `### Alternatives considered and rejected` nested inside Consequences promoted to top-level before Consequences.
- **Pattern D**: `## Related` renamed to `## Related Decisions`, with external file paths / URLs / PR references split off into a new `## References` section.
- **Pattern E**: missing `## References` with no source content gets a `<!-- TODO: populate -->` placeholder. Never fabricates.
- **Pattern F**: missing `## Alternatives Considered` with no source discussion gets a `<!-- TODO: document at least 2 alternatives -->` placeholder. Never fabricates.

### Cardinal rules

- **Read-then-confirm**: silent writes are forbidden.
- **No fabrication**: TODO placeholders for genuine content gaps; do not invent.
- **Preserve content**: restructure shape, not substance. Bullet points, prose, examples stay verbatim.
- **Idempotent**: re-running on an already-canonical ADR is a no-op.
- **Respects markers**: `<!-- adr-kit-lint: skip -->` files are left untouched; `<!-- adr-kit-lint: advisory -->` files get a warning before migration.
- **Respects `template.required_sections`**: targets the project-specific list from `.adr-kit.json` if set, otherwise the canonical seven.

## Use case

```
$ /adr-kit:migrate docs/adr/ADR-007-timer-based-task-scheduling.md

Proposed migration plan (1 file):

ADR-007-timer-based-task-scheduling.md
  Pattern A: inline `**Status:**` -> `## Status` heading
  Pattern D: `## Related` -> `## Related Decisions` + new `## References`

Confirm to apply (y/n)?
```

After confirmation: two Edit operations, file now passes the Completeness gate strictly. The user runs `/adr-kit:lint <file>` to verify (the migrate skill does not lint automatically).

## When to use it

- After adopting `.adr-kit.json` with `strict_from`, when you want to gradually move legacy ADRs into the canonical shape.
- When upgrading the project's ADR template and you want existing ADRs to follow.
- One-off, on a single file you happen to be touching for other reasons.

The skill scales from one file to a whole tree. The plan-first workflow means you can preview a tree-wide change before any disk write.

## What is intentionally not in scope

- **Filename renaming**: a Consistency-gate FAIL on filename pattern (e.g. dots in the filename, lowercase prefix) requires `git mv` and possibly cross-ref fixes. The migrate skill does not touch filenames; use the `<!-- adr-kit-lint: skip consistency -->` marker instead, or rename by hand.
- **Body-prose rewriting**: migrate restructures shape (heading levels, section order); it does not rewrite the prose inside sections.
- **Fabricating Alternatives or References content**: TODO placeholders mark the genuine gap; a human fills them in.
- **Auto-running lint after migration**: separation of concerns. The user decides when to verify.
- **Deterministic Python CLI variant** (`bin/adr-migrate`): migration is judgement-heavy. Same reasoning that put Evidence and Clarity gates as opt-in for `bin/adr-lint`. The skill is the only sanctioned interface.

## Pairs with

- **v0.9.0**: scoped lint with grandfathering. Tolerates legacy shape via ADVISORY tier.
- **v0.10.0**: `bin/adr-lint` deterministic CLI for CI integration.
- **v0.10.1**: `disable-model-invocation: true` discipline on lint.

The trio (lint + CLI + migrate) covers the read, the gate, and the rewrite. Together with the original `adr` and `setup` skills, the toolkit is now end-to-end for project-scale ADR maintenance.

## Install / upgrade

Existing installations:

```
/plugin marketplace remove rvdbreemen-adr-kit
/plugin marketplace add rvdbreemen/adr-kit
/plugin install adr-kit@rvdbreemen-adr-kit
/reload-plugins
```

After reload, `/adr-kit:migrate` appears in autocomplete alongside `/adr-kit:lint` and `/adr-kit:setup`.

## Refs

- Backlog task: TASK-424 (migrate skill design and implementation).
- Originating discipline: today's manual restructure of ADR-082 through ADR-087 (TASK-420 follow-through). Patterns A-D are exactly the transformations applied there; the skill makes them repeatable.
