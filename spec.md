# adr-kit: intent specification

What adr-kit is *for*, stated by its maintainer on 2026-08-01, independent of what
the code currently does. This document is the yardstick; the gap analysis against
the implementation lives separately.

Written in English to match the rest of the repository. The original was dictated
in Dutch; where a phrase carried more than one reading, the chosen reading is
marked **[interpretation]** so it can be corrected.

---

## R0 — Purpose

adr-kit records the software architecture choices made by the people and the agents
working on a project, so that those choices become **extra context for the coding
agent**. That context is what keeps the project on course.

Three consequences follow, and every requirement below serves one of them.

**A decision is context, not paperwork.** The reason to write an ADR down is that
the next agent — or the next person — will otherwise re-decide it, differently, in
a file nobody is looking at. The record exists to be *read back* at the moment work
happens, which is why retrieval (R5, R6) and injection (R2, R3, R4) matter as much
as authoring.

**Changing course is allowed; changing it by accident is not.** When a new choice is
made, that happens deliberately and the ADRs are adapted to match. An ADR set that
silently diverges from the code is worse than none, because it claims an authority
it no longer has. This is what the judge (R2) and supersession (R10) defend.

**An ADR has a life.** Plan, implement, record, supersede, archive. Each of those
transitions is a moment the kit must recognise and support, not a state a human has
to maintain by hand.

And a constraint on the artefact itself: an ADR is **documentation**, readable by
both a human and an agent. It carries the choice, the motivation behind it, and the
arguments for and against — the alternatives that were weighed and why they lost. A
record that states only the outcome cannot be re-evaluated later, and a decision
that cannot be re-evaluated cannot be superseded honestly.

---

## R1 — Bootstrapping an existing repository

A repository that has code and history but no ADRs must be able to acquire them in
one step.

- `/adr-kit:init` reads the **source code and the git history** and proposes the
  ADRs that the codebase already embodies.
- The ADRs are written to the `docs/` ADR directory in the canonical layout.
- ADRs created this way are **Accepted automatically**. This is the deliberate
  exception to R8: the code already exists and the user is explicitly asking for a
  record of it, so there is nothing to approve in advance.
- The generated index (`ADR-INDEX.md`, `ADR-INDEX.json`, the README block) is
  produced as part of the same step, not left for a later command.

## R2 — Lifecycle moments during agent work

Once a repository has ADRs, the kit must interrupt at the moments where a decision
is actually being made or violated, not only when a human remembers to ask.

- **Before a diff becomes a pull request**, the judge runs over that diff. If the
  change falls outside the Accepted ADRs, the coding agent fixes it *first*; the PR
  does not proceed on a violation.
- At the same moment, the kit asks the second question: **is a new ADR needed?**
  Are there decisions in this diff that no ADR records yet?

## R3 — Leaving plan mode

When an agent has produced a full plan and is about to leave plan mode for build
mode, that transition is a decision point. The kit checks there whether new ADRs
should be written, before any code is produced. This is a hook, not a convention
the model has to remember.

## R4 — Maximal use of the agent's hook surface

Coding agents expose many hooks, pre- and post-. adr-kit must use as many of them
as carry signal, rather than relying on the model to invoke the right command at
the right time.

## R5 — Relevant context at the start of work

At the start of a new chat, and again when a prompt or an agent begins work, a hook
looks at the repository it is in and runs an ADR query, returning the **top 5 ADRs**
relevant to that prompt or to the code changes about to be made.

**The LLM itself picks the five.** The vector database of R6 supplies the
candidate set — that part is deterministic machinery — but the final selection of
which five ADRs are relevant to this prompt is a model judgement, not a scoring
formula. Retrieval narrows; the model chooses.

This is the division of labour R11 asks for, applied to one case: deterministic
where determinism is cheap and correct (embedding, candidate recall, metadata
filtering such as status and supersession), model judgement where the question is
genuinely about meaning ("is this decision relevant to what the user just asked?").

## R6 — A vector database over the ADRs

The ADRs are embedded into a vector database so the right ADR is found fast — not
only by tag, theme or keyword, but by **semantic proximity**.

## R7 — Precise cross-references, always-current index

- ADRs reference each other where that is warranted, and the **LLM decides** when it
  is warranted.
- Writing a new ADR, or updating one, may require **older ADRs to be updated too**.
  That must happen precisely and reliably, not best-effort.
- The index must **always** be up to date as a consequence.

## R8 — Human-gated acceptance, with evidence

An agent may never decide on its own that an ADR is Accepted.

