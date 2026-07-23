# Selective ADR context

ADR Kit uses `docs/adr/ADR-INDEX.json` as the local query database for ADR
discovery. Markdown ADRs remain the authority: the index only supplies
deterministic retrieval metadata, lifecycle state, summaries, enforcement
scope, and relationships so an agent does not need to read every ADR.

## Query contract

```bash
python bin/adr-index --check docs/adr
python bin/adr-context --format json --limit 5 "task description"
python bin/adr-context --format json --status Accepted --authority binding \
  --paths src/api.py --components api --symbols RequestHandler "change request"
```

The shared query engine reads schema-v2 `ADR-INDEX.json`, validates bounded
inputs, excludes historical decisions by default, and ranks records from
query text plus exact path, component, symbol, topic, scope, and relationship
signals. Results explain every match. Open only the returned source ADRs before
applying a constraint; never treat the generated summary as decision authority.

`--history` opts into Rejected, Superseded, and Deprecated records.
`--strict-index` fails when the index is missing, stale, or incompatible.
Without strict mode the CLI may rebuild an in-memory index from source ADRs
for compatibility and reports the fallback in its result.

Schema-v1 indexes are accepted through one minor-release compatibility window
by taking that visible Markdown fallback; regenerate them to schema v2 rather
than editing them. Existing result fields remain present during the same
window. Legacy `score_adr(..., weights=...)` callers remain callable, but their
weights no longer influence relevance: the shared positive-evidence ranking
contract is authoritative. Projects without retrieval metadata still match on
title, decision summary, enforcement scope, and relationships; completeness is
advisory until the project explicitly enables strict policy.

## Retrieval metadata

Frontmatter may declare:

- `topics` and `aliases` for language people use when asking questions;
- `components` and `symbols` for exact code and architecture identifiers;
- `context_scope: global|selective` to reserve session-wide injection for a
  small set of universally applicable Accepted decisions;
- a `## Decision Contract` body section with `Must`, `Must Not`,
  `Exceptions`, and `Verification` as a compact, reviewable retrieval view.

The index derives `decision_authority` (`binding`, `advisory`, or `historical`)
from lifecycle status and binding metadata; authors do not declare it directly.

For Accepted binding ADRs, metadata completeness is advisory by default.
Projects can configure `"retrieval_completeness": "strict"` only after their
ADR set has been enriched and probed. Retrieval metadata must not invent or
change the decision: an agent proposes it, a human reviews it, and the source
ADR remains authoritative.

## Safe migration

Preview candidates without changing any ADR:

```bash
python bin/adr-migrate --suggest-retrieval --dry-run docs/adr
```

The report contains deterministic candidates and explicitly states that
automatic writing is disabled. Review candidates against the ADR prose,
apply approved metadata deliberately, rebuild the index, and run the probes.
The existing format migration commands remain compatible and separate.

Rollback is equally local: revert the metadata edits, restore the previous
`.adr-kit.json`, and rebuild `ADR-INDEX.json`. Keep `strict_index` and strict
retrieval completeness disabled until the new index and probes are green.
During the compatibility window, older client payloads continue to receive the
stable result fields but do not gain the new lifecycle filters or explanations.

## Project probes and health

Create `docs/adr/adr-context-probes.json` using
`schemas/adr-context-probes.schema.json`, then run:

```bash
python bin/adr-context --check-probes
python bin/adr-status --format json
python bin/adr-doctor --check docs/adr
python bin/adr-guardian retrieval-health
```

Each probe supplies a query and optional paths, components, symbols, topics,
limit, expected inclusions, and expected exclusions. Failures show actual
ranks, scores, roles, and matching signals. Probe failures are blocking doctor
findings; incomplete retrieval metadata follows the configured advisory or
strict policy. Guardian remains read-only and never starts an interview.

## Lifecycle behavior

- Session start injects only Accepted records explicitly marked
  `context_scope: global`.
- Prompt and edit events retrieve governing Accepted records separately from
  advisory Proposed records.
- Subagent and compaction events preserve the already-selected parent context;
  they do not broaden the ADR set.
- Hooks fail open if local retrieval is unavailable. Deterministic lint,
  acceptance, enforcement, and supersession remain the authoritative gates.
- Copilot CLI does not expose every lifecycle event, so its prompt retrieval
  is supported while unsupported event claims remain explicit in the client
  capability matrix.

This keeps context small and explainable while preserving human acceptance
authority and the existing four verification gates.
