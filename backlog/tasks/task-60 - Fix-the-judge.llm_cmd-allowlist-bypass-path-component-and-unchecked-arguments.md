---
id: TASK-60
title: >-
  Fix the judge.llm_cmd allowlist bypass (path component and unchecked
  arguments)
status: To Do
assignee: []
created_date: '2026-07-30 17:53'
labels:
  - security
  - judge
  - review-finding
dependencies: []
references:
  - .full-review/01-quality-architecture.md
  - docs/adr/ADR-001-llm-gates-opt-in.md
modified_files:
  - bin/adr-judge
  - schemas/adr-kit-config.schema.json
  - tests/test_adr_judge_security.py
priority: high
ordinal: 65500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found by the comprehensive review, reproduced end to end. See `.full-review/01-quality-architecture.md` finding C1.

`bin/adr-judge:1716-1718` states its threat model correctly at `:67-70`: repo-tracked `.adr-kit.json` "can be authored by anyone with commit access; restrict the binary to a known set." The check does not implement it.

```python
cfg_binary = Path(candidate[0]).name          # "bin/claude.exe" -> "claude.exe"
cfg_binary_stem = Path(candidate[0]).stem     # -> "claude"  <-- passes the allowlist
if cfg_binary in _LLM_CMD_ALLOWLIST or cfg_binary_stem in _LLM_CMD_ALLOWLIST:
    llm_cmd = candidate
```

The directory component is discarded before comparison, and `shutil.which()` at `:1054` resolves a path carrying a directory component directly, with no PATH search.

**Two independent vectors, both confirmed:**

1. Repo-shipped binary. A committed `bin/claude.exe` plus a committed `judge.llm_cmd` naming it. The reviewer executed this: the payload ran, wrote its marker, returned a forged `{"ADR-001":{"verdict":"OK"}}`, and the judge exited 0. Cloning the repository and committing once is sufficient. On Windows a backslash path works; a forward-slash relative path fails CreateProcess and instead triggers the exit-1 defect (TASK-61). POSIX execvp runs either form.
2. No file needed. Only `candidate[0]` is inspected; every argument after it is unvalidated. `["claude", "-p", "--dangerously-skip-permissions", "--allowedTools", "Bash"]` passes the allowlist and invokes the genuine CLI with tool permissions disabled, on a prompt built from repository content. `schemas/adr-kit-config.schema.json:140-146` types `llm_cmd` as an untyped string array, so the schema is not a second layer.

**Reachability.** Gated behind `judge.llm_enabled`, which was `false` by default per ADR-001 and was set to `true` in this repository's `docs/adr/.adr-kit.json` on 2026-07-30. Latent before that; live now. Practical exposure here is low (single committer), but the shipped product carries it to every user.

**Interaction with TASK-59.** That task proposes making the LLM pass on by default and adding OpenRouter and Ollama backends. A backend registry must admit `ollama`, so this guard cannot merely be tightened — it should be replaced by a named-backend indirection (`judge.backend: "ollama"` resolving to a code-side command table) so repository-tracked config never supplies an argv at all. That also satisfies TASK-59's requirement that the OpenRouter key come from the environment and never from committed config.

**Interim fix if the registry lands later:** reject any `judge.llm_cmd[0]` containing a path separator (`os.sep`, `os.altsep`, or a literal `/`), and validate the argument vector against a small safe-flag allowlist rather than only its head. Env `ADR_KIT_LLM_CMD` and CLI `--llm-cmd` stay unrestricted; those are operator-controlled, which is the distinction the original comment draws and which is correct.

State the governing rule wherever it lands: repo-tracked config may select among backends the operator has enabled; it may never introduce a new endpoint, a new binary, or a credential.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A repo-tracked `judge.llm_cmd` naming a path (bin/claude, ./claude, an absolute path, a backslash path) is refused and the judge falls back to the default command with a warning
- [ ] #2 Arguments after `llm_cmd[0]` are validated; a config passing --dangerously-skip-permissions or --allowedTools through repo-tracked config is refused
- [ ] #3 Env ADR_KIT_LLM_CMD and CLI --llm-cmd remain unrestricted, since those are operator-controlled
- [ ] #4 A regression test reproduces both vectors and asserts the repo-supplied binary is NOT executed
- [ ] #5 The rule is stated in the ADR governing TASK-59: repo-tracked config may select among operator-enabled backends but may never introduce an endpoint, binary or credential
- [ ] #6 If the TASK-59 backend registry lands first, this guard is replaced by the named-backend indirection rather than duplicated
<!-- AC:END -->
