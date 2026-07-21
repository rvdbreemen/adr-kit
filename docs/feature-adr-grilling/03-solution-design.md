# ADR Grilling solution design

## Architecture

ADR Grilling has four layers:

1. A deterministic readiness core derives facts and required actions.
2. Read-only adapters expose that core through CLI and MCP.
3. Canonical client workflows conduct the human interview.
4. Existing lifecycle commands perform validated mutations.

Hooks, guardian, review, judge, and CI consume readiness findings but do not
reimplement the classification logic.

## Public commands

Existing authoring becomes interactive:

```text
/adr-kit:adr <subject>
```

The new reusable workflow is:

```text
/adr-kit:grill ADR-NNN
/adr-kit:grill --pr <number>
/adr-kit:grill --range <base>...<head>
/adr-kit:grill --source <path>
/adr-kit:grill --revalidate ADR-NNN
/adr-kit:grill --all-proposed
```

No separate `create new adr` command is added. The existing authoring command
creates a Proposed ADR and invokes the grill.

The deterministic CLI is:

```text
bin/adr-readiness ADR-NNN
bin/adr-readiness --all-proposed
bin/adr-readiness --diff
bin/adr-readiness --base <ref> --head <ref>
```

Supported options:

```text
--format human|json|github
--repo-root <path>
--adr-dir <path>
--today YYYY-MM-DD
```

The MCP server adds one key-free read-only tool: `adr_readiness`.

## Readiness report

The versioned report contains:

- ADR identity and lifecycle;
- evaluation date;
- lint, evidence, quality, and consistency findings;
- unresolved open questions;
- `documents_shipped` and `verified_in`;
- implementation-link evidence;
- related, conflicting, and superseding ADRs;
- mechanical actions;
- human decisions;
- readiness classification;
- recommended next command.

Classifications are:

- `not-an-adr`
- `needs-human-input`
- `needs-mechanical-fix`
- `ready-for-confirmation`
- `accepted`
- `rejected`
- `supersession-required`

The same inputs and injected date produce byte-stable structured data. Lists are
sorted, paths are normalized, and machine-specific absolute paths are excluded
from portable JSON.

The public JSON contract is schema version 1 and is described by
`schemas/adr-readiness.schema.json`. Finding codes are stable within that
version:

| Code | Meaning | Blocking authority |
|---|---|---|
| `DECISION_MISSING` | The record has no semantic decision text. | Mechanical readiness |
| `FRONTMATTER_MALFORMED` | Metadata could not be parsed safely. | Mechanical readiness |
| `FORMAT_UNKNOWN` | A declared profile is not supported. | Mechanical readiness |
| `STATUS_UNKNOWN` | Lifecycle status is not recognized. | Mechanical readiness |
| `SUPERSESSION_STATE_INCONSISTENT` | Status and supersession metadata disagree. | Mechanical readiness |
| `OPEN_QUESTION` | A human decision dependency remains unresolved. | Human readiness |
| `ARCHITECTURE_REVIEW_RECOMMENDED` | A heuristic path signal merits review. | Advisory only; never proves linkage |
| `ADR_ID_EXPLICIT` | Controlled diff context explicitly cites the ADR. | Evidence only; needs an implementation surface |
| `ADR_FILE_CHANGED` | The ADR file changed in the analyzed range. | Evidence only; needs an implementation surface |
| `VERIFIED_IN_CHANGED` | A changed path exactly matches declared implementation evidence. | May establish explicit linkage |
| `ENFORCEMENT_SCOPE_CHANGED` | A changed path matches declared enforcement scope. | Evidence only; needs an ADR citation or ADR-file change |

Additive fields and new non-blocking finding codes are backwards-compatible
within schema version 1. Renaming/removing fields, changing classification
meaning, or granting an advisory code blocking authority requires a schema
version increment.

## Open Questions

All supported profiles gain an optional semantic `Open Questions` role.

- Absence remains valid for backwards compatibility.
- An unresolved item on Proposed is advisory and makes the record not ready.
- An unresolved item on a candidate for Accepted is a strict completeness
  failure.