- There must always be evidence of **which human** accepted the ADR and **when**.
- The user is asked to review and consciously accept, wherever that is possible and
  meaningful.
- The one exception is R1's init flow.

### R8.1 — The signer is configured, not assumed

The recorded actor is `User: <user>`, where `<user>` is a **configured value**, not
a literal baked into a command line or a default that names the tool.

- It is asked for during **installation**, and again on **upgrade** when it is not
  yet set.
- It is changeable afterwards through the settings surface of R13.
- The default the installer *proposes* comes from `git config user.name`, because
  the repository already knows who is working in it — but it is proposed for
  confirmation, never adopted silently.

**Where it is stored matters.** The signer is a property of the machine and the
person, not of the repository. It belongs in the gitignored machine-local config
alongside the LLM client id, not in the tracked `.adr-kit.json`. A signer committed
to the repository would put one person's name on every teammate's acceptance —
which is worse than no name at all, because it is a false attribution rather than a
missing one.

**And no default may name the tool.** `--changed-by` currently defaults to
`adr-kit`, so omitting the flag writes a durable record saying the tool accepted its
own ADR. When the signer is unset and none is supplied, the command must **refuse**
rather than sign on the user's behalf. An unsigned acceptance is a bug; a
self-signed one is a lie in the audit trail.

### R8.2 — A git identity may be adopted, announced, when it names a person

*Added after v0.44.0, which shipped the refusal above as a breaking change: a
fresh clone, a container and a CI runner all failed at the first lifecycle
command, `bin/adr new` included.*

The refusal was stricter than R8.1 requires. R8.1 forbids a default that **names
the tool** — the `adr-kit` actor, where the toolkit writes itself into the record
as the decider. `git config user.name` is the opposite of that: a value the human
configured on this machine, which every commit in the repository already carries.
It is a configured value, not an assumed one.

So the lifecycle commands may adopt it, under two conditions that preserve what
R8.1 was protecting:

- **Announced, never silent.** A derived actor is printed when it is used. A name
  that lands in an immutable Status History must never be one the user did not
  know was being written. This is weaker than the confirmation R8.1 asks of the
  *installer*, and deliberately so: a lifecycle command is not an install flow and
  cannot stop to ask, but it can refuse to be quiet.
- **A person, never a machine.** `github-actions[bot]`, `runner`, `jenkins`, a
  bare `user` or `root`: these are configured values that name a machine. They
  fall through to the refusal, because R8 asks for evidence of which *human*
  accepted a decision, and a bot's name under an acceptance is the same false
  attribution a committed signer would be.

Precedence: `--changed-by`, then the configured `lifecycle.signer`, then the
derived git identity, then refuse.

The installer's obligation in R8.1 is unchanged and comes first in practice:
setup, init and upgrade propose a candidate — from the signed-in GitHub account
as well as git — and write it only once the user chooses. The derivation is the
floor for machines where nobody ran that flow, not a replacement for it.

## R9 — Grilling until the ADR is sharp

adr-kit itself evaluates whether an ADR is good enough. When it is not:

- The user is interrogated using the grilling technique until the decision is clear
  and precise.
- **Every question asked and every answer given is recorded.**
- The result is written as a **Proposed** ADR. The user reads it and then accepts
  it — acceptance is a separate, human act (R8).

## R10 — Supersession, never deletion

An ADR is never removed. It is superseded.

- A superseded ADR stops governing, but does not disappear.
- The supersession relationship is carried as metadata in **both the index and the
  vector database**, so the chain is always traceable.

## R11 — Graph and embeddings as first-class machinery

Graph techniques and embedding vectors improve findability, analysis speed and the
*determinism* of the whole system. They must be used to their full extent.

Preference order: **deterministic techniques first, LLM where genuinely needed.**

## R12 — LLM routing: client first, but never client-only

The coding client's own LLM is the preferred backend, but the ability to use other
models must be built in **from the start**, not retrofitted:

- local runtimes: **Ollama** and **LM Studio**
- external API endpoints: **OpenRouter** and comparable services

The choice is offered during setup and can be changed later through the settings
command.

## R13 — Settings as a first-class surface

Anything adjustable — judge-by-default, which hooks are active, the LLM backend of
R12 — is adjustable through `/adr-kit:settings`.

---

## R14 — The agent consults the ADRs whenever it matters, on two tracks

Consulting the decision record must not depend on the agent remembering to. It is
enforced on two tracks at once, and both are required:

