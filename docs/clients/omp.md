# OMP (oh-my-pi) support

ADR Kit supports [OMP](https://github.com/can1357/oh-my-pi) through a native
extension that ships in the same plugin as the Claude Code distribution. The
extension is a thin adapter over the shared Python engines (ADR-050). OMP is
not a certified client: it is absent from `clients/capabilities.json`, the
automatic installer, `adr-doctor` and the generated
[client support matrix](../client-support.md), and the three-client release
gate (ADR-010) does not cover it.

Verified on OMP 18.12.5, Windows.

## Install

```bash
omp plugin marketplace add rvdbreemen/adr-kit
omp plugin install --scope user adr-kit@rvdbreemen-adr-kit
omp plugin list
```

Inside a session the equivalents are `/marketplace add rvdbreemen/adr-kit` and
`/marketplace install adr-kit@rvdbreemen-adr-kit`. Start a new session
afterwards: OMP loads extension modules at startup, and `/reload-plugins`
refreshes skills and MCP servers but not extensions. Use `--scope project` to
limit the install to one repository.

OMP reads the repository's `.claude-plugin/marketplace.json` and caches the
plugin under
`~/.omp/plugins/cache/plugins/rvdbreemen-adr-kit___adr-kit___<version>/`. It
registers the plugin under the npm name from the root `package.json`,
`@rvdbreemen/adr-kit-opencode`, and loads the extension that file declares
under `omp.extensions`. `scripts/install-agent-envs.py` does not detect or
install OMP.

Then initialize each project once:

```text
/skill:init
```

This installs the ADR Kit pre-commit gate and the managed guidance blocks in
`AGENTS.md` and `CLAUDE.md`, both of which OMP reads. Copy the CI workflows
from `templates/github-workflows/` for the pull-request tier.

## Native surface

| Surface | Behaviour under OMP |
|---|---|
| Skills | All 17 skills load. The nine with `disable-model-invocation: true` (`init`, `setup`, `install-hooks`, `lint`, `migrate`, `retire`, `settings`, `supersede`, `upgrade`) are hidden from the model and run only when invoked as `/skill:<name>`. OMP has no `/adr-kit:` namespace. |
| Agent | `adr-generator` is available as a task agent. |
| MCP | The plugin's `.mcp.json` registers the `adr-kit` server with the seven read-only tools (`adr_context`, `adr_judge`, `adr_status`, `adr_quality`, `adr_readiness`, `adr_lint`, `adr_related`). The server starts in the plugin cache; pass `project_root` to target a project other than the session's working directory. |
| Engine root | The extension sets `ADR_KIT_ROOT` to the installed plugin when it is unset. OMP provides no `${CLAUDE_PLUGIN_ROOT}`, and the skills resolve the engine as `${ADR_KIT_ROOT:-${CLAUDE_PLUGIN_ROOT}}` (ADR-044). A value you set yourself is kept. |
| Python | `ADR_KIT_PYTHON`, then the first of `python3`, `python` and, on Windows, `py -3` that runs Python 3.10 or newer. The MCP server in `.mcp.json` runs `python`. |

## Hooks

OMP runs only TypeScript/JavaScript extensions, never the command hooks in
`hooks/hooks.json`. The extension maps OMP's events onto `hooks/adr-hook.py`:

| ADR Kit moment | OMP event | How the context arrives |
|---|---|---|
| Session | `session_start` | With the first prompt, as a hidden custom message |
| Prompt | `before_agent_start` | Hidden custom message; static ADR Kit instructions are appended to the system prompt |
| Edit (`edit`, `write`, `ast_edit`) | `tool_call` | Passive tool context |
| Post-edit backstop | `tool_result` | Passive tool context, only after a successful edit |
| Pull-request moment (`bash`) | `tool_call` | Blocks the call only on the shared guard's explicit deny |
| Subagent | `before_agent_start` in the child session | Hidden custom message carrying the main session's context, once |
| Compaction | `session.compacting` | Compaction context |

Plan exit has no OMP event and does not fire.

OMP delivers `tool_call` context after the tool batch settles, so the
pre-edit decision reaches the model after the edit, alongside the post-edit
backstop, rather than before it. Only the paths an edit touches are sent to the
hook, never file content.

Every handler is bounded (2 s, 5 s for the pull-request guard) and catches its
own faults. OMP treats a failing `tool_call` handler as a block, so a missing
interpreter, a timeout or a hook error yields no context instead.

## LLM layers

The per-commit judge pass, `adr-suggest` and the guardian's LLM tier are on by
default and run on OMP's own model through
`omp -p --no-extensions --no-session --no-tools`: no API key and no pinned
model (ADR-036, ADR-043). `--no-extensions` keeps ADR Kit's own extension out
of a judging call. The hook renders Claude Code's output shape, so the
extension names its own host through `ADR_KIT_HOST_CLIENT=omp-cli`. The first
prompt in a project records `omp-cli` as the judge's host when none is
recorded; a recorded choice is never replaced. The next prompt then asks once
whether to keep each layer on, and an "off" goes to the gitignored
`.adr-kit.local.json` (ADR-049). `ADR_KIT_NO_LLM=1` switches every layer off
for a run.

## Alongside a Claude Code install

OMP's `claude-plugins` discovery provider can also load plugins from Claude
Code's own registry (`~/.claude/plugins`). That copy contributes skills and the
MCP server but never the extension, which OMP loads only from its own plugin
installs. When ADR Kit is installed in both, MCP servers with the same name
keep the first definition found and identical skills are de-duplicated. On
different versions the skills differ, and OMP keeps one under its bare name and
loads the other with a namespace prefix. Upgrade both together, or keep only
one.

## Update and removal

```bash
omp plugin marketplace update rvdbreemen-adr-kit
omp plugin upgrade adr-kit@rvdbreemen-adr-kit
omp plugin disable adr-kit@rvdbreemen-adr-kit     # reversible pause
omp plugin uninstall adr-kit@rvdbreemen-adr-kit
```

`marketplace update` only refreshes the catalog; `upgrade` reinstalls. Removing
the plugin does not touch project files: remove the pre-commit gate first with
`python "$ADR_KIT_ROOT/scripts/setup-project.py" --project-root <project> --remove-pre-commit`.

## Verify

```bash
omp plugin list
```

In a new session inside a project with `docs/adr/`:

- `echo "$ADR_KIT_ROOT"` in the shell prints the plugin directory;
- `/skill:lint` runs `adr-lint` without a `plugin root not found` error;
- `docs/adr/.adr-kit.local.json` names `omp-cli` as `judge.host_client` after
  the first prompt.

Focused evidence: `tests/test_omp_extension.py` drives every handler through a
Bun harness against a fixture project.

## Support boundary

OMP has a native extension for this package, but it is not included in
`clients/capabilities.json` or the generated three-client support matrix. The
installer, native doctor, evidence bundle and release certification gate
remain unchanged, and OMP does not claim those clients' update, rollback,
doctor or certification guarantees. Report OMP API or runtime issues with the
OMP version, platform, ADR Kit version and the result of
`python -m pytest -q tests/test_omp_extension.py`.
