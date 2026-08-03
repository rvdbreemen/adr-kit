# Changelog

All notable changes to `adr-kit` are documented in this file. The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **BREAKING: `bin/adr accept` now requires `--confirm`.** Acceptance is the one
  lifecycle transition that decides rather than records, and it writes a name and
  a date into a Status History that is immutable afterwards. Since v0.44.1 derives
  the signer from `git config user.name`, the common case became one where an
  accept nobody meant to run wrote the user's own name into a record they never
  saw -- and R8's own argument is that a false attribution is worse than a missing
  one.

  What the flag buys is narrow and worth stating exactly: an acceptance can no
  longer happen *by accident* -- from a script written against an older interface,
  from a CI job, from an agent following a stale instruction. It does not stop a
  caller who deliberately passes it, and nothing at the process level could: an
  agent runs with the user's own terminal, working directory and environment.

  Inferring presence from `sys.stdin.isatty()` was tried first and is wrong on
  Windows, which `clients/capabilities.json` marks release-required: a subprocess
  with `stdin=DEVNULL` reports `isatty() == True`, because `NUL` is a character
  device. A presence test that says "someone is there" for the null device is
  worse than no test, because it reads as a guarantee.

  `bin/adr accept --auto` is unchanged, because spec R1 grants the init flow that
  exception explicitly. The gates still run first, so a record that cannot be
  accepted reports why rather than asking for a flag.

  **Upgrade:** add `--confirm` to any script or workflow that accepts an ADR.

### Added

- **The guardian sweep runs `bin/adr signer --audit`.** It already knew how to
  find history entries attributed to the toolkit or to nobody, and ran nowhere.
  The weekly cheap-tier sweep now reports them alongside the lint, retirement and
  status sections.

### Changed

- **The signer is derived from `git config user.name` when it names a person**,
  instead of refusing until someone configured one by hand. v0.44.0 made that
  refusal a breaking change: a fresh clone, a container and a CI runner all
  failed at the first lifecycle command, `bin/adr new` included. Reading a git
  identity is not the tool signing on your behalf -- R8.1 forbids "a default
  that names the tool", and a git identity is the opposite of that: a value the
  human configured on this machine, which every commit in the repository already
  carries.

  Two properties survive. The derived actor is **announced** on use, because a
  name that lands in an immutable Status History should never be one the user did
  not know was written. And an identity that is configured but names a machine --
  `github-actions[bot]`, `runner`, a bare `user` -- is refused rather than
  adopted, because R8 asks for evidence of which *human* accepted. Precedence is
  unchanged otherwise: `--changed-by`, then `lifecycle.signer`, then the derived
  value, then the refusal.

### Added

- **`bin/adr signer --suggest` proposes an identity at install and upgrade
  time.** It reads the signed-in GitHub account (`gh api user`, when the CLI is
  available) and `git config user.name`, ranks them, and shows each with its
  source -- a proposal you cannot trace is one you cannot judge. It writes
  nothing: the setup flow shows the candidates and the user chooses. `--format
  json` gives a caller the same list. `/adr-kit:setup`, `/adr-kit:init` and
  `/adr-kit:upgrade` now run it, and `init` does so before the step that creates
  ADRs rather than discovering the refusal halfway through a batch.
- **`bin/adr signer` reports where the current value came from** -- the
  machine-local file, or a derived git identity -- because "why is this the
  name?" is the question that surface exists to answer.


## [0.44.0] - 2026-08-03

### Breaking changes

**`bin/adr-audit` is a different program.** It used to be the init discovery
scanner (`--root`, `--output`, `--skip`, printing candidate JSON). That scanner
is now `bin/adr-discover`, with its flags and output unchanged, and `bin/adr-audit`
is the new lint-plus-judge command. Rename every call that meant discovery. The
kit's own callers — `bin/adr-doctor`, the init and adr skills, the validate
workflow — were updated in the same change.

A bare `bin/adr-audit` now refuses rather than answering. Defaulting to stdin was
the one shape that could be wrong in silence: with stdin closed, an unrenamed
script would read an empty diff, judge nothing, print `verdict: exit 0 (on
course)` and pass. It exits 2 naming `--whole-codebase` and `--diff`, and points
at `bin/adr-discover`.

**Every lifecycle command refuses to run without a configured signer**, including
`bin/adr new`. `--changed-by` used to default to the literal `adr-kit`; it has no
default now, and on refusal the command writes nothing and exits non-zero.
Affected: `new`, `accept`, `propose`, `reject`, `document`, `supersede`, and the
new `relate` and `answer`. Because creation is on that list, an unprepared
machine fails at the first record rather than the first acceptance. The setting,
`lifecycle.signer`, lives in the gitignored `docs/adr/.adr-kit.local.json` and so
cannot be inherited from the repository: every machine, container and CI runner
needs its own. Run `python bin/adr signer --set "User: <your name>"` once per
machine, or pass `--changed-by` every time.

Three further changes alter behaviour without renaming anything:

- **`llm_judge` defaults to `true`.** An Enforcement block that omits the key was
  treated as opted out and never reached a model; it is judged now, and a
  `VIOLATION` blocks the commit. With `judge.llm_enabled` true since v0.43.0, a
  repository that changes nothing can go from zero model calls at commit time to
  one per in-scope ADR, and can find a commit blocked that used to pass. An
  explicit `"llm_judge": false` keeps the old behaviour; an ADR with no
  Enforcement block is still skipped. Run `python bin/adr-migrate docs/adr/
  --enable-llm-judge --dry-run` before upgrading, or set `judge.llm_enabled:
  false` to keep the commit path model-free.
- **The prompt-submit hook injects five ADRs where it injected three,** and
  `context.default_limit` now reaches it. A project that already set that key for
  the command line is affected most: `default_limit: 15` goes from three injected
  ADRs per prompt to fifteen with no change on their side. Set it to the number
  you want; `3` restores the old behaviour.
- **`gh pr create` can now be denied.** A `PreToolUse` guard judges
  `origin/<base>...HEAD` before the command runs and denies the tool call when
  the branch violates an Accepted ADR. Its matcher is `Bash`, so every Bash tool
  call spawns the hook — roughly 0.3 s per call on a Windows checkout. It takes
  effect on upgrade with no action. There is no configuration key that disables
  it; the opt-out is disabling the plugin. To clear one denial: fix the code,
  supersede the decision, or set `ADR_KIT_OVERRIDE="ADR-NNN: reason"`.

### Added

- **`/adr-kit:audit` and `bin/adr-audit` ask both governance questions at once.**
  A clean judge over vague ADRs proves nothing, because a vague rule cannot be
  violated; a sharp ADR set nobody checks the code against is documentation, not
  governance. The exit codes keep the two apart, because they have different
  owners: 0 clean, 1 the code violates an Accepted ADR, 3 the ADR set fails its
  own gates, 4 both, 2 the audit could not run. 3 and 4 sit above 1 so a caller
  testing `!= 0` still blocks while a caller who cares can tell them apart.
- **`--whole-codebase` reaches code no diff has ever touched.** A rule added
  after a file was written has never been applied to that file, and never will be
  by a gate that only sees changes. Mechanically it is a diff against the empty
  tree, so every line reads as added and `forbid_pattern` applies repository
  wide; the right-hand side is the working tree, so a local run answers about the
  code in front of you. Such a diff is large by construction — this repository's
  own is 9.85 MB — so the mode passes the CI-sized 32 MiB budget rather than
  failing closed on size.
- **The LLM pass is bounded by scope, not by the flag.** An ADR is judged only
  when the diff touches a file matching its rules' `path_glob` set; a commit
  outside every scope makes no model call, and a skipped ADR is recorded in the
  `--json` attestation rather than disappearing. ADR-017 promised this in prose
  and the code never did it — tolerable while `llm_judge` defaulted to false, and
  the difference between one call and one call per ADR now that it does not. With
  N opted-in ADRs, a commit touching M scopes costs M calls. **The trap:** a
  block with no rules, or a rule without a `path_glob`, has no boundary to narrow
  with and is judged on every commit. The shipped template emits exactly such an
  empty block, so delete the section when a decision has no code surface.
- **`bin/adr-migrate --enable-llm-judge`, the opt-out migration.** It removes the
  legacy `"llm_judge": false` from Accepted ADRs so the true default applies —
  removing the key rather than writing `true`, so there is one fewer thing to
  re-flip if the default moves again. A rule-less block is marked no-code-surface
  with a reason instead of becoming a call on every commit; `--force-enable
  ADR-NNN` overrides that. `--except ADR-NNN --reason "..."` records a refusal,
  and the reason is mandatory. `/adr-kit:upgrade` gained step 4b, which shows
  each Decision with its rule count and asks before applying.
- **`llm_judge_reason` makes an opt-out durable.** Since the default flipped, a
  bare `"llm_judge": false` is ambiguous: deliberate refusal, or leftover from
  the era when false was the default? A reason resolves it, and the memory lives
  in the ADR rather than in a state file a fresh clone would lose. The migration
  re-proposes a bare `false` and leaves a reasoned one alone.
- **A local precomputed vector layer (ADR-018, superseding ADR-014).** Lexical
  retrieval misses on vocabulary: ask "should the commit hook still run when the
  model is unreachable?" and the ADR that says "fail open on tooling drift"
  shares no token with the question. `adr-embed build` embeds every ADR into a
  machine-local `docs/adr/.adr-kit-vectors.json`; `adr-embed query` finds
  decisions by meaning. `build` is the only place in the kit that may call an
  embedding model, and a human or a CI job invokes it, so nothing embeds because
  someone typed a prompt. The read path is standard-library cosine over a file —
  no numpy, no daemon, no network — which keeps ADR-016's zero dependencies and
  ADR-015's 2 s hook budget intact. Staleness announces itself: every entry
  records the model, the dimension and a content hash, and a changed dimension
  refuses the store outright rather than scoring nonsense.

  **What it does not do yet.** `adr-embed` is the only reader. `adr-context`,
  `bin/adr_query.py` and the lifecycle hooks do not consult the store, so
  everyday retrieval is unchanged and still lexical. Building a store today gives
  you a queryable index and the contract the retrieval path will read; it does
  not make `/adr-kit:context` semantic.
- **`bin/adr-settings`, one surface for every knob.** Each row says where its
  value came from — machine-local, project, default or unset — because "why is
  this on?" is the question a settings screen exists to answer. Writes route
  themselves: a signer lands in the gitignored local file, because writing one
  person's name into the tracked file would sign every teammate's acceptances.
  `--check-embedding` probes for a local embedding runtime read-only and reports
  the routes forward, treating a missing runtime as a normal outcome.
- **An OpenAI-compatible backend, so LM Studio and similar endpoints work.**
  Configured through `judge.openai_base_url`, `judge.openai_model` and the
  `ADR_KIT_OPENAI_API_KEY` environment variable. The base URL is machine-local by
  design and refused in the tracked config: repository-tracked configuration may
  select a backend but never introduce an endpoint, because an endpoint a
  repository can name is an endpoint a repository can redirect.
- **The branch is judged before the pull request exists.** Opening a PR is a
  shell call, so a pre-tool guard intercepts `gh pr create` and judges the whole
  branch first — earlier than CI can be, because CI only learns of the PR once it
  is there. This is the one hook that may block, and that is the point. It fails
  open on everything that is not a violation: no judge, no git, no base branch, a
  timeout, a diff over the cap. Matching is anchored on the command shape, so
  `gh pr list` and a comment mentioning the command do not fire it.
- **Leaving plan mode asks for the ADRs the plan needs.** The `ExitPlanMode` tool
  call is the moment a decision becomes an intention, which is the cheapest point
  to notice that nobody wrote it down. Advisory: it never blocks the transition.
- **`bin/adr relate` writes a cross-reference on both sides at once.**
  Supersession was the only reciprocal writer; a plain cross-reference had none,
  so an ADR could cite ADR-042 forever while ADR-042 never learned of it. The
  link goes in a `related` frontmatter field, written to both records in one
  transaction and unwound the same way by `--remove`. Frontmatter rather than
  prose, because reference bookkeeping is a mutation the kit has always permitted
  on an Accepted record while editing its body is not.
- **`bin/adr answer` keeps a grilling question with its answer.** `## Open
  Questions` holds unresolved items by design and acceptance requires the list to
  be empty, so an author who answered a question had to delete it to accept the
  ADR — leaving the Status History, which records who flipped the status, never
  what they were asked. The command rewrites the item as `- [x] <question> —
  **Answered <date> by <signer>:** <answer>`, which the parser already treats as
  resolved, so both halves survive acceptance untouched.
- **Index freshness is checked where it rots,** at the strength each place can
  honestly claim. The guardian nudges at SessionStart, in-process because `check`
  may not spawn, behind an mtime precondition that is a skip and not a proof. The
  commit hook warns rather than blocks, because it reads the worktree while the
  commit is the staged snapshot and a partial commit would otherwise be refused
  wrongly. CI blocks, and now ships downstream as `.github/actions/adr-index-check`
  plus a copyable workflow.
- **Accepted ADRs are swept for quality decay.** Quality was checked once, at
  acceptance, and then frozen; an ADR does not stay sharp on its own. `adr-quality
  --adr-dir --status Accepted` scores them and exits 1 on decay, and the
  guardian's cheap tier runs it. The response is a supersession or a retirement,
  never a rewrite: an Accepted body is immutable.
- **Quality drives the grilling queue.** A sub-threshold score is now a reason to
  be queued in its own right, and the absence of every reason is a reason to
  leave — a Proposed ADR that is sharp, unlinked, unshipped and asking nothing
  drops out instead of teaching the reader to skim.
- **The bootstrap scanner reads the git history.** `.git/**` was in the skip list
  and all four scanners walked the working tree, which shows what a project is
  but not how it got that way. It now reads decision-shaped commit subjects,
  file-level churn, and the order tooling arrived. History candidates are stamped
  `source: "history"` and carry a `why_this_is_weak` note: a file that exists is
  a fact, a commit subject is a claim someone typed once, possibly about a
  decision reversed three commits later. Everything fails open — no git, no
  repository, no commits — because a bootstrap that refuses on a thin history is
  worse than one that scans what it can and says which half is missing.
- **Two shipped CI workflow templates,** offered by `/adr-kit:install-hooks`:
  `adr-judge.yml` for the pull-request enforcement gate and `adr-index-check.yml`
  for generated-index freshness. Both are declarative-only, with no model, no
  secret and no API key. Both need `fetch-depth: 0` or only one side of the diff
  exists.
- **ADR-019 records why `Stop`, `SubagentStop` and `SessionEnd` stay silent.**
  Answering "were decisions made this session?" honestly means reading a whole
  session, which wants a model — and a session ends when nobody is watching, so a
  hook that spends there spends on an event you cannot see fire and cannot
  refuse. The question moved to `/adr-kit:audit` and `adr-suggest`, which run
  when someone asks. `NOOP_EVENTS` now carries a reason per entry.
- **The generated ADR graph carries `related` links.** `bin/adr_catalog.py`
  derives `related_ids` from the prose section and the new frontmatter field, so
  an `adr relate` link becomes an edge in `ADR-INDEX.json` and raises the
  `context.weights.related_decisions` signal for both records. Nothing changes
  for a project that never calls `relate`.
- **Both new commands ship to all three certified clients,** so the canonical
  workflow set is 17: Claude Code, Codex CLI and GitHub Copilot CLI each carry
  `audit` and `settings`.

### Changed

- **Init accepts the ADRs it reconstructs, after asking once per batch.**
  Reconstructing a decision the code already implements is documentation, not
  authorisation: nobody approves a new direction, they confirm the record matches
  what ships. `bin/adr accept --auto` is not a bypass — it demands
  `documents_shipped: true`, a `verified_in` pointer, no unresolved Open
  Questions and a quality score above the threshold, and refuses by name when one
  fails. The skill names `bin/adr new` explicitly instead of gesturing at "the
  lifecycle command".
- **Init cannot finish on a stale index.** It runs `adr-index docs/adr --check`
  as its last step and blocks on a non-zero.
- **`docs/client-support.md` names the missing fail-closed edit floor on GitHub
  Copilot CLI.** ADR-004 makes the pre-edit tier the one tier that refuses rather
  than degrades; Copilot exposes no pre-tool event that can carry model context,
  so on that client the floor does not exist and `postToolUse` reporting drift
  after the write is a weaker guarantee by construction. The matrix said
  "unsupported native event", which is accurate and tells a reader nothing.
- **The `adr-judge` composite action always passes `--max-diff-bytes`,**
  defaulting to 32 MiB, and a command-line value overrides `judge.max_diff_bytes`
  outright. That key is the pre-commit number now and no longer governs the CI
  gate. To keep your configured cap there, pass `with: max-diff-bytes: <value>`.
- **The shipped pre-commit hook changed,** gaining the index-freshness warning.
  A downstream project only gets it by re-running `/adr-kit:install-hooks` or
  `/adr-kit:upgrade`; the guardian's wrapper-staleness nudge will say so.
- **The grill nudge no longer waits for a model to read a sentence.**
  `refresh-readiness` existed and only prose in the guardian skill ever called
  it, so on a fresh clone the gitignored 24-hour cache stayed empty and the nudge
  stayed silent. `adr-guardian check` now rebuilds the queue in-process when the
  cache is missing or expired, skips entirely while a valid one exists, and fails
  open in every direction.

### Fixed

- **`bin/adr-settings` printed a stored credential back.** `judge.openai_api_key`
  rendered like any other string, so a key in the gitignored local file came
  straight out onto the terminal on `--all`. The file was never the exposure; the
  terminal is — scrollback, a screenshot, a pasted bug report. Secret keys now
  render as `<set>` or `(not set)`, with the matching environment variable
  reported as a boolean beside them. The value is still stored and still reaches
  the judge.
- **`bin/adr document` wrote an empty signer into the status history.** It
  appends a history entry like every other lifecycle command and so must resolve
  a signer like every other one; it did not. The audit gate then rejected the
  entry, so an ADR correctly marked as documenting shipped behaviour could never
  be accepted — and the failure surfaced two commands later, blaming acceptance.
- **`bin/adr accept --auto` would have accepted an untouched template.** Every
  gate it ran was structural, and a scaffold is structurally perfect: all
  sections present, valid frontmatter, quality 0.88 against a 0.70 threshold. It
  would have written "Chosen option: **Option A**, because state the decisive
  rationale" into the record as an Accepted decision. It now refuses a record
  still carrying template instructions, because their presence is not a heuristic
  about quality — it is proof a section was never written.