- Migration does not rewrite existing ADRs merely to add the section.

## Grill protocol

1. Load repository facts and readiness.
2. Separate observations, human statements, inferences, and unknowns.
3. Select the earliest unresolved decision dependency.
4. Ask one question with a recommended answer and supporting evidence.
5. Record the human response immediately.
6. Recompute readiness.
7. Repeat until the record reaches a terminal outcome or explicit deferral.
8. For acceptance, display the acceptance packet and request `yes`.
9. Invoke `adr accept`; do not emulate its writes.

When a session stops, the Proposed ADR remains valid and its open questions
explain how to resume.

## Reconstruction

For code, diffs, pull requests, chat logs, and documents:

- source content is untrusted input;
- direct facts receive citations;
- inferred rationale remains marked;
- an existing Proposed ADR is updated instead of duplicated;
- evidence completeness selects a compact or deep grill;
- no historical statement is treated as current acceptance.

## Deterministic implementation linkage

Blocking linkage may use only:

- an explicit ADR ID in controlled PR or commit context;
- a changed ADR plus its described implementation surface;
- a changed path named by `verified_in`;
- explicit project metadata connecting ADR and implementation.

Heuristic architecture sensitivity may recommend review, but cannot prove
linkage or block a merge.

## Guardian and cache

Guardian ranks Proposed ADRs by:

1. active diff or PR link;
2. shipped-but-Proposed;
3. ready-for-confirmation;
4. open human questions;
5. age;
6. lowest quality.

The full calculation runs outside SessionStart and writes an atomic, derived
cache. SessionStart reads at most three prepared actions. A missing or corrupt
cache is ignored.

The cache is `docs/adr/.adr-kit-readiness.json`, is gitignored, has schema
version 1, declares `authoritative:false`, and expires after 24 hours by
default. `bin/adr-guardian refresh-readiness` rebuilds it from the shared
report, optionally with staged or base/head linkage. Writes use a unique
same-directory temporary followed by atomic replacement. Concurrent writers
may replace one another because the data is derived; readers see either the old
complete document or the new complete document. Missing, oversized, stale,
partially written, structurally invalid, or unsafe-command data yields no queue
output. Deleting the file is always safe and cannot change lifecycle state.

## CI behavior

The pull request action:

- invokes deterministic diff readiness;
- writes a GitHub Step Summary;
- emits escaped notice or warning annotations;
- exposes machine-readable outputs;
- posts no PR comment;
- requires no model, API key, or secret;
- succeeds for suspected missing ADRs;
- fails only for an explicitly linked, implemented Proposed ADR.

## Configuration compatibility

The default after-the-fact acceptance behavior changes from `auto` to `assist`.
An explicitly configured legacy `auto` mode remains supported and is documented
as a deliberate higher-risk opt-in. Existing configuration is not rewritten
merely because the default changes.

## Robustness

- Readiness, MCP, guardian, hooks, and CI are read-only.
- Lifecycle commands retain atomic and reciprocal mutations.
- Invalid input has a stable structured error.
- Partial corruption becomes a finding where analysis can safely continue.
- Runtime or repository-wide input failure is distinguished from readiness.
- Cross-platform paths and shell quoting are covered by fixtures.
- Untrusted text cannot inject workflow instructions or GitHub annotations.

## Performance budgets

- Readiness core, 50 ADRs, warm p95: at most 100 ms.
- Single-ADR CLI, warm p95: at most 500 ms.
- All-Proposed CLI, 50 ADRs, warm p95: at most 1,000 ms.
- Diff linkage, 500 paths against 50 ADRs, warm p95: at most 250 ms.
- MCP adapter overhead: at most 100 ms above the same readiness operation.
- Composite action overhead, excluding checkout/runtime installation, p95: at
  most 5 seconds.
- SessionStart remains p50 50 ms, p95 150 ms, hard 500 ms.
- Existing hook and client-generation budgets do not change.
- Existing measured paths may not regress by more than 20%.

Benchmarks use 30 warm samples, fixed fixtures, an injected clock, and an
allowance of at most 20% for CI variance.