**Track 1 — instruction.** `CLAUDE.md`, `AGENTS.md` and their equivalents carry
instructions good enough that an agent reading them knows when to consult, when to
propose, and when to stop and ask. This track covers the cases where judgement is
the point.

**Track 2 — the harness's own hooks.** The coding agent exposes hook points inside
the running session, and those fire whether or not the instruction was read,
followed, or compacted away. Two examples that define the shape:

- a **query before work begins**, so the relevant decisions are in context before
  the first line is written (this is R5);
- a **judge check at the moment a pull request is about to be created**. In a
  harness, opening a PR is a tool call — `gh pr create` through the shell tool — so
  a pre-tool hook can intercept it and run the judge over the branch diff *before
  the PR exists*. That is R2's "before a diff becomes a PR", literally: earlier
  than CI can ever be, because CI only learns about the PR once it is there.

**Track 3 — repository and CI gates.** Git hooks and pipeline jobs sit outside the
session entirely. They catch what the session missed, what a different agent did,
and what a human did by hand. They are the only track that still works when nobody
is using an agent at all.

The three are not alternatives, and each covers the others' blind spot. Track 1
alone degrades silently the moment context runs short or a different agent takes
over. Track 2 alone is invisible to anyone not working through that harness — a
teammate on a different client, or a commit pushed from a laptop. Track 3 alone
arrives too late to shape the work: it can reject, but it cannot inform.

Where this document marks something *prose-only*, it means track 1 exists and
tracks 2 and 3 do not — a real gap, not a stylistic preference.

## R16 — Setup detects the local embedding runtime and offers a way forward

Setup and upgrade must find out whether a local embedding runtime is available,
and act on the answer instead of leaving the user to discover the gap later.

**Detected and present.** If Ollama is reachable and carries an embedding model,
local embedding is the default and every embedding-backed feature is on. No
question is asked, because the answer is already yes.

**Detected and absent.** Say so. Explain how to install Ollama, then offer three
routes rather than one:

1. **Install it now.** Install Ollama locally together with the Qwen embedding
   model.
2. **Configure an existing runtime.** The user may already have one on another
   host, or prefer LM Studio (R12).
3. **Use a remote endpoint.** OpenRouter or another API endpoint, offered here so
   the user is never left with no working option.

**Warn before installing, on hardware grounds.** If no GPU is detected, say so
*before* installing anything, and recommend the remote route instead — an
embedding model on CPU is slow enough to make the 2 s hook budget (ADR-015)
unreachable, which turns a feature into a regression.

### What this requires of the implementation

- Detection is deterministic, local, stdlib-only and fail-soft. It must never
  block setup, and a missing runtime is a normal outcome, not an error.
- Installing third-party software is a **consented action**, never silent and
  never elevated without asking. The user chose route 1 or they did not.
- The GPU check is a heuristic, and it must present itself as one. Ollama runs on
  CPU; the warning is about speed, not capability.
- Model size is part of the offer, not a surprise afterwards. `qwen3-embedding:8b`
  is roughly 4.7 GB. State the download size before starting it, and offer a
  smaller variant where one exists.
- Whatever is chosen lands in the settings surface (R13), so it can be changed
  later without re-running setup.

## R15 — `/adr-kit:audit`: one command that lints and judges

There must be a single command that can be *demanded* — by a person, a hook, or a
CI job — and that runs both halves of the check in one pass:

1. **Lint** — the quality of the ADRs themselves. Are the records complete,
   evidenced, clear, consistent; are the cross-references sound.
2. **Judge** — the code against those ADRs. Either the **whole codebase** or a
   **diff** of it.

The point of combining them is that each half is meaningless without the other. A
clean judge over a set of vague ADRs proves nothing, because vague rules cannot be
violated. A sharp ADR set that nobody checks the code against is documentation, not
governance. Anyone asking "are we still on course?" needs both answers at once, and
should not have to know that they come from two binaries.

**Two modes, one command:**

- *Diff mode* — the default in a hook or PR context. Judge the change at hand.
- *Whole-codebase mode* — judge everything, not only what changed. This is the mode
  that answers "does the code as it stands today obey the decisions as they stand
  today", which no per-diff gate can answer: a rule added after a file was written
  has never been applied to that file. **[interpretation: mechanically this is a
  diff against the empty tree, so every line reads as added and `forbid_pattern`
  applies repo-wide; `require_pattern` already reads a snapshot and needs no
  change. Such a diff is large, which is exactly what the separate CI diff budget
  exists for.]**

