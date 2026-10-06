# adr-kit Components

Seven components. The eighteen `c4-code-*.md` cluster documents this level was
synthesized from were retired on 2026-08-09 (KISS simplification plan): they
were hand-written, no generator or CI kept them honest, and the module
docstrings carry the code-level detail. A `c4-code-*.md` name below is a
historical provenance reference, not a live link. This file adds the
cross-component structure that no single component document can see. It is one
of four C4 levels — see [Document map](#document-map) at the end of this file
for how to navigate from here to the code, container and context levels.

## System Components

| Component | Short description | Document |
| --- | --- | --- |
| **Decision Record Engine** (`decision-engine`) | The semantic core: what an ADR *means*. Three body profiles mapped onto stable semantic roles, the frontmatter dialect, the directory-to-graph projection, and the retrieval query engine — plus the two mutators of ADR *identity* (profile migration, renumbering) and `adr_llm_judge_migration.py`, the deterministic Enforcement-block rewrite `bin/adr-migrate` loads for the upgrade skill. 8 files, 4,017 lines, stdlib-only, **zero outbound repository dependencies**. | [c4-component-decision-engine.md](./c4-component-decision-engine.md) |
| **Enforcement and Verification Engine** (`enforcement-engine`) | The only part of adr-kit that **blocks**. Judges a staged diff against every Accepted ADR's fenced JSON `## Enforcement` block, scores and gates ADR quality, and owns the killable-subprocess regex sandbox that makes repository-authored policy safe to execute. The LLM pass judges one ADR at a time in isolation and runs on the host model only (ADR-036): `bin/adr_llm.py` resolves a host-CLI subprocess (`claude -p`, `codex exec`, `copilot -p`) where a host client is recorded, `judge.llm_pass_timeout_seconds` (default 600) caps the whole pass, and every failure degrades to declarative-only. `adr-judge --check-scope` names each Enforcement rule of an Accepted ADR and whether its scope resolves. 5 CLIs plus 6 importable runtime/backend modules, 11 files, 7,709 lines. | [c4-component-enforcement-engine.md](./c4-component-enforcement-engine.md) |
| **Selective Context Retrieval** (`retrieval-and-injection`) | Makes recorded decisions *findable* at the moment an agent needs them. One generator (`adr-index` over its importable core `adr_index_core.py`, the sole writer of every derived index view; the hook runtime and the guardian call that core by import) plus four readers covering ADR-004's session, task and edit tiers. Retrieval is lexical over the generated index plus one-hop graph neighbours. 5 CLIs plus 1 module, 3,104 lines, fail-open by construction — every path exits 0. | [c4-component-retrieval-and-injection.md](./c4-component-retrieval-and-injection.md) |
| **Health, Guardian and Lifecycle** (`health-and-lifecycle`) | The time dimension of an ADR set: the only sanctioned status writer (`bin/adr`, transactional with snapshot rollback, now requiring `--confirm` and a person-named signer on acceptance per ADR-027), the SessionStart staleness detector, the health ledger, retirement scoring (`adr-retire` scans `git ls-files --cached --others --exclude-standard` inside a git repository), seven-class readiness with a CI merge gate, `adr-substance` (the guardian's LLM-tier check that each written section of a Proposed ADR says something, on ADR-002's cadence, never per commit), `adr-settings`, and the local `adr-doctor` check/repair/probe engine. 19 files, 8,145 lines. | [c4-component-health-and-lifecycle.md](./c4-component-health-and-lifecycle.md) |
| **Agent and Client Integration** (`agent-integration`) | Every path by which an LLM agent or CLI client reaches the engine, deliberately kept separate: a hand-rolled MCP stdio server (7 read-only deterministic tools, key-free; ADR-040 admits only such tools), a Python lifecycle-hook runtime that pushes context unasked and hands an unfinished Proposed ADR to interactive grilling at the next user-visible prompt (ADR-041, `grill.auto_start`), an instruction corpus of skills/prompts/one subagent, a capability registry plus desired-state installer for the three certified clients, and the separate native OpenCode plugin. Owns no ADR semantics — every path terminates in a shared `bin/` CLI. Since ADR-023/024, one of its hooks (`hooks/adr_pr_guard.py`) is also a second, direct caller into the enforcement floor at the `gh pr create` moment. | [c4-component-agent-integration.md](./c4-component-agent-integration.md) |
| **Contracts, Packaging and Distribution** (`contracts-and-distribution`) | The declarative contract layer and the release toolchain that acts on it: 11 JSON Schemas, 14 files under `templates/`, 8 `packaging/*.json` registries, 27 `scripts/*.py` modules (among them the release driver `scripts/release.py` with `release_phases.py`, `release_shell.py` and `release_npm.py`, which runs the release from the maintainer's machine and lets `release-publish.yml` create the tag from the merged commit, ADR-042), 13 workflows (including `install-smoke.yml`) plus 3 composite actions, the two generated certified client payloads (`codex/`, `copilot/` — 114 tracked files each), and the root OpenCode package source. | [c4-component-contracts-and-distribution.md](./c4-component-contracts-and-distribution.md) |
| **Quality Assurance** (`quality-assurance`) | The single pytest suite plus its fixture, corpus and certification-evidence families — 107 `test_*.py` modules, 1,410 `def test_` functions, 36,763 lines, larger than `bin/` itself (25,525 lines). Dominated by black-box subprocess tests over the extensionless CLIs, and the only mechanical guard on several ADR gates. | [c4-component-quality-assurance.md](./c4-component-quality-assurance.md) |

**Not covered by any of the seven:** `bin/adr-discover` (546 lines, the
renamed missing-ADR scanner, with its git-history helper `bin/adr_history_scan.py`)
and `bin/adr-audit` (493 lines, the combined
`adr-lint` + `adr-judge` command ADR-026 records). See
[Coverage gap](#coverage-gap-binadr-discover-and-binadr-audit).

## Component Relationships Diagram

```mermaid
flowchart TB
    subgraph ext["External systems"]
        GIT(["git CLI"])
        BACKEND(["host model CLI:<br/>claude -p / codex exec /<br/>copilot -p<br/>(ADR-036)"])
        GHA(["GitHub Actions + gh"])
        PCF(["pre-commit.com"])
        HOSTS(["Claude Code / Codex / Copilot<br/>OpenCode hosts"])
        AJV(["Node20 + ajv-cli"])
        PYPI(["PyPI — pytest"])
    end

    DE["decision-engine<br/>LEAF: no outbound repo dep"]

    subgraph EEG["enforcement-engine"]
        JUDGE["adr-judge · adr-lint · adr-quality<br/>only fail-closed mechanism"]
        RT["adr_config · adr_state · adr_regex<br/>shared primitives"]
    end

    RI["retrieval-and-injection<br/>adr_index_core sole writer · fail-open"]
    HL["health-and-lifecycle<br/>only ADR status writer"]
    AI["agent-integration<br/>MCP (7 tools) · hooks · skills · installer"]

    subgraph CDG["contracts-and-distribution"]
        CONTRACTS["schemas/ · templates/<br/>read DOWNWARD"]
        RELEASE["packaging/ · scripts/ incl. release.py<br/>workflows/ · codex/ · copilot/"]
    end

    QA["quality-assurance<br/>tests/ — 1,410 test functions"]
    DISCOVER["bin/adr-discover<br/>missing-ADR scanner<br/>renamed via ADR-026 · NO component"]
    AUDIT["bin/adr-audit<br/>combined lint+judge · ADR-026<br/>5-way exit · NO component"]

    MD[("ADR-NNN-*.md<br/>3 writers")]
    IDX[("ADR-INDEX.json<br/>3 readers, 3 strictnesses")]

    JUDGE -->|import| DE
    RI -->|import| DE
    HL -->|import| DE
    AI -->|import| DE
    QA -->|import| DE
    DISCOVER -->|import| DE

    RI -->|import| RT
    HL -->|import| RT

    HL -->|subprocess| JUDGE
    AI -->|MCP tool call| JUDGE
    AI -->|"subprocess, ADR-023 PR guard<br/>deny on violation"| JUDGE
    RELEASE -->|subprocess| JUDGE
    QA -->|subprocess| JUDGE
    PCF -->|git hook| JUDGE
    CONTRACTS -->|git hook| JUDGE
    AUDIT -->|"subprocess (ADR-026):<br/>adr-lint + adr-judge"| JUDGE

    HL -->|subprocess| RI
    AI -->|MCP tool call| RI
    AI -.->|"subprocess, ADR-024<br/>advisory nudge, never blocks"| RI
    RELEASE -->|subprocess| RI
    GHA -->|subprocess| RI
    QA -->|subprocess| RI

    AI -->|"import, ADR-021<br/>index refresh"| RI
    HL -->|"import, guardian<br/>index freshness"| RI

    RI -->|import| HL
    AI -->|MCP tool call| HL
    QA -->|subprocess| HL
    HOSTS -->|subprocess| HL
    HL -->|"subprocess, material drift"| DISCOVER

    HL -->|import| AI
    HL -->|MCP tool call| AI
    RELEASE -->|reads JSON| AI
    QA -->|subprocess| AI
    HOSTS -->|MCP tool call| AI

    HL -->|import| RELEASE
    AI -->|copies bytes| RELEASE
    QA -->|import| RELEASE
    GHA -->|subprocess| RELEASE
    RELEASE -->|copies bytes| DE
    RELEASE -->|copies bytes| EEG
    RELEASE -->|copies bytes| RI
    RELEASE -->|copies bytes| HL
    RELEASE -->|copies bytes| AI

    AI -->|reads JSON| CONTRACTS
    JUDGE -->|reads JSON| CONTRACTS
    RI -->|reads JSON| CONTRACTS
    HL -->|reads JSON| CONTRACTS

    RELEASE -->|subprocess| QA
    RELEASE -->|"writes<br/>in-repo only"| QA
    AI -->|reads JSON| QA

    DE -->|reads + writes| MD
    HL -->|writes| MD
    JUDGE -->|writes| MD
    RI -->|writes| IDX
    RI -->|reads JSON| IDX
    HL -->|reads JSON| IDX
    AI -->|reads JSON| IDX

    RI -->|"subprocess<br/>adr-suggest, advisory"| BACKEND
    JUDGE -->|"subprocess<br/>one isolated call per ADR"| BACKEND
    HL -->|"subprocess<br/>adr-substance, guardian LLM tier"| BACKEND
    JUDGE -->|subprocess| GIT
    HL -->|subprocess| GIT
    RELEASE -->|subprocess| GIT
    AI -->|subprocess| HOSTS
    RELEASE -->|subprocess| AJV
    QA -->|import| PYPI
```

**Label vocabulary** — every edge carries exactly one:

| Label | Mechanism |
| --- | --- |
| `import` | Python import by bare name, after a `sys.path` change or an explicit-path `_load_sibling` load (there is no package) |
| `subprocess` | Process spawn — `sys.executable`, a `bin/` CLI, or an external binary; LLM passes reach the host model CLI only this way, selected by `judge.host_client` or `ADR_KIT_LLM_CMD`, and degrade to declarative-only on failure (ADR-036) |
| `MCP tool call` | JSON-RPC 2.0 over stdio to `bin/adr-mcp`, which then subprocesses onward |
| `git hook` | Invoked by the installed pre-commit wrapper or the pre-commit.com framework |
| `reads JSON` / `reads + writes` | File read (or read-modify-write) on disk — JSON, or Markdown for the ADR bodies |
| `writes` | File write on disk — durable via `os.fsync` + `os.replace` throughout |
| `copies bytes` | Verbatim file copy by `scripts/build-client-adapters.py`, drift-checked with `--check` |

Three conventions matter for reading the arrows.

**Data-flow direction on artefact edges.** `reads`/`writes` edges point the way the bytes
travel, so the dependency between a generator and its consumer runs *through* the artefact
node, not directly between components. `adr-index` writes `ADR-INDEX.json`; the hook
runtime reads it. The one call between them is the ADR-021 refresh: on a stale index at a
refreshing event, `hooks/adr_hook_core.py` imports `regenerate_index` from
`adr_index_core` under an `O_EXCL` lock, so the generator stays the only writer. Only the two artefacts that carry a
cross-component hazard are drawn — `ADR-NNN-*.md` (three writers, one of them
transactional) and `ADR-INDEX.json` (three readers at three strictness levels). Three more
shared files exist and are one-per-component-pair rather than structural:
`.adr-kit-state.json` (written by `adr-watch` and `adr-guardian`),
`.adr-kit-readiness.json` (written by `adr-guardian refresh-readiness`, read by the hook
runtime) and `.adr-kit.json` (read independently by the judge, retrieval and health).

**Sub-component targets inside `enforcement-engine`.** The arrows from
`retrieval-and-injection` and `health-and-lifecycle` land on the shared runtime primitives
node, not the judge. Drawn at component granularity they would suggest the fail-open tiers
depend on the fail-closed floor, which is the inverse of what the code does.

**The `agent-integration → quality-assurance` edge is not a test edge.** It is
`hooks/hook_benchmark.py` reading `tests/fixtures/hooks/reference-corpus.json` at runtime —
shipped code consuming a test fixture as production configuration. See cycle 6.

## Layering

### The intended stack

**Foundational.** `decision-engine` is a true leaf: its four library modules import no
other repository module, define no `main()`, and raise rather than exit — the caller maps
exceptions to status. Twenty-four shipped files outside it import it (22 in `bin/`, plus
`hooks/adr_hook_core.py` and `scripts/benchmark-adr-grilling.py`; the decision-engine
document names each one).
Python is the only hook host since the native host was retired in 0.55.1 (ADR-029), so no
second implementation of the semantic layer remains. Everything that parses an ADR reads through it, which is why
"the ADR set means one thing" is an enforceable property rather than a hope.

The second foundational element is the *declarative half* of
`contracts-and-distribution` — `schemas/` and `templates/`. These are data, not code,
and four components read them downward at runtime.

**Engines.** `enforcement-engine`, `retrieval-and-injection` and `health-and-lifecycle`
sit above the leaf. They divide by posture, not by subject matter: enforcement is the sole
fail-closed mechanism (ADR-004 puts blocking authority in `bin/adr-judge`, joined since
ADR-023 by the pull-request guard's own call into that same judge), while retrieval and
health are fail-open and report-only — every read path exits 0. That posture split is the
load-bearing boundary in the whole system, and it is enforced socially rather than
mechanically.

**Surfaces.** `agent-integration` and the *release half* of `contracts-and-distribution`
are the outer skin. Nothing in either owns ADR semantics; every path terminates in a
`bin/` CLI. `agent-integration`'s import edges out of itself
(`hooks/adr_hook_core.py` importing `query_adr_context`, and lazily `adr_index_core` for
the ADR-021 index refresh) remain the exception that mostly proves the rule — but they
are no longer the *only* ones: since ADR-023/024, its
`hooks/adr_pr_guard.py` also reaches directly into `enforcement-engine` (a fail-closed
subprocess call, not an import) and into `retrieval-and-injection` (an advisory subprocess
nudge that can never block) — both drawn above as new edges out of `AI`.

**Verification.** `quality-assurance` sits on top and depends on all six others. It should
be removable without affecting behaviour. It is not — see below.

**Allowed direction:** downward only. A surface may reach an engine; an engine may reach
the leaf; nothing should reach up. Four things violate that.

### One component spans both ends of the stack

`contracts-and-distribution` is the structural oddity, and naming it resolves most of the
apparent tangle. Its `schemas/` + `templates/` half is *declarative data consumed
downward* by `enforcement-engine`, `retrieval-and-injection`, `health-and-lifecycle` and
`agent-integration`. Its `packaging/` + `scripts/` + `codex/` + `copilot/` half consumes
those same four components *upward* — copying every mirrored `bin/` file verbatim,
subprocessing nine of the CLIs in workflow steps, and rendering
`agent-integration`'s skills, prompts and `hooks.json` from `agent-integration`'s own
registries.

So four of the loops below are the same fact seen four times: a component that is
simultaneously the bottom and the top of the stack. That is a naming problem, not a
design defect — and it is separable, because the two halves share no code. The two loops
that survive that reframing are genuine, and they are listed first.

### Cycles, ranked by mechanism (import > subprocess > file read)

**1. `health-and-lifecycle` ↔ `contracts-and-distribution` — a code-level inversion, the
worst of the set.** `bin/adr_doctor_checks.py` imports `scripts/adr_settings.py`
(`resolve_settings`), `scripts/project_setup.py` (`validate_markers`, `collect_changes`,
`apply_changes`) and, lazily and only outside a generated mirror,
`scripts/client_generation.py` (`generate`, `bin/adr_doctor_checks.py:239`).
`bin/` importing `scripts/` works only because `bin/adr-doctor:56-58` appends the repository
root and `scripts/` to `sys.path` (and masks its own `bin/` entry during the import block). The health-and-lifecycle document labels this a layering inversion in its
own dependency table. The return edge is the generator copying and subprocessing all of
`bin/`. Consequence: `scripts/` is not release-only infrastructure — `adr-doctor` cannot
run without it, so the release toolchain is a runtime dependency of the health tool.

**2. `health-and-lifecycle` ↔ `agent-integration` — import in one direction, MCP in the
other.** `bin/adr_doctor_probes.py:13` does `from hooks.hook_benchmark import measure`
and imports `detect_clients` from `clients/installer/` (`bin/adr_doctor_checks.py` imports
`CLIENT_IDS` too), then drives a four-message MCP session against `bin/adr-mcp` as a
*client*. Meanwhile `bin/adr-mcp` subprocesses `adr-readiness` and `adr-status` to serve
two of its seven tools, and the hook runtime reads the `.adr-kit-readiness.json` queue that
`adr-guardian` writes — the same queue that feeds the ADR-041 automatic grill handoff. The health-and-lifecycle document records the MCP
half as "purely process-level in both directions", so a signature change cannot break it;
the `hooks.hook_benchmark` import is the part that can, being a real code edge from an
engine up into a surface.

**3. `agent-integration` ↔ `contracts-and-distribution` — generator and generated.** The
generator reads `clients/{capabilities,workflows,exceptions}.json` and
`hooks/manifest.json` as declared inputs and emits this component's own `hooks.json`,
17 skills and 51 prompts; the installer then copies the resulting `codex/`/`copilot/`
payload to a per-user data root and patches only that copy (ADR-006); and
`agent-integration` reads `schemas/client-capabilities.schema.json` and the `templates/`
copy-out artefacts. Three mechanisms, no import edge, and the ownership boundary is
documented on both sides — the mildest of the four.

**4. `retrieval-and-injection` ↔ `health-and-lifecycle` — subprocess down, lazy import
up.** `bin/adr` subprocesses `bin/adr-index` inside every lifecycle transaction (and
restores its snapshot if index regeneration fails); `bin/adr-context` imports
`adr_retrieval_health` for `--check-probes`. That import used to be lazy; since the
TASK-62 explicit-path loader it is loaded at module scope (`bin/adr-context:61`) and the
function-local imports at `:139` and `:520` resolve from that cache. The reverse direction
gained a code edge too: `bin/adr-guardian:476` loads `adr_index_core` to check index
freshness without a subprocess. It is a cycle in both directions now: change the health
probe's signature and a retrieval CLI breaks, and the reverse.

**5. `contracts-and-distribution` ↔ `quality-assurance` — a three-way loop.** CI gates the
suite (`validate.yml` runs a 10-module packaging subset plus a 3-OS × Python 3.10/3.12
matrix, and `install-smoke.yml` exercises the `.pre-commit-hooks.yaml` install); the suite asserts on CI's own files (text assertions over
`.github/workflows/*.yml` and `packaging/*.json`); and `scripts/refresh-otgw-corpus.py:186`
*writes* `tests/testsets/otgw-firmware/manifest.json` including the 169 `sha256` entries
that `test_otgw_corpus.py` then asserts are byte-unchanged. One release script owns a
corpus the suite guards.

The write edge carries a qualification worth keeping attached to it, because it bounds the
blast radius: `refresh-otgw-corpus.py` is invoked by **no workflow** (verified — the only
matches for `refresh-otgw` outside the script itself are its own `__pycache__`), and it is
absent from `packaging/public-artifacts.json`'s `include_roots`, as is `tests/` entirely
(both verified). So this is a manual, in-repo maintenance operation that never reaches a
distributed tree. It is a real loop in the source repository and a non-loop in anything
shipped — unlike cycle 6, which ships.

**6. `quality-assurance` ↔ `agent-integration` (and transitively `health-and-lifecycle`) —
shipped code reads a test fixture.** This is the most surprising cross-component fact in
the system and it inverts the top of the stack. `hooks/hook_benchmark.py:115-118` resolves
`plugin_root / "tests" / "fixtures" / "hooks" / "reference-corpus.json"` and `json.loads`
it; `bin/adr_doctor_probes.py:13,174` calls `measure()` during `adr-doctor --deep`. So
`tests/` is not removable from a distributed tree if `--deep` is to work — the latency
*method* (budget triples, sample counts, cache states) is defined as a test fixture and
consumed as production configuration. Everything else about `quality-assurance` is
correctly one-way.

### Placement smells that are not cycles

- **`adr_state` and `adr_config` are homed in the wrong component.** Both live in the
  `bin-lib-runtime` cluster inside `enforcement-engine`, and the enforcement document
  states plainly that `adr_state` has *no consumer in this component* — its real users are
  `adr-guardian` (health) and `adr-watch` (retrieval). They are shared primitives wearing
  an enforcement badge. Moving them to their own foundational module beside
  `decision-engine` would delete two misleading arrows without changing a line of logic.

- **Duplication is used instead of dependency, deliberately, to preserve the ADR-004
  boundary.** There is no code edge in either direction between
  `retrieval-and-injection` and `bin/adr-judge`, because everything in retrieval fails open
  and the judge fails closed. The price is verbatim copies: `bin/adr-suggest` carries
  `glob_to_regex`, `parse_diff` and `_fence` copied from `bin/adr-judge` (`bin/adr-suggest:151-155`)
  with a "keep them in sync" instruction, and `bin/adr-discover:155` carries a third
  `glob_to_regex` commented "Same translator as `bin/adr-judge`" (moved here from the file
  formerly named `bin/adr-audit` when ADR-026 renamed it — the duplication itself did not
  move). **Path-glob translation — the function that decides which files an ADR governs —
  therefore has three homes and no mechanical guard.** That is the highest-consequence
  duplication in the repository, because a divergence changes enforcement *scope* silently.

- **Three readers of `ADR-INDEX.json` at three strictness levels.**
  `adr_query.load_index_graph` validates schema version, staleness, node structure and
  duplicate ids, and raises. `hooks/adr_hook_core.py:222` caps the file at 2 MiB and
  returns `[]` on any problem — no version check, no staleness check (staleness is handled
  separately by the ADR-021 refresh). `bin/adr-grill-signal:107-109` applies the same
  2 MiB cap and a bare `json.loads`, exiting 2 on an unreadable file — again no version or
  staleness check. A stale or schema-v1 graph is rejected by the query engine and accepted
  by both lenient readers.

- **Three components can write ADR Markdown.** `bin/adr` owns status transitions
  (transactionally, with snapshot rollback), `bin/adr-migrate` and `bin/adr-renumber` own
  profile and identity, and `bin/adr-judge --migrate-status-history` is a third write path
  in the component whose entire purpose is otherwise read-only judging. Only `bin/adr` is
  transactional. Neither `bin/adr-discover` nor `bin/adr-audit` writes ADR files, so this
  count is unaffected by the ADR-026 rename.

### Coverage gap: `bin/adr-discover` and `bin/adr-audit`

The census here no longer lands on a single orphan file. [ADR-026](../docs/adr/ADR-026-record-the-combined-audit-command-and-its-five-way-exit-contract.md)
(Accepted 2026-08-04) records a rename that split what earlier versions of this index
called `bin/adr-audit` into two files with different jobs:

- **`bin/adr-discover`** (546 lines) is the deterministic missing-ADR candidate scanner
  this index used to describe under the name `bin/adr-audit` — the tool `/adr-kit:init`
  runs to discover undocumented decisions. It still imports `SUPPORTED_PROFILES` and
  `detect_profile` from `adr_format` (verified at `bin/adr-discover:66`) — a
  `decision-engine` format-registry consumer, unchanged by the rename — and it still
  carries the duplicated `glob_to_regex` translator noted above, now at
  `bin/adr-discover:155`. It is the sole importer of `bin/adr_history_scan.py` (278 lines,
  fail-open git-history evidence stamped `source: "history"`), which puts that module in
  the same gap. Its only known in-repo caller is
  `bin/adr_doctor_core.py:216` (`audit_script = bin_dir / "adr-discover"`, verified by
  direct read), which subprocesses it on material drift — that caller is
  `health-and-lifecycle`.
- **`bin/adr-audit`** (493 lines) now names something new: the combined `adr-lint` +
  `adr-judge` command ADR-026 records, with a five-way exit contract —
  `EXIT_OK=0`, `EXIT_CODE_VIOLATION=1`, `EXIT_TOOLING=2`, `EXIT_ADR_QUALITY=3`,
  `EXIT_BOTH=4` — implemented by `exit_code()` at `bin/adr-audit:270` (verified by direct
  read; the `lint`/`judge` outcomes feed `bad_adrs`/`bad_code` booleans that combine into
  one of the five codes). It runs `bin/adr-lint` and `bin/adr-judge` as subprocesses,
  either against a diff (the default) or, in `--whole-codebase` mode, against a diff of
  every tracked file versus the empty tree — a caller *into* `enforcement-engine`, not a
  member of it. A bare invocation with neither `--diff` nor `--whole-codebase` is refused
  at exit 2, naming `bin/adr-discover` rather than silently reporting a clean pass against
  an empty diff. Unlike the scanner, it imports nothing from `decision-engine`: its only
  imports are stdlib (`argparse`, `json`, `os`, `subprocess`, `sys`, `pathlib`, `typing`).

None of these files is claimed as a Code Element by any of the seven component documents;
`enforcement-engine`'s own document is explicit that both are "documented here only as an
inbound caller."

The census now closes. `bin/` holds **48** tracked files (26 extensionless entrypoints
plus 22 `*.py` modules, verified by `git ls-files bin` on 2026-10-06). This index assigns
them as follows: `decision-engine` 8, `enforcement-engine` 11, `retrieval-and-injection` 6,
`health-and-lifecycle` 19, `agent-integration` 1 (`bin/adr-mcp`) — 45 files — plus the
three in this gap (`adr-discover`, `adr_history_scan.py`, `adr-audit`): 48. Five of those
assignments are made here and are not yet in the component documents, each placed by its
only importer or caller (read from the code, not from a component document):
`adr_llm_judge_migration.py` (loaded by `bin/adr-migrate:541`) in `decision-engine`;
`adr_index_core.py` (the importable generator behind `bin/adr-index`, also loaded by the
guardian and the hook runtime) in `retrieval-and-injection`; `adr-substance` (run by the
guardian skill's LLM tier) and `adr-settings` (run by `/adr-kit:settings`) in
`health-and-lifecycle`; and `adr_history_scan.py` (imported only by `bin/adr-discover`)
in this gap.

### One number that looks like agreement and is not

Two different 39s appear in the component documents and they exclude different files.
`contracts-and-distribution` reports **39 `bin/` files copied into each client mirror** —
that is 40 minus `bin/bump-version`, a declared `COPY_EXCLUSIONS` entry. This index's own
previous census also reached **39** — that is 40 minus the file then named `bin/adr-audit`.
Same total, different exclusion; do not read the match as corroboration. Neither 39 holds
today: `bin/` has 48 tracked files, and each generated mirror carries 47 of them
(`git ls-files codex/bin` and `copilot/bin`, 2026-10-06) — 48 minus the same
`bin/bump-version` exclusion.

## Document map

Four C4 levels document this system. This file is the component level; the other three
are one hop away.

| Level | Document(s) | What it covers |
| --- | --- | --- |
| Code | Retired 2026-08-09 (KISS simplification plan): the module docstrings in `bin/`, `hooks/` and `scripts/` carry the code-level detail | Function signatures, arguments and module-level dependencies, next to the code they describe |
| Component (this level) | The seven `c4-component-*.md` documents indexed above, synthesized here | Component boundaries, cross-component dependencies, layering and cycles |
| Container | [c4-container.md](./c4-container.md) | What actually runs: CLI Toolkit, MCP Server, Hook Runtime, Native OpenCode Plugin, Pre-commit Gate, Instruction & Skill Corpus, Client Generation & Release Toolchain, Generated Client Mirrors. Substitutes **distribution** for **deployment** throughout, because this repository ships no deployment artifact of any kind — no Dockerfile, Kubernetes manifest, Terraform file, docker-compose file or serverless function definition exists anywhere in the tree — and deliberately carries no `apis/` directory or OpenAPI specification, because adr-kit exposes no HTTP interface (its four machine-readable contracts are a stdio JSON-RPC tool surface, the certified clients' lifecycle-hook event contract, a set of CLI exit-code contracts, and the host-loaded OpenCode plugin API). |
| Context | [c4-context.md](./c4-context.md) | Who uses adr-kit and why, one level above the container boundary: four evidenced personas (maintainer/human decision-maker, coding agent, committing engineer, CI/the automated gate), the system features and user journeys each one drives, and the external systems (git, the host CLI runtime, the public GitHub repository, GitHub Actions, the host model CLI used only where a host client is recorded, the pre-commit.com framework) adr-kit depends on. |
