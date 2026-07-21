---
name: retire
description: "Rank Accepted ADRs for retirement. Use for stale decisions, removed technology, supersession signals, or ADR cleanup. Read-only."
argument-hint: "[ADR directory; defaults to docs/adr/]"
disable-model-invocation: true
allowed-tools: [Read, Bash]
---

# adr-kit retire

Use `$ARGUMENTS` as the ADR directory; default to `docs/adr/` when it is empty.

You are running `/adr-kit:retire`. This is a read-only audit of Accepted ADRs
that may no longer describe the project accurately.

## Procedure

1. Resolve the ADR target from the optional argument; default to `docs/adr/`.
2. Run the bundled deterministic scanner from the project root:

   ```bash
   python <adr-kit-plugin-path>/bin/adr-retire <target> \
     --repo-root . --threshold 0.4 --format markdown
   ```

3. Present every returned candidate with its four signal scores:
   `staleness_90day`, `tech_removal`, `broken_supersession`, and
   `policy_mismatch`.
4. For any `REVIEW` or `RETIRE` result, ask the user whether the decision is
   actually obsolete, then offer `/adr-kit:grill --revalidate ADR-NNN`.
   Revalidate changed forces, remaining implementation, new evidence, and
   human intent before choosing unchanged, successor, reject-candidate, or
   defer. Keep this audit read-only until the user confirms a separate
   lifecycle command.

## Boundaries

- Do not modify ADR statuses or status histories during this audit.
- Treat `MONITOR` as an observation, not as proof that an ADR is obsolete.
- A retirement recommendation is evidence for review, not permission to
  remove an Accepted decision silently.