**Exit behaviour must distinguish the two failures.** "Your ADRs are not good
enough" and "your code violates an ADR" are different problems with different
owners, and a single non-zero exit that conflates them tells the caller nothing
about what to fix.

**Naming note.** `bin/adr-audit` already exists and is something else: the
deterministic repository scanner used by `/adr-kit:init` to discover candidate
decisions. Either that binary is renamed to what it does (`adr-discover`), or the
new command must not reuse the word. Two things called audit that audit different
things is exactly the ambiguity ADRs are supposed to prevent.

---

## Appendix A — Where the kit attaches: hooks and CI, as shipped

R2, R3 and R4 are about *moments*. This appendix lists every moment adr-kit
already attaches to, which ADR function runs there, and why that pairing was
chosen. It is an inventory of the code as it stands on 2026-08-01, not a wish
list; the gaps follow in Appendix B.

### A.1 — Agent hooks (Claude Code plugin, `hooks/hooks.json` → `hooks/adr_hook_core.py`)

All six are deterministic, fail-open, and never call a model. They inject text;
they do not block. The timeouts are the budget ADR-015 fixes as a contract.

| Event | Matcher / budget | ADR function | Why here |
|---|---|---|---|
| `SessionStart` | 5 s | Global Accepted ADRs (`context_scope: global`, max 3) plus the readiness queue | The agent needs orientation before the first prompt, and this is the only moment where "what governs this whole repository" is the right question. Reads a local cache only — no scan, no model. |
| `UserPromptSubmit` | 5 s | Query the index for ADRs relevant to the prompt; split into governing (Accepted) and advisory (Proposed) | This is R5's moment: work is about to start and the prompt is the best available statement of intent. |
| `PreToolUse` | `Edit\|MultiEdit\|Write`, 1 s | ADRs governing *that file path*, plus a "possible durable architecture decision → grill" nudge | The last moment before code changes. ADR-004 calls this the fail-closed floor: an edit-time constraint the agent cannot miss because it arrives with the edit. |
| `PostToolUse` | same matcher, 1 s | The same ADRs, phrased as a backstop | Catches the case where the pre-edit injection was ignored or the edit went further than announced. |
| `SubagentStart` | 1 s | Passes the parent's ADR context down | A subagent starts with an empty context; without this it works unaware of constraints the parent was given. |
| `PreCompact` | 1 s | Re-injects the ADR context that compaction is about to drop | Compaction silently discards exactly the standing constraints that were injected earliest. |

Deliberately no-op: `Stop`, `SubagentStop`, `SessionEnd`, `PostCompact`,
`PermissionRequest`, `Notification`, `Interrupt`. They are enumerated in
`NOOP_EVENTS` rather than left unhandled, so an unexpected event is a decision
rather than an accident.

### A.2 — Git hooks

| Hook | ADR function | Why here |
|---|---|---|
| `templates/githooks/pre-commit` | `bin/adr-judge` on the staged diff, declarative pass always, LLM pass for in-scope ADRs | The commit is the first point where a decision has become durable. Fail-closed on violation, fail-open on missing tooling. Carries a `flock` guard so two concurrent commits cannot both spend on the LLM pass. |
| `.pre-commit-hooks.yaml` (`id: adr-judge`) | Same engine via `bin/adr-judge-precommit` | Teams standardised on the pre-commit framework get the same gate without the native hook. |

### A.3 — CI workflows (this repository)

| Workflow | Trigger | ADR function | Why here |
|---|---|---|---|
| `adr-judge-self.yml` | `pull_request` → main | Judge the whole branch diff (`origin/base...HEAD`) | R2's first half. The commit hook sees one commit; the PR is where the *cumulative* change is judged. Deliberately not on `push`, because `GITHUB_BASE_REF` is empty there. |
| `adr-readiness.yml` | `pull_request` → dev, main | `adr-readiness` action: are Proposed ADRs linked to the implementation this PR carries? | A PR that implements a Proposed decision should not merge while the decision is still unaccepted. |
| `adr-index-check.yml` | `push` + `pull_request` | `adr-index --check docs/adr` | R7's "index always current", enforced rather than hoped for. Cheap, deterministic, no model. |
| `adr-lint-self.yml` | `push` + `pull_request` | `adr-lint` over `examples/` and `tests/fixtures/` | Note: this is a **self-test of the linter**, not a lint of this repository's own ADRs. |
| `adr-guardian-audit.yml` | weekly cron (Mon 06:00) + dispatch | Cheap tier: `adr-lint docs/adr`, `adr-retire`, `adr-status` → one tracking issue | Staleness is not a per-commit property. A weekly sweep with a single self-updating issue makes ADR health a team-visible number instead of whatever the last session happened to notice. Never runs a model. |
| `adr-retire-audit.yml` | weekly cron + dispatch | `adr-retire --threshold 0.4` → issue on findings | Decisions age out silently; this is the only mechanism that says so unprompted. |
| `release-candidate.yml` / `release-publish.yml` | dispatch / tag push | `adr-lint --strict docs/adr` + `adr-index --check` | Release is the last gate. `--strict` adds canonical frontmatter, evidence resolution and reciprocal supersession checks that are too slow for every commit. |
| `validate.yml` | `push` + `pull_request` | Schema validation of `ADR-INDEX.json`, required-files check, full pytest matrix | Guards the contracts the other workflows depend on. |

