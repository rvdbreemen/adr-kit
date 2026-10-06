# Health, Guardian and Lifecycle

## Overview

- **Name**: Health, Guardian and Lifecycle (`health-and-lifecycle`)
- **Description**: The component that owns the *time dimension* of an ADR set. It performs the
  only sanctioned lifecycle status transitions, and it is otherwise entirely read-side: staleness
  detection at session start, a per-machine health ledger with trend history, a coverage dashboard,
  four-signal retirement scoring, seven-class deterministic readiness with a CI merge gate,
  bounded fail-open grill advisories, retrieval-health probes, the guardian's LLM-tier
  section-substance check (`adr-substance`), the settings screen (`adr-settings`), and the local
  `adr-doctor` check/repair/probe engine.
- **Type**: CLI toolchain (10 executable entry points) plus 9 importable stdlib-only Python
  libraries. No long-running service, no daemon, no server socket.
- **Technology**: Python 3.10+, standard library only — verified across all 19 files. Zero
  third-party imports. The extensionless-script convention (`bin/adr-retire`, not
  `adr_retire.py`) means the 10 entry points are not normally importable; tests load them through
  `importlib.machinery.SourceFileLoader` / `spec_from_file_location`, and every production
  consumer reaches them as a **subprocess**. The 9 `.py` siblings are ordinary flat modules
  importable once `bin/` is on `sys.path`.
- **Size**: 19 files, 8,145 lines (re-measured with `wc -l` at v0.59.1). Largest single file:
  `bin/adr` (1,679 lines), then `bin/adr-guardian` (1,263).

---

## Purpose

Every other component in adr-kit answers "what does this ADR say?" or "does this diff violate
it?". This component answers **"is the ADR set still honest, and what should happen to it next?"**

It solves four problems that are all fundamentally about elapsed time:

1. **Decisions rot silently.** An ADR accepted eighteen months ago may name a library that no
   longer exists in the tree, or point at a `verified_in` target that has moved. Nothing in a
   commit-time gate notices, because the gate only looks at the diff. `bin/adr-retire` and
   `bin/adr-doctor` look at the whole tree against the whole ADR set.
2. **Nobody remembers to check.** A health tool that must be invoked is a health tool that is not
   invoked. `bin/adr-guardian check` runs at Claude Code SessionStart, decides whether a health
   tier is *due* on a two-tier cadence, and injects a short nudge into the session — then gets out
   of the way. It never runs the sweep itself; the in-session model does (ADR-002's
   "dumb detector, smart sweep" split).
3. **Proposed ADRs get implemented and never accepted.** `bin/adr-readiness` classifies every
   record into one of seven readiness classes and computes *explicit, inspectable* evidence that a
   diff implements a linked Proposed ADR. `bin/adr-readiness-ci` is the only thing in the
   component that turns that finding into a non-zero exit code, blocking a merge.
4. **The tooling itself drifts out of the project.** Installed pre-commit wrappers, `.mcp.json`
   launchers, client hook packages, generated client adapters and managed guidance blocks can all
   go stale relative to the installed plugin version. `bin/adr-doctor` measures that and applies an
   enumerated set of safe repairs.

The component also holds the **write** side of the lifecycle: `bin/adr` is the single sanctioned
writer of `## Status` transitions, and it is the strictest transactional writer in the repository —
its `_commit_lifecycle_changes` snapshots the ADR files *plus* `README.md`, `ADR-INDEX.md` and
`ADR-INDEX.json`, applies every atomic replace, regenerates the indexes, and restores the whole
snapshot if any step fails, including index regeneration.

The consistent posture across the read side is **fail-open, report-only**. The one fail-closed
enforcement floor in adr-kit lives in `bin/adr-judge` at pre-commit — a different component. This
component's SessionStart detector, hook advisories and dashboards can never block work; only
`bin/adr-readiness-ci` (a CI merge gate) and `bin/adr-doctor` (a CI health gate) emit a blocking
exit code, and neither runs on a developer's commit path. `bin/adr-substance`, the one file here
that asks a model anything, is advisory too: it exits 0 whether it found vacuous sections or could
not reach a model.

---

## Software Features

### Lifecycle writing

- **Ten subcommands, one writer.** `bin/adr new|profiles|propose|accept|reject|answer|relate|
  supersede|document|signer`. `answer` resolves an open question in place (a question that wraps
  onto several lines, or carries nested bullets, is marked as one question since 0.58.0) (`- [ ] text` → `- [x] text — **Answered <date> by
  <signer>:**`), keeping both the question and the resolution inside the immutable ADR rather than
  deleting it, which is the required path through ADR-022's append-only constraint; `relate`
  records a `related:` cross-reference on both ADRs in one command instead of two hand-edits;
  `signer` is read-only diagnostics over the ADR-027 machinery below (`--suggest` proposes
  candidates and writes nothing, `--audit` lists history entries with no human actor, `--set`
  writes the machine-local signer).
- **Transactional status transitions** — a legal-transition table (`LEGAL_TRANSITIONS`,
  `bin/adr:79`) gates every mutation; the write itself goes through a snapshot/apply/regenerate/
  rollback transaction that also covers the three generated index artefacts. A failed rollback is
  surfaced with both error messages rather than swallowed. Since 0.56.0–0.59.0 the writer also
  keeps `status_history` entries inside the `## Status History` block, exits 2 rather than
  discarding a transition an old-style Status line still carries, and writes a CRLF file back as
  CRLF.
- **Seven-gate acceptance check** — `_assert_acceptance_gates` (`bin/adr:724`) blocks acceptance on
  unresolved `## Open Questions`, then shells out to `bin/adr-lint --strict --gates
  schema,completeness,audit,evidence,clarity,consistency,policy` with `--context-dir` pointed at the
  ADR's own directory so a `supersedes`/`related` reference can resolve against its siblings. This
  is the strictest gate invocation in the repo; `adr-lint` itself defaults to only three gates.
  The lint and quality subprocesses run with stdin closed and a 120 s timeout
  (`LIFECYCLE_TOOL_TIMEOUT_S`, `bin/adr:23`), reported as an error rather than waited on.
- **`accept` requires `--confirm` (ADR-027, breaking in v0.45.0).** Acceptance is the one lifecycle
  transition that *decides* rather than records: it writes a signer name and a date into a
  `## Status History` entry that is immutable from that point on, and the signer is commonly
  *derived* — `git config user.name`, adopted and announced on stderr, per the resolution order
  explicit flag → `lifecycle.signer` → derived git identity → refusal. `--confirm` is the guard
  against that derived name landing in an immutable record nobody agreed to: it stops acceptance
  happening *by accident* — from a stale script, from CI, from an agent following an old
  instruction — without stopping a caller who deliberately passes it
  (`_assert_acceptance_was_asked_for`, `bin/adr:831`). A name that would name a machine
  (`github-actions[bot]`, `runner`, a bare `user`, …) is refused outright rather than asked to
  confirm (`person_shaped`, `bin/adr:1365`). **`accept --auto` is exempt** — spec R1 grants the
  init flow that exception, since there the user asked for a batch of records over code that
  already exists, and that request is itself the consent.
- **Human-gated auto-accept** — `accept --auto` additionally requires `documents_shipped: true`,
  at least one `verified_in` pointer, and an `adr-quality` composite score above
  `lifecycle.auto_accept.quality_threshold` (default 0.70). In the default `assist` mode it prints
  an eligibility line and mutates nothing without `--confirm` — the same flag, a separate check
  (`command_auto_accept`, `bin/adr:806`), reached only via the exempted path above.
- **Body-profile instantiation** — `adr new --profile madr|nygard|canonical` and
  `adr profiles --format json`, consuming the ADR-005 profile registry.

### Staleness detection and the health ledger

- **Two-tier due-date cadence** — `_compute_due_tiers` (`bin/adr-guardian:499`) computes
  `(cheap_due, llm_due)` from independent per-tier clocks against `drift_stale_days` (default 1)
  and `llm_stale_days` (default 14). Never having run counts as due.
- **Non-blocking SessionStart nudge** — `adr-guardian check` prints either nothing or exactly one
  JSON line carrying an `[adr-guardian]` `additionalContext` block. It is read-only on ADRs,
  spawns nothing, runs no model, and always exits 0. Two in-process steps go beyond counting
  files: `_stale_index_lines` (`bin/adr-guardian:460`) asks `adr_index_core` whether the three
  generated index artefacts still match the ADRs and adds a STALE line if not, and
  `_refresh_queue_if_stale` (`:415`) rebuilds the Proposed work queue cache through
  `adr_readiness.build_readiness_report` when the cache is missing or past its `expires_at` — so
  the queue that feeds the grill nudge and ADR-041's automatic handoff exists on a fresh clone
  without waiting for a sweep. Both fail silent. A cwd-guard silences `check` entirely when no
  `docs/adr/` with ADRs is reachable.
- **Nudge throttling and trend history** — `nudge_cooldown_hours` (default 24) suppresses repeat
  nudges; an append-only `trend` list capped at 52 entries carries drift and coverage numbers
  forward so the nudge can say `trend: drift 2 -> 0, coverage 40% -> 45%`.
- **Cross-process-safe state** — `.adr-kit-state.json` mutations go through
  `adr_state.update_state`, which takes an advisory lock (`fcntl` on POSIX, `msvcrt` on Windows)
  around a complete read-modify-write and finishes with an atomic `os.replace`. Corrupt state is
  tolerated as empty state with one stderr warning.
- **Sweep handoff channel** — `stamp --retire-seen '<json array>'` records which retirement
  candidates the in-session sweep already reported; the `/adr-kit:guardian` skill reads it back
  through `adr-guardian state` to suppress repeat nudges. The detector itself never reads it.
- **Copied-artifact staleness** — `_artifact_report` (`bin/adr-guardian:379`) compares the
  `ADR_KIT_WRAPPER_VERSION="X.Y.Z"` stamp in `.githooks/pre-commit` and `.git/hooks/pre-commit`,
  and the `_wrapper_version` on the guardian entry inside `.claude/settings.json`, against the
  installed plugin version. A stale artefact is itself a due item, so it surfaces even when both
  sweep tiers are fresh.

### Health reporting

- **Coverage dashboard** — `bin/adr-status --format table|markdown|json` computes `total`,
  `by_status`, `health_pct`, `avg_age_days`, `with_enforcement`, `enforcement_valid_pct`,
  `coverage_pct`, `llm_judge_pct`, and the three ADR-004 enforcement-floor buckets
  (`accepted_declarative`, `accepted_manual_review`, `accepted_no_enforcement`). Coverage is
  defined over **Accepted ADRs only**. `summary.coverage_pct` is the documented feed for
  `adr-guardian stamp --coverage`.
- **Four-signal retirement scoring** — `bin/adr-retire` scores each ADR as the unweighted mean of
  `staleness_90day`, `tech_removal`, `broken_supersession` and `policy_mismatch`, yielding
  `KEEP` / `MONITOR` (≥0.4) / `REVIEW` (≥0.6) / `RETIRE` (≥0.8). Only `broken_supersession` runs
  for non-Accepted statuses, so a Proposed ADR can score at most 0.25 and can never reach
  `MONITOR`.
