# ADR Kit v0.33.0 multi-perspective source audit

Date: 2026-07-18  
Commit reviewed: `68c13eba384c8302fa46c7981bdf8277f1be0d0e`  
Branch: `main` at `origin/main`  
Backlog: TASK-25

## Executive summary

At the reviewed v0.33.0 commit, the repository had a strong deterministic,
stdlib-first architecture and a substantial test suite. Its four dogfood ADRs
passed strict lint, both generated ADR indexes were current, manifests agreed
on v0.33.0, and the focused core, packaging, MCP, and performance tests were
mostly healthy.

The audit nevertheless found five release-blocking enforcement defects, one
release-blocking Unix packaging defect, and one P1 authoring-template defect
that is now fixed. The most important conclusion is that v0.33.0 must not be
represented as a fail-closed security boundary:

- repository-authored regular expressions can hang the judge indefinitely;
- invalid config types and oversized diffs can silently disable enforcement;
- Git-quoted paths and partial staging can bypass scoped/required rules;
- shipped Claude hook and skill commands are not executable on Unix;
- lifecycle updates are not atomic and do not enforce the advertised state
  machine.

Documentation and template defects that could be corrected without changing
enforcement behavior were fixed as part of TASK-25. TASK-26 subsequently
introduced selectable profiles, fixed newline-stable payload comparison and
the Python 3.10 source floor, added a Windows/Unix compatibility matrix, and
partially hardened supersession preflight. The remaining source behavior
findings should be split into focused implementation tasks.

## Review method

Three independent review perspectives were run in parallel, followed by
cross-file reproduction in the main review:

1. **Core enforcement and lifecycle:** judge, parser, context ranker, guardian,
   watcher, lifecycle CLI, generated validators, MCP boundaries.
2. **Packaging and portability:** Claude/Codex/Copilot manifests, hooks,
   installers, generated payloads, Python floor, release tooling, client
   contracts.
3. **Quality and documentation:** tests, CI, examples, canonical templates,
   public claims, security policy, roadmap, and dogfood artifacts.

The review read ADR-001 through ADR-004 first and separated:

- **Enforcement:** violations of an Accepted ADR or an advertised binding
  contract.
- **Discovery:** architectural decisions or behavior that should be recorded or
  reconciled but is not itself an ADR violation.

No production source behavior was changed during the baseline review to make a
finding disappear. Later TASK-26 remediation is called out explicitly below.

## Prioritised findings

| ID | Priority | Area | Status |
| --- | --- | --- | --- |
| F-01 | P1 | Regex timeout cannot stop catastrophic backtracking | Open |
| F-02 | P1 | Config type coercion silently weakens enforcement or enables LLM use | Open |
| F-03 | P1 | Diffs over 1 MiB skip all enforcement with exit 0 | Open |
| F-04 | P1 | Git-quoted paths bypass scoped rules | Open |
| F-05 | P1 | `require_pattern` reads the working tree, not the staged snapshot | Open |
| F-06 | P1 | Claude hooks and direct skill entry points are not executable on Unix | Automatic path fixed in TASK-29; manual path open |
| F-07 | P1 | Canonical authoring templates were invalid/incomplete | Fixed in TASK-25/TASK-26 |
| F-08 | P2 | Lifecycle transitions and supersession writes are unsafe | Partially fixed in TASK-26 |
| F-09 | P2 | Context results can hide Proposed lifecycle state | Open |
| F-10 | P2 | Generated validators do not preserve Enforcement semantics | Open |
| F-11 | P2 | Advertised Python 3.9 floor was false | Fixed in TASK-25/TASK-26 |
| F-12 | P2 | Generated-payload check is newline-unstable on Windows | Fixed in TASK-26 |
| F-13 | P2 | Native MCP assumes an unversioned `python` command | Fixed in TASK-29 automatic installer |
| F-14 | P2 | Installer validation and failure isolation are incomplete | Mostly fixed in TASK-29 |
| F-15 | P2 | Release helper can leave a partially bumped or incompletely staged tree | Open |
| F-16 | P2 | Guardian/watcher state rewrites are not transactionally isolated | Open |
| F-17 | P2 | Skill invocation metadata contradicted the README safety claim | Docs reconciled |
| F-18 | P2 | Public security, roadmap, install, and release docs were stale | Fixed in TASK-25 |
| F-19 | P3 | CI misses minimum-Python, Windows, example, and full generated-index coverage | Platform matrix fixed in TASK-26/TASK-29; other gaps open |
| F-20 | P3 | Public metadata and dogfood stub had visible version/integration drift | Mostly fixed |

