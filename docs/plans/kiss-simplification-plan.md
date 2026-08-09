# KISS simplification plan: closer to the spec by amending it

Maintainer decision context, recorded 2026-08-09. The maintainer's judgement,
after reviewing the embedding and backend machinery: "het voelt zwaar en
overbodig" - the vector layer and the local-model/backend surface weigh more
than the problem they solve. This plan turns that judgement into an ordered,
task-tracked change set.

Status of this document: a plan, not a decision record. Every decision it
proposes lands as a spec amendment or an ADR supersession (R10) before code is
removed. Backlog tasks reference this file; this file references them back in
the task table at the end.

## The finding

`spec.md` is the yardstick, and by its own rule - *"a mechanism that exists in
the code but that no shipped path reaches does not count as implemented"* - the
heaviest subsystems in the kit fail the bar they were built to:

- **The vector layer** (ADR-018, ADR-020; `bin/adr-embed`,
  `bin/adr_vector_store.py`, `bin/adr_embedding_runtime.py`,
  `hooks/adr_embed_query.py`, the rerank in `bin/adr_query.py`, the doctor
  probes). No store exists in this repository. The rerank receives the already
  truncated lexical top-5 (`min_score` filter, then `ordered[:limit]`), so the
  zero-token-overlap miss that justifies R6 in prose cannot be closed by the
  shipped path: the vector pass reorders candidates lexical ranking already
  found. Full semantic search exists only in `adr-embed query`, whose own help
  labels it a store diagnostic.
- **The backend registry beyond `host`** (three HTTP backends, credential
  refusals, runtime probes, the R16 setup dialogue). Roughly 550 lines of
  `bin/adr_llm.py` plus ~700 dedicated test lines serve backends no user of
  this repository has selected. The `host` backend - the one that runs - is
  about 60 lines.

Measured footprint of the two subsystems together: ~1,500 production lines,
~1,300 dedicated test lines, ~12 config keys, two ADRs, one spec requirement
(R16) that exists only to serve another (R6).

The complexity is **specified**, not accidental: R6, R6.1, R11 (embedding
half), R12 (multi-backend), and R16 demand exactly this machinery. Therefore
the kit cannot become both simpler and closer to the spec unless the spec
moves. Amending the spec deliberately - and superseding the ADRs that
implement it - is the honest path, and it is the kit's own thesis applied to
itself.

## What stays untouched

Bought complexity that earns its weight. Not in scope for removal:

- The judge and the `host` backend (`claude -p` / `codex exec` / `copilot -p`
  over stdin). R2 is the core of the product.
- Per-ADR isolation in the LLM pass (TASK-63): without it one ADR's Decision
  text can flip another ADR's verdict, reproduced 3/3.
- R12.1's security rule: tracked configuration selects, it never introduces.
  With one backend the rule becomes structurally true instead of carefully
  argued - that is a strengthening, not a relaxation.
- The generated client mirrors (`codex/`, `copilot/`) and
  `scripts/build-client-adapters.py`. R17/R18 buy them; generation keeps them
  free.
- Zero runtime dependencies (R18), the 2 s deterministic budget (R21), the
  fail-open hooks / fail-closed judge split.
- The graph half of R11: stdlib, deterministic, and it carries R7's
  cross-reference machinery.

## Spec amendments (step 1)

1. **R6 and R6.1: retire.** Retrieval is lexical scoring over the generated
   index plus one-hop graph neighbours; the model performs R5's final
   selection. The zero-overlap miss is answered by frontmatter metadata
   (`topics`, `aliases`, `symbols`, `components`), which the scorer already
   reads. At 36 ADRs this is sufficient; semantic recall becomes interesting
   near ~500 records, and the shipped rerank did not deliver it anyway.
2. **R11: keep the graph, drop the embeddings clause.**
3. **R12: reduce to `host` plus one operator escape hatch** (`ADR_KIT_LLM_CMD`
   / `--llm-cmd`, already operator-only). Drop openrouter, ollama and
   openai-compatible. Named loss, stated in the amendment: on machines without
   an agent CLI (CI, bare laptops) the LLM pass degrades to declarative-only -
   which is exactly the floor ADR-001 already defines.
4. **R16: retire entirely.** It exists only to provision R6's runtime.
5. **R13 stays**, and shrinks with the config surface it describes.

## ADR work (step 2)