- **Bounded, git-scoped tree scanning** — inside a git repository `_walk_repo_files` takes its file
  list from `git ls-files -z --cached --others --exclude-standard` (`_git_listed_files`,
  `bin/adr-retire:263`, 60 s timeout): tracked files plus untracked ones git does not ignore, so
  build output and caches no longer count as "technology still in use" (0.59.0). Outside a
  repository it falls back to `os.walk(followlinks=False)`, prunes ignored directories and
  directory links (including Windows junctions, `_is_dir_link`), refuses to descend into any
  directory containing a `.git` entry, and stops after 100,000 visited entries or 10 s. Both paths
  cap at `MAX_FILES = 50_000`. `_WALK_CACHE` memoizes on `(repo_root, frozenset(extensions))` and
  `main` resolves the union of every ADR's technology terms in a single pass — the ADR-015 fix
  that replaced N full-tree walks for N ADRs.
- **Retrieval health** — `adr_retrieval_health.run_retrieval_health` validates the project's
  declared retrieval probes against the generated ADR graph and flags Accepted binding ADRs that
  carry no selective-context metadata. Status is a deliberate trichotomy: `pass`, `fail` (a real
  finding), `degraded` (the index itself was missing, stale, invalid or an unsupported version, so
  no judgement was possible). That distinction is what lets hooks fail open while CI and the
  doctor report failure.

### Readiness and grilling

- **Seven-class deterministic readiness** — `adr_readiness.build_readiness_report` classifies each
  record as `not-an-adr`, `needs-human-input`, `needs-mechanical-fix`, `ready-for-confirmation`,
  `accepted`, `rejected` or `supersession-required`. The evaluation date is **injected**, every
  list is sorted, and the report is emitted with `sort_keys=True` — so the same repository,
  arguments and date produce byte-stable output. Each item carries the record's own `date` (latest
  status change, else the frontmatter date), which is what the queue ranks age by. Since 0.57.0 a
  required section that holds only a migration placeholder raises `SECTION_PLACEHOLDER_ONLY` and
  moves the record to `needs-human-input` (next command `/adr-kit:grill`); readiness still gains
  no exit-1 path.
- **Explicit implementation-link evidence** — `implementation_evidence` declares an ADR *linked*
  only when a changed path lies outside `docs/adr/` **and** one of three corroborations holds: the
  ADR id is cited in the diff text, the ADR file itself changed, or a `verified_in` target changed.
  Heuristics are never allowed to prove linkage; architecture-sensitive paths produce a separate,
  explicitly non-blocking `ARCHITECTURE_REVIEW_RECOMMENDED` advisory.
- **CI merge gate** — `bin/adr-readiness-ci` re-spawns `bin/adr-readiness --all-proposed
  --format json`, renders a GitHub Step Summary, emits `::error`/`::notice` annotations and five
  step outputs, and exits 1 when `summary.blocking_count` is truthy. All values pass through
  `github_escape` (`%`→`%25`, CR→`%0D`, LF→`%0A`) or `markdown_escape` first.
- **Bounded fail-open hook advisories** — `bin/adr-grill-signal` reads only the generated
  `ADR-INDEX.json` (refusing anything over 2 MiB), emits at most three signals per category, and
  prints `[adr-grill] STRONG …` / `[adr-grill] ADVISORY …` lines — the exact prefixes the
  pre-commit hook greps for before writing them to stderr with `|| true`.
- **Proposed-ADR work queue cache** — `adr_guardian_queue` ranks Proposed ADRs on a nine-key sort
  (linked, shipped, ready, open questions, needs human input, below quality threshold, age,
  quality score, id) with human-readable `reasons`. The `needs_human` signal (0.57.0) keeps a
  record that readiness honestly flags as unfinished in the queue, and its reason is placed before
  the unconditional `age N days` entry so it survives the `reasons[:2]` cut of the SessionStart
  block. It then persists at most three
  `/adr-kit:grill ADR-NNN` actions into the gitignored `docs/adr/.adr-kit-readiness.json` with a
  24-hour TTL, a 256 KiB ceiling and an explicit `"authoritative": false`. The writer uses an
  `"xb"` temp file plus `os.replace` with eight `PermissionError` retries — Windows AV/indexer
  hardening. This queue is the sole eligibility source for ADR-041's automatic grilling handoff;
  the handoff itself (`AUTO_GRILL_PENDING`, `grill.auto_start`) is emitted by the hook runtime in
  `agent-integration`, not here.

### Section substance (LLM tier)

- **`bin/adr-substance` asks whether a written section says anything** (0.58.0, TASK-203). The
  deterministic surfaces stop at markers: readiness and lint see a section that is missing, empty
  or holds an adr-kit placeholder, but "TBD", "see above" or three sentences of generic prose read
  as written to all of them. For each Proposed ADR with written, non-placeholder required
  sections it makes **one isolated call** to the host model, resolved through
  `adr_llm.resolve_llm_backend` (`bin/adr-substance:254`) — the same host-only registry the judge
  uses (ADR-036) — with `judge.llm_timeout_seconds` per call. The model must quote the vacuous
  text; a quote not found in the section is dropped, so every finding points at the author's own
  words.
- **On ADR-002's cadence, never per commit.** The `/adr-kit:guardian` skill runs it in the LLM
  tier and adds its `--estimate` line (call count, nothing spent) to the tier's cost prompt.
  It is deliberately kept out of `adr-readiness` (byte-stable, key-free report), out of the MCP
  server, and out of `adr-lint`.
- **Advisory and fail-open.** No recorded backend, a missing CLI or an unusable answer marks the
  run `degraded` and lists the unanswered ADRs; the exit code stays 0.

### Settings