- **`bin/adr new` produced unparseable YAML for an actor containing a colon.** The
  status-history placeholder was substituted verbatim, so `User: Robert van den
  Breemen` broke the block it was written into.

### Upgrade notes

1. **Set a signer on every machine**, or no lifecycle command will run:
   `python bin/adr signer --set "User: <your name>"`. It is machine-local by
   design and cannot be inherited from the repository, so containers and CI
   runners need their own.
2. **Rename any direct call to `bin/adr-audit` that meant discovery** to
   `bin/adr-discover`. A bare `bin/adr-audit` now exits 2 rather than answering.
3. **Decide about the LLM pass before your next commit.** Run `python
   bin/adr-migrate docs/adr/ --enable-llm-judge --dry-run` to see what the new
   default covers, or set `judge.llm_enabled: false` to keep the commit path
   model-free. Delete empty `## Enforcement` blocks: a block with no rules is
   judged on every commit.
4. **Re-run `/adr-kit:install-hooks` or `/adr-kit:upgrade`** to pick up the
   changed pre-commit wrapper.
5. **Check `context.default_limit`** if you had set it: it now applies at prompt
   time as well as on the command line.
6. **Gitignore `docs/adr/.adr-kit-vectors.json` before your first `adr-embed
   build`.** It is derived, model-specific and different on every machine, and no
   shipped command adds the line for you.
7. **If your CI pins `judge.max_diff_bytes`,** pass it to the action explicitly:
   `with: max-diff-bytes: <value>`.

## [0.43.0] - 2026-07-31

### Upgrade notes

**The per-commit LLM judge is now on by default.** If you do not want it, set
`judge.llm_enabled: false` in `docs/adr/.adr-kit.json` before upgrading. Nothing
is spent until an author sets `llm_judge: true` on an ADR, so a project with no
opted-in ADRs pays nothing either way.

**`judge.llm_cmd` and `judge.llm_model` are deprecated and ignored.** They still
validate, so existing configs keep working, but they no longer choose anything.
Select a backend with `python bin/adr-judge --set-backend {host,openrouter,ollama}`
and inspect the result with `--show-config`. This is deliberate: those keys let
repository-tracked configuration choose the binary the judge executes, and
`docs/adr/.adr-kit.json` is authored by anyone with commit access.

### Added
- **The LLM judge runs by default, on your own agent's model.** `judge.backend`
  is an enum -- `host` (default), `openrouter`, `ollama` -- resolving to a
  code-side command table. The `host` backend uses the CLI of the agent adr-kit
  was installed for and passes **no model flag**, so each CLI resolves the model
  its user configured; nothing is pinned. The judge cannot detect which client it
  runs in, because a `git commit` happens whether or not any agent is running, so
  the installer records the client at install time rather than probing `PATH`.
  New flags: `--show-config` (every value with its provenance, no secret ever
  printed), `--set-backend`, `--host-client`, `--model`. An unavailable backend
  degrades to declarative-only and never blocks a commit. See ADR-017, which
  supersedes ADR-001.
- **`bin/adr-suggest` shares that same registry** (`bin/adr_llm.py`), so both
  entry points resolve a model the same way and neither carries a default command.


- **The MCP server speaks both protocol eras.** Revision `2026-07-28` made the
  Model Context Protocol stateless and removed the `initialize` handshake.
  `bin/adr-mcp` now serves the handshake era (`2024-11-05` through
  `2025-11-25`) and the modern era (`2026-07-28`) from one process. Modern
  results carry `resultType` and `_meta.serverInfo`; `server/discover` and
  `tools/list` also carry `ttlMs` and `cacheScope`. The era is a pure function
  of the single frame, with no per-connection lock, because the revision
  forbids relying on prior requests to establish context. See ADR-016.

### Changed

- **The judge no longer imports `jsonschema` on the commit path.** The stdlib
  structural checks already cover every constraint the schema expresses — a
  differential test over 90 Enforcement blocks found zero verdicts it changed —
  while the import cost roughly 220 ms on every invocation. Authoring-time
  depth is unchanged: `adr-lint` still runs the full schema. Measured with
  interleaved A/B sampling on a 1.2 MB diff: 1105 ms to 721 ms p50, a 1.53x
  improvement.
- **A malfunctioning `jsonschema` no longer disarms enforcement.** A validator
  fault was returned as a validation issue, which marked the Enforcement block
  structurally invalid and made the judge skip every rule in that ADR — so one
  broken library silently disarmed the whole set. It now degrades to the stdlib
  checks, the same as a missing library.

### Fixed

- **`bin/adr-suggest` ignored the model policy the judge enforces.** It carried
  its own pinned `claude-sonnet-4-6` and honoured `suggest.llm_cmd` /
  `judge.llm_cmd`, so repository-tracked configuration could still choose the
  binary it executed -- the guarantee held at one entry point and not the other.
  Both now share `bin/adr_llm.py`. ADR-017's enforcement covered only
  `adr-judge`, which is why this survived; it now covers all three executables
  across all three client distributions.
- **`bin/bump-version` wrote only part of the release.** It carried its own
  hard-coded path list instead of reading `packaging/version-sites.json`, and
  silently skipped both README version pins -- the snippets users copy into
  their own workflow and pre-commit config. Both bump writers now share one
  plan-then-apply engine. Note that `scripts/bump-version.py`, the writer the
  runbook prescribes, was never affected.
- **A failed bump could leave the CHANGELOG announcing a release nothing
  carried.** `scripts/bump-version.py` wrote the release heading before the
  transaction rather than inside it, so a mid-run failure left the canonical
  source ahead of every manifest, with no rollback.
- **`.githooks/pre-commit` was version-stamped but declared nowhere,** so no gate
  verified it. `bin/adr-guardian` compares that stamp against the plugin version
  and reports the hook stale; it is now a declared site.
- **The import-safety suite failed on Python 3.10.** It ran each executable with
  `-P`, which is not a flag before CPython 3.11, so the interpreter exited 2 and
  the test read that as the tool being broken. The variant is skipped below 3.11.
- **The MCP server did not speak UTF-8 on Windows.** The stdio transport
  mandates UTF-8 and newline-delimited framing; `bin/adr-mcp` wrote its frames
  in text mode using the platform default, so on a cp1252 host an em dash left
  as the byte `0x97` and every frame ended `\r\n`. Strict readers aborted the
  session, lenient ones silently accepted mojibake, and a character with no
  cp1252 mapping turned a tool result into JSON-RPC `-32603`. Stdio is now
  pinned to UTF-8 with LF framing. Pre-existing and independent of the protocol
  era.
- **Superseding an ADR erased its original acceptance date.** For a record
  predating the `## Status History` convention, the date lived only in the
  Status line the command replaces, and the freshly created history block held
  just the new transition. The lifecycle commands now seed the recovered entry
  first, recording `changed_by: unknown` rather than inventing a signer, and
  refuse instead of writing a lossy history when the prior state cannot be
  read. Applies to `accept`, `reject`, `propose`, `document` and `supersede`.
- **Status history was written as invalid YAML when a value contained a colon.**
  A `reason` such as "Human approval: records the ..." — or the documented
  `--changed-by "User: <name>"` — ended the plain scalar and made the *entire*
  block unparseable. Three shipped ADRs were already affected and are repaired,
  with no change to any date, status, actor or wording. It went unnoticed
  because adr-kit reads these blocks with its own line-oriented parser; only an
  external consumer using a real YAML parser saw the damage.
- **`bin/adr accept` could not resolve a reference to another ADR.** It linted
  the single file being accepted, so a populated `supersedes` reported
  `target not found` even though the same ADR passed a directory lint.
  Acceptance now uses the whole directory as lookup context while still
  reporting findings only for the ADR being accepted, so an unrelated broken
  ADR does not block it. The error also names the failing finding rather than
  only a count.
- **`require_pattern` blocked on a finding no author could act on.** Under
  `--snapshot diff` a modified file has no reconstructable post-image, so the
  rule failed closed — a statement about the invocation, not the code. It is
  now an advisory, and the MCP `adr_judge` tool asks for `--snapshot worktree`.
  Deleted or unstaged files, and unreadable or unsafe paths, still fail closed.
- **`bin/adr-status --format json` emitted `summary.by_status` in a random key
  order,** because the dict was built from a set and iteration followed
  `PYTHONHASHSEED`. Five seeds produced five orders; they now agree.
- **Forbidden tokens could pass the enforcement floor.** `parse_diff` split on
  `str.splitlines()`, which breaks on eight characters git does not treat as
  line terminators. Content after one was dropped before any rule saw it, so a
  token preceded by a form feed — ordinary page-break punctuation in GNU C
  style and Emacs sources — was never matched. Reproduced 5 of 5; now 0 of 5.
- **An added line starting with `++` hijacked the file-header branch,**
  re-attributing the rest of the hunk to a fabricated path and leaving the real
  file with zero added lines. Header branches are now hunk-gated.
- **A module committed next to `bin/adr-judge` could run as code.** The script
  put its own directory ahead of the standard library on `sys.path`, so a
  committed `bin/jsonschema.py` was imported on the always-on declarative path.
  Reachable wherever that directory is writable by a contributor, including CI
  running the judge from a pull-request checkout. It also defeated CPython's
  own `-P` / `PYTHONSAFEPATH` mitigation. Siblings are now loaded by explicit
  file location and the directory is no longer importable.
- **A failed install left the client marketplace registered.** All three
  installers register the marketplace and then install the plugin; when the
  second step failed on a first install, the transaction rollback was a no-op
  because it restores a previous prepared source that does not yet exist. Each
  installer now undoes a registration it made itself, and leaves a
  pre-existing one alone.
- **`build-client-adapters.py --check` reported drift on a Windows checkout.**
  The generator emits LF while git materialises CRLF for paths `.gitattributes`
  does not pin, so byte comparison failed while `git diff` was empty. Line
  endings are now normalised for the comparison only; content is still compared
  byte for byte, and binary outputs are never normalised.

## [0.42.0] - 2026-07-26

A performance and release-safety release. The two deterministic CLI paths that
could keep a user waiting past two seconds are now single-pass, the SessionStart
hook gets a hardened timeout, and two new guards protect the release process
itself: a daily merge-back drift check and a payload path-leak gate. No command
surface or configuration key changes; no action is required to upgrade.

### Changed

- **`adr-lint` and `adr-retire` scan the repository once, not once per ADR.**
  `adr-retire` walked the full tree from `detect_tech_removal` for every ADR it
  scored, which made its runtime linear in ADR count (measured 5.2 s at 100
  ADRs); it now memoizes the walk and resolves every ADR's technology terms in
  one early-exit pass (560 ms at 100 ADRs, flat). `adr-lint` re-read up to 5000
  files for every named frontmatter gate; it now resolves all gates in a single
  pass over the scan set. Both scanners also stop descending into nested
  checkouts (any directory carrying a `.git` entry, such as agent worktrees
  under `.claude/worktrees/`), which are not project source. Output is
  byte-identical before and after on an unchanged tree; the 2-second user-wait
  budgets and the measured evidence ship in
  `tests/fixtures/cli/latency-corpus.json`, guarded by
  `tests/test_cli_performance.py`.

### Fixed

- **SessionStart hook no longer risks tripping its own runner timeout.** The
  shipped `hooks.json` for all three clients raises the SessionStart runner
  timeout from 1 to 5 seconds (now also declared as `runner_timeout_sec` in the
  hook manifest), so a cold start on the Python fallback host degrades to a
  skipped nudge instead of a client-visible hook error. The hook itself remains
  fail-open.

### Added

- **Release branches are checked for merge-back drift.** New
  `scripts/check-branch-sync.py` fails when `dev` is missing commits that are on
  `main`, and names the released versions that never made it back rather than
  reporting a bare commit count. `.github/workflows/branch-sync-check.yml` runs
  it daily. Releases land on `main` while work continues on `dev`, and nothing
  moved those commits back, so `dev` drifted one release at a time: by v0.40.0 it
  was 32 commits behind, still declared 0.37.0, and had lost the release
  toolchain it is meant to run (`bump-version.py`, `check-release-version.py`,
  `packaging/version-sites.json`, `docs/RELEASING.md`, `release-publish.yml`)
  along with ADR-012, ADR-013 and ADR-014. Cutting a release from `dev` in that
  state would have reverted three published versions. The runbook and
  `/release-adr-kit` now carry the merge-back as an explicit numbered step.
- Release payload validation now fails when a file carries a maintainer home
  directory, and holds compiled artifacts to the stricter rule that they may
  not reference a Windows drive at all. The scan reads the resolved release
  file set as bytes, so the shipped Windows hook binaries are covered rather
  than skipped as binary. Redaction placeholders such as `C:\Users\...` stay
  legal so existing documentation comments continue to pass.

## [0.41.0] - 2026-07-25

A correctness and consolidation release. Three tools that read an ADR's status
or Enforcement block disagreed with the pre-commit gate, so this release makes
every reader the same reader and fixes the disagreements that had already
appeared. There are no new commands or configuration keys, and no ADR that
`adr-judge` treats as Accepted today changes status.

### Fixed

- **Isolated regex worker no longer mixes responses after a restart.** When
  `RegexEvaluator` was restarted (for example after a pattern hit its
  wall-clock budget), the reader thread of the retired worker could deliver its
  end-of-stream sentinel into the *new* worker's response queue. A subsequent
  `require_pattern` or `forbid_pattern` evaluation could then read that stale
  sentinel and fail closed with "worker exited unexpectedly", blocking a commit
  that had no violation. The reader now binds its own stdout and queue, so a
  retired worker can only ever write to the queue it was started with.
- **Cross-tool status agreement.** `adr-index`, `adr-watch`, `adr-judge`,
  `adr-lint`, and `adr-retire` now read an ADR's status through a single shared
  `adr_catalog.adr_status` reader. Previously two forked single-line regexes
  disagreed, so the same ADR could read as Accepted by one tool and Unknown by
  another (for example `  Status: Accepted` or `Status Accepted`). The unified
  line form is a superset of both prior variants, so no ADR that any tool read
  as Accepted changes status.
- **`adr-status` now reports what the gate enforces.** The dashboard shared
  neither reader with `adr-judge`, so it disagreed in two ways. It had no
  plain-line status tier, reporting an ADR the gate enforces as `Accepted`
  under `unknown` (and it never matched the `**Status: Accepted**` form its own
  docstring advertised). Its Enforcement detector also accepted untagged
  ``` fences that the gate ignores, so coverage figures claimed enforcement
  that never ran. Both readers are now the shared ones.
- **Upgrade:** no action is required, but `adr-status` output can legitimately
  move. An ADR whose Enforcement block sits in an untagged fence now reports as
  having no enforcement, which lowers the coverage percentage. That is the
  accurate figure: `adr-judge` never enforced those blocks. To enforce such an
  ADR, tag its fence as ` ```json ` and re-run `bin/adr-status`.

### Changed

- **The README leads with what the project is for.** It opened with three
  agent-directed instruction blocks before stating the problem it solves. It
  now opens with intent, then splits what changes for the agent from what
  changes for the human, and routes readers through a "Start here" table and a
  three-rule agent contract. A new "What's new" section covers the nine
  releases from 2026-07-18 to 2026-07-23 (index-first selective context, ADR
  grilling, three-client certification, the release runbook and version
  registry, selectable formats) with links to the guide behind each one. The
  repository map, comparison table, project resources, and the FAQ answer that
  pinned the filename contract to a stale version are refreshed.
  `ROADMAP.md` records v0.35.0 through v0.40.0 as landed, and `CONTRIBUTING.md`
  points its release section at `docs/RELEASING.md`, the registry bump writer,
  the tag-triggered publish workflow, and the merge-back step.

- **New `docs/README.md` documentation index.** One map of every guide, split
  by audience: which four documents a coding agent needs and the invariants
  that hold across them, then the human-facing getting-started, day-to-day,
  direction, and contributing sets. It also lists which files are generated and
  by which command, so no one hand-edits a generated view.

- **Single readers for shared ADR parsing.** The Enforcement block regex (five
  identical copies), `enforcement_globs`, `adr_id_from_filename` with
  `ADR_FILENAME_RE` (six copies), project `docs/adr` discovery, and the two
  config loaders now each live in one module and are imported by every caller.
  This removes the drift that produced the status and enforcement bugs above.
  The shared `docs/adr` discovery lives in the stdlib-only `adr_state` module so
  hook entry points pay no extra import cost.

- **Hot-path performance.** `bin/adr-judge` now caches snapshot file reads for
  the duration of one pre-commit pass, so a file governed by several
  `require_pattern` rules or multiple ADRs is fetched from git once instead of
  re-spawning `git show` per rule. `adr_format.detect_profile` is memoized and
  `adr_catalog.load_adr_record` extracts the Decision section a single time,
  removing a repeated full-document parse per ADR across `adr-index`,
  `adr-context`, `adr-related`, and lint. Behavior is preserved; the isolated
  regex safety budget and reporting output are unchanged.

### Removed

- **Dead code cleanup.** Removed unreferenced helper functions
  (`load_readme_records`, `decision_oneline`, `render_queue_actions`,
  `_path_matches`, `require_client_id`, `read_update_state`, `_run_version`),
  stale precompiled patterns left behind by earlier refactors in `adr-context`
  and `adr-related`, dead module constants, unused imports, and leftover local
  bindings. No public workflow, CLI surface, or behavior changed.

## [0.40.0] - 2026-07-23

### Added

- **`ADR-INDEX.json` schema v2 is now the local selective-context query
  database.** The CLI, MCP server, lifecycle hooks, status, doctor, and
  guardian share one deterministic engine with bounded text, path, component,
  symbol, topic, lifecycle, authority, history, score, and result-limit inputs.
  Results explain why each ADR matched, while source Markdown remains the
  decision authority.
- **ADRs can carry retrieval metadata and a compact Decision Contract.**
  Frontmatter supports topics, aliases, components, symbols, and global versus
  selective context scope. `Must`, `Must Not`, `Exceptions`, and
  `Verification` sections give agents a bounded view that is reviewed during
  human grilling rather than silently inferred as new authority.
- **Project-specific retrieval probes and health reporting.**
  `adr-context --check-probes`, `adr-status`, `adr-doctor`, and
  `adr-guardian retrieval-health` report expected inclusions, exclusions, and
  Accepted-binding metadata completeness without invoking a model.