## P1 findings

### F-01: regex timeout cannot stop catastrophic backtracking

Evidence:

- `bin/adr-judge:108-134` runs `re.search` in a daemon thread and calls
  `join(timeout)`.
- The helper is used by declarative forbid and require rules.
- `bin/adr-generate-scripts:84,108` emits direct regex searches with no timeout.
- Reproduction: `(a+)+$` against 30 `a` characters plus `!`, with a nominal
  0.1-second helper timeout, exceeded an outer 5-second process timeout.

CPython's regex engine can hold the global interpreter lock during
backtracking, so the joining thread cannot enforce the deadline. A trusted but
mistaken ADR, or an untrusted repository policy change, can hang commits, CI,
hooks, and MCP calls.

Recommendation: evaluate patterns in a killable subprocess with an input and
wall-clock budget, or constrain the supported regex language. Apply the same
policy to generated validators and add catastrophic-pattern regression tests.

### F-02: config type coercion weakens enforcement or enables paid passes

Evidence:

- `bin/adr-judge:1405-1413` loads JSON without validating it against
  `schemas/adr-kit-config.schema.json`.
- `bin/adr-judge:1597-1610` converts values with Python truthiness and `int()`.
- `bin/adr-suggest:660-662` uses the same truthiness pattern for opt-in state.

Examples:

- `"advisory_only": "false"` is truthy, so violations can exit 0.
- `"max_diff_bytes": -1` skips every non-empty diff.
- `"llm_enabled": "false"` and `"suggest.enabled": "false"` are truthy and can
  enable LLM subprocesses.

Recommendation: validate runtime config before use, reject wrong types with
exit 2, bound numeric values, and use explicit boolean parsing. Test JSON
strings, negative sizes, nulls, and unknown keys.

### F-03: oversized diffs skip all enforcement

Evidence: `bin/adr-judge:1689-1695` prints a skip message and returns success
when the diff exceeds the default 1 MiB cap.

This is a deterministic bypass: a violating change can be padded beyond the
cap. It conflicts with ADR-004's description of the pre-commit judge as the
sole fail-closed floor.

Recommendation: fail closed with a distinct actionable error, or stream/batch
the deterministic pass. An explicit, audited override is safer than a silent
success.

### F-04: Git-quoted paths bypass scoped rules

Evidence:

- `bin/adr-judge:491-522` strips only a literal `b/` prefix.
- A header such as `+++ "b/src/\303\251.py"` remains quoted and escaped.
- The resulting path does not match a normal `src/**/*.py` scope.

Recommendation: parse Git's quoted-path format, or request a machine-readable
diff/name stream with a fixed quoting configuration. Add non-ASCII, whitespace,
tab, quote, rename, and delete fixtures.

### F-05: `require_pattern` uses the working tree instead of the index

Evidence: `bin/adr-judge:680-746` reads `repo_root / path` even when the caller
supplies `git diff --cached`.

With partial staging, an unstaged required token can make a non-compliant
staged commit pass. Conversely, an unstaged removal can block a compliant
staged commit.

Recommendation: reconstruct post-diff content or read the staged blob through
Git. Tests must separate index and working-tree content.

### F-06: Unix entry points are not executable

Evidence:

- `.claude-plugin/plugin.json:36,49,61` directly executes
  `.claude-plugin/hooks/run-hook.cmd`.
- Git records that wrapper as mode `100644`, including tag v0.33.0.
- Several root `bin/adr-*` paths invoked directly by skills are also `100644`.
- CI generally invokes scripts through `python`, so it does not exercise the
  shipped shell execution contract.

On Linux/macOS, a standard Git-based installation can fail with permission
denied before a fail-open hook wrapper runs.

Recommendation: set executable modes for every directly executed entry point,
standardise invocation through an explicit interpreter where appropriate, and
test a packaged plugin on Linux and macOS.

TASK-29 resolves the automatic-install path: it copies the validated release
to a persistent platform-local marketplace, restores executable modes for the
polyglot Claude hook and packaged `bin/` entry points on Unix, and tests that
prepared payload on macOS and Linux CI. A manual Git marketplace install still
depends on executable modes recorded by the release archive; use the automatic
installer when portability must be guaranteed.

