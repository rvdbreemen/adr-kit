# ADR Kit v0.37.0 — ADR Grilling

> Release candidate: publish only after the complete Python 3.10/3.12 matrix
> passes on Windows, Linux, and macOS. The current `dev` candidate still needs
> executable Git modes corrected for the new direct entrypoints.

ADR Kit v0.37.0 turns Proposed ADRs into active decision work. The new ADR
Grilling workflow helps engineers and architects create, reconstruct, complete,
and revalidate decisions through one evidence-backed question at a time—without
weakening deterministic verification or human lifecycle authority.

## Highlights

- **One-question ADR Grilling.** Start with a subject, an incomplete Proposed
  ADR, a pull request, a commit range, a chat log, or a design document. The
  grill separates observed facts, human statements, inferences, and unknowns,
  then asks only the next decision-relevant question.
- **Deterministic readiness.** The new `bin/adr-readiness` CLI and read-only
  `adr_readiness` MCP tool distinguish mechanical defects from questions that
  require an engineer or architect. Output is stable, key-free, and available
  as human-readable text, JSON, or GitHub annotations.
- **Proposed ADRs become a work queue.** Guardian maintains a bounded,
  non-authoritative readiness cache and offers at most three resumable grill
  actions at session start. It never starts an interview in a hook.
- **Safe pull-request automation.** The new `adr-readiness` GitHub Action is
  advisory for suspected undocumented decisions and blocks only when changed
  implementation is explicitly linked to a Proposed ADR.
- **The human remains the decision maker.** Grilling can prepare an acceptance
  packet, but only explicit same-session confirmation followed by `adr accept`
  can transition an ADR. Accepted ADRs cannot retain unresolved open questions.
- **Three native clients, one semantic workflow.** Claude Code, OpenAI Codex,
  and GitHub Copilot CLI now receive the same 15 canonical ADR workflows,
  generated reproducibly from one source model.

## A complete decision flow

Create a Proposed ADR and start the interactive grill:

```bash
python bin/adr new "Choose an event delivery model" --adr-dir docs/adr
```

```text
# Claude Code
/adr-kit:grill ADR-042

# OpenAI Codex
$adr-kit:grill ADR-042

# GitHub Copilot CLI
Open /skills and invoke grill with ADR-042
```

Inspect deterministic readiness at any point:

```bash
python bin/adr-readiness ADR-042
python bin/adr-readiness --all-proposed
python bin/adr-readiness --base origin/dev --head HEAD
```

After all open questions and verification findings are resolved, the engineer
reviews the acceptance packet and explicitly invokes the lifecycle transition:

```bash
python bin/adr accept ADR-042 \
  --changed-by "engineer@example.com" \
  --reason "Reviewed the decision and its trade-offs"
```

## Upgrade and compatibility

- ADR Kit remains dependency-free at runtime and supports Python 3.10 or newer.
- Existing MADR, Nygard, and canonical ADRs remain valid.
- The after-the-fact acceptance default changes from implicit `auto` to
  `assist`. Eligibility is reported first; mutation requires `--confirm` after
  human review.
- Existing automation that intentionally needs the legacy transition can set
  `lifecycle.auto_accept.mode: "auto"` or pass `--auto-mode auto` explicitly.
- Hooks, readiness, MCP, and CI require no model, network service, API key, or
  secret. Optional semantic judgment remains opt-in.
- After updating the plugin, run `/adr-kit:upgrade` to refresh copied project
  guidance and hook artifacts while preserving local edits.

## Pull-request readiness gate

Add the model-free readiness action after a full-history checkout:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- uses: rvdbreemen/adr-kit/.github/actions/adr-readiness@v0.37.0
  with:
    adr-dir: docs/adr
```

The action returns `0` for clean or advisory-only results, `1` for an explicitly
linked implementation of a Proposed ADR, and `2` for infrastructure or
configuration errors.

## Performance and verification

Windows release-baseline certification recorded:

- complete CPython 3.12 suite: 821 passed, 6 skipped;
- complete Python 3.10 suite: 820 passed, 6 skipped;
- strict ADR lint: 11 PASS, no advisories or failures;
- generated Claude, Codex, and Copilot artifacts: zero drift;
- clean client generation: p95 896.896 ms, maximum 925.082 ms;
- warm no-op generation: p95 128.694 ms, maximum 141.799 ms, zero writes;
- readiness core: p95 66.246 ms;
- 500-path implementation linkage: p95 150.444 ms;
- pull-request readiness action: p95 1,150.890 ms.

Every new absolute budget passed and every existing measured path remained
within the 20 percent regression limit. The GitHub release remains gated on a
green cross-platform matrix for the exact release candidate.

## Learn more

- [ADR Grilling user guide](../docs/adr-grilling.md)
- [Architecture decision ADR-011](../docs/adr/ADR-011-adopt-deterministic-readiness-and-human-gated-grilling-across-the-adr-lifecycle.md)
- [Research, design, validation, and benchmark dossier](../docs/feature-adr-grilling/README.md)