- **Safe metadata adoption for existing ADR sets.**
  `adr-migrate --suggest-retrieval --dry-run` proposes retrieval metadata and
  Decision Contract candidates without changing source ADRs. Applying a
  candidate always remains an explicit, human-reviewed action.

### Changed

- **Healthy index-first retrieval replaces full-set Markdown discovery.**
  Accepted ADRs govern, Proposed ADRs are labelled advisory, and historical
  ADRs are opt-in. A visible Markdown fallback handles missing, stale,
  unsupported, or schema-v1 indexes unless strict-index mode is enabled.
- **Lifecycle context is narrower and authority-aware.** Session hooks inject
  only explicit global Accepted context; prompt and edit hooks separate
  governing Accepted records from advisory Proposed records; subagent and
  compaction hooks preserve parent context without broadening it.
- **Upgrade:** update ADR Kit, run `python bin/adr-index docs/adr`, and add
  retrieval probes before enabling strict index or strict completeness policy.
  Projects without retrieval metadata continue to work, and completeness is
  advisory by default. No ADR body profile or lifecycle transition changed.

### Fixed

- **Intermittent `UserPromptSubmit` timeout warnings on Windows.** The client
  runner now allows a five-second cold-start safety margin while preserving the
  separate 250 ms p95 and 500 ms semantic retrieval budgets. The hook remains
  deterministic, model-free, key-free, bounded, and fail-open.

### Deprecated

- **Reading every Markdown ADR to discover relevance is no longer the preferred
  workflow.** Query the generated index first, then open only returned sources.
  Schema-v1 fallback, stable result fields, older client payloads, and legacy
  scoring-weight call signatures remain compatible for one minor release;
  legacy weights no longer alter positive-evidence ranking. To roll back,
  disable strict index/completeness settings, revert approved metadata edits,
  and regenerate the previous index.

## [0.39.0] - 2026-07-22

### Added

- **One place to declare where the release version lives.**
  [`packaging/version-sites.json`](packaging/version-sites.json) is a declarative
  registry of every version-bearing file with an explicit read/write strategy: the
  CHANGELOG release heading, the three client plugin manifests, the two versioned
  marketplace manifests, the pre-commit / guardian-entry / guide template stamps,
  and the README version pins. It also records the negative invariant that the Codex
  local marketplace must inherit its version, and that README history markers such
  as "introduced in v0.31.0" are deliberately not sites. Decision recorded in
  [ADR-013](docs/adr/ADR-013-declare-version-sites-in-one-registry-and-bump-by-writing.md),
  which amends ADR-012.
- **`scripts/bump-version.py X.Y.Z` writes the version everywhere in one command**,
  and creates the CHANGELOG release heading if it is missing. Releasing 0.38.0 took
  nine hand-edits spread over four discovery rounds; this release took one command.
  `--check` reports drift without changing anything.
- **`scripts/version_sites.py`**, the shared implementation that the bump writer, the
  release gate, the client-adapter generator and the test suite all read, so a new
  version-bearing file is declared once instead of being taught to three tools that
  can drift apart. `tests/test_version_sites.py` asserts the registry still covers the
  manifests the generator independently validates.

### Changed

- **`scripts/check-release-version.py` is registry-driven** and now also gates the
  three template version stamps and the README version pins. Those stamps were
  previously caught only by a five-minute test run, and the README pins by nothing at
  all: they had silently pointed at v0.34.0 while 0.37.0 shipped.
- **Stale versions are all reported in one pass.** The client-adapter generator used
  to abort on the first stale manifest, turning a bump into a fix-one-and-rerun loop.
  It now lists every stale manifest together with the exact command that fixes them.
- **The release runbook and `/release-adr-kit` start from `bump-version.py`.** Versions
  are declared and written, never hand-edited; if a file still carries an old version,
  the fix is a registry line, not a manual patch.

## [0.38.0] - 2026-07-22

### Added

- **A documented, enforced release process for all three coding-agent
  marketplaces.** [docs/RELEASING.md](docs/RELEASING.md) is now the authoritative
  runbook: it explains that Claude Code, Codex, and GitHub Copilot all resolve
  adr-kit from the public repository, names each client's marketplace manifest,
  and separates the git-source path (end users, served by the tag) from the
  version-pinned prepared-directory path (maintainer machines, advanced with
  `scripts/install-agent-envs.py`). The decision behind it is recorded in
  [ADR-012](docs/adr/ADR-012-release-to-the-three-coding-agent-marketplaces-from-the-public-repository.md).
- **`scripts/check-release-version.py`** fails a release unless one version is
  identical across every publish surface: the three client plugin manifests, the
  two versioned marketplace manifests, the top CHANGELOG heading, and the git tag.
- **`.github/workflows/release-publish.yml`** runs on a `v*` tag: it re-runs the
  version-consistency check, the client-adapter drift check, `adr-lint --strict`,
  `adr-index --check` and the test suite, then publishes the GitHub Release using
  this CHANGELOG section as the release notes.
- **Repo-level `/release-adr-kit` command** (`.claude/commands/release-adr-kit.md`)
  that drives the whole runbook locally: prepare the version, release notes and
  README, run every gate, tag and push, then advance this machine's prepared
  marketplace and verify each client.

### Fixed

- **The installer now re-points the Claude marketplace when the version changes.**
  `claude_marketplace_source_matches()` treated any directory-backed marketplace as
  already matching the new prepared source whenever that source carried the
  prepared marker, even when the registration still pointed at an older version
  directory. `install_claude` therefore skipped the remove-and-add, so
  `claude plugin update` kept pulling from the stale directory and the client never
  advanced (0.36.0 stayed on 0.36.0 after 0.37.0 shipped). A path mismatch is now
  authoritative; the marker fallback applies only when the registration exposes no
  path at all. Codex and Copilot were unaffected.

## [0.37.0] - 2026-07-21

### Added

- **ADR Grilling across the full lifecycle.** The new `grill` workflow for
  Claude Code, Codex, and Copilot completes Proposed ADRs through one
  evidence-backed human question at a time, reconstructs decisions from PRs,
  ranges, chat logs, and documents, and revalidates supersession or retirement
  candidates. It never treats source material as acceptance authority. The
  [user guide](docs/adr-grilling.md) includes runnable authoring, reconstruction,
  queue, lifecycle, migration, and CI examples.
- **Deterministic readiness contract.** `bin/adr-readiness`, schema v1, and the
  fifth key-free MCP tool `adr_readiness` separate mechanical defects from
  unresolved human decisions and detect explicit implementation links.
- **Active Proposed queue and bounded automation.** Guardian refreshes a
  24-hour, three-item readiness cache outside hook hot paths. Edit hooks and
  pre-commit surface advisory grill commands without models or network calls.
  The new `adr-readiness` composite action blocks only implementation explicitly
  linked to a Proposed ADR and publishes sanitized summaries and outputs.

### Changed

- All three client packages now expose 15 canonical workflows. ADR creation,
  init reconstruction, review, judge, supersede, and retire route unresolved
  decisions through the shared grilling protocol.
- Unspecified after-the-fact acceptance now defaults to `assist`: eligibility
  is reported first and mutation requires confirmation. Projects that depend
  on the legacy behavior can explicitly set
  `lifecycle.auto_accept.mode: "auto"`.

## [0.36.0] - 2026-07-20

### Added

- First-class native packages for Claude Code CLI, OpenAI Codex CLI, and
  GitHub Copilot CLI now share one canonical set of 14 ADR workflows while
  retaining client-native manifests, skill metadata, prompts, hooks, and MCP
  declarations.
- Project setup, global defaults with per-project overrides, detected-client
  installation, verified updates, rollback, disable/uninstall behavior, and
  generated ADR guidance are available through deterministic stdlib tooling.
- `adr-doctor` now has fast and deep modes for generated drift, settings,
  native registration, MCP, hook packages, local judgment, and measured hook
  latency, with bounded `--check` and `--fix` repair authority.
- A normalized fail-open hook runtime covers the supported lifecycle moments
  each client exposes, with Windows-native latency evidence and portable
  Python fallback behavior.

### Changed

- Added deterministic, evidence-backed certification and support-matrix gates
  for the Claude Code, Codex, and GitHub Copilot CLI payloads. Client-native
  plugin, skill, prompt, and hook optimization is now release-blocking.
- Native Windows observations now assemble into the release schema through the
  existing client build entrypoint. Release automation pins a separate evidence
  commit, avoiding a self-referential candidate hash while retaining exact
  candidate and prepared-payload binding.
- Client generation is byte-deterministic, zero-runtime-dependency, allowlist
  bounded, and measured on Windows. The v0.36.0 candidate records clean p95
  735.485 ms and warm no-op p95 60.974 ms with zero rewrites.
- Current implementation scope is intentionally limited to Claude, Codex, and
  Copilot. Wider coding-agent support is retained only in future TASK-43.

## [0.35.0] - 2026-07-19

### Changed

- Promoted the quiet Claude Code, OpenAI Codex, and GitHub Copilot CLI
  integration work to the user-requested `v0.35` minor release line. This
  release supersedes v0.34.2 and contains the same hook suppression, English
  skill metadata, three-client documentation, and obsolete-client cleanup.

## [0.34.2] - 2026-07-19

### Changed

- Claude Code context hooks now request raw-output suppression and omit routine
  progress labels while continuing to deliver relevant ADR context to the
  model. Codex and GitHub Copilot CLI keep their quiet native skill and MCP
  integrations.
- All three client distributions now carry verified English skill metadata.
  The README and install guides document Claude Code, OpenAI Codex, and GitHub
  Copilot CLI as first-class integrations, with portable Agent Skills and MCP
  described generically.
- Removed obsolete client-specific product references and runtime envelope
  branches from product documentation and generated payloads.

## [0.34.1] - 2026-07-19

### Fixed

- GitHub Copilot now resolves the bundled `adr-mcp` executable through
  `${PLUGIN_ROOT}` instead of looking under the active project. The MCP server
  still uses the active project as its root, and installer validation now
  exercises the manifest from an unrelated workspace.

## [0.34.0] - 2026-07-18

### Documentation

- Added an agent-first ADR discovery contract: inspect the generated JSON graph
  or call `adr-context`, use metadata and links to shortlist records, then open
  the authoritative Markdown ADR before applying a constraint.
- Added a prominent, client-neutral `INSTALL-AGENT.md` runbook so coding
  agents can detect, preview, install, initialize, and validate ADR Kit without
  reading the full README. Native Claude Code, Codex, and Copilot paths fall
  back to MCP, Agent Skills, or direct Python commands for other agents.
- Explained the MADR default in the README, human and agent installation
  guides, and the installed project guide: MADR minimizes agent inference,
  Nygard optimizes concision, and canonical preserves upgrade compatibility.

### Added

- **Versioned JSON ADR graph (TASK-30 / ADR-007).**
  `bin/adr-index docs/adr` now generates `ADR-INDEX.json` alongside the compact
  Markdown and README views. The timestamp-free graph exposes format-neutral
  lifecycle metadata, bounded decision summaries, enforcement scope, evidence
  pointers, and sorted typed relationship edges under
  `schemas/adr-index.schema.json`.
- **Actionable context results.** `bin/adr-context --format json` retains its
  existing ranking fields and adds source path, lifecycle status, body format,
  decision summary, scope, declared links, and invariant metadata.
- **Three-platform installer contract (TASK-29).**
  `scripts/install-agent-envs.py` now validates its full source and Python
  3.10+ child runtime before client mutations, prepares a persistent
  platform-local marketplace with the exact interpreter embedded in Codex and
  Copilot MCP manifests, restores Unix executable modes, and completes a real
  MCP initialize/tools-list smoke test. Detection and installation failures
  are isolated per client. CI runs the installer contract on Windows, macOS,
  and Linux.
- **Shipped profile catalog (TASK-28).** `bin/adr profiles` now gives humans
  and coding agents an ordered catalog, with JSON output, MADR preference,
  format guidance, exact template paths, and installed availability. Profile
  selection and template resolution share one registry, so only `madr`,
  `nygard`, and `canonical` are selectable and a missing shipped template
  blocks ADR creation before a record is written.
- **Legacy format discovery and migration plans (TASK-27).**
  `bin/adr-migrate --plan` scans canonical and recognizable old filenames,
  reports supported-profile metadata/rename work, and conservatively detects
  Y-Statement, Tyree/Akerman, arc42, hybrid, and unknown shapes. Install,
  init, upgrade, and lint surface the same read-only advice; no path migrates
  content automatically. The deterministic supported-profile path also
  normalizes legacy numeric H1 headings and adds required extension sections.
- **Selectable ADR body profiles (TASK-26).** `madr`, `nygard`, and the
  backward-compatible `canonical` profile share one stdlib semantic registry.
  `bin/adr new` honors `template.profile` with MADR as the default, while
  `--profile` selects one record.
- **Deterministic profile migration.** `bin/adr-migrate --to-profile` supports
  dry-run, check, explicit-source disambiguation, and idempotent conversion
  without rewriting invariant metadata, history, references, or Enforcement.
- **Format research and ADR-005.** A cited evaluation covers Nygard, MADR,
  Y-Statements, Tyree/Akerman, arc42, and ISO-oriented records. ADR-005
  supersedes ADR-003's canonical-only storage decision.

### Changed

- Index, context, and relationship tools now share one stdlib, format-aware ADR
  catalog loader. `adr-index --check` checks all three generated views and CI
  validates the JSON graph against its versioned schema.
- Lint, quality, index, context, judge, related, retirement, suggestion,
  audit, lifecycle, and edit-time injection consume semantic roles across all
  supported profiles. Unknown and ambiguous hybrid records fail strict lint
  with an explicit migration path.
- Generated client payload drift checks normalize CRLF and LF before
  comparison, keeping `--check` deterministic across Windows and Unix.
- Directly invoked hooks and engine entry points now retain executable modes in
  Git archives, and the Windows/macOS/Linux CI matrix checks both manual and
  automatically prepared installation paths.

### Fixed

- Closed every actionable finding from the 2026-07-18 multi-perspective source
  audit: bounded regex execution, schema-validated runtime configuration,
  fail-closed diff limits, exact staged/worktree snapshots, decoded Git paths,
  complete generated-validator semantics or explicit rejection, legal and
  rollback-safe lifecycle changes, explicit context authority, transactional
  release bumps, and cross-process guardian/watcher state updates.
- Release preflight now validates and computes all ten versioned targets before
  the first write, rolls every target back on failure, and prints the complete
  staging set.
- Public install, security, roadmap, supersession, validator, audit, and
  changelog-link documentation now matches the shipped behavior.
- The `clarity` gate no longer reports acronyms it cannot help with. It ignores
  a documented allowlist of universal technical vocabulary (`ADR`, `JSON`,
  `YAML`, `HTTP`, and similar), accepts the `expansion (ACRONYM)` word order in
  addition to `ACRONYM (expansion)`, and skips YAML frontmatter, where an inline
  expansion cannot be written. Previously any ADR whose title contained a common
  acronym could never satisfy `bin/adr accept`, because acceptance runs the gate
  set that includes `clarity`. Its finding summary also counted only the first
  five hits; it now counts every distinct acronym.
- The packaged Windows hook wrapper is now smoke-tested through its absolute
  path, matching how `plugin.json` launches it. The previous bare-name
  invocation failed on shells that set `NoDefaultCurrentDirectoryInExePath`.

## [0.33.0] - 2026-07-18

### Added

- **Separate native Codex plugin.** A self-contained `codex/` distribution now ships a validated `.codex-plugin/plugin.json`, 14 Codex-native skills, and the four-tool key-free MCP server. Codex workflows are invoked as namespaced skills such as `$adr-kit:context`, not Claude Code slash commands.
- **Detected-client installer.** `scripts/install-agent-envs.py` verifies real Claude Code, Codex, and standalone GitHub Copilot CLI executables from their version output, installs every detected client through its native plugin API, supports explicit selection and dry runs, and performs post-install plugin/MCP validation.
- **Separate standalone Copilot CLI plugin.** The `copilot/` distribution and `.github/plugin/marketplace.json` install 14 skills plus the MCP server without reusing the Claude or Codex manifest.
- **Generated client payload gate.** `scripts/sync-agent-plugins.py --check` keeps Codex and Copilot engine/schema/template payloads byte-identical to the canonical source and fails CI on drift.

### Changed

- **MCP calls can select a workspace per request.** All four tools accept optional `project_root` and `adr_dir` arguments, so plugin-hosted MCP processes operate on the active project instead of their install cache.
- **Release versioning covers all client manifests.** `bin/bump-version` now stamps Claude, Codex, and Copilot manifests plus both marketplace versions in one release operation.

### Fixed

- **Codex commands are no longer documented as `.codex/skills` copies.** The README and installation guide now describe the actual Codex plugin and namespaced skill invocation contract.
- **Installed hooks resolve every native client cache.** The shared pre-commit wrapper selects the newest ADR Kit engine across Claude Code, Codex, and Copilot CLI installs instead of depending on the Claude cache alone.

## [0.32.0] - 2026-07-07

### Added

- **Canonical ADR frontmatter and migration tooling (tasks 17 and 18).** ADRs can now carry a small, stdlib-parseable metadata block with stable fields for `id`, `title`, `status`, `date`, binding/gate information, supersession links, `documents_shipped`, and `verified_in` evidence. `bin/adr-migrate` adds or repairs that metadata without rewriting the markdown body, and `schemas/adr-frontmatter.schema.json` documents the contract for other agents and CI systems.
- **Strict local governance linting (task 18).** `bin/adr-lint --strict` now enables schema validation, local `verified_in` resolution, reciprocal supersession checks, binding gate lookup, and fail-level handling for all enabled findings. The strict path is intended for CI, doctor checks, and auto-acceptance workflows where advisory drift should not be silently ignored.
- **Generated README index mode (task 19).** `bin/adr-index` now has a second, backward-compatible mode: `bin/adr-index docs/adr/` rebuilds only the sentinel-owned block in `docs/adr/README.md`, while `--check` fails when the README index is stale or duplicate ADR ids exist. The existing ADR-004 context-index mode remains intact through `--adr-dir docs/adr -o docs/adr/ADR-INDEX.md`.
- **Lifecycle CLI commands (task 20).** New `bin/adr` commands cover `propose`, `accept`, `supersede`, `reject`, and `document`. They update frontmatter, the Status section, append-only Status History, reciprocal supersession links, and then refresh the generated README index.
- **After-the-fact ADR acceptance (task 21).** `bin/adr document` marks shipped behaviour with `documents_shipped: true` and local `verified_in` evidence pointers. `bin/adr accept --auto` accepts only when strict lint and quality checks pass; `--auto-mode assist` reports eligibility without mutating.
- **Local ADR doctor (task 22).** New `bin/adr-doctor` runs strict lint plus generated-index freshness checks, then reports shipped-but-still-Proposed ADRs, old Proposed ADRs, Accepted ADRs whose evidence files changed after acceptance, and missing named gates. Material drift triggers a local `bin/adr-audit --root ...` pass and includes the audit summary in the output.
- **Agent-facing governance instructions.** `AGENTS.md`, `CLAUDE.md`, `agents/adr-generator.md`, and `skills/adr/SKILL.md` now point agents at Backlog.md, strict lint, `adr-doctor`, and generated indexes instead of hand-editing ADR indexes.