- Supersede **ADR-018** and **ADR-020** with one new ADR recording the
  retirement of the vector layer and the evidence (no store, recall gap not
  closed by the shipped path, 36-record corpus).
- Amend or supersede **ADR-017** to host + escape hatch. **ADR-025** (select
  vs introduce) stands.
- The reversed work is acknowledged by task id, not erased: TASK-79 (vector
  layer epic), TASK-85 (LM Studio / OpenAI-compatible), TASK-87 (runtime
  detection at setup), TASK-94 (wire semantic retrieval), TASK-107, TASK-109,
  TASK-135 (embedding model defaults). Supersession, never deletion (R10).

## Removals (step 3, after the records exist)

- `bin/adr-embed`, `bin/adr_vector_store.py`, `bin/adr_embedding_runtime.py`,
  `hooks/adr_embed_query.py`, the `_apply_semantic_order` vector route, the
  embedding doctor probes, `EMBEDDING_EVENTS` and the `user-prompt-submit`
  network declaration in `hooks/manifest.json` (the event goes back to
  `network_allowed: false`).
- In `bin/adr_llm.py`: `OpenRouterBackend`, `OllamaBackend`,
  `OpenAICompatibleBackend`, `HttpBackend`, and their factories; keep
  `SubprocessBackend`, the registry shape, and the credential refusal.
- Config keys: `judge.openrouter_model`, `judge.ollama_model`,
  `judge.openai_model`, plus the already-ignored `judge.llm_cmd`,
  `judge.llm_model`, `judge.llm_default`, `suggest.llm_cmd`. The schema
  refuses each removed key **by name** with a sentence saying what replaced
  it, so an existing config fails loudly, not silently.
- Dedicated tests for the removed backends and store contract.

## Consolidations (step 4)

- **Health family:** `adr-audit` (R15: lint + judge, diff and whole-codebase
  modes) and `adr-guardian` (R20: the unprompted track) remain the two
  entry points. `adr-status`, `adr-quality`, `adr-readiness`, `adr-doctor`
  become library modules or subcommands behind them.
- **Setup family:** one `/adr-kit:setup` with modes replaces
  `init`/`setup`/`install-hooks`/`upgrade` as separate user-facing entry
  points (R19 asks for one deterministic act). The R16 dialogue is already
  gone by then.
- **C4-Documentation:** keep the context and component levels; drop the
  eighteen hand-written `c4-code-*.md` files (~10k lines) whose content the
  docstrings already carry and which no generator or CI keeps honest.

## Investment (step 5) - the gap the freed budget pays for

Appendix A.4 names the real asymmetry: *"an unrecorded decision survives by
default."* Implement **B1**: a `PreToolUse` hook on `ExitPlanMode` that runs
the deterministic candidate finder against the plan text and names what looks
undecided. Budgeted like the other pre-hooks: 1 s, injection only, no model.
(B3, linting this repository's own ADRs on every PR, is already tracked as
TASK-113.)

## Execution constraints

- One PR per step; never one big cleanup PR. The 11-minute full pytest run is
  mandatory before merge; ADR-010's per-file line limits and the adapter
  regeneration (`python scripts/build-client-adapters.py`, confirm with
  `--check`, expect `changed=0`) apply to every code step.
- Spec amendment and ADR supersession (steps 1–2) travel together in the
  first PR; no code is removed before the records that authorise it exist.
- Expected end state: `bin/` from ~25.5k to ~18k lines, 26 → ~18 entry
  points, 66 → ~40 config keys, no daemon, no model download, no network in
  any hook - with every gate the amended spec demands still standing.

## Task table

| Step | Task | Scope |
|---|---|---|
| 1+2 | TASK-143 | Amend spec (R6, R6.1, R11, R12, R16); supersede ADR-018/020; amend ADR-017 |
| 3 | TASK-144 | Remove the embedding/vector subsystem |
| 3 | TASK-145 | Reduce LLM backends to host + operator escape hatch |
| 3 | TASK-146 | Prune the config schema; refuse removed keys by name |
| 4 | TASK-147 | Consolidate health commands behind adr-audit and adr-guardian |
| 4 | TASK-148 | Consolidate the four setup entry points into one |
| 4 | TASK-149 | Trim C4-Documentation to context and component levels |
| 5 | TASK-150 | Plan-exit hook (B1, R3): name undecided decisions when a plan completes |
