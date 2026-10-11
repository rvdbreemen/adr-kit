---
id: "ADR-048"
title: "Certify each native client on every platform it runs on"
status: "Accepted"
date: "2026-10-11"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
related:
  - "ADR-010"
  - "ADR-039"
  - "ADR-044"
topics:
  - "native certification"
  - "release evidence"
  - "platform support"
  - "client versions"
aliases:
  - "windows-native.json"
  - "linux-native.json"
  - "Windows native release baseline"
  - "release_eligible"
components:
  - "scripts/client_certification.py"
  - "scripts/client_evidence.py"
  - "scripts/client_support_matrix.py"
  - "tests/certification"
symbols:
  - "validate"
  - "assemble_native_bundle"
  - "NATIVE_EVIDENCE_PATHS"
  - "CERTIFICATION_MAX_AGE_DAYS"
context_scope: "selective"
format: "madr"
---

<!-- markdownlint-disable MD025 -->

# ADR-048 Certify each native client on every platform it runs on

## Status

Accepted, 2026-10-11.

## Status History

```yaml
status_history:
  - date: 2026-10-11
    status: Proposed
    changed_by: "User: Claude"
    reason: Initial proposal
    changed_via: adr-kit
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Accepted decision after all four verification gates passed
    changed_via: adr-kit lifecycle
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: "ADR-048 amends ADR-010: every platform is certifiable from a real run on it, certification stays optional per release, and claims follow the evidence"
    changed_via: adr-kit lifecycle
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-039
    changed_via: adr-kit lifecycle
  - date: 2026-10-11
    status: Accepted
    changed_by: "User: Robert van den Breemen"
    reason: Related to ADR-044
    changed_via: adr-kit lifecycle
```

## Context and Problem Statement

ADR-010 made Windows the native release baseline for the three certified
clients. It required independent Windows records for Claude Code, Codex and
Copilot, recorded macOS and Linux as best-effort, and let a failing Windows
record block every stable release. The 2026-10-11 review of the evidence found
that this no longer describes what users run, or what the kit knows about it:

* **The evidence is from 0.36.0.** `tests/certification/<client>/windows-native.json`
  dates from 2026-07-19 and covers ADR Kit 0.36.0 with Claude Code 2.1.215,
  Codex 0.144.6 and Copilot 1.0.71. All three were captured on a dirty tree and
  carry `release_eligible: false`.
* **The gate is not run.** Releases 0.37.0 to 0.59.1 shipped without a new
  record. `docs/RELEASING.md` step 5 calls native certification optional, and CI
  validates only a simulated bundle, with `--max-age-days 36500` so it never
  goes stale (`.github/workflows/validate.yml:154`).
* **Only Windows can be certified.** The validator refuses any `os` but
  `windows` (`scripts/client_certification.py:69`) and requires a passing
  Windows record (`:93`). The assembler reads only `<client>/windows-native.json`
  (`scripts/client_evidence.py:20-24`) and stamps `"os": "windows"` on every
  record (`:194`).
* **macOS and Linux were never run** ("no runner available"). Those are the
  platforms where a bare `python` stops the MCP server (DEF-25), so the
  certification never looked where that defect is.
* **The versions are pinned outside the evidence.** `tests/test_native_client_packages.py:51-53`
  and `docs/clients/{claude,codex,copilot}.md` state the 0.36.0-era client
  versions as facts.
* **Part of the contract needs a logged-in client.** The event probe costs one
  model call per client (`scripts/probe-client-events.py`), and workflow
  invocation runs a session. ADR-010 already allows authenticated,
  maintainer-run smoke under the same evidence binding.

How should native certification work, so that it states which clients work on
which platforms at current versions, and says nothing it has not measured?

## Decision Drivers

* A support claim follows the evidence: no platform, client or version is
  claimed without a passing, current, commit-bound native record.