### Changed

- **`bin/adr-index` consolidates the v0.31 and v0.32 index flows.** The command now preserves the ADR-004 compact context index for `docs/adr/ADR-INDEX.md` and also supports the local README index needed by lifecycle and doctor tooling. Both modes exclude generated `ADR-INDEX.md` from ADR discovery.
- **Release metadata moved to 0.32.0.** `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `templates/adr-kit-guide.md`, `templates/githooks/pre-commit`, `templates/cc-settings/guardian-hook-entry.json`, and this repo's dogfood `.githooks/pre-commit` are stamped together so Claude Code's plugin update flow and copied-artifact staleness checks see the same version.

## [0.31.0] - 2026-07-05

### Added

- **Layered ADR context injection (ADR-004).** A documented model for feeding ADR knowledge into agent work through three fail-open injection tiers plus the one fail-closed pre-commit floor, modeled on the OpenWolf inject/freshen/enforce loop. New surfaces:
  - **`bin/adr-index`** generates `docs/adr/ADR-INDEX.md`, a compact one-row-per-ADR map (id, status, scope, one-line decision) that `CLAUDE.md` `@`-imports so every session is ADR-aware at a fixed low token cost. Deterministic and timestamp-free; a new `adr-index-check` CI workflow diffs the committed index against a fresh regenerate. The init/setup stubs now include the `@docs/adr/ADR-INDEX.md` import.
  - **Edit-tier injector** (`bin/adr-watch --pre-edit`), wired as a `PreToolUse` hook for `Edit|MultiEdit|Write` in `.claude-plugin/plugin.json`. Before an edit it injects the single top-ranked governing Accepted ADR's `## Decision` text (bounded to `inject.max_tokens`, default 400) as `hookSpecificOutput.additionalContext`, so the agent honours the decision *as it writes* rather than after. Reuses the existing adr-watch matcher and a separate `inject` cooldown key in `.adr-kit-state.json`. Advisory only, always exits 0. New `inject` config block added to `schemas/adr-kit-config.schema.json`.
  - **`bin/adr-status` floor coverage buckets**: the summary now reports how many Accepted ADRs are covered by declarative rules vs. manual review (`{"llm_judge": false}`) vs. no Enforcement block, in text and markdown, so the deterministic floor's coverage is visible without false-positiving the documented manual-review pattern.
  - Canonical fields are pinned (scope = Enforcement `path_glob`; status = `## Status` reconciled with the latest `status_history` entry) and shared by all readers; a no-drift regression test locks `bin/adr-index`'s readers to `bin/adr-watch`'s. Covered by `tests/test_adr_index.py`, new `TestPreEditInject` cases in `tests/test_adr_watch.py`, and `TestFloorBuckets` in `tests/test_adr_status_coverage.py`.
- **Lint consistency gate now flags one-directional (dangling) supersession.** `bin/adr-lint`'s consistency gate already FAILed *concurrent* supersession (2+ Accepted ADRs claiming one target); it now also catches the single-claimant case where an Accepted ADR claims `Supersedes ADR-X` but the target's Status line does not name it back as successor. This is the common drift where the successor lands but the superseded ADR is never flipped, so it still reads as live and the audit trail is one-way. A claim against a target absent from the directory is deliberately left to the broken-reference detectors (`bin/adr-retire`) to avoid flagging prose mentions of unknown ADR numbers; clean bidirectional supersessions are unaffected. The finding flows through the normal consistency-gate severity policy, so projects can tune it via their severity config. Covered by three new tests in `tests/test_adr_lint_supersession.py`.

## [0.30.5] - 2026-06-14

### Fixed