Shipped for downstream projects: `templates/github-workflows/adr-readiness.yml`
and `adr-guardian-audit.yml`, plus the composite actions
`.github/actions/adr-judge` and `.github/actions/adr-readiness`.

### A.4 — What this inventory shows

The **enforcement** side is well covered: every write path (edit, commit, PR,
release) has a gate, and each gate runs the cheapest tool that can answer at that
moment. The **authoring** side is not: of all the moments above, only the
PreToolUse nudge ever raises the question *should a new ADR exist?*, and it does so
as a suggestion in injected text. There is no moment where that question is asked
with the whole change in view.

## Appendix B — Proposals

Ordered by the size of the gap they close, with the reason each moment is the right
one rather than a nearby one.

**B1. A hook on leaving plan mode (R3).**
Claude Code exposes `ExitPlanMode` as a tool, so `PreToolUse` with that matcher is
a real attachment point, symmetric with the existing `Edit|Write` matcher. The plan
is complete and no code exists yet: the cheapest possible moment to notice a missing
decision, and the only one where the answer can still shape the implementation
rather than justify it. Budget it like the other pre-hooks — 1 s, injection only,
no model — by running the deterministic candidate finder against the plan text and
naming what looks undecided.

**B2. "Does this need a new ADR?" as a PR job (R2, second half).**
`bin/adr-suggest` exists and no shipped workflow runs it. A PR-time job that posts
its findings as a comment closes the half of R2 that is currently missing. Advisory,
not blocking: a missing ADR is a judgement call, and a gate that blocks on it would
teach people to write empty ADRs to get past it — the same failure mode that
produced six rule-less Enforcement blocks in this very repository.

**B3. Lint this repository's own ADRs on every PR.**
`adr-lint-self.yml` lints `examples/`, and `docs/adr` is only linted weekly by the
guardian and at release time. A broken ADR can therefore live in `main` for six
days. Adding `adr-lint docs/adr` to the PR path costs a second and closes that
window. Keep `--strict` for release: the strict gates are authoring-time feedback,
not merge-time.

**B4. Raise `UserPromptSubmit` to five results, and let the model choose them.**
`MAX_RESULTS = 3` in `hooks/adr_hook_core.py:24`, and the five come out of a
deterministic scoring formula. R5 asks for five, chosen by the model from a
retrieved candidate set. That is a two-part change: widen the candidate set here,
and add the model-side selection R5 describes.

**B5. A Stop or SessionEnd sweep, once the cost is understood.**
Every hook today fires *before* work. Nothing fires after a session concludes, which
is when the set of decisions actually made is knowable. This is the natural home for
"you changed X, Y and Z this session; two of those look like decisions". Listed last
deliberately: it is the only proposal that wants a model in a hook, and the current
design keeps hooks model-free on purpose. It belongs in an ADR before it belongs in
code.

## How to read this document

Each requirement is a claim about behaviour a user can observe. "Implemented" means
a user following the documented path gets that behaviour, on a real repository,
without knowing the internals. A mechanism that exists in the code but that no
shipped path reaches does not count as implemented.

Instruction-in-a-skill is judged on what the requirement asks for, not dismissed by
default. Several requirements here deliberately want a model to exercise judgement
(R5's choice of five, R7's decision about cross-references, R9's grilling). For
those, a well-specified skill IS the mechanism, and the question is whether the
instruction is reliably reached and reliably followed.

Where a requirement instead asks for a **hook**, a **guarantee**, or "always" (R3,
R4, R7's index, R8's evidence, R10's traceability), prose is not enough: something
must fire without the model choosing to, or hold without the model remembering to.
That distinction is reported as its own status — *prose-only* — rather than as a
flat failure, so it stays visible which half of the system a gap sits in.