* Users run all three platforms; the evidence should be able to say so.
* `not-run` is an honest evidence class (the probe's own rule); an outcome that
  could not be measured is never recorded as passing.
* One maintainer must be able to produce the evidence without a dedicated
  Windows machine for every release.
* ADR-010's evidence binding stays: candidate commit, payload hash, client
  version, contract date, environment, outcomes, latency, lifecycle,
  preservation and retained redacted logs.

## Considered Options

* Certify each client on every platform it runs on, from a real run on that
  platform.
* Keep Windows as the only certifiable baseline, and refresh it on Windows.
* Drop native certification and rely on the simulated fixture and the doctor.
* Do nothing.

## Decision Outcome

Chosen option: **certify each client on every platform it runs on, from a real
run on that platform**, because a claim can only be as wide as the evidence
behind it, and the platforms users run are the ones the evidence has missed.

1. **A record certifies the platform it ran on.** Windows, macOS and Linux are
   each certifiable. A native observation lives at
   `tests/certification/<client>/<os>-native.json`. Its schema is unchanged
   apart from naming its `os`. A record never speaks for another platform.
2. **Certified means complete, native, bound and fresh.** A client is certified
   on a platform when its record for that platform passes every required
   outcome natively, binds to the candidate commit and payload hash, and is at
   most 30 days old (`CERTIFICATION_MAX_AGE_DAYS`, unchanged).
3. **Claims follow the evidence.** The support matrix, the README and
   `docs/clients/*.md` claim certification per client and platform, only where
   such a record exists. Elsewhere they state the record's actual state:
   incomplete, failing, or not run, with the reason.
4. **Versions come from the evidence.** The client version a document or test
   names is read from the record that measured it. No other file pins it.
5. **Incomplete records are kept, and certify nothing.** A record whose
   model-dependent outcomes could not be run is committed with
   `release_eligible: false`. Every outcome that was not measured reads
   `not-run`, with its reason, and the support matrix shows the record as
   incomplete (Open Question 2).
6. **Certification stays optional for a release.** A release may ship without a
   new run, and it then claims only what its records show. ADR-010's rule that a
   failing Windows record blocks every stable release no longer applies; it had
   not been run since 0.36.0 (Open Question 1).
7. **OpenCode stays outside** the certified set, as ADR-039 decided.

**Proposed by:** Claude (agent) at the request of User: Robert van den Breemen,
on 2026-10-11, after the maintainer chose that every platform counts, that
model-free outcomes are recorded now and the rest in a session with
credentials, and that the newest stable client versions are certified.
**Decision Maker:** User: Robert van den Breemen settled both open questions on
2026-10-11, taking the recommended option each time.

### Confirmation

* Validator and assembler tests accept a passing record on each of the three
  platforms, refuse a record that names another platform than its file, and
  refuse a stale, unbound or incomplete record as certified.
* A test fails when a document or test names a client version that is not the
  one recorded in the evidence.
* `tests/certification/<client>/linux-native.json` exists for the three
  clients, at the newest stable versions, with every model-free outcome
  measured and every model-dependent outcome `not-run` with its reason.

## Decision Contract

### Must

* Certify a client only on a platform where a native record for that platform
  passes every required outcome, binds to the candidate, and is at most 30 days
  old.
* State, for every client and platform, either the certification or the
  record's actual state with its reason.
* Read every stated client version from the evidence.

### Must Not

* Record an outcome as passing that was not measured on that platform.
* Let a record for one platform certify another, or let an incomplete record
  certify anything.
* Pin a client version in a test or document outside the evidence.
* Claim certification in a release for a client and platform without a record
  that is fresh at that release's commit.

### Exceptions

* The simulated fixture (`tests/certification/simulated-pass.json`) stays a
  generator test input. It never certifies a client.

### Verification

* `tests/test_client_certification.py` and `tests/test_native_client_packages.py`,
  extended with the implementation.

## Consequences

### Positive

* The support claim says which platforms work at which versions, measured.
* Linux and macOS, where DEF-25 bites, become visible in the evidence.
* A release no longer needs a Windows machine to refresh its evidence.

### Negative

* More records to keep fresh: three clients times three platforms. Mitigation:
  an incomplete or stale record is shown as such rather than blocking.
* Complete records still need logged-in clients. Mitigation: ADR-010's
  maintainer-run authenticated smoke stays allowed, and a session with
  credentials completes the model-dependent outcomes.

## Pros and Cons of the Options

### Certify every platform it runs on

* Good, because the claim matches what was measured, on the platforms users run.
* Bad, because the evidence grows from three records to as many as nine.

### Keep the Windows baseline

* Good, because nothing in the tooling changes.
* Bad, because macOS and Linux stay unmeasured, and every refresh needs Windows.

### Rely on the simulated fixture and the doctor

* Good, because it costs nothing per release.
* Bad, because a fixture states what we believe, not what a client does; every
  hook defect the kit shipped passed it (`probe-client-events.py`).

### Do nothing

* Good, because nothing changes.
* Bad, because the documents keep claiming a 0.36.0 certification for 0.59.

## Open Questions

- [x] Release gate: does certification stay optional for a release, with the release claiming only what its records show (recommended), or does every stable release need at least one certified platform per client, or does Windows stay required? — **Answered 2026-10-11 by User: Robert van den Breemen:** Optional, and claims follow the evidence. A release may ship without a new run, but the README, docs and support matrix claim 'certified' only per client and platform with a record at most 30 days old at that release's commit; everywhere else they state the record's actual state. This replaces ADR-010's rule that a failing Windows record blocks every stable release, which has not been run since 0.36.0.
- [x] Incomplete records: are records with model-dependent outcomes not-run committed as `release_eligible: false` evidence (recommended), or kept out of the repository until complete? — **Answered 2026-10-11 by User: Robert van den Breemen:** Commit them as release_eligible: false evidence. The record sits at tests/certification/<client>/<os>-native.json, every outcome that was not measured is not-run with its reason, and the support matrix shows 'incomplete'. Measured evidence is kept, following the probe's rule that not-run is an honest evidence class; such a record certifies nothing.

## Related Decisions

* Amends ADR-010 (Certify three native CLI clients through one outcome
  contract): replaces "Windows is the native release baseline" and the
  Windows-only release gate; the outcome contract and the evidence binding stay.
* ADR-039 (Add a native OpenCode plugin without expanding the certified CLI
  gate): OpenCode stays outside the certified set.
* ADR-044 (Resolve the interpreter and the engine through one resolver): DEF-25,
  the defect the Windows-only evidence could not see.

## References

* `scripts/client_certification.py:69`, `:93`; `scripts/client_evidence.py:20-24`, `:194`.
* `tests/certification/{claude,codex,copilot}/windows-native.json`.
* `tests/test_native_client_packages.py:51-53`; `docs/clients/*.md`.
* `docs/RELEASING.md` step 5; `.github/workflows/validate.yml:154`.
* `scripts/probe-client-events.py`.