- **Config schema rejected the `judge.*` performance-budget knobs (#10).** `schemas/adr-kit-config.schema.json` declares the `judge` object with `additionalProperties: false` but omitted the TASK-712 performance-bounded-hooks fields that adr-kit's own dogfood `.adr-kit.json` (and downstream projects) already set: `pre_commit_timeout_ms`, `pre_push_timeout_ms`, `llm_timeout_ms`, `warn_on_exceed`. Config validation therefore failed with `'pre_commit_timeout_ms' was unexpected` before any ADR was evaluated, including against this repo's own config. The four knobs are now declared as permissive, documented properties; the change is additive, so previously-valid configs stay valid.

## [0.30.4] - 2026-06-13

### Fixed

- **`bin/bump-version` now also stamps the guide template's version line.** `templates/adr-kit-guide.md` opens with `<!-- adr-kit-guide vX.Y.Z -->`, which `/adr-kit:upgrade` uses to decide whether a project's copied guide is fresh; the line had been frozen at v0.18.0 because no release step updated it, so the freshness check would have reported every guide as stale forever. Found by running `/adr-kit:upgrade` on this repo itself. Covered by a lockstep test (template line must equal `plugin.json` version) and a bump fixture test.

### Changed

- **This repo now carries its own adr-kit footprint** (dogfooding): `CLAUDE.md` stub and the pre-commit wrapper at `.githooks/pre-commit` with `core.hooksPath` set, so Enforcement violations are caught locally before CI. ADR-003 deliberately carries no Enforcement block (process decision, no code surface).

## [0.30.3] - 2026-06-13

### Fixed

- **markdownlint failure in `skills/install-hooks/SKILL.md` (MD029).** The JSON hook-entry example sat unindented inside an ordered list, splitting the list and failing the `validate` workflow on main. The block is now indented as a continuation of list item 4; numbering is valid again and CI is green.

## [0.30.2] - 2026-06-13

### Changed

- **README rewritten around the decision lifecycle (capture, guard, maintain).** The old README grew feature-by-feature across eleven releases and read as a changelog with a table of contents. The new structure leads with what the toolkit is for (architecture decisions that AI coding agents actually follow), puts the agentic install paths first (Claude Code, Codex CLI, Copilot CLI, portable fallbacks, and the MCP server), and makes the upgrade story explicit: plugin updates flow automatically, copied artifacts are stamp-checked by the guardian and refreshed by `/adr-kit:upgrade`, and existing MADR / Nygard ADR sets import via `/adr-kit:migrate`. All 14 skills and the CLI engines are described in terms of what they do for a software project rather than when they shipped. Reference detail that moved out of the README (full config keys, hook internals) lives on in the project guide, INSTALL.md, and the CHANGELOG. No behavioural changes.

## [0.30.1] - 2026-06-13

### Fixed

- **`bin/bump-version` rewritten in pure stdlib Python (was bash).** The bash version shelled out to `python3` for each file edit. On Windows the `python3` command resolves to the Microsoft Store alias, which routes through the Python Install Manager; that launcher scans argv for a script file and dispatches on THAT file's shebang. Step 4 passed the bash-shebanged `templates/githooks/pre-commit` as an argument, so the launcher warned `shebang 'bash' ... treated as an arbitrary command` and executed bash instead of python, which crashed with cygheap fork errors during the v0.27.0 through v0.29.0 releases (stamps were applied by hand each time; the lockstep tests caught nothing missed). The rewrite spawns no child processes at all, so there is nothing for a launcher to misroute; it also needs no Git Bash, resolves the repo root from its own location (worktree-safe), and matches every other bin in this repo. Same CLI, same output, same exit codes. Invoke as `bin/bump-version X.Y.Z` (or `python bin/bump-version X.Y.Z` on Windows). 8 tests in `tests/test_bump_version.py`, including a structural guard that the script never gains a child-process call.

## [0.30.0] - 2026-06-12

### Added

- **MADR / Nygard format compatibility (task-5).** Lowers the switching cost for projects with existing ADR sets in the two dominant community formats.
  - `bin/adr-audit` now classifies every file in `docs/adr/` by template profile (`canonical` | `madr` | `nygard` | `unknown`) via a linear, fence-aware heuristic (`detect_template_profile`) and emits a new `template_profile` finding for MADR / Nygard shaped ADRs, pointing at `/adr-kit:migrate`. Advisory only; never blocks.
  - `/adr-kit:migrate` gains two named patterns: **Pattern G "MADR mapping"** (Context and Problem Statement to Context; Considered Options plus Pros and Cons to Alternatives Considered; Decision Outcome to Decision plus Consequences; frontmatter status to `## Status`) and **Pattern H "Nygard lift"** (the four Nygard sections map 1:1; TODO placeholders for Alternatives Considered, Related Decisions, References). Read-then-confirm posture unchanged.
  - Optional `template.profile` ("canonical" | "madr" | "nygard") in `.adr-kit.json` (`schemas/adr-kit-config.schema.json`): informational declaration of a project's source profile, surfaced in audit findings. Lint behaviour is unchanged.
  - Fixtures `tests/fixtures/madr/` and `tests/fixtures/nygard/` plus hand-migrated, lint-clean counterparts in `tests/fixtures/madr-migrated/` and `tests/fixtures/nygard-migrated/`; covered by `tests/test_template_profiles.py` (13 tests).
  - `docs/adr/ADR-003-template-profile-compatibility.md` records the input contract: the canonical seven-section template stays the only storage format; MADR and Nygard are import formats; detection is heuristic and advisory.

## [0.29.0] - 2026-06-12

### Added

- **`bin/adr-status`: Enforcement coverage metric (task-4).** The summary now reports `coverage_pct` (percent of Accepted ADRs carrying a parseable `## Enforcement` block with at least one rule) and `llm_judge_pct` (percent of Accepted ADRs whose Enforcement includes `llm_judge: true`). Present in all three output formats (json, markdown, table). Additive only: all existing field names are unchanged. 12 tests in `tests/test_adr_status_coverage.py`.
- **`bin/adr-guardian`: trend history (task-4).** `adr-guardian stamp` now appends an entry to a new append-only `trend` list in `.adr-kit-state.json`: `{date, tier, total_adrs, drift_violations, retire_candidates, suggest_hits, audit_findings, coverage_percent}`. Fields for the tier that did not run are carried from the last known values (or null). Capped at 52 entries (roughly a year of weekly sweeps; oldest dropped). New `stamp --coverage PCT` flag records the coverage percent that the guardian skill reads from `adr-status --format json`. Corrupt trend data degrades silently. When at least two sweeps have been stamped, the SessionStart nudge block adds a one-line delta vs the previous sweep, e.g. `trend: drift 2 -> 0, retire 1 -> 2, coverage 40% -> 45%`: the guardian becomes a KPI with memory instead of a snapshot.

## [0.28.0] - 2026-06-12

### Added

- **`bin/adr-related`: read-only ADR dependency graph CLI (task-3).** `adr-related ADR-NNN [--adr-dir docs/adr] [--format human|json]` prints outbound edges (Related Decisions entries, Supersedes claims, Superseded by / Amended by status refs) and inbound edges (every other ADR referencing the target, with reference kind: related, supersedes, superseded-by, amended-by, mention). Whole-token id matching (ADR-043 never matches inside ADR-0430). Dangling references are flagged. Exit 0 on success, 2 on unknown id or missing directory. Stdlib-only, linear regexes. 24 tests in `tests/test_adr_related.py`.
- **`/adr-kit:related` skill (task-3):** thin read-only wrapper around `bin/adr-related`. Model-invocable; safe from parallel subagents.
- **`/adr-kit:supersede` skill (task-3):** guided supersession workflow (`disable-model-invocation: true`). Shows the target's dependency graph first, drafts the superseding ADR via the adr-generator subagent (Status: Proposed, back-linked), and only after user approval flips the old ADR's Status line to `Superseded by ADR-M` and appends status_history entries on both sides. Verifies the chain with `bin/adr-related` + `bin/adr-lint`. Hard-stops when the target already carries a `Superseded by` pointer at a different ADR (never overwrites an existing supersession; same invariant the adr-lint consistency gate enforces since v0.25.0). Never auto-accepts the new ADR.

## [0.27.0] - 2026-06-12

### Added

- **Copied-artifact staleness detection (task-15).** Plugin-level hooks refresh automatically when the plugin updates, but artifacts copied into a project freeze at install time: the git pre-commit wrapper and the project-scoped guardian entry in `.claude/settings.json` keep resolving the newest engines, yet their own feature surface lags until refreshed. The templates now carry version stamps (`ADR_KIT_WRAPPER_VERSION="X.Y.Z"` in `templates/githooks/pre-commit`, `_wrapper_version` in `templates/cc-settings/guardian-hook-entry.json`) that `bin/bump-version` keeps in lockstep with the release. `bin/adr-guardian check` compares the stamps against the installed plugin version with pure file reads (no subprocesses) and adds a `wrapper: ... STALE -> /adr-kit:upgrade` line to the SessionStart nudge; a stale wrapper counts as a due item, so it surfaces even when both sweep tiers are fresh, riding the existing nudge cooldown. Staleness rules avoid false positives: an up-to-date stamp is silent, a non-adr-kit pre-commit hook is never reported, and an unstamped settings entry is reported present but never stale (it self-resolves engines). New `adr-guardian artifacts [--format json]` subcommand exposes the same report for skills and manual inspection. 17 tests in `tests/test_adr_guardian_artifacts.py`, including lockstep guards that fail when a release bump misses the template stamps.

### Changed

- **`/adr-kit:upgrade` generalized into the artifact refresh driver (task-15).** Previously a one-shot v0.11 to v0.12 migration. New Step 0 runs `adr-guardian artifacts` and refreshes each stale artifact idempotently: the git wrapper is replaced from the current template (diff-and-ask when locally edited), the settings guardian entry is rewritten with JSON-structural editing (sibling hooks untouched), and an outdated `.claude/adr-kit-guide.md` is refreshed. Artifacts the plugin cannot reach (GitHub Action `@vX` pins, `pre-commit` framework `rev:`) are reported with the right tool to bump them (Dependabot/Renovate, `pre-commit autoupdate`). The legacy v0.11 to v0.12 migration remains as the one-time path.

## [0.26.0] - 2026-06-12

### Added

- **`/adr-kit:review` skill (`skills/review/SKILL.md`): PR/branch-level ADR audit (task-14).** Audits the COMMITTED work of a branch or PR (merge-base with the base ref, default `origin/main`; `gh pr view` supplies the base and PR metadata when available) in two passes. Enforcement: the range diff is piped through `bin/adr-judge --diff` (declarative-only, key-free; identical verdicts to the pre-commit hook and the CI action), with the three `/adr-kit:judge` resolution paths offered per violation. Discovery: detects NEW architectural decisions the range introduces that no ADR documents yet, using both the headless `bin/adr-suggest` detector and an in-session vigilance pass over the diff PLUS the stated intent (commit subjects/bodies, PR title/body), because decisions are often confessed in prose while the diff looks like plumbing. Candidates are deduped against the existing set via `bin/adr-context`; the user picks which findings to act on; picked decisions are drafted via the `adr-generator` subagent with `Status: Proposed` and never auto-accepted. Degrades honestly: no `gh` means git-log intent only, no `claude` CLI means enforcement-only plus the in-session pass.
- **`bin/adr-suggest --intent-file <path>` (task-14).** Appends the change author's stated intent (commit messages, PR description) to the decision-detector prompt as untrusted data inside the same content-derived sentinel fences introduced by the task-12 hardening: evidence of what the change intends, never instructions to the model (PR bodies are author-controlled). Content is truncated at 8000 chars. Without the flag the prompt is byte-identical to the no-intent form; the response schema, advisory posture, and opt-in gate are unchanged. A bad path is a usage error (exit 2), matching `--diff`. Four new tests in `tests/test_adr_suggest.py`.

## [0.25.0] - 2026-06-12

### Security

- **Prompt-injection hardening for the LLM judge and suggest passes (task-12).** Diff and ADR content in `bin/adr-judge` and `bin/adr-suggest` prompts are now wrapped in unique sentinel data fences (`<<<ADR-KIT-DATA-<sha256-prefix> BEGIN/END>>>`), with an explicit instruction that fenced content is untrusted data and any instructions inside it must be ignored. The fence token is derived from a SHA-256 of the fenced content, so a diff cannot pre-place a matching END marker: embedding any guessed token changes the token. The ADR fence token depends only on the ADR set, preserving the prompt-cache prefix.
- **Enforcement blocks are schema-validated before use (task-12).** `bin/adr-judge` now structurally validates every Enforcement block (known rule kinds only, required non-empty string `pattern`, optional `path_glob`/`message`, boolean `llm_judge`; mirrors `schemas/adr-enforcement.schema.json`, stdlib-only with jsonschema as optional deeper layer) BEFORE any rule is compiled as a regex or lands in an LLM prompt. Invalid blocks are reported as ADVISORY `enforcement_config` findings and never silently used; malformed JSON syntax keeps the existing exit-2 contract. Tests in `tests/test_adr_judge_security.py`, including a forged-END-marker test and a 4-way parallel-run concurrency test.

### Added

- **Judge override audit trail (task-10).** A pre-commit FAIL can now be overridden for ONE named ADR per commit via `ADR_KIT_OVERRIDE="ADR-NNN: <reason>" git commit ...`. The override downgrades only that ADR's violations to loudly printed warnings (other ADRs still block), refuses an empty reason, and appends a record (timestamp, ADR id, reason, git user, SHA-256 of the judged diff) to the untracked log `docs/adr/.adr-kit-overrides.jsonl` (excluded via `.git/info/exclude`). Judging stays read-only: no tracked file is touched while a staged diff is evaluated. Convention: the commit message SHOULD carry a matching `ADR-Override: ADR-NNN <reason>` trailer. New modes: `adr-judge --check-override` (validate the env var) and `adr-judge --audit-overrides [--json]` (read-only reconciliation of the local log against commit trailers).
- **Concurrent-supersession detection (task-10)** in the adr-lint consistency gate. Two or more Accepted ADRs declaring `Supersedes ADR-NNN` for the same target now FAIL, with every claimant file named; the message reports whether the target's Status line names a successor. A single clean supersession still passes. Tests in `tests/test_adr_judge_override.py` and `tests/test_adr_lint_supersession.py`.

## [0.24.0] - 2026-06-12

### Added

- **`bin/adr-watch`: in-flight ADR guidance for just-edited files (task-6).** New stdlib-only Python bin that closes the guidance gap between SessionStart context injection (guardian) and pre-commit enforcement (adr-judge). Given one or more edited file paths it prints at most three compact one-line nudges naming the Accepted ADRs that likely apply. Two signals: Enforcement-block `path_glob` match (strongest, reuses the adr-judge glob translator including `**` and `{a,b}` brace expansion) and adr-context-style keyword relevance of the path against ADR title + Decision text. Deterministic, key-free, no LLM, no network; each ADR file is read exactly once and all regexes are precompiled and linear-time. Always exits 0 (advisory, never blocks). Self-guards: silent no-op when the working directory has no `docs/adr/` with ADRs.
- **PostToolUse hook wiring (plugin-level, task-6).** `.claude-plugin/plugin.json` now declares a `PostToolUse` hook (matcher `Edit|MultiEdit|Write`) invoking the new `.claude-plugin/hooks/post-tool-use` bash script via the existing `run-hook.cmd` cross-platform polyglot. In `--hook` mode adr-watch extracts `tool_input.file_path` from the payload and emits the nudges as a `hookSpecificOutput.additionalContext` envelope under Claude Code, or plain text elsewhere. Degrades silently (exit 0) when Python, the bin, or the payload is missing or malformed.
- **Per-session nudge cooldown (task-6).** The same ADR+file pair is not nudged again within `watch.cooldown_hours` (default 4). State lives under a separate `watch` key in `docs/adr/.adr-kit-state.json`, written atomically via `os.replace`; sibling guardian keys are preserved and corrupt state is tolerated as empty. New `watch` config block (`enabled`, `cooldown_hours`) in `schemas/adr-kit-config.schema.json`. 23 tests in `tests/test_adr_watch.py`.

## [0.23.0] - 2026-06-12

### Added

- **`bin/adr-renumber`: safely renumber one ADR for the merge-collision workflow (task-8).** Dry-run by default (prints the full plan: file rename, heading rewrite, and every cross-reference rewrite with file:line); `--apply` executes. `--to ADR-NNN` is optional and defaults to the next free number (max in use + 1; gaps are not reused so retired numbers stay retired). Updates Related Decisions entries, "Superseded by" and "Amended by" status strings, Status History mentions, and plain ADR-NNN references across all ADRs in the directory. Whole-token matching only: renumbering ADR-043 never touches ADR-0430. Refuses (exit 2) when the target number is taken, the source is missing, or the source number is ambiguous (duplicates: pass the file path). Stdlib-only, linear regexes. Tests in `tests/test_adr_renumber.py`.

### Changed

- **`bin/adr-lint`: the duplicate-number consistency finding now names every file sharing the number and points at `bin/adr-renumber` as the fix.** Detection itself pre-existed and already failed CI (consistency is `always_strict` regardless of `strict_from`); this release adds the post-merge regression tests and the actionable message.

## [0.22.0] - 2026-06-12

### Added

- **Guardian team mode (task-9).** New weekly CI-cron sweep workflow `.github/workflows/adr-guardian-audit.yml` runs the cheap tier only (`adr-lint` + `adr-retire` + `adr-status`), aggregates one markdown report, and maintains a single "ADR guardian audit" tracking issue (created on findings, body updated on later runs, closed when clean). Report-only: never fails the build, never runs an LLM (ADR-001 posture), no secrets beyond `GITHUB_TOKEN`. A copy-paste variant for downstream projects ships in `templates/github-workflows/adr-guardian-audit.yml`. The guardian skill (`skills/guardian/SKILL.md`) documents the split: SessionStart nudge = per-developer freshness, CI cron = shared team visibility.

### Fixed

- **Multi-session-safe guardian state (task-9).** `bin/adr-guardian` now writes `.adr-kit-state.json` via a unique per-process temp file plus `os.replace` (atomic on POSIX and Windows), tolerates corrupt or partial state files on read (treated as empty state, one stderr warning, file overwritten by the next stamp), and takes a best-effort non-blocking advisory lock (`fcntl`/`msvcrt`, guarded by `ImportError`) around writes. Last-writer-wins semantics are documented in the script header; the state file is per-machine advisory data, not a ledger. Tests in `tests/test_adr_guardian_state.py`.

## [0.21.0] - 2026-06-12

### Added

- **`bin/adr-mcp`: thin Model Context Protocol server over stdio (task-7).** Hand-rolled JSON-RPC 2.0 on the Python stdlib only (no `mcp` package), newline-delimited messages. Exposes 4 key-free tools that wrap the existing CLIs via subprocess: `adr_context` (heuristic ADR ranking), `adr_judge` (declarative Enforcement pass on a diff, never `--llm`), `adr_status` (repository health JSON), `adr_quality` (per-ADR grades). `adr-suggest` is deliberately not exposed: it is LLM-only and the MCP server stays key-free. Project root via `--root`, `PROJECT_ROOT` env, or cwd; ADR directory via `--adr-dir` (default `<root>/docs/adr`). Brings the same guardrails to compatible local stdio clients without the skills format. Tests in `tests/test_adr_mcp.py` (14 end-to-end stdio tests).

## [0.20.1] - 2026-06-07

### Fixed

- **`bin/bump-version` now also bumps `.claude-plugin/marketplace.json`.** The helper previously updated only `plugin.json` and `CHANGELOG.md`, leaving the marketplace manifest to be edited by hand. `marketplace.json` `plugins[].version` is the field the Claude Code plugin update system compares against, so a bump that misses it ships to the repo but is never picked up by clients (the propagation gap behind the "fixed but still serving the old version" reports, e.g. issue #6). The script now updates the marketplace entry whose `name` matches `plugin.json`, and errors out if no such entry exists rather than bumping silently. Documented and staging hint updated to include `marketplace.json`.

## [0.20.0] - 2026-06-07

### Added

- **`/adr-kit:context` skill (`skills/context/SKILL.md`) — load the relevant ADRs before implementing (issue #7).** Projects with many ADRs make it expensive for an agent to know which decisions apply before starting work: loading all of them burns the context window, loading none means existing decisions get ignored. This skill takes a topic (e.g. `"mqtt discovery"`, `"caching"`) and drives the existing `bin/adr-context` ranker (`--format json --limit 5`), then reads the top hits and presents them as readable context — `ADR-NNN — title`, a one-line paraphrase of the `## Decision`, the file path, and the relevance score — followed by a one-or-two-sentence statement of the net constraint. Empty results are reported honestly ("No ADRs match '<topic>'; all existing ADRs may apply, or none constrain this work") rather than silently. Read-only and safe to call from parallel subagents; no MCP server required (unlike the `adr_planning_context` MCP tool in the `kschlt/adr-kit` fork, which has a known subagent-blocking issue). The `bin/adr-context` CLI and its 20 tests already shipped; this release adds the missing slash-command wrapper that exposes it in Claude Code.

## [0.19.2] - 2026-06-07

### Fixed

- **Catastrophic regex backtracking (ReDoS) in `## Enforcement` parsing — remaining tools (issue #9 follow-up).** v0.19.1 fixed the nested lazy quantifier `(?:.*?\n)*?` in `bin/adr-retire` only. The identical pattern lived on in three sibling tools that also parse `## Enforcement` blocks: `bin/adr-judge` (the pre-commit / CI enforcement gate), `bin/adr-generate-scripts`, and `bin/adr-lint`. A fence-less `## Enforcement` section (heading with prose but no ` ```json ` block) therefore still hung those tools — most importantly `adr-judge`, which runs on every commit. De-nested the quantifier (`(?:.*?\n)*?` → `.*?`); a single lazy quantifier under `re.DOTALL` is linear and behaviour-identical on properly-fenced ADRs. `bin/adr-status` already used a single non-nested `.*?` and was unaffected. Added `tests/test_enforcement_redos.py` — a parametrized guard across all three tools asserting linear runtime, no nested quantifier in the pattern, and continued matching of fenced blocks.

## [0.19.1] - 2026-06-05

### Fixed

- **`bin/adr-retire` hung on ADRs with a fence-less `## Enforcement` section (#9).** `ENFORCEMENT_BLOCK_RE` used a nested lazy quantifier `(?:.*?\n)*?` under `re.DOTALL`. When an ADR had a `## Enforcement` heading but no ` ```json ` fenced block to anchor on, the regex backtracked catastrophically (~0.75s for a single 7.5KB ADR, growing with file size), stacking into a multi-minute hang across a real ADR set (observed on a 123-ADR project where 4 ADRs carried prose-only "manual review" Enforcement notes). Replaced with the linear, lookahead-anchored `extract_section("Enforcement")` plus a simple non-nested `JSON_FENCE_RE`. Behaviour is preserved (a fence-less Enforcement section yields no rules and `policy_mismatch` 0.0, identical to the previous non-match path); the unused `ENFORCEMENT_BLOCK_RE` is removed. Regex work drops from a timeout to 0.118s over 128 ADRs, with verified capture parity against all properly-fenced ADRs. Added regression test `test_enforcement_without_json_fence_scores_zero_quickly`.

## [0.19.0] - 2026-05-31

### Added

- **`.github/actions/adr-judge/action.yml` — reusable composite GitHub Action for PR-level enforcement.** Computes the PR diff via `git diff --unified=0 origin/<base>...HEAD` (using `GITHUB_BASE_REF`), fetches the base branch explicitly so shallow clones work, downloads `bin/adr-judge` from the same tag the action was loaded from, and pipes the diff to `adr-judge --diff - --adr-dir`. **Declarative-only by default** — no `--llm` flag, no API key, no `claude` CLI required in the runner. Exits 1 on any Enforcement-block violation, 0 on a clean diff, 2 on config/input error.
- **`.github/workflows/adr-judge-self.yml` — self-dogfood workflow.** Runs the composite action against adr-kit's own `docs/adr/` on every PR targeting `main`. Trigger is `pull_request` only (`push` excluded because `GITHUB_BASE_REF` is empty on push commits and the PR diff collapses to nothing). Confirms declarative-only enforcement gates work with no secrets.
- **`bin/adr-judge-precommit` — thin Python wrapper for the `pre-commit` framework.** The framework passes staged filenames to hooks, but `bin/adr-judge` needs the diff on stdin. This wrapper: (1) runs `git diff --cached --unified=0`, (2) pipes the result to the sibling `bin/adr-judge` resolved via `Path(__file__).resolve().parent`, (3) propagates the exit code. Sibling-resolution means it works regardless of PATH, consistent with how the native pre-commit hook resolves `bin/adr-judge` via the plugin cache.
- **`.pre-commit-hooks.yaml` — pre-commit framework hook declaration.** Declares an `adr-judge` hook (`id: adr-judge`, `language: script`, `pass_filenames: false`, `stages: [pre-commit]`, `minimum_pre_commit_version: "2.18.0"`) that invokes `bin/adr-judge-precommit`. Declarative-only by default. Enables teams already using the `pre-commit` framework to register enforcement without writing a native git hook.
- **README "CI integration" section extended.** New sub-section "PR-level enforcement: `bin/adr-judge`" (after the existing `adr-lint` section) with: a copy-paste GitHub Actions workflow snippet for downstream projects; a pre-commit framework usage snippet (`.pre-commit-config.yaml`); honest documentation of the opt-in LLM path (requires the `claude` CLI authenticated in the runner — an `ANTHROPIC_API_KEY` alone is not sufficient; declarative-only is the supported default).
- **`tests/test_adr_judge_precommit.py` — four pytest tests** covering: exit 1 on a staged violation, exit 0 on a clean staging area, exit 0 on an empty staging area, and static verification that `bin/adr-judge` exists at the expected sibling path.

### Notes

- Both features are declarative-only and key-free by default, consistent with the v0.17.0 LLM opt-in posture.
- No ADR authored for v0.19.0: CI enforcement and pre-commit delivery are additive tooling within the existing `bin/adr-judge` contract, not new interfaces, dependencies, or NFR shifts. The roadmap explicitly targets an ADR for v0.22.0 (MADR/Nygard format compatibility) and v0.18.0 (guardian), not v0.19.0.

## [0.18.0] - 2026-05-31

### Added

- **`bin/adr-guardian` -- ADR-set health detector.** New stdlib-only Python bin with three subcommands: `check` (the SessionStart hook entry point; read-only, always exit 0, never spawns), `stamp <cheap|llm>` (records sweep completion in `.adr-kit-state.json`), and `state` (inspect current state). The `check` subcommand computes due tiers vs. the two-tier clocks, applies `nudge_cooldown_hours` throttle, and emits the `[adr-guardian]` block as Claude Code `hookSpecificOutput.additionalContext` JSON when a tier is due.
- **`/adr-kit:guardian` skill** (`skills/guardian/SKILL.md`) -- the in-session ADR-set health sweep. Orchestrates `adr-judge` (declarative drift), `adr-retire` (stale detection), `adr-lint`/`adr-status` (health), `adr-suggest` (missing-ADR detection, LLM tier), and `adr-judge --llm` (full audit, LLM tier). Applies mix-by-finding-type responses (drift = prominent; missing ADR = passive; stale = autonomous draft; health = report). Confirms cost before any LLM-tier phase. Stamps state when done. Accepts optional argument `cheap | llm | all`.
- **Two-tier cadence**: cheap tier (drift + retire + lint) runs daily (`guardian.drift_stale_days: 1`, free); LLM tier (suggest + audit) runs bi-weekly (`guardian.llm_stale_days: 14`, costs ~$0.10-0.30). Each tier stamped independently so the clocks do not interfere.
- **Mix-by-finding-type responses**: drift violations surfaced prominently (highest signal); missing-ADR suggestions passive (user picks); stale ADRs get an autonomous draft for review (never auto-applied); ADR-set health reported with fix offer. Per spec 6.
- **Both hook-install paths shipped** (spec 7): plugin-level (`hooks` key in `.claude-plugin/plugin.json` + `.claude-plugin/hooks/`) auto-registers when the plugin is enabled globally; project-scoped instructions added to `skills/install-hooks/SKILL.md` for JSON-structural add/remove of the SessionStart entry in `.claude/settings.json` (idempotent, never clobbers sibling hooks).
- **`guardian` config block** in `schemas/adr-kit-config.schema.json` with full descriptions and defaults: `enabled` (default `true`), `drift_stale_days` (default 1), `llm_stale_days` (default 14), `nudge_cooldown_hours` (default 24), `llm_autorun` (default `false`, consistent with ADR-001 opt-in posture).
- **Gitignored state file**: `docs/adr/.adr-kit-state.json` added to `.gitignore` (per-machine, never committed). `/adr-kit:init` adds it to the project gitignore during setup.
- **Guardian section in `templates/adr-kit-guide.md`** (v0.18.0 header bump): documents the two-tier cadence, mix-by-finding-type table, config block, both hook-install paths, and in-session model behaviour for the `[adr-guardian] ... DUE` block.
- **`/adr-kit:init` Step 5b** -- guardian setup step offering `enabled` toggle, project-scoped hook install, and gitignore update.
- **`docs/adr/ADR-002-adr-guardian-session-start-staleness-detector.md`** -- dogfood ADR recording the guardian design decision (Status: Proposed).
- **`tests/test_adr_guardian.py`** -- 29 tests covering due/not-due logic across both clocks, cwd-guard no-op, `nudge_cooldown_hours` throttle, retire-candidate state display, `stamp` updates, `state` round-trip, always-exit-0 under corrupt state/config, and JSON envelope format (Claude Code `hookSpecificOutput` path).

### Changed

- `.claude-plugin/plugin.json`: description updated to mention guardian; `hooks` key added declaring the SessionStart hook; version bumped to 0.18.0.

## [0.17.0] - 2026-05-31

### Changed (BREAKING DEFAULT)

- **Per-commit LLM judge is now OPT-IN.** The pre-commit hook no longer hard-codes `--llm`. Existing users who relied on automatic per-commit LLM judging must set `judge.llm_enabled: true` in `docs/adr/.adr-kit.json` to restore the old behaviour. One-liner migration: `echo '{"judge":{"llm_enabled":true}}' > docs/adr/.adr-kit.json`. Enable for a single commit: `ADR_KIT_LLM=1 git commit ...`. On-demand LLM review is always available via `/adr-kit:judge` and `adr-judge --llm` — these are unaffected by this change.
- **`suggest.enabled` default flipped `true` → `false` (opt-in).** The per-commit `adr-suggest` nudge pass is now off by default. Enable per-project: `suggest.enabled: true` in `.adr-kit.json`. Enable per-commit: `ADR_KIT_SUGGEST=1 git commit ...`.

### Added

- **`judge.llm_enabled` config switch** (default `false`): user-facing master switch for the per-commit LLM pass. `/adr-kit:init` now interactively asks whether to enable it and writes the choice to `docs/adr/.adr-kit.json`. The legacy `judge.llm_default` key is preserved for CI / direct-CLI back-compat.
- **Flock concurrency guard in the pre-commit hook.** When `flock` is available, the hook takes a non-blocking advisory lock (`$ROOT/.git/adr-kit-judge.lock`). Under lock contention (rapid or parallel commits) the cheap declarative gate still runs; LLM passes are suppressed via `ADR_KIT_NO_LLM` for that commit instead of piling up concurrent `claude -p` calls. Degrades gracefully to no-lock on bare Windows cmd.exe where `flock` is absent.
- **`/adr-kit:init` interactive LLM opt-in.** After hook install the skill now prints a cost/latency notice (up to 2 Sonnet calls per commit, 120s timeout each, ~$0.10–$0.30 per commit) and asks two questions (both defaulting to No): enable per-commit LLM judging, enable per-commit ADR-suggest. Writes the chosen booleans to `docs/adr/.adr-kit.json`. Adds a `llm:` line to the wrap-up summary.

### Fixed

- **`bin/adr-suggest` now honors `suggest.enabled`** (previously documented but never read — latent no-op). The opt-in check fires before any diff reading or LLM invocation, mirroring the judge LLM opt-in pattern.

## [0.16.0] - 2026-05-29

### Added

- **`bin/adr-suggest` — advisory ADR-needed detector.** A new bin, distinct from `bin/adr-judge`. Where `adr-judge` *enforces* existing Accepted ADRs and can block a commit, `adr-suggest` runs one LLM pass over the staged diff to detect whether the change introduces a *new* architectural / contract / dependency decision **not yet covered by any ADR**, and prints a one-line nudge to run `/adr-kit:adr`. It **never blocks the commit**: the advisory path always exits 0. A missing `claude` CLI, a timeout, a non-zero exit, a malformed response, or a docs/lockfile-only diff all resolve to a silent skip. CLI: `adr-suggest [--diff PATH|-] [--adr-dir DIR] [--config PATH] [--llm-cmd CMD] [--llm-timeout SECS] [--json] [--repo-root ROOT]`.
  - Reuses the same LLM-command resolution as `adr-judge` (`--llm-cmd` > `ADR_KIT_LLM_CMD` env > `.adr-kit.json` `suggest.llm_cmd`/`suggest.llm_model` > `judge.llm_cmd`/`judge.llm_model` > default `claude -p --model claude-sonnet-4-6`), including the repo-config binary allowlist (SEC-HIGH).
  - Existing ADR ids + titles + one-line decisions are passed to the model so it does not suggest a duplicate of a decision already recorded.
  - Advisory output goes to **stderr** only (stdout stays pipe-clean); `--json` emits the parsed result object `{needs_adr, confidence, reason, suggested_title, category}` to stdout.
- **Pre-commit hook: advisory suggestion section** (`templates/githooks/pre-commit`). A third section runs `adr-suggest` after the `adr-judge` pass, piping `git diff --cached --unified=0` to it. Its exit status is swallowed (`|| true`) so it can never fail a commit. Gated by `ADR_KIT_SUGGEST_DISABLE` (runs by default; set `=1` to skip).
- **Config: `suggest.*` block** in `.adr-kit.json` (`schemas/adr-kit-config.schema.json`). Optional, back-compatible (absent block = defaults): `suggest.enabled` (bool, default true), `suggest.llm_cmd` / `suggest.llm_model` (fall back to `judge.*`), `suggest.llm_timeout_seconds` (default 120).
- **Tests**: `tests/test_adr_suggest.py` — fake-`claude` binary approach mirroring `tests/test_adr_judge_llm.py`. Covers high-confidence advisory, needs_adr=false silence, low-confidence silence, docs-only / lockfile / empty-diff skips (no LLM call), missing CLI, malformed JSON, `--json` output, fenced-JSON parsing, and assertions that existing ADR titles reach the prompt.

## [0.15.0] - 2026-05-27

### Fixed / Improved (37 review findings from multi-agent code review)

#### Security

- **llm_cmd allowlist** (`bin/adr-judge`): `judge.llm_cmd` from `.adr-kit.json` is now validated against an explicit allowlist of known Claude CLI binaries. Unknown binaries trigger a warning and fall back to the default; `ADR_KIT_LLM_CMD` env and `--llm-cmd` CLI flag remain unrestricted (operator-controlled).
- **ReDoS guard** (`bin/adr-judge`): ADR-controlled regex patterns are now executed inside a `threading.Timer`-based 1-second timeout per pattern. A timed-out pattern produces an ADVISORY finding instead of hanging the pre-commit hook indefinitely.
- **Path traversal in require_pattern** (`bin/adr-judge`): diff-derived file paths are validated to resolve under `repo_root` before reading. Absolute paths and `..` sequences are rejected.
- **LLM stderr info disclosure** (`bin/adr-judge`): verbose LLM error output is now gated behind `ADR_KIT_DEBUG=1`; default messages are generic.
- **Generated shell script — ERE validation** (`bin/adr-generate-scripts`): generated `validate.sh` now tests each pattern with a `printf | grep` preflight at startup and warns loudly if any pattern is not valid POSIX ERE.
- **Generated shell script — echo/printf** (`bin/adr-generate-scripts`): replaced `echo "$line"` with `printf '%s\n' "$line"` to avoid xpg_echo backslash interpretation.
- **Pre-commit hook glob expansion** (`templates/githooks/pre-commit`): replaced `ls -d | sort -V | tail -1` path resolution with a bash nullglob array, eliminating the ls-parsing vulnerability.
- **adr-retire symlink traversal** (`bin/adr-retire`): replaced unbounded `rglob('*')` with `os.walk(followlinks=False)` and a 50,000-file cap.

#### Performance

- **glob_to_regex caching** (`bin/adr-judge`): module-level `_GLOB_PATTERN_CACHE` eliminates O(ADRs × rules × files × globs) redundant `re.compile()` calls.
- **JSON schema singleton** (`bin/adr-judge`, `bin/adr-lint`): `schemas/adr-enforcement.schema.json` is now loaded and compiled into a `Draft7Validator` once per process instead of once per ADR.
- **Section regex precompilation** (`bin/adr-lint`, `bin/adr-quality`): `REQUIRED_SECTIONS` heading patterns precompiled at module load.
- **adr-status single-pass parsing** (`bin/adr-status`): introduced `AdrRecord` dataclass and `parse_adr()` — each ADR is read and all fields extracted exactly once. All formatters consume the cached record, eliminating 500-700 redundant regex scans on 100-ADR sets.
- **Pre-commit hook streaming** (`templates/githooks/pre-commit`): replaced `DIFF=$(git diff ...)` buffering with direct pipe streaming to `adr-judge`.
- **Generated validate.sh** (`bin/adr-generate-scripts`): rewritten from O(lines × rules × subprocess_spawn) to O(rules) subprocess spawns via single-pass `grep -nE` per rule.
- **adr-context domain inference** (`bin/adr-context`): replaced ~125 `in text_lower` substring checks per ADR with per-domain compiled word-boundary regexes.
- **adr-context metadata extraction** (`bin/adr-context`): 6 inline `re.search()` calls per ADR replaced with module-level compiled constants.
- **adr-quality gate regexes** (`bin/adr-quality`): section presence/body patterns and acronym regex precompiled at module level.
- **Diff size check** (`bin/adr-judge`): `len(diff_text)` replaces `len(diff_text.encode("utf-8"))`.
- **Dry-run shortcut** (`bin/adr-judge`): `--dry-run-enforcement ADR-NNN` now globs only the target ADR directly.

#### Architecture

- **Structured quality issues** (`bin/adr-quality`): `gate_*()` functions now return `QualityIssue` dataclasses with stable `code`, `detail`, `severity` fields instead of raw strings. JSON output includes `code`, `detail`, `severity`, `message` per issue.
- **Unified vague-language list** (`bin/adr-lint`, `bin/adr-quality`): both tools now share a canonical 8-word set (`appropriate`, `somehow`, `maybe`, `possibly`, `might`, `could`, `should consider`, `might consider`).
- **Quality gate boundary documented** (`bin/adr-lint`, `agents/adr-generator.md`): `check_quality_gate()` docstring and Step 3 in `agents/adr-generator.md` now explicitly state that `adr-lint` and `bin/adr-quality` run different gate sets with different thresholds.
- **Schema extended** (`schemas/adr-kit-config.schema.json`): `context` and `retirement` top-level config blocks now documented with full property schemas.
- **Legacy config key removed** (`bin/adr-context`): `min_relevance_threshold` fallback removed; canonical key is `min_score`.
- **adr-status — amended status** (`bin/adr-status`): `by_status` histogram now buckets "amended" correctly; `CANONICAL_STATUSES` constant defined.
- **adr-status — no-op flags removed** (`bin/adr-status`): `--show-enforcement` and `--show-retirement` flags (shipped as no-ops in v0.14.0) removed.
- **adr-context — bare except fixed** (`bin/adr-context`): silent `except Exception: pass` replaced with stderr warning.
- **adr-context — infer_task_domain returns Optional** (`bin/adr-context`): returns `None` instead of "backend" when no domain matches; scoring skips domain_tag credit for unknown domains.
- **CLI format consistency** (`bin/adr-retire`, `bin/adr-lint`): adr-retire default changed from `json` to `text`; adr-lint accepts `text` as alias for `human`.
- **adr-generate-scripts cleanup** (`bin/adr-generate-scripts`): extracted `_make_executable()` helper, removed duplicated chmod blocks and unused `import os`.

#### Testing

- **Wall-clock performance tests** (`tests/test_adr_performance.py`): 3 new `@pytest.mark.slow` tests assert timing budgets on 50-ADR synthetic suites for adr-judge (<3s), adr-status (<500ms), adr-context (<600ms).
- **pytest.ini**: registered `slow` marker to eliminate PytestUnknownMarkWarning.
- **225 tests passing**, 2 skipped (Windows shell-script execution).

## [0.14.0] - 2026-05-27

### Added

#### Phase 1 — Governance backbone (TASK-710, TASK-711)

- **Append-only status history**: `bin/adr-judge` parses and appends immutable
  `status_history` YAML entries; `--migrate-status-history` migrates legacy ADRs.
  `bin/adr-lint` validates histories via a new `audit` gate (default-on) while
  keeping unmigrated v0.13 ADRs compatible.
- **Automated retirement detection**: new `bin/adr-retire` tool and
  `/adr-kit:retire` skill score candidates by staleness, technology disappearance,
  broken supersession references, and risky policy patterns. Optional
  `adr-retire-audit.yml` GitHub Actions workflow runs weekly.

#### Phase 2 — Intelligence layer (TASK-712, TASK-713)

- **Profiling and dry-run**: `bin/adr-judge --profile` emits per-ADR timing
  breakdowns; `--dry-run-enforcement ADR-NNN` tests a single ADR against staged
  diffs without blocking the commit.
- **Semantic relevance ranking**: new `bin/adr-context` tool ranks ADRs for a
  task query using five weighted heuristic signals (keyword match, domain tag,
  related decisions, acceptance status, recency). Configurable weights in
  `.adr-kit.json`. Injected into `agents/adr-generator.md` context-loading step.

#### Phase 3 — Enforcement quality (TASK-714, TASK-715)

- **Policy block validation**: `bin/adr-lint` gains `--gates policy` and
  `--gates quality` (both opt-in). The policy gate validates Enforcement JSON
  against `schemas/adr-enforcement.schema.json`, compiles all regex patterns, and
  warns on anti-patterns (unescaped dots, excessive wildcards, broad globs). The
  quality gate flags vague language, missing metrics, and too few alternatives.
- **Standalone validation script generation**: new `bin/adr-generate-scripts` tool
  produces self-contained `validate.py` (Python stdlib only) and `validate.sh`
  scripts in `.generated/`. Scripts enforce the same rules as `adr-judge` without
  requiring adr-kit as a dependency, suitable for embedding in foreign CI
  pipelines.

#### Phase 4 — Observability and agent guidance (TASK-716, TASK-717)

- **ADR health dashboard**: new `bin/adr-status` tool reports total count, status
  breakdown, average age, enforcement health per ADR, and top retirement
  candidates. Output in `--format json|markdown|table`.
- **Quality scoring**: new `bin/adr-quality` tool grades each ADR A–D via four
  weighted gates (completeness 40%, evidence 20%, clarity 20%, consistency 20%).
  Returns structured JSON or human-readable text; exits 1 when grade is below B.
- **Agent decision tree**: `agents/adr-generator.md` gains a "When to Create an
  ADR" decision tree and post-decision quality check section.

#### Cross-cutting improvements

- **Python 3 availability check**: `skills/init/SKILL.md` now checks for Python
  3.9+ before any installation step, with guided installation instructions for
  macOS (Homebrew), Linux (apt/dnf/pacman) and Windows (winget). The pre-commit
  hook template (`templates/githooks/pre-commit`) also checks for Python 3 at
  hook runtime and exits gracefully with installation hints if absent.
- **`.adr-kit.json`**: new `context.weights`, `context.default_limit`,
  `context.min_score`, `retirement.*`, and timeout fields
  (`pre_commit_timeout_ms`, `pre_push_timeout_ms`, `llm_timeout_ms`,
  `warn_on_exceed`).
- **222 tests passing**, 2 skipped (Windows shell-script execution).

## [0.13.3] - 2026-05-25

### Fixed

- **`bin/adr-judge` Windows encoding (#LLM-pass)**: two Windows-specific bugs prevented the LLM judge pass from running on Windows machines.
  - **`subprocess.run` cp1252 encoding error**: when the diff or ADR content contained non-ASCII characters (e.g. `≤`), `subprocess.run` with `text=True` but no explicit `encoding` used the Windows console code page (cp1252), causing `UnicodeEncodeError` when writing the prompt to `claude`'s stdin. Fixed by passing `encoding="utf-8"` to `subprocess.run`.
  - **`sys.stdin.buffer` on Windows**: `sys.stdin.read()` uses the console code page; switching to `sys.stdin.buffer.read().decode("utf-8", errors="replace")` ensures the diff is always read as UTF-8 regardless of the active console code page.
  - **`shlex.split` path mangling**: `shlex.split` in POSIX mode (the Python default) treats backslashes as escape characters, mangling Windows paths passed via `--llm-cmd` (e.g. `C:\Users\...` → `C:Users...`). The `shutil.which` check then failed to find the binary and the LLM pass was silently skipped. Fixed by a new `_split_cmd` helper that uses `posix=False` on Windows and strips surrounding quote pairs.
  - **Test fixtures**: fake `claude` binaries in `tests/test_adr_judge_llm.py` were bash scripts, which are not directly executable on Windows. Rewrote all fixtures as Python scripts (always available) and added a `_fake_cmd(path)` helper to produce correctly-quoted `--llm-cmd` strings.

## [0.13.2] - 2026-05-25

### Fixed

- **`templates/githooks/pre-commit`**: two shell bugs caused the hook to exit 1 on clean commits (no ADR violations), effectively blocking every commit and forcing users to set `ADR_KIT_HOOK_DISABLE=1` as a workaround.
  - **`grep -avE` false-positive exit 1**: when `adr-judge` output consists entirely of advisory lines, `grep -avE` finds nothing to print and exits 1. Under `set -e` this killed the script before the actual violation check. Fixed by appending `|| true`.
  - **Missing `exit 0`**: `[ "$ADR_EXIT" -ne 0 ] && exit "$ADR_EXIT"` — when `ADR_EXIT=0` the test returns 1 (false), `&&` short-circuits, and that 1 became the script's exit code because no `exit 0` followed. Fixed by adding an explicit `exit 0` at the end of the script.

## [0.13.1] - 2026-05-08

### Fixed

- **`templates/githooks/pre-commit`**: suppress per-ADR `llm_judge` advisory lines that repeat once for every ADR with `llm_judge: true` and produce very noisy output on projects with many ADRs (e.g. 57 identical lines on OTGW-firmware). The hook now captures `adr-judge` output and filters lines matching `^  ADVISORY ` and `ADR has llm_judge:true` before printing. Violations and the summary line (`[adr-judge] OK N violations, M advisory`) are preserved. Uses `grep -a` to handle multi-byte emoji in the summary line.

## [0.13.0] - 2026-05-07

### Added — Claude Sonnet LLM judge, default-on at hook time

`bin/adr-judge` gains a `--llm` flag that runs an LLM pass for `llm_judge: true` ADRs alongside the v0.12 declarative pass. The pre-commit hook template enables it by default. ADRs with `llm_judge: true` no longer produce just an advisory — Sonnet evaluates the staged diff against the ADR's `## Decision` section and the hook blocks on a `VIOLATION` verdict.

- **`bin/adr-judge` `--llm` mode**: collects all `llm_judge: true` Accepted ADRs, batches them into ONE `claude -p --model claude-sonnet-4-6` call (single round-trip per commit), parses the JSON verdict object Sonnet returns, and emits a `violation` finding for each `{verdict: "VIOLATION", reason: ...}` entry. ADRs with `OK` or unrecognised verdicts produce no finding.
- **`bin/adr-judge` `--llm-cmd "..."`**: override the CLI invocation (model, flags, or substitute a different binary). Tests inject a fake claude binary this way; users can switch to Haiku or Opus by passing a different `--model`.
- **`bin/adr-judge` `--llm-timeout SECS`**: per-call timeout, default 120s. Configurable via `judge.llm_timeout_seconds` in `.adr-kit.json`.
- **`templates/githooks/pre-commit`**: now invokes `adr-judge --llm`. Two new env knobs documented at the top: `ADR_KIT_NO_LLM=1` for per-commit LLM opt-out (declarative checks still run), `ADR_KIT_HOOK_DISABLE=1` for full hook bypass.
- **`schemas/adr-kit-config.schema.json`**: extended with `judge.llm_default` (run LLM pass even without --llm), `judge.llm_model` (default `claude-sonnet-4-6`), `judge.llm_cmd` (full invocation override), `judge.llm_timeout_seconds`.
- **`tests/test_adr_judge_llm.py`**: 10 new tests using a fake `claude` binary fixture. Cover: violation blocks the commit, OK passes through, fenced JSON / prose-wrapped responses parse correctly, unparseable LLM output falls back gracefully, missing CLI falls back gracefully, no `llm_judge` targets means no LLM call, `ADR_KIT_NO_LLM=1` env disables the pass, and verifying the implementation truly batches (one call across N targets, not N calls).

### Behaviour changes

- **Pre-commit hook on a v0.13+ project**: `llm_judge: true` ADRs that were previously informational at commit time are now actively enforcing. A diff that semantically conflicts with such an ADR will be blocked with a one-sentence reason from the model. To opt out per commit: `ADR_KIT_NO_LLM=1 git commit ...`. To opt out persistently: remove the hook via `/adr-kit:install-hooks --uninstall` and reinstall a custom variant, or override `judge.llm_cmd` in `.adr-kit.json` to point at a no-op shell script.
- **`/adr-kit:judge` skill**: rewritten to delegate the entire LLM evaluation to `bin/adr-judge --llm` rather than reasoning in-session. Same engine, same prompt, same verdicts as the hook. The skill's value is now the **resolution loop** (write a new ADR / supersede / fix code) — the evaluation step is shared.
- ADRs without an `## Enforcement` block are still skipped silently. ADRs with declarative-only rules behave exactly as in v0.12. Pure additive change for the `llm_judge: true` set.

### Cost / performance shape

For OTGW-firmware (56 `llm_judge: true` ADRs, typical small commit):
- ~30–40 K input tokens per commit (with prompt caching the per-commit cost drops as ADRs become cached).
- ~5–10 second latency.
- Roughly $0.10–0.30 per commit on Sonnet 4.6.

Configurable downgrade to Haiku 4.5 (~3–5× cheaper, slightly lower fidelity) by setting `judge.llm_model: "claude-haiku-4-5"` in `.adr-kit.json`.

### Backwards compatibility

- v0.12 hooks already in place keep working (they don't pass `--llm`, so the v0.12 advisory behaviour is preserved). To pick up the LLM pass, refresh the hook via `/adr-kit:install-hooks` after upgrading to v0.13.
- Existing tests: 37/37 pass byte-exact (no regressions in the declarative pass, lint, or audit).
- Missing `claude` CLI is non-fatal — judge prints a `WARN` line and falls through to declarative-only. A user who hasn't installed Claude Code locally still gets the v0.12 declarative protection without setup.

### Notes

- **Why batched into one call.** Calling `claude -p` per ADR would multiply latency and cost by N. The single-batch design with the ADR set BEFORE the diff in the prompt also lets Anthropic's prompt cache hit on repeat commits where the ADR set is stable.
- **Why `claude -p` over the SDK.** The CLI reuses the user's Claude Code auth (no `ANTHROPIC_API_KEY` env-var setup), and the spawn overhead (~200ms) is dwarfed by the model latency. Tests can override via `--llm-cmd` for full isolation.
- **Why Sonnet 4.6 and not 4.7.** Quality is indistinguishable for this task, and prompt caching is more mature on 4.6. Override via `judge.llm_model`.

## [0.12.2] - 2026-05-07

### Fixed

- **`bin/adr-judge` and `bin/adr-audit`**: `glob_to_regex` now expands brace-alternation `{a,b,c}` → `(?:a|b|c)`. Without it, real-world Enforcement-block path_globs like `src/**/*.{ino,cpp,h}` or `src/{MQTTstuff,OTGW-Core,SAT*}.ino` silently matched nothing. **Real-world impact**: OTGW-firmware's ADR-049 (no String class in protocol paths) and ADR-042 (no ArduinoJson) ship with brace-style path_globs that were dead code under v0.12.0/v0.12.1 — now correctly enforce. Each alternative inside the brace is itself a valid sub-glob (so `**`, `*`, `?` work inside).
- Unclosed braces and nested braces are treated literally (escape-and-leave) rather than crashing or fabricating a regex.

### Tests

- 3 new tests in `tests/test_adr_judge.py` covering: simple brace-expanded `path_glob` matches the listed alternatives, paths NOT in the alternatives are correctly skipped, and `**` combined with brace alternation in extensions (`src/**/*.{ino,cpp,h}`).

### Notes

- Pure parser improvement, additive only. ADRs already on v0.12 with brace-style path_globs gain enforcement after a plugin re-fetch — no project-side changes required.
- `bin/adr-audit`'s default skip list (`node_modules/**`, `vendor/**`, `docs/adr/**`, etc.) does not use braces today, so its behaviour is unchanged. The fix is preventative for users who add `--skip` patterns containing braces.

## [0.12.1] - 2026-05-06

### Fixed

- **`bin/adr-judge`**: parser now recognises `**Status:** Accepted` (bold-inline) and `**Status: Accepted**` (fully bracketed) status formats in addition to the canonical `## Status\n\nAccepted` heading. **Real-world impact**: a project with 67 legacy bold-inline ADRs (OTGW-firmware) had every Accepted ADR show up as `unknown` to the judge after upgrading to v0.12.0, silently disabling diff-vs-Enforcement coverage on every commit. The judge now correctly classifies these — the project gets enforcement before it has time to migrate via `/adr-kit:migrate`.
- `adr-lint` is intentionally left strict on this point (the Completeness gate still requires a `## Status` heading, nudging users toward canonical format via `/adr-kit:migrate`). Different responsibilities: lint says "your ADR shape is wrong", judge says "is this Accepted, yes or no, what should I enforce?".

### Tests

- 3 new tests in `tests/test_adr_judge.py` covering the three bold-inline formats: `**Status:** Accepted` (rules enforce), `**Status:** Proposed` (rules ignored), `**Status: Accepted**` (rules enforce).

### Notes

- Pure parser improvement, additive only. No false positives — ADRs without an `## Enforcement` block continue to be skipped silently regardless of format.
- v0.12.0 users who hit this trap (judge reports `0 ADR(s) checked` on a project they expect to have rules) should re-fetch with `/plugin install adr-kit@rvdbreemen-adr-kit` to pick up the fix without changing anything else in their project.

## [0.12.0] - 2026-05-06

### Added — three-mode workflow

The kit now operates in three coordinated modes that match how an AI coding agent engages with a codebase: one-shot project init, automatic per-commit verification, and on-demand authoring/review during a session. v0.11 covered only the third mode.

- **`/adr-kit:init`** (`skills/init/SKILL.md`): umbrella one-shot project bootstrap. Hooks `CLAUDE.md` (slim stub + `@`-import to `.claude/adr-kit-guide.md`), copies the canonical project-side guide, runs `bin/adr-audit` to enumerate decision-shaped artefacts in source + documentation, walks the user through batched approval to generate Accepted ADRs via the `adr-generator` subagent, and installs the pre-commit hook. User-invocable only (`disable-model-invocation: true`).
- **`/adr-kit:judge`** (`skills/judge/SKILL.md`): on-demand interactive judge of a staged git diff against existing ADRs. Runs the deterministic `bin/adr-judge` for declarative `Enforcement` rules, then evaluates `llm_judge: true` ADRs **in the active Claude Code session** (no `claude -p` shell-out, no extra API key). On violation, walks three resolution paths (write a new ADR, supersede an existing ADR, fix the code) — each delegates to existing primitives.
- **`/adr-kit:install-hooks`** (`skills/install-hooks/SKILL.md`): installs or uninstalls the pre-commit hook. Supports `--uninstall` (restores any saved prior hook). Default-on after init/upgrade.
- **`/adr-kit:upgrade`** (`skills/upgrade/SKILL.md`): guided v0.11 → v0.12 migration without re-running the heavy init audit. Detects v0.11 inline `## ADR Kit Rules` block and replaces with the v0.12 marker-bracketed stub, copies the guide file, installs the hook, and walks Accepted ADRs offering Enforcement-block backfill proposals one at a time.
- **`bin/adr-judge`**: declarative diff-vs-ADR engine. Parses fenced JSON `Enforcement` blocks from each Accepted ADR; applies `forbid_pattern` / `forbid_import` / `require_pattern` rules to the staged diff with file:line citations. ADRs with `llm_judge: true` and no declarative rules emit advisory entries (non-blocking). Exit codes mirror `bin/adr-lint` (0 / 1 / 2). Fast (sub-second on typical diffs), key-free, runs in any environment.
- **`bin/adr-audit`**: deterministic candidate scanner used by `/adr-kit:init`. Walks `src/` and `docs/`, emits a JSON list of decision-shaped artefacts (top-level dependencies, framework markers, build/CI tooling, documented decision narratives in README/AGENTS/CLAUDE/docs). One candidate per file (deduped) with up to 5 example snippets. Skips `docs/adr/`, `backlog/`, and the usual non-source directories by default.
- **`templates/adr-kit-guide.md`**: canonical project-side guide. Copied to `.claude/adr-kit-guide.md` by init/upgrade/setup. Plain markdown without Claude-Code-specific syntax — readable by any agent, hook, CI script, or evaluator. Includes the four verification gates, three operating modes, slash-command index, Enforcement-block grammar with examples, supersession workflow, and the seven review checks.
- **`templates/adr-template.md`**: the canonical ADR template with the optional `## Enforcement` section pre-stubbed.
- **`templates/githooks/pre-commit`**: pre-commit hook template. Resolves the latest installed plugin version dynamically (no hard-coded paths), so plugin upgrades don't break the hook. Degrades gracefully when the plugin cache is missing — never blocks a commit due to tooling drift. Honors `ADR_KIT_HOOK_DISABLE=1` for per-commit opt-out.
- **`schemas/adr-enforcement.schema.json`**: JSON Schema (draft-07) for the optional `## Enforcement` block in an ADR. Validated by `bin/adr-judge` when `jsonschema` is installed; basic shape checks always run.
- **`tests/test_adr_judge.py`**: 9 end-to-end tests covering violation detection, advisory entries for `llm_judge:true`-only ADRs, status-form parsing (period vs comma), path-glob filtering, malformed JSON handling, and clean-diff pass.
- **`tests/test_adr_audit.py`**: 7 end-to-end tests covering tooling marker detection, dependency extraction across manifest formats, doc decision-phrase grouping (one candidate per file, not per match), skip-glob behaviour, and `--output` writing.

### Changed

- **`skills/setup/SKILL.md`**: rewritten for v0.12. Detects v0.11-style inline `## ADR Kit Rules` and explicitly leaves it untouched (telling the user to run `/adr-kit:upgrade`). On fresh installs, writes the slim marker-bracketed stub to `CLAUDE.md` AND drops the canonical guide at `.claude/adr-kit-guide.md`. Idempotent across re-runs.
- **`agents/adr-generator.md`**: adds Step 3b — propose an `## Enforcement` block when the ADR has a code surface. Three patterns: declarative rules, `llm_judge: true`, or omit-with-explanation. Template extended with the optional Enforcement section. Cross-references expanded to point at new templates and the judge runner.
- **`instructions/adr.coding.md`**: adds rule 5 — Accepted ADRs SHOULD include an `## Enforcement` block when the rule is mechanically expressible.
- **`instructions/adr.review.md`**: header now reads "seven checks" (was "six"). Adds **Check 7**: Enforcement block is set appropriately on any new Accepted ADR with a code surface. Adds the "Missing Enforcement block" review-comment template. Adds the corresponding Definition-of-Done item.
- **`skills/adr/SKILL.md`**: adds "Companion skills and runners (v0.12+)" section indexing init/judge/install-hooks/upgrade/lint/migrate, plus an "Enforcement blocks (v0.12+)" section. Cross-links to `bin/adr-judge` as the canonical runner. Verification gates and supersession workflow remain the source of truth — every other skill delegates to them.
- **`schemas/adr-kit-config.schema.json`**: extended with a top-level `judge` object holding `skip_files` (project-wide path-glob exclusions for the judge), `advisory_only` (downgrade declarative violations to advisory during early adoption), and `max_diff_bytes` (skip pathologically large diffs).
- **`.claude-plugin/plugin.json`**: version bumped to 0.12.0; description rewritten to reflect the three modes.
- **`.claude-plugin/marketplace.json`**: plugin entry version bumped to 0.12.0; description updated.

### Backwards compatibility

- All v0.11 commands (`/adr-kit:adr`, `/adr-kit:lint`, `/adr-kit:migrate`, `/adr-kit:setup`) keep working unchanged. Existing tests pass byte-exact (15/15 baseline preserved).
- ADRs without an `## Enforcement` block are skipped silently by `bin/adr-judge` — zero false positives on legacy ADR sets.
- The pre-commit hook is opt-in: not installed unless the user runs `/adr-kit:init`, `/adr-kit:upgrade`, or `/adr-kit:install-hooks`.
- v0.11 inline `## ADR Kit Rules` sections in `CLAUDE.md` are detected and explicitly preserved by the new `/adr-kit:setup`. Migration to the v0.12 footprint is via `/adr-kit:upgrade` (explicit, never silent).
- Plugin re-fetch via `/plugin install adr-kit@rvdbreemen-adr-kit` upgrades to v0.12 without a marketplace re-add.

### Notes

- **Hook is default-on from v0.12 onwards.** `/adr-kit:init` and `/adr-kit:upgrade` install the pre-commit hook automatically — no prompt. Per-commit opt-out via `ADR_KIT_HOOK_DISABLE=1`. Permanent removal via `/adr-kit:install-hooks --uninstall`.
- **LLM judge is in-session-only.** The pre-commit hook is purely deterministic. ADRs with `llm_judge: true` produce advisory output at hook time; deeper review happens via `/adr-kit:judge` inside a Claude Code session, using the model already loaded for the user's work. No API-key plumbing in the hook environment.
- **Audit is one-shot, deep.** `/adr-kit:init` scans source + documentation in a single pass and walks the user through batches of 5–10 candidates. ADRs are generated with `Status: Accepted` because they reflect decisions already in effect. The user remains the gatekeeper — `init` never fabricates, never auto-approves.

## [0.11.0] - 2026-04-25

### Added

- **`/adr-kit:migrate`** (`skills/migrate/SKILL.md`): guided rewrite skill that brings legacy-shaped ADRs into the canonical-seven-section template enforced by `/adr-kit:lint`. User-only invocable (`disable-model-invocation: true`); never silent. Six named transformation patterns:
  - **Pattern A**: inline `**Status:** ...` / `**Date:** ...` / `**Supersedes:** ...` lines folded into a top-level `## Status` heading.
  - **Pattern B**: `### Alternatives considered` nested inside Context promoted to top-level `## Alternatives Considered` between Decision and Consequences.
  - **Pattern C**: `### Alternatives considered and rejected` nested inside Consequences promoted to top-level before Consequences.
  - **Pattern D**: `## Related` renamed to `## Related Decisions`, with external file paths / URLs / PR references split off into a new `## References` section.
  - **Pattern E**: missing `## References` section with no source content gets a `<!-- TODO: populate -->` placeholder. Never fabricates.
  - **Pattern F**: missing `## Alternatives Considered` with no source discussion gets a `<!-- TODO: document at least 2 alternatives -->` placeholder. Never fabricates.
- README "What it does" section gains entries for `/adr-kit:lint`, `bin/adr-lint`, and `/adr-kit:migrate`. The single-paragraph "the pieces work together" closing now mentions all four roles (skill, agent, lint, migrate, instructions).
- `.github/workflows/validate.yml` required-files set extended with `skills/migrate/SKILL.md`.

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.11.0.
- `.claude-plugin/marketplace.json` plugin entry version bumped to 0.11.0.

### Notes

- The skill is **read-then-confirm**: it always prints a per-file plan first ("Pattern A on ADR-007: promote inline Status to heading") and asks for explicit user confirmation before writing. No silent edits.
- The skill is **idempotent**: running migrate on an already-canonical ADR is a no-op.
- The skill **respects markers**: files with `<!-- adr-kit-lint: skip -->` are left untouched. Files with `<!-- adr-kit-lint: advisory -->` get a warning before migration (the marker becomes meaningless once the file is canonical-shaped).
- The skill **respects `template.required_sections`** in `.adr-kit.json`. If a project has codified a different template, migrate targets that.
- Out of scope on purpose: filename renaming (Consistency-FAILs), body-prose rewriting, auto-fabricating Alternatives or References content, deterministic Python CLI variant. Migration is judgement-heavy; same reasoning that put Evidence and Clarity gates as opt-in for `bin/adr-lint`.

## [0.10.1] - 2026-04-25

### Fixed

- `skills/lint/SKILL.md`: added `disable-model-invocation: true` to the frontmatter so the lint skill follows the same user-only invocation discipline as `skills/setup/SKILL.md`. Before this fix, `/lint` (without plugin prefix) appeared in Claude Code's autocomplete at the root namespace, and the skill was auto-invocable by Claude. With the fix, only the canonical `/adr-kit:lint` form is registered, matching `/adr-kit:setup` and giving the plugin a uniform invocation pattern. Lint is a deliberate user action (a checking tool, not a background helper), so disabling auto-invocation is the right discipline.

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.10.1.
- `.claude-plugin/marketplace.json` plugin entry version bumped to 0.10.1.

### Notes

- No skill body change. The lint logic (severity model, gate evaluation, output format) is identical to v0.10.0.
- No `bin/adr-lint` change. The deterministic CLI is independent of the skill's invocation discipline.

## [0.10.0] - 2026-04-25

### Added

- **`bin/adr-lint`**: standalone Python 3.8+ CLI for CI / pre-commit integration. Mirrors the deterministic gates of `/adr-kit:lint` (Completeness, Consistency by default; Evidence and Clarity available behind `--gates`). Reads the same `.adr-kit.json` policy, supports per-ADR markers, and produces both human-readable and JSON output. Exit codes: `0` (no FAIL), `1` (FAIL detected), `2` (config or input error). Stdlib-only; `jsonschema` auto-detected for deeper config validation.
- `schemas/adr-kit-config.schema.json`: JSON Schema (draft-07) for `docs/adr/.adr-kit.json`. Pattern-validates `strict_from` (`^ADR-\d{3}$`), enum-validates `severity` values, validates `template.required_sections` heading shape. Used by `bin/adr-lint` when `jsonschema` is installed; falls back to basic checks otherwise.
- `tests/`: pytest suite with 15 tests covering every FAIL pattern and severity combination. Subprocess-based: each test runs `adr-lint --format json` and asserts on the JSON output, so the public interface is exercised, not internal helpers. Fixtures: `canonical/`, `missing-headings/`, `bad-filename/`, `heading-mismatch/`, `marker-skip/`, `marker-advisory/`, `marker-skip-gate/`, `with-policy/` (strict_from boundary), `bad-config/`.
- `.github/workflows/adr-lint-self.yml`: dual job that runs `pytest` and a smoke test against `examples/`. Runs on push and pull request to `main`.
- `README.md` "CI integration" section between "Configuration" and "FAQ", with a copy-paste-ready GitHub Actions snippet that downstream users can drop into their own workflow to block PRs on FAIL.

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.10.0.
- `.claude-plugin/marketplace.json` plugin entry version bumped to 0.10.0.

### Notes

- The CLI does not replace the skill. The skill stays canonical for nuanced review; the CLI is for unattended CI gates. They are designed to agree on Completeness and Consistency. They can legitimately disagree on Evidence and Clarity, where Claude's judgement is structurally better than a regex.
- Smoke-tested locally against a representative 87-ADR real-world project (the same set used in the v0.9.0 smoke test): produces 7 PASS / 80 ADVISORY / 0 FAIL with exit code 0 and parseable JSON. Matches the skill's output exactly.
- Future work: `/adr-kit:migrate` (interactive helper to rewrite legacy ADRs into the canonical template) is still planned for a later release; v0.10.0 is scoped to the CLI alone.

## [0.9.0] - 2026-04-25

### Added

- **Scoped lint with grandfathering.** `/adr-kit:lint` now reads an optional project-level config file at `docs/adr/.adr-kit.json` and per-file HTML-comment markers inside individual ADRs. The two mechanisms together let a project apply the four gates surgically: strict on new ADRs, advisory on legacy ones, ignored on archived ones.
- `skills/lint/SKILL.md`:
  - New "Configuration" section documenting the `.adr-kit.json` schema (`strict_from`, `ignore`, `severity` per-gate overrides, `template.required_sections` override).
  - New "Per-ADR markers" subsection: `<!-- adr-kit-lint: skip -->` / `skip <gates>` / `advisory` tell the linter how to treat a single ADR without a project-wide config.
  - New "Severity decision tree" (Graphviz block) that documents the precedence rules: ignore beats markers, markers beat config, and within config the precedence is `always_strict` > `always_advisory` > `advisory_before_strict_from`.
  - Output format gains an ADVISORY tier between PASS and FAIL. Single-file output reports each finding with the reason it was downgraded (e.g. "ADVISORY: ADR predates strict_from=ADR-042"). Directory-tree output groups files into PASS strictly / ADVISORY only / FAIL / SKIPPED counts.
  - Reporting section: the bottom-line "next step" sentence now always points at a FAIL, never an ADVISORY. ADVISORY is informational; FAIL is what the user is asked to act on.
  - Completeness gate now respects `template.required_sections` when set in the config; otherwise the canonical seven still apply.
- `examples/.adr-kit.sample.json`: fully annotated example config with `_comment` keys explaining each field.
- `examples/ADR-sample-003-grandfathered-legacy.md`: a worked legacy-template ADR using the `<!-- adr-kit-lint: advisory -->` marker, demonstrating how a pre-canonical ADR coexists with strict gating on newer ADRs.
- `README.md` gains a "Configuration" section between "ADR conventions" and "FAQ" covering both mechanisms with copy-paste-ready snippets.
- `.github/workflows/validate.yml` required-files set extended with the two new example files.

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.9.0.
- `.claude-plugin/marketplace.json` plugin entry version bumped to 0.9.0.

### Notes

- Backwards compatible: when no `.adr-kit.json` and no per-ADR markers are present, behaviour is identical to v0.8.0 (everything strict, FAIL on any gate failure).
- Defaults are safe: Consistency stays `always_strict` by default even when `strict_from` is set, because filename / heading mismatches and duplicate numbers are real bugs regardless of when the ADR was written.
- Future work: `/adr-kit:migrate` (v0.10.0) will help projects mass-rewrite legacy ADRs into the canonical template; `severity_profile` presets (v0.11.0) will offer named bundles instead of per-gate configuration.

## [0.8.0] - 2026-04-25

### Added

- `schemas/plugin.json.schema.json`: hand-curated JSON Schema (draft-07) for `.claude-plugin/plugin.json`. Validates the documented field types and rejects the historical bug pattern that broke install in v0.7.2 (`repository` as object). The schema's top-level `description` field documents which historical bugs each constraint prevents.
- `schemas/marketplace.json.schema.json`: JSON Schema (draft-07) for `.claude-plugin/marketplace.json`. Required fields: `name`, `description`, `owner` (object with `name`), `plugins` (non-empty array). Each plugin entry requires `name`, `source`, `version`, `description`. The schema's top-level description references the v0.7.1 missing-manifest incident.
- `.github/workflows/validate.yml`: two new CI steps that run `ajv-cli` (draft-07, with `ajv-formats`) against both manifests on every push and pull request. The workflow now fails the build on schema violations, not just JSON syntax errors. `marketplace.json` was added to the required-files set; `schemas/plugin.json.schema.json` and `schemas/marketplace.json.schema.json` are now also required (so a future contributor cannot accidentally remove the schemas without CI noticing). `skills/lint/SKILL.md` was also added to the required-files list (was missing since v0.7.0).
- `CONTRIBUTING.md` "Pre-release smoke test" section: a 5-step manual checklist that release authors run in a fresh Claude Code session before tagging. Steps cover `claude --plugin-dir`, `/plugin`, `/help`, `/adr-kit:setup` (idempotency check), and `/adr-kit:lint`. Schema validation catches manifest field-type bugs; the smoke test catches the install-path bugs schema validation cannot reach.

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.8.0.
- `.claude-plugin/marketplace.json` plugin entry version bumped to 0.8.0 (also corrects the v0.7.1/v0.7.2 drift where the marketplace manifest still listed 0.7.1 while the plugin manifest had advanced to 0.7.2).
- `CONTRIBUTING.md` "Validation" section now mentions the new schema validation step alongside the existing `jq empty` and required-files checks.

### Notes

- This release closes the post-mortem from the v0.7.1 and v0.7.2 install-side regressions. The schemas are sized to current manifest fields only; they are not a substitute for the official Claude Code plugin manifest spec, which (when published) will replace this hand-curated pair. The schemas are best-effort regression tests for the bugs we have actually shipped.

## [0.7.2] - 2026-04-25

### Fixed

- **`plugin.json` `repository` field rejected by Claude Code plugin manifest schema.** Versions v0.1.0 through v0.7.1 declared `repository` as an object (`{ "type": "git", "url": "..." }`), borrowing the convention from npm's `package.json`. Claude Code's plugin manifest schema instead expects a plain URL string for `repository`. Result: after fixing the marketplace.json issue in v0.7.1, `/plugin install adr-kit@rvdbreemen-adr-kit` failed with `Validation errors: repository: Invalid input: expected string, received object`.
- Changed `repository` to a plain URL string: `"https://github.com/rvdbreemen/adr-kit.git"`.
- The CI workflow added in v0.5.0 catches JSON syntax errors via `jq empty` but does not validate the manifest schema. A follow-up task (post-v1.0.0) will add schema validation against the official Claude Code plugin manifest spec.

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.7.2.

## [0.7.1] - 2026-04-25

### Fixed

- **Plugin install via marketplace was incomplete in v0.1.0 through v0.7.0.** The repo had `.claude-plugin/plugin.json` (the per-plugin manifest) but lacked `.claude-plugin/marketplace.json` (the marketplace manifest). Without the marketplace manifest, `/plugin marketplace add rvdbreemen/adr-kit` could not register the marketplace under the `rvdbreemen-adr-kit` name, and the subsequent `/plugin install adr-kit@rvdbreemen-adr-kit` failed with "Unknown command" errors when users tried `/adr-kit:setup` afterwards.
- Adds `.claude-plugin/marketplace.json` declaring `name: "rvdbreemen-adr-kit"`, owner metadata, and one plugin entry (`adr-kit`, source `./`, version 0.7.1).
- After upgrading: existing installations should remove and re-add the marketplace, then re-install:
  ```
  /plugin marketplace remove rvdbreemen-adr-kit
  /plugin marketplace add rvdbreemen/adr-kit
  /plugin install adr-kit@rvdbreemen-adr-kit
  /reload-plugins
  /adr-kit:setup
  ```

### Changed

- `.claude-plugin/plugin.json` version bumped to 0.7.1.

## [0.7.0] - 2026-04-25

### Added

- `skills/lint/SKILL.md`: new `/adr-kit:lint` slash command. Reads every `ADR-*.md` in `docs/adr/` (or a single file or directory passed as argument) and reports per-file, per-gate pass/fail against the four verification gates with file:line citations for failures. Read-only (`allowed-tools: [Read, Glob, Grep]`). Lifts the gates from "documented" to "programmatically enforced" against existing ADRs.
- `ROADMAP.md`: documents Status, criteria for v1.0.0 (90 days field time, 5 unrelated installs, gate-based PR block in real review, migration guide), Planned features (signals not commitments), Out-of-scope non-goals (multi-language, visualisation, bundling, Anthropic-specific features, framework wrapping), and how decisions get made (the maintainer eats the dog food).
- `MIGRATING-FROM-ADR-SKILL.md`: guide for users of Jim van den Breemen's adr-skill explaining the overlap (same gates, same template, same patterns), the differences (skill-only vs full toolkit), and three migration paths (replace, co-install, stay). Slash commands are namespaced by plugin prefix so co-installation does not cause conflicts.
- README: optional fifth slash command (`/adr-kit:lint`) added to the Install section. New Quickstart bullet for "Audit existing ADRs". New "Project resources" section linking to ROADMAP, MIGRATING, CHANGELOG, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT.
- `plugin.json` keywords add `lint`. Description expanded to mention the lint and setup commands.

## [0.6.0] - 2026-04-25

### Added

- `.github/ISSUE_TEMPLATE/bug.yml`: structured bug-report form with fields for tool/version, adr-kit version, reproduction steps, expected vs actual behaviour.
- `.github/ISSUE_TEMPLATE/feature_request.yml`: structured feature-request form that requires alternatives-considered (mirroring the same discipline the skill asks of an ADR).
- `.github/pull_request_template.md`: PR checklist that explicitly references the four verification gates (Completeness, Evidence, Clarity, Consistency) and the CHANGELOG-update requirement.
- `SECURITY.md`: minimal security-disclosure policy (no secrets handled, file-write scope is constrained, reports go to maintainer email).
- `CODE_OF_CONDUCT.md`: short adoption-by-reference of Contributor Covenant 2.1, with reporting email and scope; full canonical text lives at the upstream URL.
- `examples/ADR-sample-001-postgresql-for-event-store.md`: worked-example ADR that passes all four verification gates. Fictional but realistic decision (PostgreSQL vs Kafka vs EventStoreDB for an event store) with concrete measurements, alternatives, and risks-with-mitigations.
- `examples/ADR-sample-002-evidence-gate-before-after.md`: same decision (sync vs async webhook delivery) written twice, once failing the Evidence gate and once passing. Illustrates what "replace bare adjectives with measurements" looks like in practice.
- `README.md` FAQ section: where ADRs are stored, how to customize the conventions, what to do if the project already has ADRs in another format, whether the skill auto-creates ADRs, whether this is an Anthropic product.
- `README.md` Comparison section: short table contrasting `adr-kit` with a plain ADR template along format, pre-flight discipline, acceptance bar, code-review integration, tool integration, and onboarding axes.

## [0.5.0] - 2026-04-25

### Added

- `.github/workflows/validate.yml`: GitHub Actions CI that validates `plugin.json` (`jq empty`), enforces the required-files set, asserts that `plugin.json` version matches the top entry of `CHANGELOG.md`, and runs `markdownlint` over skills, agents, instructions, and examples.
- `CONTRIBUTING.md`: dev loop (`claude --plugin-dir .`), how to add a skill or agent, version-bump and release procedure, code style (no em dashes, English, kebab-case file names), validation, and issue-reporting guidelines.
- `argument-hint: "[short title of the decision]"` on `skills/adr/SKILL.md` so users see the expected slash-command syntax in the picker.
- `allowed-tools: [Read, Write, Edit]` on `skills/setup/SKILL.md` so the one-time `/adr-kit:setup` does not prompt for tool permission.
- `homepage` (already present), enriched `keywords` list (covers Claude Code, Copilot, Codex, agent-skills, AI coding assistant, decision-records, verification-gates, anti-rationalization), and an empty `dependencies: []` placeholder in `.claude-plugin/plugin.json`.

## [0.4.0] - 2026-04-25

### Added

- `CHANGELOG.md` in Keep a Changelog format. Retroactively documents v0.1.0, v0.2.0, and v0.3.0.
- `.gitignore` with sensible defaults for Claude Code plugin development (OS files, editor metadata, common cache directories).

### Changed

- Adopted the `adr-kit--vX.Y.Z` git tag convention that `claude plugin tag` expects. Existing legacy tags (`v0.1.0`, `v0.2.0`, `v0.3.0`) remain in place so pinned installs do not break; they are also mirrored to the new naming on the same commits, and the new convention applies from v0.4.0 forward.

## [0.3.0] - 2026-04-25

### Added

- `/adr-kit:setup` slash command via `skills/setup/SKILL.md`. One-time per project, idempotent: appends an "ADR Kit Rules" section to the project's `CLAUDE.md`, creates `CLAUDE.md` if it does not exist, skips if the section is already present.
- The install flow in `README.md` and `INSTALL.md` now lists four slash commands (`marketplace add`, `install`, `reload-plugins`, `setup`).

## [0.2.0] - 2026-04-25

### Added

- Native Claude Code plugin support via `.claude-plugin/plugin.json` manifest.
- Plugin install path: `/plugin marketplace add rvdbreemen/adr-kit` + `/plugin install adr-kit@rvdbreemen-adr-kit` + `/reload-plugins`.

### Changed

- **Breaking for non-Claude-Code tools**: `SKILL.md` source path moved from `adr-kit/SKILL.md` to `adr-kit/skills/adr/SKILL.md` to match the Claude Code plugin layout. Existing client-specific destination paths were unchanged. `INSTALL.md` and the bundled install script were updated accordingly.

## [0.2.0-attribution] - 2026-04-25

### Changed

- `README.md` Credits section and `SKILL.md` credit paragraphs now name [Jim van den Breemen's adr-skill](https://github.com/Jvdbreemen/adr-skill) explicitly as the source where the anti-rationalization guards and verification gates patterns were first combined into a single ADR skill. The original pattern sources (`addyosmani/agent-skills`, `trailofbits/skills`) remain credited as upstream.

## [0.1.0] - 2026-04-25

### Added

- Initial public release of `adr-kit`.
- `SKILL.md`: comprehensive ADR guide with anti-rationalization guards (a 9-row excuse / counter-argument table) and four named verification gates (Completeness, Evidence, Clarity, Consistency).
- `agents/adr-generator.md`: focused subagent for authoring a complete ADR file given a decision and context.
- `instructions/adr.coding.md`: ADR rules during coding work, including implementation checklist and supersession workflow.
- `instructions/adr.review.md`: six named ADR checks for code review with concrete review-comment templates.
- `examples/ADR-template.md`: clean template to copy into new ADRs.
- `INSTALL.md`: per-tool install paths for Claude Code, GitHub Copilot CLI, and OpenAI Codex, plus a one-shot helper script and a generic fallback.
- `README.md`, `LICENSE` (MIT).

### Credits

The anti-rationalization guards pattern is adapted from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills). The verification gates pattern is adapted from [trailofbits/skills](https://github.com/trailofbits/skills). Both patterns were first combined into a single ADR skill by [Jim van den Breemen's adr-skill](https://github.com/Jvdbreemen/adr-skill); `adr-kit` builds on that combination.

[Unreleased]: https://github.com/rvdbreemen/adr-kit/compare/v0.43.0...HEAD
[0.43.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.42.0...v0.43.0
[0.37.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.36.0...v0.37.0
[0.36.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.35.0...v0.36.0
[0.35.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.34.2...v0.35.0
[0.34.2]: https://github.com/rvdbreemen/adr-kit/compare/v0.34.1...v0.34.2
[0.34.1]: https://github.com/rvdbreemen/adr-kit/compare/v0.34.0...v0.34.1
[0.34.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.33.0...v0.34.0
[0.33.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.32.0...v0.33.0
[0.32.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.31.0...v0.32.0
[0.31.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.30.5...v0.31.0
[0.30.5]: https://github.com/rvdbreemen/adr-kit/compare/v0.30.4...v0.30.5
[0.30.4]: https://github.com/rvdbreemen/adr-kit/compare/v0.30.3...v0.30.4
[0.30.3]: https://github.com/rvdbreemen/adr-kit/compare/v0.30.2...v0.30.3
[0.30.2]: https://github.com/rvdbreemen/adr-kit/compare/v0.30.1...v0.30.2
[0.30.1]: https://github.com/rvdbreemen/adr-kit/compare/v0.30.0...v0.30.1
[0.30.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.29.0...v0.30.0
[0.29.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.28.0...v0.29.0
[0.28.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.27.0...v0.28.0
[0.27.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.26.0...v0.27.0
[0.26.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.25.0...v0.26.0
[0.25.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.24.0...v0.25.0
[0.24.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.23.0...v0.24.0
[0.23.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.22.0...v0.23.0
[0.22.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.21.0...v0.22.0
[0.21.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.20.1...v0.21.0
[0.20.1]: https://github.com/rvdbreemen/adr-kit/compare/v0.20.0...v0.20.1
[0.20.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.19.2...v0.20.0
[0.19.2]: https://github.com/rvdbreemen/adr-kit/compare/v0.19.1...v0.19.2
[0.19.1]: https://github.com/rvdbreemen/adr-kit/compare/v0.19.0...v0.19.1
[0.19.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.18.0...v0.19.0
[0.18.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.17.0...v0.18.0
[0.17.0]: https://github.com/rvdbreemen/adr-kit/compare/77fa59bc61f658dc6321872c9e5280dc721227d8...v0.17.0
[0.16.0]: https://github.com/rvdbreemen/adr-kit/commit/77fa59bc61f658dc6321872c9e5280dc721227d8
[0.15.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.14.0...v0.15.0
[0.14.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.13.3...v0.14.0
[0.13.3]: https://github.com/rvdbreemen/adr-kit/compare/v0.13.2...v0.13.3
[0.13.2]: https://github.com/rvdbreemen/adr-kit/compare/v0.13.1...v0.13.2
[0.13.1]: https://github.com/rvdbreemen/adr-kit/compare/v0.13.0...v0.13.1
[0.13.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.12.2...v0.13.0
[0.12.2]: https://github.com/rvdbreemen/adr-kit/compare/v0.12.1...v0.12.2
[0.12.1]: https://github.com/rvdbreemen/adr-kit/compare/v0.12.0...v0.12.1
[0.12.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.11.0...v0.12.0
[0.11.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.10.1...adr-kit--v0.11.0
[0.10.1]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.10.0...adr-kit--v0.10.1
[0.10.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.9.0...adr-kit--v0.10.0
[0.9.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.8.0...adr-kit--v0.9.0
[0.8.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.7.2...adr-kit--v0.8.0
[0.7.2]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.7.1...adr-kit--v0.7.2
[0.7.1]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.7.0...adr-kit--v0.7.1
[0.7.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.6.0...adr-kit--v0.7.0
[0.6.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.5.0...adr-kit--v0.6.0
[0.5.0]: https://github.com/rvdbreemen/adr-kit/compare/adr-kit--v0.4.0...adr-kit--v0.5.0
[0.4.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.3.0...adr-kit--v0.4.0
[0.3.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rvdbreemen/adr-kit/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.1.0