- **`bin/adr-settings` is the one place to read and change every knob** behind
  `/adr-kit:settings`. Each row carries its provenance — project setting, machine-local setting,
  environment override (`ADR_KIT_NO_LLM`, `ADR_KIT_LLM_CMD`) or code default. Writes are routed
  by key: `lifecycle.signer` and `judge.host_client` (`LOCAL_KEYS`) go to the gitignored
  `docs/adr/.adr-kit.local.json`, everything else to the tracked `.adr-kit.json`, through a
  temp-file + `fsync` + `os.replace` write, after validation against
  `schemas/adr-kit-config.schema.json`. The default view lists the `FEATURED` keys, which include
  `grill.auto_start` (ADR-041's project-wide opt-out, 0.54.0) and the guardian cadence knobs.
  Not to be confused with `scripts/adr_settings.py`, the separate settings resolver the doctor
  imports.
- **Shell-quoting and injection hardening** — the grill-signal `normalize_path` scrubs control
  characters and rewrites `::` to `__` so a crafted filename cannot forge a workflow command or
  hook directive; `_quote` quotes for POSIX (`shlex.quote`) or PowerShell (single-quote doubling)
  and truncates at 4096 characters. The probe-file loader resolves the configured path and returns
  a `fail` payload rather than raising when it escapes the ADR directory.

### The doctor

- **ADR-set health engine** — `adr_doctor_core.run_doctor` (`bin/adr_doctor_core.py:205`) runs
  `adr-index --check` and `adr-lint --strict` as JSON subprocesses, resolves `verified_in` pointers
  (`commit:<sha>` via `git cat-file -e <sha>^{commit}`; `path:symbol` by substring), and emits up to
  seven finding types: `shipped_but_proposed` and `old_proposed` (Proposed ADRs — the latter gated
  by `doctor.proposed_stale_days`, default 30), `accepted_evidence_changed` (an Accepted ADR's
  `verified_in` target changed after acceptance, by mtime), `missing_gate` (from the lint
  consistency gate), `retrieval_probe_config` and `retrieval_probe` (a configured probe errored or
  failed), and `selective_context_metadata` at `FAIL` level. It escalates to a full
  `bin/adr-discover --root <repo_root>` subprocess (the deterministic missing-ADR candidate
  scanner; `adr_doctor_core.py:216`, still called through a function named `run_audit`) when a
  finding's type is in `MATERIAL_DRIFT_TYPES = {"accepted_evidence_changed", "missing_gate"}`. **The resulting exit code reports findings, not repair success**
  (`bin/adr_doctor_core.py:304`: `1 if index_code != 0 or lint_code != 0 or findings else 0`) — a
  bare `adr-doctor` run first regenerates the index (so `index_code` returns to 0) and can still
  exit 1 on the very same run, because none of the seven finding types above is something
  `--fix-index` repairs; a stale Proposed ADR or a missing gate needs a human decision, not a
  rewrite.
- **The doctor knows about generated client trees (ADR-032).** `generated_tree_owner(plugin_root)`
  and `client_root(plugin_root, client)` (`bin/adr_doctor_models.py:155`, `:174`) answer a question
  the doctor could not ask before: *is this tree a canonical payload root, or is it itself one
  client's mirrored install?* Identity is positive, not import-failure-shaped — a canonical root
  always carries `clients/workflows.json` (the generator's own input); its absence plus a
  client-specific plugin manifest (`.codex-plugin/plugin.json`, or `plugin.json` + `hooks.json` for
  Copilot) identifies a mirror and names which client owns it. `client_root` then re-roots every
  per-client check: in a canonical root each client owns a subdirectory (`codex/`, `copilot/`), but
  in a mirror there is exactly one client and it owns the root itself — `codex/.mcp.json`, not
  `codex/codex/.mcp.json`, a distinction whose absence used to make the doctor report six failures
  against paths that were never meant to exist. The owning client's checks run for real; the other
  two report `unsupported`, not `failed` — not broken, simply not installed there. `run_client_checks`
  (`bin/adr_doctor_checks.py:314`) consumes both through every `check_mcp_launcher`/
  `check_hook_package` call. The generated-adapters check is the sharpest edge: because the doctor's
  default mode repairs, and a mirror carries no canonical inputs to diff, `_generated_check`
  (`bin/adr_doctor_checks.py:223`) returns `unsupported` **before** importing the generator at all —
  `client_generation` is imported lazily (`:239`), only once a canonical root is confirmed,
  specifically so a repair-mode run in `codex/` or `copilot/` can never write into the tree it is
  inspecting.
- **Fast local client tier** — `adr_doctor_checks.run_client_checks` emits, in order:
  `generated-adapters` (drift of `codex/` and `copilot/` against the canonical inputs), `settings`,
  `project-guidance` (managed marker blocks in `AGENTS.md`, `CLAUDE.md`,
  `.github/copilot-instructions.md`, read as `utf-8-sig`), then per client a `native-client` /
  `mcp-launcher` / `hook-package` triple. `hook-package` requires the Python runtime
  `hooks/adr-hook.py` (plus `hooks/run-hook.cmd` outside Copilot) and nothing else.
- **Enumerated safe repairs** — default mode regenerates the index and, **only in an installed
  payload**, the client adapters. Since 0.59.0 a payload root that is a git checkout
  (`(plugin_root / ".git").exists()`, `bin/adr_doctor_checks.py:257`) gets adapter drift reported
  as `stale` with the `scripts/build-client-adapters.py` command instead of a rewrite — repair
  mode used to rewrite this repository's own `codex/` and `copilot/` from every test that ran the
  doctor without `--check`. `--fix` additionally authorises backed-up managed-guidance rewrites
  through `project_setup.collect_changes`/`apply_changes`. `--check` is the same diagnosis with
  every mutation suppressed.
- **Bounded deep probes** — `--deep` adds a 10 s native `<cli> plugin list` (through
  `clients.installer.bounded.run_bounded`, stdin closed), a 15 s four-message stdio MCP handshake
  against `bin/adr-mcp` that must see exactly the seven-tool set (0.53.0), and a 5-sample
  hook-latency harness via `hooks.hook_benchmark.measure`. The local model probe and its
  `.adr-kit/model-health.json` cache left the doctor with ADR-036's removal of the non-host judge
  backends; the doctor no longer judges model health at all. Every probe failure becomes a check,
  never an exception. The `hook-latency-extension` check (`bin/adr_doctor_probes.py:199`) reports
  `healthy` when `all_targets_met`, else `degraded`, `required: false`, and `unsupported` when the
  reference corpus is absent (`:166`) — which is every installed payload, since `tests/` is not
  shipped. Its budgets are ADR-030's, calibrated to the Python host that ships (below). Re-run live
  on this checkout after the recalibration: `adr-doctor --check --deep` reported
  `hook-latency-extension: healthy` with every event's p50/p95/hard-timeout target met — and the
  run's `overall_status` was still `failed`, from an unrelated `native-registration claude:
  trust-pending` (this machine's Claude CLI plugin needing a trust prompt). That is the signal
  ADR-030 restores: a specific, actionable finding about one client, not a permanent red that
  taught nobody to look.
- **Versioned report and single exit code** — `adr_doctor_models.check()` is the sole producer of
  the ten-key check object. Each check carries two independent axes: a `status` on an eight-value
  ladder (`STATUS_ORDER`, `bin/adr_doctor_models.py:10`, worst-to-best) — `failed` > `stale` >
  `trust-pending` > `degraded` > `repaired` > `disabled` > `unsupported` > `healthy` — and a
  `required` bool. `build_report` folds checks into a per-client rollup by taking the worst status
  on that ladder, an `overall_status` (`failed` if the exit code is set, else `degraded` if any
  check is `degraded`/`trust-pending`, else `repaired` if anything repaired, else `healthy`), and
  `exit_code = 1 if adr_exit_code or any required check is failed|stale`. `FAILURE_STATUSES =
  {failed, stale}` is deliberately a two-value set: `trust-pending` and `degraded` can turn
  `overall_status` red without ever failing the exit code, which is what lets ADR-032's
  `unsupported` sit two rungs *below* `failed` on the same ladder rather than needing a separate
  vocabulary — "not applicable here" and "broken" are different points on one ordering, not
  different types.

---

## Code Elements

The code-level documents were retired under TASK-149; their names are kept below as cluster
labels, not links. Every count and anchor in this document was re-measured against source at
v0.59.1.

| Cluster | Role in this component |
|---|---|
| `c4-code-bin-cli-lifecycle.md` | The five entry points that own the time dimension: `bin/adr` (the only sanctioned lifecycle writer, transactional with snapshot rollback), `bin/adr-guardian` (two-tier staleness detector + `.adr-kit-state.json` ledger + trend history), `bin/adr-status` (coverage dashboard), `bin/adr-retire` (four-signal retirement scorer), `bin/adr-doctor` (166-line argparse shell over the doctor libraries, carrying the TASK-62 `sys.path` hardening and the ADR-032 generated-tree import support). |
| `c4-code-bin-lib-doctor.md` | The whole of `adr-doctor`'s logic in four flat modules: `adr_doctor_core` (ADR-set health, index/lint/staleness/retrieval, escalation to `adr-discover`), `adr_doctor_checks` (fast local client tier + enumerated safe repairs), `adr_doctor_probes` (bounded deep tier: native CLI, MCP handshake, hook latency), `adr_doctor_models` (the versioned JSON contract, `check()`/`build_report()`/`render_human()` and the exit-code rule). |
| `c4-code-bin-cli-readiness.md` | The three thin readiness entry points: `bin/adr-readiness` (human/JSON/GitHub renderer and the component's de-facto internal RPC), `bin/adr-readiness-ci` (the CI merge gate — the only exit-1-on-findings path here), `bin/adr-grill-signal` (index-only fail-open hook advisories). 453 lines total; all classification lives in the libraries. |
| `c4-code-bin-lib-readiness-grill.md` | The deterministic engine behind readiness and grilling: `adr_readiness` (seven-class model + implementation-link evidence + placeholder findings), `adr_readiness_ci` (GitHub Step Summary, annotations, step outputs, escaping), `adr_grill_signal` (bounded index-only advisories), `adr_guardian_queue` (ranked Proposed queue + 24 h TTL cache), `adr_retrieval_health` (probe validation + selective-metadata findings, the pass/fail/degraded trichotomy). |
| [`bin/adr-substance`](../bin/adr-substance) | The guardian's LLM-tier section-substance check (310 lines). No code-level document ever covered it; placed here by `c4-component.md`'s census because the guardian skill is its only caller. |
| [`bin/adr-settings`](../bin/adr-settings) | The settings screen behind `/adr-kit:settings` (400 lines). Likewise placed here by the census. |

---

## Interfaces

### 1. `bin/adr` — lifecycle CLI

- **Protocol**: CLI, subprocess. Exit 0 success, 2 on any `AdrLifecycleError`.
- **Description**: The only sanctioned writer of ADR status transitions. Every mutation is a
  snapshot/apply/regenerate/rollback transaction that also covers the generated indexes.
- **Operations**:
  - `adr new <title> [--adr-dir DIR] [--date YYYY-MM-DD] [--changed-by WHO] [--reason TEXT] [--profile madr|nygard|canonical] [--config PATH]`
  - `adr profiles [--format human|json]`
  - `adr propose|reject <adr>`
  - `adr accept <adr> [--auto] [--auto-mode auto|assist] --confirm [--quality-threshold F] [--repo-root DIR]`
  - `adr answer <adr> --answer TEXT [--question <number|text>]`
  - `adr relate <adr> --to <other-adr> [--remove]`
  - `adr supersede <old> --by <new>`
  - `adr document <adr> --verified-in POINTER [--verified-in ...]`
  - `adr signer [--adr-dir DIR] [--set NAME] [--audit] [--suggest] [--format text|json]`
- **`--confirm` is required for `accept` since v0.45.0 (ADR-027, breaking).** Acceptance writes a
  signer and date into an immutable `## Status History` entry; the flag exists so that write is
  asked for rather than arrived at, and it blocks an accidental caller — a stale script, CI, an
  agent on an old instruction — without stopping a deliberate one. Omitting it exits 2 naming the
  signer that would have been written. `accept --auto` is exempt (spec R1's init-flow consent).
- **Stdout**: one line per performed action (`accepted: ADR-016-foo.md`).

### 2. `bin/adr-guardian` — detector CLI and SessionStart hook contract

- **Protocol**: CLI, plus a **host lifecycle-hook stdout contract**. Wired into a project through
  a `SessionStart` entry in `.claude/settings.json`, installed from
  `templates/cc-settings/guardian-hook-entry.json` — a shell one-liner that picks the newest
  `~/.claude/plugins/cache/rvdbreemen-adr-kit/adr-kit/*/` directory with
  `ls -d … | sort -V | tail -1`, probes `command -v python3 || python || py`, runs `check`, and
  swallows everything with `|| true` (timeout 10 s). If that pipeline yields nothing, the
  `[ -n "$ADR_KIT" ]` guard fails and the guardian silently does not run. GNU `sort -V` is the
  portability defect 0.59.1 removed from `templates/githooks/pre-commit` only; this entry still
  uses it, tracked as open bug TASK-220.
- **Description**: Read-only staleness detection and the write side of the sweep ledger.
- **Operations**: `check`, `stamp <cheap|llm> [--violations N] [--retire N] [--retire-seen JSON]
  [--lint STR] [--suggest N] [--audit N] [--coverage PCT] [--state-dir DIR]`, `state`,
  `artifacts [--format human|json]`, `refresh-readiness [--base REF --head REF] [--ttl-hours N]`,
  `retrieval-health [--probes-file PATH] [--format human|json]`.
- **Envelope**: when `CLAUDE_PLUGIN_ROOT` is set and `COPILOT_CLI` is not —
  `{"suppressOutput":true,"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[adr-guardian] …"}}`;
  otherwise the flat `{"suppressOutput":true,"additionalContext":"…"}`.
- **Exit codes**: **always 0** for every subcommand (a blanket `except Exception: return 0` at
  `bin/adr-guardian:1254-1257`); 2 only when no subcommand is given.

### 3. `bin/adr-status` — dashboard CLI and JSON contract

- **Protocol**: CLI + JSON on stdout.
- **Operations**: `adr-status [ADR_DIR] [--adr-dir DIR] [--format table|markdown|json] [--limit N]`.
- **JSON shape**: `{summary, adrs[], retirement_candidates[], retrieval}`. No schema file exists.
- **Exit codes**: 1 only for a missing ADR directory; otherwise `main() -> None` falls off the end
  and exits 0. **Report-only — it cannot signal "unhealthy".**

### 4. `bin/adr-retire` — retirement scorer CLI and JSON contract

- **Protocol**: CLI + JSON on stdout.
- **Operations**: `adr-retire [ADR_DIR] [--format text|markdown|json] [--threshold 0.0..1.0] [--config PATH] [--repo-root DIR]`.
  Inside a git repository the file set is `git ls-files --cached --others --exclude-standard`;
  the bounded walk is the fallback outside one.
- **JSON shape**: `[{adr_id, status, retirement_score, signals{staleness_90day, tech_removal, broken_supersession, policy_mismatch}, recommendation}]`, sorted by descending score then id.
- **Exit codes**: 0 / 2 on `RetireError`. A `RETIRE` recommendation is *not* a non-zero exit.

### 5. `bin/adr-doctor` — health gate CLI and JSON contract

- **Protocol**: CLI + JSON on stdout; **the only gating tool in this component that a developer
  runs locally**.
- **Operations**: `adr-doctor [ADR_DIR] [--repo-root DIR] [--plugin-root DIR] [--config PATH]
  [--global-settings PATH] [--stale-days N] [--format text|human|json] [--check] [--fix] [--deep]`.
  `--fix-index` is a hidden `argparse.SUPPRESS` alias.
- **JSON contract**: [`schemas/doctor-output.schema.json`](../schemas/doctor-output.schema.json) —
  `schema_version` const 1, `mode` `fast|deep`, checks `additionalProperties:false` over exactly
  ten keys, `exit_code` enum `[0,1]`, plus the flat legacy fields
  `adr_dir/repo_root/index/lint/findings/audit`. **Declared but never validated anywhere.**
- **Exit codes**: 0 / 1 from `report["exit_code"]` (`adr_doctor_models.build_report`:
  `1 if adr.get("exit_code") or required_failures else 0`). Two independent sources feed it, and
  neither is repair success: the ADR side's own `1 if index_code != 0 or lint_code != 0 or findings
  else 0` (`bin/adr_doctor_core.py:304`, seven finding types — see *The doctor* above), and any
  client-side check with `required: true` whose status is `failed`/`stale` — which includes
  adapter drift in a git checkout, now reported `stale` rather than repaired. **A bare `adr-doctor`
  run can regenerate the index, pass strict lint, and still exit 1** on the same run, because a
  stale Proposed ADR or a missing gate is a finding no repair touches — the exit code reports what
  was found, not what was fixed.

### 6. `bin/adr-readiness` — the component's de-facto internal RPC

- **Protocol**: CLI + JSON on stdout, consumed by three independent subprocess callers.
- **Operations**: `adr-readiness [ADR] [--all-proposed] [--diff] [--base REF --head REF]
  [--format human|json|github] [--repo-root PATH] [--adr-dir PATH] [--today YYYY-MM-DD]`.
  `--base`/`--head` must be supplied together and use triple-dot `base...head` (merge-base
  symmetric difference, matching GitHub PR diff semantics).
- **JSON contract**: [`schemas/adr-readiness.schema.json`](../schemas/adr-readiness.schema.json) —
  `schema_version` const 1; required per-ADR `adr_id, title, path, status, classification,
  mechanical_findings, human_findings, quality, implementation_link, next_command`.
- **Exit codes**: 0 on success **regardless of findings**, 2 on error, **never 1**. This is not a
  gate.
- **Subprocess consumers**: `bin/adr-readiness-ci` (30 s), `bin/adr-guardian refresh-readiness`
  (10 s), `bin/adr-mcp` `tool_adr_readiness` (60 s). Any change to this JSON breaks three callers
  at once. A fourth consumer reads the same report shape in-process: `adr-guardian check`'s queue
  refresh calls `adr_readiness.build_readiness_report` directly.

### 7. `bin/adr-readiness-ci` — CI merge gate and GitHub Actions contract

- **Protocol**: CLI, plus the **GitHub Actions runner contract** (`$GITHUB_STEP_SUMMARY` and
  `$GITHUB_OUTPUT` appends, `::error`/`::notice` workflow commands on stdout). Wrapped by the
  composite action [`.github/actions/adr-readiness/action.yml`](../.github/actions/adr-readiness/action.yml)
  (inputs `adr-dir`, `base`, `head`, `python-version` default 3.11) and consumed by
  [`.github/workflows/adr-readiness.yml`](../.github/workflows/adr-readiness.yml).
- **Operations**: `adr-readiness-ci --base REF --head REF [--repo-root PATH] [--adr-dir PATH]
  [--today YYYY-MM-DD] [--summary-file PATH] [--output-file PATH]`. Always runs the child with
  `--all-proposed`.
- **Step outputs** (sorted `key=value`, CR/LF stripped): `blocking-count`, `blocking-adrs`
  (compact JSON array), `advisory-count`, `schema-version`, `conclusion`
  (`blocked` | `advisory-or-clean`).
- **Exit codes**: 0 clean-or-advisory, **1 blocking**, 2 infrastructure failure (also emitted as
  `::error title=ADR readiness infrastructure::`). The 0/1/2 split is what lets a workflow
  distinguish "your PR is blocked" from "the check itself broke".

### 8. `bin/adr-grill-signal` — git-hook stdout line contract

- **Protocol**: CLI, invoked from `templates/githooks/pre-commit:317-322`, which pipes its output
  through `grep -aE "^\[adr-grill\] (STRONG|ADVISORY) "` to stderr and discards the exit status
  with `|| true`.
- **Operations**: `adr-grill-signal [--repo-root PATH] [--index PATH] [--staged]
  [--paths P ...] [--source-text TEXT] [--shell posix|powershell] [--format human|json]`.
- **JSON shape**: `{schema_version: 1, linked_proposed[], suspected_decisions[], signal_count}`.
  No schema file.
- **Exit codes**: **0 always** on the success path, 2 on error. Prints nothing when the report is
  empty.

### 9. `adr_readiness` MCP tool (served by another component, backed by this one)

- **Protocol**: JSON-RPC 2.0 over stdio, `tools/call`. The tool is *defined* in `bin/adr-mcp`
  (`:309` schema, `:667` handler) — the MCP component — and *implemented* by spawning
  `bin/adr-readiness --format json` from this component. There is no import-level coupling.
- **Arguments**: `adr_id?`, `all_proposed?`, `base?`+`head?` (together), `today?`, plus the shared
  `project_root`/`adr_dir` workspace pair.
- **Guarantee**: readiness only, no lifecycle mutation. ADR-011's Enforcement block pins a
  `require_pattern` on the literal `adr_readiness` in `bin/adr-mcp` to keep the tool present.
  `bin/adr-status` is exposed the same way (as is `bin/adr-quality`, from `enforcement-engine`);
  `bin/adr` is deliberately not — ADR-040 admits only read-only deterministic tools, and
  `adr-substance` stays out for the same reason.

### 10. MCP *client* interface (doctor deep probe)

- **Protocol**: JSON-RPC 2.0 over stdio, this component acting as the **client**.
- **Description**: `adr_doctor_probes._mcp_deep` spawns `python bin/adr-mcp` and drives a
  four-message session with a 15 s timeout: `initialize` (protocolVersion `2025-06-18`, clientInfo
  `adr-doctor/1`), `notifications/initialized`, `tools/list`, `tools/call adr_status`.
- **Contract**: `healthy` requires exit 0, a non-error tool result, and a tool set **exactly equal**
  to `{adr_context, adr_judge, adr_status, adr_quality, adr_readiness, adr_lint, adr_related}` —
  set equality, not containment, so the probe fails on a missing *or* an unexpected tool. The
  installer smoke test checks the same seven-tool set (0.53.0).

### 11. JSON file contracts on disk

| File | Producer | Consumers | Shape / bounds |
|---|---|---|---|
| `docs/adr/.adr-kit-state.json` (+ `.lock` sibling; gitignored, per-machine) | `adr-guardian stamp`, `check` (only `last_nudged`) | `adr-guardian check`/`state`, the `/adr-kit:guardian` skill | `{cheap_tier{last_run,drift_violations,retire_candidates,lint}, llm_tier{last_run,suggest_hits,audit_findings}, retire_seen[], last_nudged, trend[≤52]}` |
| `docs/adr/.adr-kit-readiness.json` (gitignored) | `adr-guardian refresh-readiness`, and `adr-guardian check` when the cache is missing or expired → `adr_guardian_queue.write_queue_cache` | `hooks/adr_hook_core.py:238` (`_load_queue_payload`, feeding the SessionStart queue context and ADR-041's `AUTO_GRILL_PENDING` handoff), `adr-guardian check`'s own expiry test, `adr_guardian_queue.load_queue_actions` (tests only) | `schema_version 1`, ≤3 actions, 24 h TTL, ≤256 KiB, `"authoritative": false`, commands matched against `^/adr-kit:grill ADR-\d{3,4}$` |
| `docs/adr/.adr-kit.local.json` (gitignored, per-machine) | `adr-settings --set` for `LOCAL_KEYS` (`lifecycle.signer`, `judge.host_client`), `bin/adr signer --set` | `bin/adr`'s signer resolution, `adr-substance` through `adr_llm`, `adr-settings` | Nested JSON in the same layout as `.adr-kit.json`; ADR-025 keeps machine facts out of the tracked file. |
| `docs/adr/adr-context-probes.json` | hand-authored per project | `adr_retrieval_health.load_probes` | [`schemas/adr-context-probes.schema.json`](../schemas/adr-context-probes.schema.json), `schema_version` const 1, ≤100 probes, ≤20 expectations each |

### 12. Configuration contract — `docs/adr/.adr-kit.json`

Validated against [`schemas/adr-kit-config.schema.json`](../schemas/adr-kit-config.schema.json).
Blocks this component reads:

- `guardian`: `enabled` (true), `drift_stale_days` (1), `llm_stale_days` (14),
  `nudge_cooldown_hours` (24), `llm_autorun` (false)
- `retirement`: `threshold_days` (90), `check_supersession`, `check_tech_removal`,
  `check_policy_mismatch`
- `lifecycle.auto_accept`: `mode` (`assist`), `quality_threshold` (0.70)
- `doctor.proposed_stale_days` (default 30)
- `context.probes_file`, `context.retrieval_completeness` (`off|advisory|strict`, default
  `advisory`)
- `template.profile` (for `adr new`)
- `judge.backend`, `judge.llm_timeout_seconds` (read by `adr-substance` for its per-ADR call)
- every schema key, through `adr-settings`, which also writes them; `grill.auto_start` is shown
  there but read by the hook runtime, not by this component

`bin/adr-guardian` reads it through the **fail-open** `adr_config.load_json_config` (returns `{}`
on any problem), not the fail-closed `load_validated_config` the pre-commit judge uses.

### 13. Importable Python surface

The 9 `.py` modules are importable once `bin/` is on `sys.path`; the doctor modules additionally
require `<root>` and `<root>/scripts` on the path because they import from `scripts/`. There is no
`bin/__init__.py`.

- `adr_readiness.{build_readiness_report, readiness_for_record, implementation_evidence, architecture_advisories, explicit_adr_ids, normalize_path, ReadinessError}`
- `adr_readiness_ci.{render_summary, output_values, write_outputs, annotations, github_escape, markdown_escape}`
- `adr_grill_signal.{analyze_index, normalize_path, MAX_SIGNALS}`
- `adr_guardian_queue.{rank_proposed, build_queue_cache, write_queue_cache, load_queue_actions, QUEUE_CACHE_NAME}`
- `adr_retrieval_health.{load_probes, evaluate_probes, run_retrieval_health, render_retrieval_health, ProbeConfigError}`
- `adr_doctor_core.{run_doctor, render_text}` — `run_doctor` takes a **duck-typed argparse
  Namespace**, not keyword arguments
- `adr_doctor_checks.{run_client_checks, check_mcp_launcher, check_hook_package, resolve_launcher_target}`
- `adr_doctor_probes.run_deep_extensions` (plus `_mcp_deep` and `_native_deep`, imported by
  `tests/test_client_doctor.py:26` despite the underscore)
- `adr_doctor_models.{check, benchmark_extension, build_report, render_human, generated_tree_owner, client_root}`

The 10 extensionless entry points expose `main()` (and `build_parser()` in `bin/adr-readiness`)
in form only. Tests reach `extract_status`, `compute_summary`, `find_retirement_candidates`,
`score_adr`, `detect_*`, `mutate_status`, `append_status_history` and `_compute_due_tiers` through
`SourceFileLoader`; nothing else does.

### 14. `bin/adr-substance` — LLM-tier advisory CLI

- **Protocol**: CLI + optional JSON on stdout; one host-CLI subprocess per checked ADR, through
  `adr_llm` (prompt on stdin, the host client's own model).
- **Operations**: `adr-substance [--adr-dir DIR] [--adr ADR-NNN] [--estimate] [--json]
  [--llm-cmd CMD] [--llm-timeout S]` (`bin/adr-substance:214-222`). `--estimate` prints the call
  count and spends nothing.
- **JSON shape**: `{checked[], findings[{adr, heading, quote, reason}], unanswered[], degraded}`.
  No schema file.
- **Exit codes**: 0 whenever it ran, including with findings or degraded for want of a backend;
  2 on a configuration or input error. **Advisory only.**
- **Caller**: the `/adr-kit:guardian` skill's LLM tier. Nothing in a commit path calls it.

### 15. `bin/adr-settings` — settings CLI

- **Protocol**: CLI + optional JSON on stdout; writes `.adr-kit.json` or `.adr-kit.local.json`.
- **Operations**: `adr-settings [--adr-dir DIR] [--format text|json] [--all] [--list]
  [--set KEY=VALUE | --unset KEY]`.
- **JSON shape**: `{adr_dir, settings[]}` for the view, `{result[]}` for a write.
- **Exit codes**: 0 on success, 2 on an unknown key, invalid value, `--set`/`--unset` together, or
  an unwritable config (`SettingsError`).
- **Caller**: the `/adr-kit:settings` skill.

---

## Dependencies

> Sibling *component* slugs were not supplied to this synthesis. Each dependency below is named by
> its authoritative Code-phase cluster slug, with the likely component name in parentheses.

### Components used

| Dependency | Mechanism | What is used |
|---|---|---|
| `bin-lib-semantic-core` (Semantic Core) | **Python import** | `adr_format` (`SUPPORTED_PROFILES`, `profile_catalog`, `profile_template_path`, `configured_profile`, `normalize_profile`, `unresolved_open_questions`, `section_text`); `adr_schema` (`migrate_text`, `parse_frontmatter`, `render_frontmatter`, `split_frontmatter`); `adr_catalog` (`adr_status`, `ENFORCEMENT_BLOCK_RE`, `ADR_FILENAME_RE`, `load_adr_records`, `build_relationships`, `normalize_adr_id`); `adr_query` (`load_index_graph`, `query_records`, `IndexQueryError`) via `adr_retrieval_health`. `bin/adr-status` imports `adr_catalog.adr_status` **specifically so the dashboard reports the same status `adr-judge` acts on**. |
| `bin-lib-runtime` (Runtime Safety) | **Python import** | `adr_config.load_json_config` (fail-open config read) and `adr_state.{find_project_adr_dir, load_state, update_state}` (advisory-locked, fsync'd, atomically replaced state transactions). `adr-substance` additionally loads `adr_llm` (`enforcement-engine`), the host-only backend registry of ADR-036, so its model calls resolve exactly as the judge's do. |
| `bin-cli-gates` (Verification Gates) | **Subprocess** (`sys.executable`), plus one **direct Python import** | `bin/adr-lint --strict --gates schema,completeness,audit,evidence,clarity,consistency,policy` for acceptance (`bin/adr:724`) and `--strict` for the doctor's ADR tier; `bin/adr-quality --format json` for the `accept --auto` threshold, both under the 120 s lifecycle timeout. Separately, `adr_readiness.py` imports `adr_quality_core.{QUALITY_THRESHOLD, score_path}` directly to populate the `quality`/`below_threshold` fields of its own JSON report — the one place in this component that reaches a gates module in-process rather than through a subprocess. |
| `bin-cli-retrieval` (Retrieval and Context) | **Subprocess**, plus one **in-process import** | `bin/adr-index` inside every lifecycle transaction (`run_index`, `bin/adr:478`) and in the doctor's default mode; the doctor's `adr-index --check` freshness gate. `adr-guardian check` loads `adr_index_core` in-process for its read-only stale-index nudge. `bin/adr-grill-signal` and `adr_retrieval_health` **read the artefact** this component produces: `docs/adr/ADR-INDEX.json`. |
| `bin-cli-enforcement` (Enforcement Floor) | **Subprocess, orchestrated by the agent** | `bin/adr-judge` is the cheap-tier drift tool and, with `--llm`, the LLM-tier audit tool. This component never spawns it: the `/adr-kit:guardian` skill runs it and reports counts back through `adr-guardian stamp --violations N` / `--audit N`. |
| `bin-cli-mcp` (MCP Server) | **Subprocess, bidirectional** | *Outbound*: `adr_doctor_probes._mcp_deep` spawns `bin/adr-mcp` as an MCP client. *Inbound*: `bin/adr-mcp` spawns `bin/adr-readiness` and `bin/adr-status` to serve two of its seven tools. Coupling is purely process-level in both directions. |
| `hooks` (Hook Integration) | **Python import + JSON file on disk** | *Import*: `adr_doctor_probes` does `from hooks.hook_benchmark import measure` for the latency extension. *File*: `hooks/adr_hook_core.py:238` (`_load_queue_payload`) **independently re-implements a reader** for this component's `.adr-kit-readiness.json` queue cache, and turns its top action into the SessionStart queue context and ADR-041's automatic grill handoff. |
| `agent-surface` (Agent Instruction Surface) | **Prose orchestration** | `skills/guardian/SKILL.md` is the in-session smart sweep: it reads `adr-guardian state`, runs the due tier's tools across four components, diffs fresh retire candidates against `retire_seen`, then calls `adr-guardian stamp` and `adr-guardian refresh-readiness`; in the LLM tier it also runs `adr-substance` after folding its `--estimate` line into the cost prompt. `skills/settings` drives `adr-settings`. `clients/workflows.json` (the grill workflow) instructs agents to run `bin/adr-readiness` before asking a question. |
| `packaging-ci` (Packaging and Release) | **Python import — a layering inversion** | `bin/adr_doctor_checks.py` imports `scripts/adr_settings.py` (`resolve_settings`, `SettingsError`), `scripts/client_generation.py` (`generate`, `GenerationError`, imported lazily at `bin/adr_doctor_checks.py:239`) and `scripts/project_setup.py` (`validate_markers`, `collect_changes`, `apply_changes`, `SetupError`). `bin/` depending on `scripts/` is inverted layering, made possible only by `bin/adr-doctor:56-58` appending the repository root and `scripts/` to `sys.path` (and masking its own `bin/` entry during the import block). |
| `clients-installer` (Client Installation) | **Python import** | `clients/installer/detection.py` (`detect_clients`), `clients/installer/contracts.py` (`CLIENT_IDS = ("claude","codex","copilot")`) and `clients/installer/bounded.py` (`run_bounded`, the deep tier's `plugin list` runner). The doctor is the *measurement* surface for what the installer *builds*. |
| `schemas-templates` (Contracts and Templates) | **Data files read at runtime** | `schemas/adr-readiness.schema.json`, `schemas/adr-context-probes.schema.json`, `schemas/adr-kit-config.schema.json`, `schemas/doctor-output.schema.json` (declared, unenforced); `templates/cc-settings/guardian-hook-entry.json` (the SessionStart wiring this component's `check` is installed by); `templates/githooks/pre-commit` (the wrapper whose `ADR_KIT_WRAPPER_VERSION` stamp `adr-guardian artifacts` reads); `templates/adr-template.{madr,nygard,canonical}.md` (instantiated by `adr new`). |
| `generated-distributions` (Generated Client Payloads) | **Drift check** | All 19 files of this component exist as byte-identical generated mirrors under `codex/bin/` and `copilot/bin/` (all 19 verified with `cmp` at v0.59.1). The doctor's `generated-adapters` check verifies those copies — so the check is **self-referential**: the doctor confirms its own copies match itself, and any edit here requires re-running `scripts/build-client-adapters.py`. The compare ignores line-ending differences in text files (TASK-57). |
| `tests` (Test and Certification Suite) | **Import + subprocess, inbound** | This is the component's *only* mechanical guard: `tests/test_cli_performance.py` enforces the ADR-015 latency budget for `adr-retire`, and `tests/test_adr_retrieval_health.py` is named in ADR-014's `verified_in`. See *Measurement honesty* 1. |
| **`bin/adr-discover`** | **Subprocess** | `adr_doctor_core.run_audit` shells out to `bin/adr-discover --root <repo_root>` on material drift (`bin/adr_doctor_core.py:216`). `bin/adr-discover` (546 lines, the deterministic missing-ADR candidate scanner that used to be named `adr-audit`) is claimed by no component document; `c4-component.md` lists it in its census gap. The current `bin/adr-audit` is a different tool — the lint-plus-judge "are we still on course" run — and this component does not call it. |

### External systems

- **`git` CLI** — read-only verbs only. `git diff --name-only -M` / `--unified=0 -M` (10 s in
  `adr-readiness`, 5 s in `adr-grill-signal`), `git -C <root> cat-file -e <sha>^{commit}` for
  `commit:` pointer resolution in the doctor, and `git ls-files --cached --others
  --exclude-standard` (60 s) for `adr-retire`'s file set. `bin/adr` reads `git config user.name`
  to derive a signer. No mutating verb anywhere in the component.
- **Filesystem** — the substrate and, importantly, a *signal*: `pointer_changed_after` uses
  `os.path.getmtime`, so file mtimes are load-bearing (see finding 8). Also: advisory locking
  (`fcntl.flock` / `msvcrt.locking`), `os.fsync`, `os.replace`, `os.walk` over the whole consuming
  repository.
- **GitHub Actions runtime** — `$GITHUB_STEP_SUMMARY` and `$GITHUB_OUTPUT` append targets,
  `::error`/`::notice` workflow commands. Consumed by `.github/workflows/adr-readiness.yml` via the
  composite action.
- **GitHub API via the `gh` CLI** — used by the two report-only cron workflows that drive this
  component's tools: `.github/workflows/adr-guardian-audit.yml` (weekly cheap-tier sweep →
  single "ADR guardian audit" tracking issue) and `.github/workflows/adr-retire-audit.yml`
  (`adr-retire --threshold 0.4` → tracking issue). Both always exit 0 and need no secret beyond
  `GITHUB_TOKEN`.
- **`claude` / `codex` / `copilot` CLIs, two roles** — the doctor detects them and probes
  `plugin list` (10 s) under `--deep` only; all three are optional, and absence yields
  `unsupported`, not failure. Separately, `adr-substance` runs the recorded host client's
  non-interactive entry point (`claude -p`, `codex exec` or `copilot -p`, from
  `judge.host_client` or `ADR_KIT_LLM_CMD`/`--llm-cmd`) once per checked ADR. **No file in this
  component opens a network socket itself**; whatever network the host CLI uses is the host's.
- **Agent host runtimes** (Claude Code CLI, Codex CLI, GitHub Copilot CLI) — consume
  `adr-guardian check`'s SessionStart envelope and the `[adr-grill]` stderr lines.
  OpenCode is not probed by this certified native doctor; its separate plugin can
  consume the shared MCP and hook engines, but ADR-039 does not extend the
  installer or doctor contract.
- **One model caller, off every hot path.** `bin/adr-substance` is the only file in this
  component that asks a model anything, and only when the guardian skill's LLM tier runs it. The
  guardian's "LLM tier" is otherwise a *cadence label*: the detector says the tier is due, and the
  in-session model runs `adr-suggest`, `adr-judge --llm` and `adr-substance` itself. `bin/adr-guardian`,
  the readiness engine, the doctor and the lifecycle writer invoke no model. `ADR_KIT_NO_LLM` is
  read by the pre-commit template and the judge, and only *displayed* here by `adr-settings`;
  `adr-substance` does not check it (verified: neither `bin/adr-substance` nor
  `adr_llm.resolve_llm_backend` reads it), so turning the tier off is the guardian skill's call.

---

## Governing ADRs

Verified against the ADR sources and every Enforcement block in `docs/adr/`.

| ADR | Status | How it governs | Mechanically enforced here? |
|---|---|---|---|
| **ADR-002** — ADR Guardian: SessionStart Staleness Detector with Two-Tier Cadence | Accepted 2026-05-31, `binding: false` | Names `bin/adr-guardian check` as the dumb SessionStart detector plus in-session smart sweep, and names `adr-retire`/`adr-lint`/`adr-status` as the cheap-tier tools (ADR-002:54, :64, :74). Defines `.adr-kit-state.json` as gitignored per-machine state with independent tier clocks. Its cadence is also what bounds `adr-substance`: semantic checks run in the LLM tier, never per commit. | No. Enforcement block present with empty rule arrays. |
| **ADR-004** — Layered ADR Context Injection for Agent Work | Accepted | Its **session tier *is*** `bin/adr-guardian check` (ADR-004:67). Its three fail-open tiers / one fail-closed floor model is why every read path here exits 0 and why the floor lives in `bin/adr-judge` instead. The three enforcement-floor buckets `adr-status` reports are this ADR's model. Its "pin canonical fields" clause fixes the `entries[-1]` status reconciliation the readers use. | No. Enforcement block present with empty rule arrays. |
| **ADR-010** — Certify Three Native CLI Clients Through One Outcome Contract | Accepted 2026-07-23, `binding: true`, gate `three-client-release` | Names `bin/adr-doctor` as the measurement surface (ADR-010:73, :413) and dictates the doctor almost clause by clause: fast tier uses local files and cached health only; both tiers may repair an enumerated set of safe ADR-Kit-owned state; `--check` is the same diagnosis without mutation; `--fix` adds backed-up managed rewrites; deep probes must be bounded; a missing/ambiguous/unreachable/rejected model must never read as successful judgment (the doctor now satisfies that clause by not judging model health at all). Requires that the per-event hook latency budgets the `hook-latency-extension` checks be honest numbers — ADR-030 is the ADR that made them so. | No — its `require_pattern`s glob `schemas/client-capabilities.schema.json`, not `bin/`. |
| **ADR-011** — Adopt Deterministic Readiness and Human-Gated Grilling | Accepted 2026-07-20, `binding: false` | Directly defines the readiness boundary: a shared stdlib-only read-only engine, the seven classification values implemented verbatim in `READINESS_CLASSES`, stable ordering under an injected date, hooks emitting only short fail-open advisories with an exact grill command, CI needing "no secret or model", and CI blocking **only** on explicit inspectable evidence of a linked implemented Proposed ADR. Its warm p95 targets: 500 ms single-record CLI, 1 s all-Proposed over 50 records, ≤100 ms MCP adapter overhead, ≤5 s PR action overhead. | Only indirectly — its `require_pattern`s glob `clients/workflows.json` and `bin/adr-mcp`. Nothing guards the read-only or fail-open posture of the readiness files themselves. |
| **ADR-014** — Use the Generated ADR Graph as the Selective-Context Query Engine | Accepted 2026-07-23, `binding: true`, gate `index-first-retrieval` | Governs `adr_retrieval_health.py`: probes run through the one shared engine, a historical-authority result is itself a failure, and the `degraded` status implements ADR-014's "missing, invalid, unsupported or stale graph handling will be explicit and observable". Its `verified_in` names `tests/test_adr_retrieval_health.py` directly. Also governs `adr_grill_signal`'s index-only posture. | No — its declarative rule arrays are deliberately empty; the gate is enforced by tests. |
| **ADR-015** — Enforce a Two-Second Deterministic Latency Budget as a Test Fixture Contract | Accepted 2026-07-26, `binding: true`, gate `adr-kit-cli-latency-v1` | Its frontmatter `components` lists **`adr-retire`** and its `symbols` list `resolve_present_terms` and `_WALK_CACHE` — both in this component. `tests/fixtures/cli/latency-corpus.json` carries the measured budget `adr-retire: p50 800 ms / p95 1200 ms / hard 2000 ms`, with the recorded root cause "walked the full repository once per ADR from `detect_tech_removal`; now one memoized walk plus one single-pass term resolution per run". Its 2000 ms ceiling is also the constraint every ADR-030 hook budget below stays under. | Not by the judge — its `require_pattern` globs the fixture file, so the budget is guarded by `tests/test_cli_performance.py`. |
| **ADR-027** — Derive the Lifecycle Signer From a Person-Named Git Identity, Announced | Accepted 2026-08-04, `binding: true`, gate `adr-signer-derivation-v1` | Governs `bin/adr`'s signer machinery directly: `resolve_signer`'s four-step order, the mandatory stderr announcement of a derived name, the machine-identity denylist in `person_shaped`, the machine-local (never repository-tracked) `lifecycle.signer`, and the `signer --suggest` read-only proposal. It is also why `--confirm` matters: acceptance most often signs with a *derived* name, which is exactly the value a human has not yet agreed to. | No Enforcement block in the ADR at all — the invariants are held by `tests/test_adr_signer_discovery.py` alone. |
| **ADR-030** — Recalibrate the Hook Latency Budgets to the Python Host That Actually Ships | Accepted 2026-08-05, `binding: true`, gate `adr-hook-python-budgets-v1` | Rewrites every `latency` block in `hooks/manifest.json` from measurement against the Python host, replacing budgets calibrated for the native binary ADR-029 retired. Directly names the visible cost this component carries: `bin/adr_doctor_probes.py`'s `hook-latency-extension` check reported `degraded` on every platform, every run, before this ADR, because three events declared a 100 ms hard timeout against a measured 182.6 ms bare-interpreter floor (`MEASURED_INTERPRETER_FLOOR_MS`, `hooks/hook_benchmark.py:51`) — no hook-side optimisation could ever have met them. | No — empty rule arrays; guarded by `tests/test_hook_performance.py` against the recorded corpus. |
| **ADR-041** — Automatically Hand Off Unfinished Proposed ADRs to Interactive Grilling | Accepted 2026-08-20, `binding: false`, no gate | Makes this component's readiness engine and `adr_guardian_queue` "the sole source of eligibility" for the automatic handoff; the hook runtime (another component) dispatches at most one candidate per session at a user-visible prompt. It is why `adr-guardian check` now prepares the queue itself and why the `needs_human` signal must keep an honestly flagged record enrolled. `grill.auto_start: false` is the project-wide opt-out, shown by `adr-settings`. | No — no `## Enforcement` section and an empty `verified_in`; the ADR names deterministic readiness and queue fixtures as its verification. |
| **ADR-032** — Treat a Generated Client Tree as a First-Class Doctor Context | Accepted 2026-08-05, `binding: true`, gate `adr-doctor-generated-tree-v1` | Directly defines `generated_tree_owner`/`client_root` (`bin/adr_doctor_models.py:155`, `:174`) and the resulting `_generated_check` short-circuit in `adr_doctor_checks.py` — the positive-identity rule, the per-client re-rooting, the `unsupported`-not-`failed` posture for a client not installed in a mirror, and the lazy, guarded import of `client_generation` so a repair-mode run in a mirror can never write into it. Names `bin/adr-doctor` as ADR-010's measurement surface, applied to the codex/copilot mirrors specifically. | No — empty rule arrays; guarded by `tests/generated_tree_imports.py`'s transitive import-closure walk and a before/after SHA-256 snapshot test. |

Not governing, verified: **ADR-005** supplies the profile registry `adr new --profile` consumes
(contract-level only); **ADR-001** is an *inherited* constraint (no model on a hook hot path) that
explains `_model_fast` reading a cache and `_model_deep` only talking to loopback, but its own
Decision never mentions the doctor; **ADR-007** constrains the produced `ADR-INDEX.json` artefact,
not its readers here; **ADR-009** is scoped to `bin/adr-lint` yet mentions `bin/adr accept` and
constrains the seven-gate set `_assert_acceptance_gates` invokes. **ADR-016** (Accepted
2026-07-30) and **ADR-040** govern `bin/adr-mcp`, not this component; the doctor's deep probe only
mirrors the seven-tool surface ADR-040 admits. **ADR-036** governs the judge's backend registry
that `adr-substance` borrows. **ADR-029** (Accepted 2026-08-04) governs `hooks/`, not this
component; its native hook binary was removed in 0.55.1, so `hook_benchmark.host_command` now
returns the Python host unconditionally and the budgets ADR-030 recalibrated are the only ones
that exist.

---

## Notable findings carried forward

### Component-boundary surprises

1. **Two independent, non-communicating retirement detectors live inside this one component.**
   `bin/adr-status:412 find_retirement_candidates` (Superseded/Deprecated → high; Proposed >365 d →
   medium; Accepted >730 d without Enforcement → low) and `bin/adr-retire:406 score_adr` (four-signal
   mean, configurable 90-day threshold, KEEP/MONITOR/REVIEW/RETIRE) answer the same question with
   different heuristics, thresholds and vocabularies, share no code, and neither imports the other.
   ADR-002:74 names `adr-retire` as the cheap-tier retirement tool and the sweep stamps `--retire N`
   from it, so `adr-status`'s candidate list is **display-only and feeds nothing downstream**. This
   is the most architecturally surprising thing in the component.
2. **Two independent SessionStart producers, neither aware of the other.** The plugin-level hook
   routes SessionStart to `hooks/adr-hook.py`, which reads *this component's* readiness queue cache
   itself (`hooks/adr_hook_core.py:238`) and emits Proposed-ADR advisories and, at the next
   user-visible prompt, ADR-041's automatic grill handoff. The `[adr-guardian]`
   health nudge can only come from `bin/adr-guardian check`, reached via a **project-scoped**
   `.claude/settings.json` entry. Zero files under `hooks/` reference `adr-guardian`. Both feed the
   same session from different producers — and since `check` refreshes the queue, the guardian
   entry is also what keeps the hook's queue warm on a fresh clone. A session without that
   project-scoped entry gets neither the nudge nor the automatic refresh.
3. **One JSON contract, three independent readers.** The queue cache is read by
   `adr_guardian_queue.load_queue_actions` (**no production consumer — tests only**), by
   `hooks/adr_hook_core.py:238` (`_load_queue_payload`, which also enforces `schema_version` and
   the 256 KiB ceiling), and by `adr-guardian check`'s own expiry test before it decides to
   rebuild. All three now honour the payload's own `expires_at`, so the freshness rule is single;
   the parsing is still three separate implementations of one contract.
4. **Readiness is Markdown-first while grill-signal and retrieval-health are index-first.** The same
   concepts are therefore read from differently shaped records: readiness uses `record["verified_in"]`
   and a flat `record["scope"]` glob list; the index path uses `record["metadata"]["verified_in"]` and
   `record["scope"]["path_globs"]`. The implementation-linkage rule consequently exists in two places
   (`adr_readiness.py:122` and `adr_grill_signal.py:50`), with `_ARCHITECTURE_PATH_RE` and
   `_SENSITIVE_RE` character-identical but independently defined. The two have already diverged in
   one observable way: `adr_grill_signal.py:76` compares `Path(path).name == record["path"]`
   exactly while `adr_readiness.py:149-151` casefolds both sides, so on a case-insensitive filesystem
   a differently-cased diff path yields `ADR_FILE_CHANGED` from readiness but not from the hook
   signal. Fail-open — a missing advisory, never a false block.
5. **`normalize_path` exists twice with different semantics, and the injection defence is on the
   wrong side of the boundary.** `adr_readiness.py:108` only folds separators;
   `adr_grill_signal.py:24` also strips control characters and maps `::`→`__`. The `::` defence —
   which prevents forging a GitHub workflow command — lives in the module that prints to *hook
   stderr*, while the module that actually emits `::error`/`::notice` relies on a separate
   `github_escape`. Importing the wrong `normalize_path` silently weakens the defence.
6. **The cadence ledger is strictly local.** `.github/workflows/adr-guardian-audit.yml` runs the
   cheap tier's *tools* (`adr-lint` + `adr-retire` + `adr-status`) but never invokes
   `bin/adr-guardian` itself — there is no state file in CI, by design, since it is gitignored and
   per-machine. Team-mode visibility is a tracking issue, not a shared clock.

### Gating and exit codes

 1. **Ten entry points, five exit-code conventions.** Anything scripting this component needs the
   distinction: `bin/adr` 0/2; `bin/adr-guardian` **never non-zero** for any subcommand (blanket
   `except Exception: return 0`, so scripting callers of `state`/`artifacts`/`refresh-readiness`
   cannot distinguish failure from success); `bin/adr-status` 0 implicit, 1 only for a missing
   directory — it *cannot* report "unhealthy"; `bin/adr-retire` 0/2 with a `RETIRE` score still
   exiting 0; `bin/adr-doctor` 0/1; `bin/adr-readiness` 0/2 and **never 1 even when
   `blocking_count > 0`**; `bin/adr-readiness-ci` 0/1/2; `bin/adr-grill-signal` 0 always;
   `bin/adr-substance` 0/2, with findings and a degraded run both exiting 0; `bin/adr-settings` 0/2.
   A future consumer that checks only `adr-readiness`'s exit status silently misses every block.
   A related asymmetry sits on the same path: `bin/adr-readiness`'s `_human()` indexes required
   report keys directly (`report['summary']['total']` at `:101`, `item['implementation_link']` at
   `:110`) while `adr_readiness_ci` is `.get()`-defensive throughout, and the renderer runs
   *after* the `try` whose caught tuple ends at `bin/adr-readiness:198`, so a `KeyError` is not
   caught there. Because that JSON is the de-facto internal RPC
   of three subprocess consumers, a readiness-schema change surfaces in the default human renderer
   as a traceback instead of the clean exit-2 path.
 2. **`--deep` raises the required bar.** `_mcp_deep` and `_native_deep` build their checks with
   `check()`'s default `required=True`, while their fast-tier counterparts are `required=False`.
   A native CLI whose `plugin list` output lacks `adr-kit` yields `stale` + `required` → exit 1 under
   `--deep` where fast mode exited 0. `trust-pending` is deliberately excluded from
   `FAILURE_STATUSES`, so a trust prompt does not block.
 3. **The fast doctor tier fails on integrations the user never installed — in a canonical root.**
   `mcp-launcher` and `hook-package` run for every non-disabled client regardless of whether the CLI
   is present — `detected.get(name)` feeds only the `native-client` check. `hook-package` is always
   `required=False`, but `mcp-launcher` is required whenever `.adr-kit/ADR-guide.md` exists (a
   set-up project). There, a missing `codex/.mcp.json` is a `required` `failed` check → exit 1 for
   a CLI that was never installed. This is a different code path from ADR-032's `unsupported`: that status fires only
   when `client_root` returns `None` because the tree itself *is* another client's mirror; this
   finding fires when the tree is canonical and the client's owned config is simply absent.

### The health check that mutates the tree

 1. **A bare `adr-doctor` still writes the index, and adapter drift fails the exit code.**
    `bin/adr-doctor:133` forces `args.fix_index = bool(args.fix_index or not args.check)`, so default
    mode regenerates `ADR-INDEX.{md,json}` as a side effect of a health check. Adapter repair is
    narrower than it was: only an installed payload is rewritten; a git checkout gets the drift
    reported instead (`bin/adr_doctor_checks.py:257`). But `_generated_check` builds that drift
    result with `status="stale"` and no `required=`, so the default `required=True` applies and
    `stale ∈ FAILURE_STATUSES` → **adapter drift exits 1 in fast mode, without `--deep`** — under
    `--check` anywhere, and now in default mode too when the payload root is a git checkout.
    Line-ending-only differences no longer count as drift (TASK-57 is closed).

### Measurement honesty

 1. **No ADR Enforcement `path_glob` covers a single file in this component.** Verified by parsing
    every Enforcement block in `docs/adr/` at v0.59.1: the 14 distinct globs are
    `schemas/adr-kit-config.schema.json`, `docs/adr/ADR-INDEX.json`, `templates/githooks/pre-commit`,
    `bin/adr-lint`, `bin/adr_query.py`, `hooks/adr_hook_core.py`,
    `schemas/client-capabilities.schema.json`, `clients/workflows.json`, `bin/adr-mcp`,
    `{bin,codex/bin,copilot/bin}/adr-mcp`, `{bin,codex/bin,copilot/bin}/adr{-judge,-suggest,_llm.py}`,
    `.github/workflows/release-publish.yml`, `tests/fixtures/cli/latency-corpus.json` and
    `tests/test_adr_mcp.py`. None matches any of this component's 19 files. **The
    component that runs the gates is itself entirely unguarded by the fail-closed floor.** Its
    invariants — read-only readiness, fail-open hooks, no lifecycle mutation over MCP, the 2-second
    budget — are held by the test suite alone. A regression here passes `bin/adr-judge` untouched.
 2. **`age_days` measures time since the last status transition, not authoring age.**
    `bin/adr-status:270 parse_adr` never strips frontmatter, so `extract_date` returns the
    frontmatter `date:` field — and `bin/adr:453 mutate_status` rewrites `data["date"]` on **every**
    transition. Both age-based candidate rules ("Proposed for >365 days without acceptance",
    "Accepted >730 days without Enforcement") therefore measure something other than what their
    reason strings claim.
 3. **Staleness rests on filesystem mtime, not git history.** `pointer_changed_after` compares
    `os.path.getmtime` against the acceptance date, so a fresh clone, a checkout or a line-ending
    rewrite can manufacture `accepted_evidence_changed` findings — and because that type is in
    `MATERIAL_DRIFT_TYPES`, it escalates to a full `bin/adr-discover` subprocess.
 4. **Hook-latency evidence is single-host.** `hooks/hook_benchmark.py:146-147` calls
    `host_command(plugin_root, "codex-cli", …)` for every event — a hardcoded host — which
    qualifies any ADR-010 *parity* reading of the reported latency. The doctor further aggregates
    per-event p50/p95/max by **max across events** (worst event wins). This is the same file whose
    recalibrated budgets (ADR-030) made `hook-latency-extension` reportable as `healthy` at all: the
    numbers behind that verdict are still evidence from one client name, and
    `MEASURED_INTERPRETER_FLOOR_MS` (`:51`, 182.6 ms on this machine, 124 ms recorded on the corpus's
    original 2026-07-26 measurement) is a property of the machine the doctor runs on, not of the
    kit — a slower CI runner narrows the margin the recalibrated budgets carry.
 5. **`signal_count` under-reports the payload.** `adr_grill_signal.py:122` computes
    `min(3, len(linked) + len(suspected))` while `MAX_SIGNALS` is applied *per list*, so 3 linked +
    3 suspected emits **six** items and still reports `3`. The only test asserts `signal_count <= 3`.
    No production consumer reads the field today.
 6. **The timeout ladder far exceeds every stated budget.** 5 s per git call in `adr-grill-signal`,
    10 s in `adr-readiness`, 30 s for the child in `adr-readiness-ci`, 60 s for `adr-retire`'s
    `git ls-files`, 120 s for each lint/quality child of `bin/adr accept` and for each
    `adr-substance` model call, 10 s native / 15 s MCP in the doctor. These are ceilings rather than
    expectations, but all exceed ADR-011's p95 targets and ADR-015's 2 s goal. All ten entry points
    now have a row in `tests/fixtures/cli/latency-corpus.json` (`tests/test_cli_corpus_coverage.py`
    fails on an entrypoint with none), but nine of those rows are `startup` budgets measured with
    `--help`; **only `adr-retire` carries a `workload` budget that a test measures** on this
    repository (`tests/test_cli_performance.py`). `adr-doctor --check` is recorded in
    `known_over_ceiling` at 6,800 ms under ADR-033's exception for user-invoked whole-repository
    commands.

### Unenforced contracts and dead surface

 1. **`schemas/doctor-output.schema.json` is declared but never validated.** No test, runtime check
    or CI step evaluates `build_report`'s output against it, so producer and schema can drift
    silently. Related: `check()` accepts a `degradations` argument and the schema *requires* the key,
    but no caller anywhere passes it — the array is always `[]`. A dead field in a required contract
    slot. A third unchecked contract crosses a component boundary: **`bin/adr-grill-signal` never
    inspects `schema_version` on `ADR-INDEX.json`**, even though ADR-007's Enforcement pins that
    artefact to schema v2. A v1 graph would be consumed silently on the hook path, and because the
    reader never opens ADR Markdown, a stale index simply yields stale advisories. The producer is
    guarded; this consumer is not.
 2. **Dead and unreachable surface, catalogued.** `adr_guardian_queue.load_queue_actions` has no
    production consumer. `--format github` in `bin/adr-readiness` duplicates
    `adr_readiness_ci.render_summary` and **has already diverged** (`_github` emits every ADR and
    omits Evidence lines; `render_summary` skips non-linked non-Proposed items and includes them) —
    referenced only by tests. `adr_doctor_core.main()` is a second, still-working standalone CLI with
    `prog="adr-doctor"` that nothing invokes. The `text`-with-no-checks branch at
    `bin/adr-doctor:158-159` is unreachable because `run_client_checks` always appends at least three
    checks. `run_deep_extensions` accepts a `checks` keyword that its body never reads.
    `ADR_FILENAME_RE` in `adr_doctor_core.py` is compiled and unused. And one live path is fragile
    rather than dead: `adr_readiness_ci.py:71` detects the empty state with `if len(lines) == 4`,
    coupling the "No ADR readiness findings." message to the exact four-line header length — adding
    a header line silently suppresses it, in the merge-gate path.
 3. **The lifecycle CLI cannot reach every status its own readers understand.**
    `LEGAL_TRANSITIONS` has `Deprecated` and `Amended` only as *source* states and there is no
    `deprecate`/`amend` subcommand, yet `adr-status`'s `CANONICAL_STATUSES` recognises both and
    `find_retirement_candidates` treats `deprecated` as high-confidence. Those states can only arrive
    by hand-editing or an external writer.
 4. **`adr-guardian check --adr-dir` only works for one layout.** `bin/adr-guardian:1236-1237` steers
    discovery by mutating `os.environ["CLAUDE_PROJECT_DIR"] = Path(args.adr_dir).resolve().parent.parent`,
    so the flag works only when the ADR directory is exactly `<root>/docs/adr`. Any other layout
    resolves elsewhere, the cwd-guard trips, and `check` exits 0 in silence.
 5. **`detect_policy_mismatch` treats unparseable enforcement as *total* policy mismatch.**
    `_enforcement_rules` returns `None` on malformed JSON and the signal becomes the maximum 1.0 —
    not "no enforcement", but "maximally mismatched enforcement".

### Platform and packaging

 1. **Windows hardening is real but uneven.** `adr_guardian_queue.write_queue_cache` retries
    `os.replace` eight times with linear backoff on `PermissionError` (AV/indexer holding the
    destination handle). `_pointer_parts` refuses to read a Windows drive letter as a `path:symbol`
    separator. `adr-retire`'s fallback walk refuses to follow Windows junctions. But
    `_ensure_utf8_streams()` exists only in `bin/adr-readiness` and `bin/adr-guardian`; in
    `bin/adr-grill-signal` the two `print()` calls sit *outside* the `try/except` that catches
    `UnicodeError`, so a non-ASCII path on a cp1252 console raises rather than degrading to exit 2,
    and `bin/adr-readiness-ci` lacks the guard entirely.
 2. **All 19 files exist as byte-identical mirrors in `codex/bin/` and `copilot/bin/`.** `bin/` is
    the source of truth; the mirrors are generated by `scripts/build-client-adapters.py`. Editing a
    mirror is always wrong, and editing `bin/` without regenerating turns the doctor's own
    `generated-adapters` check `stale` — in this repository's checkout a reported, not a repaired,
    state.
 3. **`AdrRecord` is a plain `__slots__` class, not a dataclass** — explicitly to dodge a Python 3.14
    `SourceFileLoader` + dataclass interaction when an extensionless file is imported via
    `importlib`. That constraint follows from the extensionless-script convention and applies to all
    of `bin/`, not just this file.

---

## Component Diagram

```mermaid
flowchart TB
    subgraph triggers["Triggers"]
        SESSION["Agent host SessionStart<br/>.claude/settings.json entry"]
        SKILL["/adr-kit:guardian skill<br/>in-session smart sweep"]
        SETSKILL["/adr-kit:settings skill"]
        PRECOMMIT["git pre-commit hook<br/>templates/githooks/pre-commit"]
        HUMAN["Engineer or agent<br/>direct CLI"]
        GHA["GitHub Actions<br/>adr-readiness · guardian-audit · retire-audit"]
    end

    subgraph comp["Component: health-and-lifecycle"]
        direction TB

        subgraph life["bin-cli-lifecycle"]
            ADR["bin/adr<br/>the only lifecycle writer<br/>snapshot + rollback"]
            GUARD["bin/adr-guardian<br/>check · stamp · state · artifacts<br/>refresh-readiness · retrieval-health"]
            STATUS["bin/adr-status<br/>coverage dashboard"]
            RETIRE["bin/adr-retire<br/>4-signal retirement scorer"]
            DOCSHELL["bin/adr-doctor<br/>166-line argparse shell"]
        end

        subgraph llmtier["LLM tier and settings"]
            SUBST["bin/adr-substance<br/>advisory, exit 0"]
            SETTINGS["bin/adr-settings<br/>provenance + routed writes"]
        end

        subgraph doclib["bin-lib-doctor"]
            DCORE["adr_doctor_core<br/>ADR-set health"]
            DCHECKS["adr_doctor_checks<br/>fast tier + safe repairs"]
            DPROBES["adr_doctor_probes<br/>bounded deep tier"]
            DMODELS["adr_doctor_models<br/>check · build_report · exit code"]
        end

        subgraph rdycli["bin-cli-readiness"]
            RDY["bin/adr-readiness<br/>de-facto internal RPC<br/>never exit 1"]
            RDYCI["bin/adr-readiness-ci<br/>MERGE GATE, exit 1"]
            SIG["bin/adr-grill-signal<br/>fail-open, exit 0"]
        end

        subgraph rdylib["bin-lib-readiness-grill"]
            LRDY["adr_readiness<br/>7 classes + link evidence"]
            LCI["adr_readiness_ci<br/>summary · outputs · annotations"]
            LSIG["adr_grill_signal<br/>analyze_index, max 3+3"]
            LQ["adr_guardian_queue<br/>rank + TTL cache"]
            LRH["adr_retrieval_health<br/>pass · fail · degraded"]
        end
    end

    subgraph owned["State this component owns"]
        ST[("docs/adr/.adr-kit-state.json<br/>+ .lock — per-machine, gitignored")]
        RQ[("docs/adr/.adr-kit-readiness.json<br/>3 actions · 24h TTL · authoritative:false")]
        CFG[("docs/adr/.adr-kit.json<br/>+ .adr-kit.local.json")]
    end

    subgraph siblings["Sibling components"]
        SEM["bin-lib-semantic-core<br/>adr_format · adr_schema<br/>adr_catalog · adr_query"]
        RUNTIME["bin-lib-runtime<br/>adr_config · adr_state"]
        LLM["adr_llm<br/>host-only backend registry"]
        GATES["bin-cli-gates<br/>adr-lint · adr-quality"]
        ENF["bin-cli-enforcement<br/>adr-judge"]
        RETRIEVE["bin-cli-retrieval<br/>adr-index · adr_index_core · adr-suggest"]
        MCPC["bin-cli-mcp<br/>bin/adr-mcp"]
        HOOKS["hooks<br/>hook_benchmark · adr_hook_core"]
        PKG["packaging-ci<br/>client_generation · project_setup<br/>adr_settings"]
        INST["clients-installer<br/>detection · contracts · bounded"]
        SCH["schemas-templates<br/>schemas + templates"]
        DISCOVER["bin/adr-discover<br/>census gap"]
    end

    subgraph ext["External systems"]
        GIT[("git CLI — diff, cat-file, ls-files")]
        FS[("filesystem — mtime is a signal<br/>flock/msvcrt, os.replace, os.walk")]
        RUNNER[/"GITHUB_STEP_SUMMARY · GITHUB_OUTPUT<br/>::error / ::notice"/]
        GHCLI["gh CLI — tracking issues"]
        NATIVE["claude · codex · copilot CLIs<br/>plugin list 10s · host model calls"]
    end

    IDX[("docs/adr/ADR-INDEX.json<br/>generated, schema v2")]
    MD[("docs/adr/ADR-NNN-*.md")]

    SESSION -->|"exit 0, one JSON line"| GUARD
    SKILL -->|"state, stamp, refresh-readiness"| GUARD
    SKILL --> RETIRE
    SKILL --> STATUS
    SKILL -->|"LLM tier, after --estimate"| SUBST
    SKILL -.->|"runs, reports counts back"| ENF
    SKILL -.->|"runs, reports counts back"| RETRIEVE
    SETSKILL --> SETTINGS
    PRECOMMIT -->|"greps [adr-grill], status discarded"| SIG
    HUMAN --> ADR
    HUMAN --> DOCSHELL
    HUMAN --> RDY
    GHA -->|"composite action"| RDYCI
    GHA --> RETIRE
    GHA --> STATUS
    GHA --> GHCLI

    ADR -->|"transactional write"| MD
    ADR -->|"subprocess, inside the transaction"| RETRIEVE
    ADR -->|"subprocess, 7 gates, 120s"| GATES
    ADR -->|"subprocess, --auto threshold"| GATES

    GUARD -->|"locked read-modify-write"| ST
    GUARD --> LQ --> RQ
    GUARD -->|"in-process queue refresh<br/>when cache expired"| LRDY
    GUARD -->|"in-process stale-index check"| RETRIEVE
    GUARD --> LRH
    GUARD -->|"subprocess, 10s"| RDY
    GUARD -->|"reads version stamps"| SCH

    STATUS --> LRH
    RETIRE -->|"ls-files, 60s"| GIT
    RETIRE -->|"fallback walk, 50k cap"| FS

    SUBST --> SEM
    SUBST -->|"resolve_llm_backend"| LLM
    LLM -->|"one call per Proposed ADR"| NATIVE
    SETTINGS -->|"atomic routed write"| CFG
    SETTINGS -->|"validates against"| SCH

    DOCSHELL --> DCORE
    DOCSHELL --> DCHECKS
    DOCSHELL -->|"--deep only"| DPROBES
    DOCSHELL --> DMODELS
    DCHECKS --> DMODELS
    DPROBES --> DMODELS
    DCORE --> LRH
    DCORE -->|"subprocess"| RETRIEVE
    DCORE -->|"subprocess --strict"| GATES
    DCORE -->|"only on material drift"| DISCOVER
    DCORE --> GIT
    DCHECKS --> PKG
    DCHECKS --> INST
    DPROBES --> INST
    DPROBES -->|"import hook_benchmark.measure"| HOOKS
    DPROBES -->|"MCP client, stdio, 15s<br/>exactly 7 tools"| MCPC
    DPROBES --> NATIVE

    RDY --> LRDY
    RDY --> GIT
    RDYCI -->|"subprocess sys.executable"| RDY
    RDYCI --> LCI --> RUNNER
    SIG --> LSIG
    SIG -->|"2 MiB cap"| IDX
    SIG --> GIT

    LRDY -->|"Markdown-first"| SEM
    LRH -->|"index-first"| SEM
    LSIG -->|"index-only"| IDX
    SEM --> MD
    RETRIEVE --> IDX

    GUARD --> RUNTIME
    ADR --> SEM
    STATUS --> SEM
    RETIRE --> SEM

    MCPC -.->|"spawns adr-readiness, adr-status<br/>for 2 of its 7 tools"| RDY
    RQ -.->|"read fail-open by adr_hook_core<br/>queue context + ADR-041 handoff"| HOOKS
```

**Reading the diagram.** Three things are deliberate rather than accidental:

- The dotted arrows from `/adr-kit:guardian` to `bin-cli-enforcement` and `bin-cli-retrieval` are
  hops the **in-session model** performs — it runs `adr-judge`/`adr-suggest` and passes counts back
  through `adr-guardian stamp`. `bin/adr-guardian` never spawns them. That is ADR-002's
  "dumb detector, smart sweep" invariant drawn as a graph. `adr-substance` sits on the same side
  of that line: the skill runs it, the detector never does.
- `bin-cli-mcp` appears on both sides: the doctor is an MCP *client* against it, and it is a
  subprocess *client* of two tools in this component. Coupling is purely process-level in both
  directions, with no shared imports.
- `docs/adr/.adr-kit-readiness.json` is the component's only outward-facing data contract: written
  here (by `refresh-readiness`, and by `check` when it has expired), read by three independent
  implementations (this component's Python library, the guardian's own expiry test, and the hook
  core that turns its top action into ADR-041's grill handoff), all against the payload's own
  `expires_at`.
