# adr-kit Components

Seven components, synthesized from the eighteen `c4-code-*.md` cluster documents.
Every claim below is traceable to a component document; this file adds only the
cross-component structure that no single component document can see.

## System Components

| Component | Short description | Document |
| --- | --- | --- |
| **Decision Record Engine** (`decision-engine`) | The semantic core: what an ADR *means*. Three body profiles mapped onto stable semantic roles, the frontmatter dialect, the directory-to-graph projection, and the retrieval query engine — plus the two mutators of ADR *identity* (profile migration, renumbering). 7 files, 3,396 lines, stdlib-only, **zero outbound repository dependencies**. | [c4-component-decision-engine.md](./c4-component-decision-engine.md) |
| **Enforcement and Verification Engine** (`enforcement-engine`) | The only part of adr-kit that **blocks**. Judges a staged diff against every Accepted ADR's fenced JSON `## Enforcement` block, scores and gates ADR quality, and owns the killable-subprocess regex sandbox that makes repository-authored policy safe to execute. 5 CLIs (~4,700 lines) over 4 runtime modules (~600 lines). | [c4-component-enforcement-engine.md](./c4-component-enforcement-engine.md) |
| **Selective Context Retrieval** (`retrieval-and-injection`) | Makes recorded decisions *findable* at the moment an agent needs them. One generator (`adr-index`, the sole writer of every derived index view) plus four readers covering ADR-004's session, task and edit tiers. 5 CLIs, 2,743 lines, fail-open by construction — every path exits 0. | [c4-component-retrieval-and-injection.md](./c4-component-retrieval-and-injection.md) |
| **Health, Guardian and Lifecycle** (`health-and-lifecycle`) | The time dimension of an ADR set: the only sanctioned status writer (`bin/adr`, transactional with snapshot rollback), the SessionStart staleness detector, the health ledger, retirement scoring, seven-class readiness with a CI merge gate, and the local `adr-doctor` check/repair/probe engine. 17 files, 5,745 lines. | [c4-component-health-and-lifecycle.md](./c4-component-health-and-lifecycle.md) |
| **Agent and Client Integration** (`agent-integration`) | Every path by which an LLM agent or CLI client reaches the engine, deliberately kept separate: a hand-rolled MCP stdio server (5 read-only tools, key-free), a lifecycle-hook runtime that pushes context unasked, an instruction corpus of skills/prompts/one subagent, and a capability registry plus desired-state installer. Owns no ADR semantics — every path terminates in a `bin/` CLI. | [c4-component-agent-integration.md](./c4-component-agent-integration.md) |
| **Contracts, Packaging and Distribution** (`contracts-and-distribution`) | The declarative contract layer and the release toolchain that acts on it: 11 JSON Schemas, 11 copy-out templates, 8 `packaging/*.json` registries, 20 `scripts/*.py` modules, 10 workflows plus 2 composite actions, and the two generated client payloads (`codex/`, `copilot/` — 91 tracked files each, 88 of them a deterministic projection). | [c4-component-contracts-and-distribution.md](./c4-component-contracts-and-distribution.md) |
| **Quality Assurance** (`quality-assurance`) | The single pytest suite plus its fixture, corpus and certification-evidence families — 71 modules, 806 test functions collecting as 903 tests, 19,906 lines, larger than `bin/` itself. Dominated by black-box subprocess tests over the extensionless CLIs, and the only mechanical guard on several ADR gates. | [c4-component-quality-assurance.md](./c4-component-quality-assurance.md) |

