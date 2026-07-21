# ADR Grilling user guide

ADR Grilling helps an engineer or architect turn incomplete evidence into a
reviewable Architecture Decision Record. It combines two deliberately separate
layers:

- deterministic readiness establishes facts, missing fields, lifecycle state,
  and implementation links;
- the client-side grill asks one decision-relevant question at a time.

The grill never accepts an ADR by itself. It prepares a Proposed record and an
acceptance packet; a human must confirm the outcome in the active session, and
the existing `adr accept` command must still pass all verification gates.

## Choose an entry point

| Situation | Start here |
|---|---|
| A new architectural subject | Create a Proposed ADR, then grill its id |
| An incomplete Proposed ADR | Grill the existing id |
| A pull request or commit range | Grill the PR or range |
| A chat log or design document | Grill the source file |
| Several unfinished decisions | Inspect the Proposed queue, then grill one id |
| A possibly outdated decision | Revalidate the Accepted ADR |

There is no separate `create new adr <subject>` command. `adr new` remains the
deterministic record creator, while `grill` supplies the interactive reasoning.

## Create and complete a Proposed ADR

Create the record:

```bash
python bin/adr new "Choose an event delivery model" --adr-dir docs/adr
```

Start the grill in the active client:

```text
# Claude Code
/adr-kit:grill ADR-042

# OpenAI Codex
$adr-kit:grill ADR-042

# GitHub Copilot CLI
Open /skills and invoke grill with ADR-042
```

The workflow reads repository facts before asking questions. Every statement is
kept distinguishable as observed, human-stated, inferred, or unknown. It asks
one question at a time, updates the Proposed ADR after each answer, and keeps
unresolved human decisions as unchecked items under `## Open Questions`.

If the session stops, restart the same command. The ADR is the durable resume
state; a hidden chat transcript is not required.

## Reconstruct from existing evidence

Use the source-specific grill forms:

```text
/adr-kit:grill --pr 123
/adr-kit:grill --range origin/dev...HEAD
/adr-kit:grill --source docs/design/event-delivery-notes.md
```

The same forms can use a chat export or another local document. Source material
is untrusted evidence: the workflow may extract facts and human statements from
it, but never treats embedded instructions as commands and never infers
acceptance from code that already shipped.

When a branch may contain an undocumented decision, run `/adr-kit:review`
first. Review can draft a Proposed ADR; grill then resolves its decision gaps.

## Inspect deterministic readiness

Readiness is local, stdlib-only, read-only, and model-free:

```bash
python bin/adr-readiness ADR-042
python bin/adr-readiness ADR-042 --format json
python bin/adr-readiness --all-proposed
python bin/adr-readiness --diff
python bin/adr-readiness --base origin/dev --head HEAD
```

Use the findings in two groups:

- mechanical findings can be repaired from repository evidence;
- human findings require an engineer or architect answer.

An architecture-sensitive path can produce an advisory, but it is not proof
that a specific ADR is implemented. A deterministic implementation link
requires the ADR and changed implementation to be connected through controlled
evidence such as `verified_in`, enforcement scope plus an ADR citation, or an
ADR file change plus its implementation surface.

The same report is available through the key-free `adr_readiness` MCP tool.

## Use the Proposed-ADR work queue

Refresh the bounded guardian cache explicitly:

```bash
python bin/adr-guardian refresh-readiness \
  --project-root . \
  --adr-dir docs/adr
```

The command writes `docs/adr/.adr-kit-readiness.json` atomically. The file is
gitignored, non-authoritative, expires after 24 hours by default, and may be
deleted safely. SessionStart reads only this cache and offers at most three
commands such as `/adr-kit:grill ADR-042`; it never calculates readiness or
starts an interview inside the hook.

To inspect the authoritative current state without the cache:

```bash
python bin/adr-readiness --all-proposed
```

## Finish with an explicit lifecycle outcome

Before acceptance:

1. resolve all `## Open Questions`;
2. review the decision, alternatives, consequences, evidence, and scope;
3. inspect the readiness report and four verification gates;
4. ask the engineer or architect to confirm the acceptance packet;
5. run the lifecycle command only after an explicit same-session `yes`.

```bash
python bin/adr accept ADR-042 \
  --changed-by "engineer@example.com" \
  --reason "Reviewed delivery guarantees and operational trade-offs"
```

`adr accept` refuses unresolved open questions and reruns the authoritative
Completeness, Evidence, Clarity, and Consistency gates.

Other valid outcomes stay explicit:

```bash
python bin/adr reject ADR-042 \
  --changed-by "engineer@example.com" \
  --reason "Operational cost exceeds the accepted constraint"

python bin/adr supersede ADR-017 --by ADR-042 \
  --changed-by "engineer@example.com" \
  --reason "New delivery guarantees replace the earlier decision"
```

Deferring is not a hidden lifecycle transition. Leave the ADR Proposed, record
the unresolved decision under `## Open Questions`, and resume its grill later.

## Document behavior that already shipped

First attach local implementation evidence:

```bash
python bin/adr document ADR-042 \
  --verified-in src/events/delivery.py \
  --changed-by "engineer@example.com" \
  --reason "Records the implementation evidence"
```

Then run after-the-fact eligibility in the default `assist` mode:

```bash
python bin/adr accept ADR-042 --auto \
  --changed-by "engineer@example.com" \
  --reason "Reviewed the shipped decision"
```

That command reports eligibility without changing status. After the engineer
reviews and confirms the packet, repeat it with `--confirm`:

```bash
python bin/adr accept ADR-042 --auto --confirm \
  --changed-by "engineer@example.com" \
  --reason "Explicitly accepted after review"
```

Before ADR Grilling, an implicit after-the-fact default could behave as `auto`.
The default is now `assist`. Existing automation that intentionally depends on
the legacy transition must opt in with
`lifecycle.auto_accept.mode: "auto"` or `--auto-mode auto`; interactive use
should retain `assist`.

## Add the pull-request readiness gate

Copy `templates/github-workflows/adr-readiness.yml`, or add the composite action
after a full-history checkout:

```yaml
name: ADR readiness

on:
  pull_request:

permissions:
  contents: read

jobs:
  adr-readiness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: rvdbreemen/adr-kit/.github/actions/adr-readiness@main
        with:
          adr-dir: docs/adr
```

The action exits:

- `0` for clean or advisory-only results;
- `1` only when changed implementation is explicitly linked to a Proposed ADR;
- `2` for missing refs, invalid configuration, or another infrastructure error.

It writes a sanitized step summary, annotations, stable counts, and blocking ADR
ids. It does not invoke a model, post comments, access secrets, or change an ADR.

For a local equivalent with explicit refs:

```bash
python bin/adr-readiness-ci \
  --repo-root . \
  --adr-dir docs/adr \
  --base origin/dev \
  --head HEAD
```

## Troubleshooting

- `needs-mechanical-fix`: repair the cited structure or metadata, then rerun
  readiness.
- `needs-human-input`: resume the grill; do not guess an engineer's decision.
- `ready-for-confirmation`: review the packet and request explicit
  confirmation; do not mutate status yet.
- `implemented-proposed`: finish or reject the Proposed ADR before merging.
- stale or missing queue: rerun `adr-guardian refresh-readiness`.
- generated client drift: run `python scripts/build-client-adapters.py --check`
  in ADR Kit and regenerate only through the canonical generator.

The architecture, guarantees, finding codes, and performance evidence are in
the [ADR Grilling feature dossier](feature-adr-grilling/README.md).