Reference: [Claude Code hooks](https://code.claude.com/docs/en/hooks).

### F-07: canonical authoring templates were invalid and incomplete

Before TASK-25:

- `templates/adr-template.md` encoded regexes with single JSON backslashes:
  `\s` was invalid JSON and `\b` became a backspace character.
- The canonical template and the templates embedded in the ADR skill and
  generator omitted mandatory v0.32 frontmatter.
- The authoring flow then instructed users to run strict lint, which failed with
  `missing canonical frontmatter`.
- Template text incorrectly described the opt-in LLM violation as advisory.

Resolution in TASK-25:

- replaced the invalid Enforcement example with a JSON-valid block;
- added canonical frontmatter to all authoring surfaces;
- aligned the initial lifecycle state and Status History;
- corrected LLM behavior text;
- added regression tests that parse the example and run the filled template
  through the strict schema gate.

TASK-26 replaced the single authoring template with deterministic MADR,
Nygard, and backward-compatible canonical templates behind one semantic
registry. The default template is now MADR, and all three client payloads carry
the same JSON-valid invariant metadata and Enforcement shape.

## P2 findings

### F-08: lifecycle transitions and supersession writes are unsafe

Evidence:

- `bin/adr:268-323` permits generic status transitions without a state machine
  or the advertised four acceptance gates.
- `supersede` overwrites an existing `superseded_by` value.
- The old ADR is written before the successor is fully loaded and written, so a
  later failure can leave a one-way chain.
- Native Codex/Copilot supersede instructions used a positional successor while
  argparse requires `--by`.

Recommendation: preflight both ADRs, reject illegal/conflicting transitions,
write both through a transaction/rollback strategy, and make `accept` use one
gate-aware path. TASK-25 corrected the documented CLI syntax and removed the
false conflict-guard claim.

TASK-26 now preloads and validates both records, rejects a successor that
already claims another target, rejects an existing conflicting
`superseded_by`, and writes the successor before the predecessor. Legal
transition enforcement and a transactional two-file rollback remain open.

### F-09: context results can hide Proposed status

Evidence:

- `bin/adr-context:300-307,356-367` gives Accepted ADRs a scoring boost but
  leaves Proposed ADRs eligible.
- Results do not include lifecycle status.
- `tests/test_adr_context.py:204-217` explicitly expects Accepted and Proposed
  records.

This differs from ADR-004 and the prior README claim that only Accepted ADRs are
returned as binding context.

Recommendation: either filter to Accepted by default with an explicit
`--include-proposed`, or return status and make clients render it prominently.
TASK-25 corrected the public description to match current behavior.

### F-10: generated validators are only a semantic subset

Evidence:

- `bin/adr-generate-scripts:62-75` drops `path_glob`.
- It omits `require_pattern`.
- Shell preflight treats `grep` exit 1 ("valid pattern, no match") as an invalid
  regular expression.
- Generated Python validators have the F-01 regex exposure without a timeout.

Recommendation: define the supported subset explicitly in output metadata, or
compile every Enforcement rule with parity tests against `adr-judge`. TASK-25
removed the README claim that generated validators compile complete
Enforcement semantics.

### F-11: Python 3.9 support was not real

Evidence:

- `bin/adr-generate-scripts:245` and `bin/bump-version:81,173,187,208,222` pass
  `newline=` to `Path.write_text`.
- Python 3.9's `Path.write_text` has no `newline` parameter; Python 3.10 added
  it.
- CI tests only Python 3.11.

TASK-25 changed the documented and bootstrap floor to Python 3.10 and updated
the related test/error text. TASK-26 removed the Python 3.10-incompatible
`Path.write_text(newline=...)` calls, added a Python 3.10 grammar guard, and
added Python 3.10/3.12 jobs on Windows and Ubuntu.

References: [Python 3.9 pathlib](https://docs.python.org/3.9/library/pathlib.html),
[Python 3.10 pathlib](https://docs.python.org/3.10/library/pathlib.html).

### F-12: payload sync is newline-unstable on Windows

Evidence:

- `scripts/sync-agent-plugins.py:55-64,92-123` mixes text-normalised expected
  content with raw byte comparisons.
- The repository has no `.gitattributes`.
- On this `core.autocrlf=true` checkout,
  `python scripts/sync-agent-plugins.py --check` reports five drift groups.
- Git-index blob comparison showed the generated payload was semantically
  current.
- The only deterministic baseline suite failure was
  `tests/test_agent_installer.py:168-176`.

Recommendation: define LF in `.gitattributes` for generated/script surfaces or
normalise both sides consistently. Add Windows CI.

Resolved in TASK-26: the payload synchronizer normalizes CRLF and LF on both
sides before comparison, a regression test covers both newline forms, and the
Windows/Ubuntu compatibility matrix runs the payload gate.

### F-13: native MCP assumes the command is named `python`

Evidence: `codex/.mcp.json`, `copilot/.mcp.json`, and native skill instructions
hard-code `python`. Unix installations may expose Python 3 only as `python3`.
Registration/list validation does not start the MCP server.

Recommendation: generate or configure the interpreter command during install,
and make validation perform a real MCP initialize/tool call. TASK-25 documents
the current requirement and workaround.

Resolved in TASK-29: the automatic installer probes the interpreter that
launched it, requires Python 3.10+, writes its resolved absolute path into
prepared Codex and Copilot MCP manifests, and completes MCP initialize plus
tools/list before changing client registration. Unix hosts no longer require a
command named `python` or a manual installed-manifest edit.

### F-14: installer validation and failure isolation are incomplete

Evidence:

- `scripts/install-agent-envs.py:116-124` ignores Claude install scope and can
  update the wrong scope.
- `detect_clients()` lets timeout and OS errors from one candidate abort
  detection of every other client.
- Source structure is validated after some external marketplace mutations.
- Post-install validation relies primarily on list output.

Recommendation: validate source manifests first, isolate detection per client,
model install scope explicitly, and add rollback/action summaries plus a real
plugin/MCP smoke test.

TASK-29 validates all required JSON and release versions before client
mutation, bounds and isolates version detection, targets Claude's user scope,
continues after per-client install failures, and performs a real packaged MCP
smoke test. Client-native marketplace mutations remain non-transactional; the
installer reports the failed client and preserves successful installations so
the user can rerun only the normal command for that client.

### F-15: release helper can leave a partial tree

Evidence:

- `bin/bump-version:111-153` writes manifests before validating later
  marketplace entries.
- A missing `Unreleased` heading can be treated as success after manifest
  writes.
- Its final staging hint omits files it changed, including the guide,
  pre-commit wrapper, and one marketplace.
- Prior CONTRIBUTING steps repeated changelog work already performed by the
  helper and omitted payload regeneration.

Recommendation: preflight everything, compute changes in memory, then apply
atomically. Test rollback and the complete changed-file set. TASK-25 rewrote
the contributor release sequence around current behavior.

### F-16: shared state writes are not transactionally isolated

`adr-watch` and guardian flows load and rewrite shared
`docs/adr/.adr-kit-state.json` state with fixed temporary paths and incomplete
cross-process locking. Concurrent hooks/sessions can lose cooldown, trend, or
health updates.

Recommendation: lock the full read-modify-write cycle and use unique temporary
files plus atomic replacement.

### F-17: skill invocation metadata contradicted the README

The README said `judge`, `review`, and `guardian` were not auto-invocable, but
their skill frontmatter omits `disable-model-invocation: true`.

TASK-25 made the command table reflect shipped metadata and clarified that
model invocation is separate from mutation authority. A later product decision
should either add the metadata or explicitly accept auto-invocation.

### F-18: public documentation was materially stale

Corrected in TASK-25:

- Python floor, release pins, CLI/test counts, valid MCP JSON, canonical
  filename/configuration scope, current context and validator semantics;
- INSTALL validation limits, Python alias requirement, and known portability
  limitations;
- contributor release and validation sequence;
- SECURITY scope and supported release;
- ROADMAP shipped/planned split and v1.0 readiness criteria;
- canonical project-guide workflow table and JSON examples;
- stale dogfood `CLAUDE.md` session/edit-tier references;
- bug-report version example.

## P3 findings

### F-19: CI does not cover advertised portability and examples

Current CI is centred on Ubuntu/Python 3.11. It does not cover the minimum
Python floor, Windows newline behavior, Unix packaged direct execution, native
MCP startup, or every public JSON/template example. The ADR index workflow
checks the compact index but not every generated document surface.

Recommendation: add Python 3.10 and Windows jobs, a packaged Unix execution
smoke test, native MCP initialize/tool calls, documentation contract tests, and
both generated-index checks.

TASK-26 added Python 3.10/3.12 jobs on Windows and Ubuntu plus profile,
installer, newline, and documentation contract tests. Packaged Unix direct
execution, native MCP startup, and complete packaging-contract coverage remain
open.

TASK-29 extends the matrix to macOS, exercises prepared Unix executable modes,
and completes a real packaged MCP initialize/tools-list handshake. Manual Git
marketplace executable modes and complete generated-document coverage remain
open.

### F-20: public metadata and dogfood integration drift

The review found stale release pins/counts, a v0.6 issue-template example,
outdated changelog compare links, and a tracked `CLAUDE.md` stub missing the
decision index and edit-tier instruction. TASK-25 corrected all except the
historical changelog link-definition set, which should be regenerated as a
separate mechanical cleanup.

The Codex `.mcp.json` also uses a legacy camel-case wrapper. Codex 0.144.6 still
loads it, so this is a future-compatibility note rather than a current outage.

## ADR enforcement and discovery result

### Enforcement

No branch diff existed relative to `origin/main`, so there was no feature diff
to judge. The repository itself conforms to the four Accepted dogfood ADRs at
the documentation/architecture level:

- local and deterministic default paths;
- no default model spend;
- guardian/injection paths intended to fail open;
- one shared semantic contract across selectable MADR, Nygard, and canonical
  ADR body profiles (superseding the baseline canonical-only decision).

F-02 and F-03 weaken ADR-001/ADR-004's runtime guarantees and should be treated
as implementation defects against those decisions.

### Discovery

`adr-audit` identified GitHub Actions/CI policy as a decision candidate. The
repository contains a substantial CI architecture but no dedicated ADR for its
platform, portability matrix, trust boundary, or required gates. Before
expanding CI, consider a Proposed ADR that records:

- GitHub Actions as the hosted CI platform;
- required operating-system and minimum-Python coverage;
- which checks are merge-blocking;
- how generated client payloads and native install smoke tests are proven.

No ADR draft was created automatically.

## Verification evidence

Baseline and independent review runs:

- strict ADR lint: four ADRs passed with zero advisories;
- `adr-doctor`: clean;
- compact and README ADR indexes: current;
- core focused suite: 196 passed, 2 skipped;
- packaging focused suite: 61 passed, 1 skipped, 1 failed (F-12 only);
- full suite under concurrent review load: 522 passed, 3 skipped, 2 failed
  (F-12 plus one performance threshold);
- repeated/isolated performance runs: passed;
- later full quality run: 523 passed, 3 skipped, 1 failed (F-12 only);
- 527 tests collected before TASK-25 added documentation regressions.

Final post-TASK-26 verification:

- 558 tests collected;
- full suite: 555 passed, 3 skipped;
- focused selectable-format, client, compatibility, and documentation suite:
  42 passed;
- strict ADR lint: all five ADRs passed with zero advisories;
- doctor: index and lint healthy, zero findings;
- compact and README ADR indexes: current;
- generated Claude/Codex/Copilot payload check: synchronized;
- markdownlint: 62 applicable documentation files, zero issues;
- `git diff --check`: no whitespace errors (checkout EOL warnings only).

Post-TASK-29 cross-platform installer verification:

- full suite: 585 passed, 3 skipped;
- focused installer, MCP, compatibility, and documentation suite:
  70 passed, 1 skipped;
- Windows detected-client and three-client dry-run completed without writes;
- prepared payload completed a real MCP initialize/tools-list handshake;
- strict ADR lint: all six ADRs passed with zero advisories;
- generated payload and both ADR index checks: current;
- markdownlint: 61 changed/applicable documentation files, zero issues;
- GitHub Actions compatibility matrix configured for Python 3.10/3.12 on
  Windows, macOS, and Ubuntu; hosted results follow when the branch is pushed.

These results are a point-in-time handoff, not a permanent green baseline.

## Recommended implementation order

1. F-02 and F-03: remove deterministic enforcement bypasses.
2. F-01: make regex evaluation killable and bounded.
3. F-04 and F-05: make diff/path/index semantics exact.
4. F-06 and F-13: restore cross-platform plugin execution.
5. F-08: make lifecycle changes legal, conflict-safe, and atomic.
6. F-12 and F-19: build the portability matrix that prevents recurrence.
7. F-09, F-10, F-14, F-15, and F-16: align secondary workflows and tooling.