**Not covered by any of the seven:** `bin/adr-audit` (485 lines). See
[Coverage gap](#coverage-gap-binadr-audit).

## Component Relationships

```mermaid
flowchart TB
    subgraph ext["External systems"]
        GIT(["git CLI"])
        LLM(["claude CLI<br/>only LLM path"])
        GHA(["GitHub Actions + gh"])
        PCF(["pre-commit.com"])
        HOSTS(["Claude Code / Codex<br/>Copilot hosts"])
        AJV(["Node20 + ajv-cli"])
        RUSTC(["rustc"])
        PYPI(["PyPI — pytest"])
        OLLAMA(["Ollama loopback"])
    end

    DE["decision-engine<br/>LEAF: no outbound repo dep"]

    subgraph EEG["enforcement-engine"]
        JUDGE["adr-judge · adr-lint · adr-quality<br/>only fail-closed mechanism"]
        RT["adr_config · adr_state · adr_regex<br/>shared primitives"]
    end

    RI["retrieval-and-injection<br/>adr-index sole writer · fail-open"]
    HL["health-and-lifecycle<br/>only ADR status writer"]
    AI["agent-integration<br/>MCP · hooks · skills · installer"]

    subgraph CDG["contracts-and-distribution"]
        CONTRACTS["schemas/ · templates/<br/>read DOWNWARD"]
        RELEASE["packaging/ · scripts/ · workflows/<br/>codex/ · copilot/"]
    end

    QA["quality-assurance<br/>tests/ — 903 tests"]
    ORPHAN["bin/adr-audit<br/>NO component"]

    MD[("ADR-NNN-*.md<br/>3 writers")]
    IDX[("ADR-INDEX.json<br/>3 readers, 3 strictnesses")]

    JUDGE -->|import| DE
    RI -->|import| DE
    HL -->|import| DE
    AI -->|import| DE
    QA -->|import| DE
    ORPHAN -->|import| DE

    RI -->|import| RT
    HL -->|import| RT

    HL -->|subprocess| JUDGE
    AI -->|MCP tool call| JUDGE
    RELEASE -->|subprocess| JUDGE
    QA -->|subprocess| JUDGE
    PCF -->|git hook| JUDGE
    CONTRACTS -->|git hook| JUDGE

    HL -->|subprocess| RI
    AI -->|MCP tool call| RI
    RELEASE -->|subprocess| RI
    GHA -->|subprocess| RI
    QA -->|subprocess| RI

    RI -->|import| HL
    AI -->|MCP tool call| HL
    QA -->|subprocess| HL
    HOSTS -->|subprocess| HL
    HL -->|subprocess| ORPHAN

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

    JUDGE -->|subprocess| LLM
    RI -->|subprocess| LLM
    JUDGE -->|subprocess| GIT
    HL -->|subprocess| GIT
    RELEASE -->|subprocess| GIT
    AI -->|subprocess| HOSTS
    HL -->|loopback HTTP| OLLAMA
    RELEASE -->|loopback HTTP| OLLAMA
    RELEASE -->|subprocess| AJV
    AI -->|build-time only| RUSTC
    QA -->|import| PYPI
```

**Label vocabulary** — every edge carries exactly one:

| Label | Mechanism |
| --- | --- |
| `import` | Python import by bare name, after a `sys.path.insert` (there is no package) |
| `subprocess` | Process spawn — `sys.executable`, a `bin/` CLI, or an external binary |
| `MCP tool call` | JSON-RPC 2.0 over stdio to `bin/adr-mcp`, which then subprocesses onward |
| `git hook` | Invoked by the installed pre-commit wrapper or the pre-commit.com framework |
| `reads JSON` / `reads + writes` | File read (or read-modify-write) on disk — JSON, or Markdown for the ADR bodies |
| `writes` | File write on disk — durable via `os.fsync` + `os.replace` throughout |
| `copies bytes` | Verbatim file copy by `scripts/build-client-adapters.py`, drift-checked with `--check` |
| `loopback HTTP` | Bounded probe to `127.0.0.1:11434` for Ollama *identity* that never invokes a model |
| `build-time only` | `rustc` over `hooks/native/*.rs` — manual, invoked by no CI step |

Three conventions matter for reading the arrows.

**Data-flow direction on artefact edges.** `reads`/`writes` edges point the way the bytes
travel, so the dependency between a generator and its consumer runs *through* the artefact
node, not directly between components. `adr-index` writes `ADR-INDEX.json`; the hook
runtime reads it; there is no call in either direction. Only the two artefacts that carry a
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
exceptions to status. Seventeen consumers import it, one subprocesses to it, and one
re-implements it in Rust. Everything that parses an ADR reads through it, which is why
"the ADR set means one thing" is an enforceable property rather than a hope.

The second foundational element is the *declarative half* of
`contracts-and-distribution` — `schemas/` and `templates/`. These are data, not code,
and four components read them downward at runtime.

**Engines.** `enforcement-engine`, `retrieval-and-injection` and `health-and-lifecycle`
sit above the leaf. They divide by posture, not by subject matter: enforcement is the sole
fail-closed mechanism (ADR-004 puts blocking authority in `bin/adr-judge` and nowhere
else), while retrieval and health are fail-open and report-only — every read path exits 0.
That posture split is the load-bearing boundary in the whole system, and it is enforced
socially rather than mechanically.

**Surfaces.** `agent-integration` and the *release half* of `contracts-and-distribution`
are the outer skin. Nothing in either owns ADR semantics; every path terminates in a
`bin/` CLI. `agent-integration`'s single import edge out of itself
(`hooks/adr_hook_core.py` importing `query_adr_context`) is the exception that proves the
rule — everything else is a subprocess or a file read.

**Verification.** `quality-assurance` sits on top and depends on all six others. It should
be removable without affecting behaviour. It is not — see below.

**Allowed direction:** downward only. A surface may reach an engine; an engine may reach
the leaf; nothing should reach up. Four things violate that.

### One component spans both ends of the stack

`contracts-and-distribution` is the structural oddity, and naming it resolves most of the
apparent tangle. Its `schemas/` + `templates/` half is *declarative data consumed
downward* by `enforcement-engine`, `retrieval-and-injection`, `health-and-lifecycle` and
`agent-integration`. Its `packaging/` + `scripts/` + `codex/` + `copilot/` half consumes
those same four components *upward* — copying all 39 mirrored `bin/` files verbatim,
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
(`resolve_settings`, `local_judgment_state`), `scripts/client_generation.py` (`generate`)
and `scripts/project_setup.py` (`validate_markers`, `collect_changes`, `apply_changes`).
`bin/` importing `scripts/` works only because `bin/adr-doctor:12-14` inserts three roots
into `sys.path`. The health-and-lifecycle document labels this a layering inversion in its
own dependency table. The return edge is the generator copying and subprocessing all of
`bin/`. Consequence: `scripts/` is not release-only infrastructure — `adr-doctor` cannot
run without it, so the release toolchain is a runtime dependency of the health tool.

**2. `health-and-lifecycle` ↔ `agent-integration` — import in one direction, MCP in the
other.** `bin/adr_doctor_probes.py` does `from hooks.hook_benchmark import measure` and
imports `detect_clients` / `CLIENT_IDS` from `clients/installer/`, then drives a
four-message MCP session against `bin/adr-mcp` as a *client*. Meanwhile `bin/adr-mcp`
subprocesses `adr-readiness`, `adr-status` and `adr-quality` to serve three of its five
tools, and the hook runtime reads the `.adr-kit-readiness.json` queue that
`adr-guardian refresh-readiness` writes. The health-and-lifecycle document records the MCP
half as "purely process-level in both directions", so a signature change cannot break it;
the `hooks.hook_benchmark` import is the part that can, being a real code edge from an
engine up into a surface.

**3. `agent-integration` ↔ `contracts-and-distribution` — generator and generated.** The
generator reads `clients/{capabilities,workflows,exceptions}.json` and
`hooks/manifest.json` as declared inputs and emits this component's own `hooks.json`,
15 skills and 45 prompts; the installer then copies the resulting `codex/`/`copilot/`
payload to a per-user data root and patches only that copy (ADR-006); and
`agent-integration` reads `schemas/client-capabilities.schema.json` and the `templates/`
copy-out artefacts. Three mechanisms, no import edge, and the ownership boundary is
documented on both sides — the mildest of the four.

**4. `retrieval-and-injection` ↔ `health-and-lifecycle` — subprocess down, lazy import
up.** `bin/adr` subprocesses `bin/adr-index` inside every lifecycle transaction (and
restores its snapshot if index regeneration fails); `bin/adr-context --check-probes`
imports `adr_retrieval_health` — but *lazily, inside the function*, explicitly to keep it
off the hot path. The laziness is deliberate and documented, which makes this the
best-managed cycle in the system. It is still a cycle: change the health probe's signature
and a retrieval CLI breaks.

**5. `contracts-and-distribution` ↔ `quality-assurance` — a three-way loop.** CI gates the
suite (`validate.yml` runs a 10-module packaging subset plus a 3-OS × Python 3.10/3.12
matrix); the suite asserts on CI's own files (text assertions over
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
the system and it inverts the top of the stack. `hooks/hook_benchmark.py:83-86` resolves
`plugin_root / "tests" / "fixtures" / "hooks" / "reference-corpus.json"` and `json.loads`
it; `bin/adr_doctor_probes.py:20,299` calls `measure()` during `adr-doctor --deep`. So
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
  `glob_to_regex`, `parse_diff`, `_split_cmd` and `_fence` copied from `bin/adr-judge` with
  a "keep these in sync" instruction, and `bin/adr-audit:127` carries a third
  `glob_to_regex` commented "Same translator as `bin/adr-judge`". **Path-glob translation —
  the function that decides which files an ADR governs — therefore has three homes and no
  mechanical guard.** That is the highest-consequence duplication in the repository,
  because a divergence changes enforcement *scope* silently.

- **Three readers of `ADR-INDEX.json` at three strictness levels.**
  `adr_query.load_index_graph` validates schema version, staleness, node structure and
  duplicate ids, and raises. `hooks/adr_hook_core.py:182` caps the file at 2 MiB and
  returns `[]` on any problem — no version check, no staleness check.
  `hooks/native/adr-hook.rs:174` is a third reader in Rust with a hand-rolled JSON scanner
  and its own hardcoded field weights. A stale or schema-v1 graph is rejected by the CLI
  and silently accepted by both hook readers.

- **Three components can write ADR Markdown.** `bin/adr` owns status transitions
  (transactionally, with snapshot rollback), `bin/adr-migrate` and `bin/adr-renumber` own
  profile and identity, and `bin/adr-judge --migrate-status-history` is a third write path
  in the component whose entire purpose is otherwise read-only judging. Only `bin/adr` is
  transactional.

### Coverage gap: `bin/adr-audit`

`bin/adr-audit` (485 lines, a deterministic missing-ADR candidate scanner) belongs to no
component. The arithmetic is exact: `bin/` holds 40 files, and the seven components
account for 39 of them — `decision-engine` 7, `enforcement-engine` 9,
`retrieval-and-injection` 5, `health-and-lifecycle` 17, `agent-integration` 1
(`bin/adr-mcp`). `adr-audit` is the remainder.

The three documents that mention it point three different ways, so the evidence does not
settle its home:

- Its only in-repo caller is `bin/adr_doctor_core.py:216`, which subprocesses
  `bin/adr-audit --root <repo_root>` on material drift — that is `health-and-lifecycle`,
  whose document flags the file as appearing in no Code-level cluster document.
- Its only repository import is `from adr_format import SUPPORTED_PROFILES, detect_profile`
  (verified at `bin/adr-audit:41`) — a `decision-engine` format-registry consumer, and
  nothing more.
- It carries a duplicated `glob_to_regex` from `bin/adr-judge`, and the
  `decision-engine` dependency table attributes it to the `enforcement` slug — while the
  `enforcement-engine` document explicitly disclaims it: "It lives in a different
  component."

Functionally it is closest to `bin/adr-suggest` (the LLM missing-ADR detector in
`retrieval-and-injection`), which makes a fourth candidate. Documenting it under
`health-and-lifecycle` — its sole caller — is the smallest defensible fix, but the
assignment is a judgement call, not a fact the code supplies.

### One number that looks like agreement and is not

Two different 39s appear in the component documents and they exclude different files.
`contracts-and-distribution` reports **39 `bin/` files copied into each client mirror** —
that is 40 minus `bin/bump-version`, a declared `COPY_EXCLUSIONS` entry. The component
census above also reaches **39** — that is 40 minus `bin/adr-audit`. Same total, different
exclusion. Do not read the match as corroboration.
