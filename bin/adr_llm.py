"""Shared LLM backend registry for adr-kit's model-calling entry points.

ADR-017 replaced a pinned vendor CLI with a named enum resolving to a code-side
command table. `bin/adr-judge` shipped that table under TASK-59; `bin/adr-suggest`
kept its own default command vector naming one vendor and one pinned model tag,
and kept honouring `suggest.llm_cmd` / `judge.llm_cmd` (TASK-72), so the
guarantee "repository-tracked configuration may never introduce a command" held
for one entry point and not the other.

This module is that table, extracted so there is exactly one of it. A second
registry that drifts from the first is worse than the single violation it would
have replaced: it puts the rule in two places and lets them disagree silently.

Both importers reach it through their own `_load_sibling`, so no sys.path entry
is created and nothing committed next to these scripts can shadow it.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple

# Which entry point is running, used only as the warning prefix. A plain module
# global rather than a parameter threaded through three factories and four
# backend classes: exactly one entry point runs per process, so there is no
# second value for it to be wrong about. Importers assign it at load time.
TOOL = "adr-kit"

# ---------- backend registry (ADR-017) ----------
#
# The judge used to hard-code one vendor CLI and one pinned model tag. Two
# things were wrong with that shape. A user working in a different agent got a
# judge that did not match the assistant they were actually using, and the
# pinned tag was a vendor decision adr-kit had no standing to make on their
# behalf. ADR-017 replaces it with a named enum resolving to THIS table.
#
# The registry is code-side on purpose. .adr-kit.json is committed, so anyone
# with commit access authors it; it may select among backends the operator has
# enabled, but it may never introduce a binary, an endpoint, or a credential.
# Because the table lives here and config carries only an enum value, that
# property is structural rather than guarded: there is no argument vector in
# any configuration file, tracked or not, for a check to have to refuse.

BACKEND_HOST = "host"
BACKEND_OPENROUTER = "openrouter"
BACKEND_OLLAMA = "ollama"
BACKEND_NAMES = (BACKEND_HOST, BACKEND_OPENROUTER, BACKEND_OLLAMA)
DEFAULT_BACKEND = BACKEND_HOST

# Non-interactive entry point of each certified client (ADR-010), verified
# 2026-07-30 against the installed binaries: claude 2.1.220, codex-cli 0.145.0,
# GitHub Copilot CLI 1.0.71. Deliberately NO model flag in any row -- each CLI
# then resolves whatever model its own user configured, which is the entire
# point of the host backend.
HOST_COMMANDS = {
    "claude-code-cli": ["claude", "-p"],
    "codex-cli": ["codex", "exec"],
    "github-copilot-cli": ["copilot", "-p"],
}

# Machine-local, gitignored sibling of .adr-kit.json. Neither entry point can
# detect which client it runs in -- a `git commit` is client-agnostic, it
# happens whether or not any agent is running -- so the installer records the
# client here at install time, when it is known with certainty because the
# operator named it. ADR-017 rejects probing PATH: on a machine with all three
# CLIs installed the probe order would silently decide which vendor receives
# the repository diff, and that is a privacy decision made by accident.
LOCAL_CONFIG_NAME = ".adr-kit.local.json"

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_KEY_ENV = "OPENROUTER_API_KEY"
OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"
DEFAULT_OLLAMA_MODEL = "gemma4:12b"

# Config keys that would carry a credential. docs/adr/.adr-kit.json is
# committed, so a key written there is a published key. The schema already
# refuses unknown properties, but "unknown property" does not tell an author
# what to do instead, and a leaked credential is worth an error that names the
# environment variable by hand.
# Anchored on the WHOLE key, not a substring: `inject.max_tokens` is a real
# setting and a substring match on "token" would refuse a valid config with a
# security error, which is the most expensive kind of false positive there is.
# Hence `_token` but not `_tokens`.
_CREDENTIAL_KEY_RE = re.compile(
    r"(?i)^(.*_)?(api_?key|key|secrets?|token|password|passwd|credentials?"
    r"|bearer|authorization)$"
)

# Repo-tracked llm_cmd is now IGNORED outright (ADR-017): the backend registry
# above replaced it, and a registry that must admit `ollama` cannot be
# expressed as a tightened Claude-CLI allowlist. What survives here is the
# diagnostic. When a project still carries an llm_cmd, the tool says exactly
# WHY that particular vector was dangerous rather than emitting a generic
# "ignored" -- an author who wrote `--dangerously-skip-permissions` into
# committed config deserves to read that sentence.
#
# Env (ADR_KIT_LLM_CMD) and CLI (--llm-cmd) remain unrestricted and remain
# honoured, because those are operator-controlled, not arbitrarily checked in
# by collaborators.
_LLM_CMD_ALLOWLIST = {
    "claude",
    "claude-code",
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
    "claude-haiku-4-5-20251001",
}

# SEC-HIGH (TASK-60): the argument vector from repo-tracked config is checked
# too, not just its head. `["claude", "-p", "--dangerously-skip-permissions",
# "--allowedTools", "Bash"]` passed the old head-only check and invoked the
# genuine CLI with tool permissions disabled, on a prompt built from repository
# content. Only flags that cannot grant the model new capabilities are allowed.
_LLM_CMD_SAFE_FLAGS = frozenset({"-p", "--print"})
_LLM_CMD_SAFE_VALUE_FLAGS = frozenset({"--model", "--output-format"})


def _warn(message: str) -> None:
    print(f"[{TOOL}] WARN: {message}", file=sys.stderr)


def _split_cmd(cmd_str: str) -> List[str]:
    """Split a shell command string into a token list, Windows-path-safe.

    shlex.split uses POSIX mode by default, which treats backslashes as escape
    characters. On Windows this mangles paths like C:\\Users\\... -> C:Users...
    before shutil.which ever sees them. Using posix=False preserves backslashes;
    we strip surrounding quote pairs that posix=False would otherwise keep.
    """
    tokens = shlex.split(cmd_str, posix=(sys.platform != "win32"))
    if sys.platform == "win32":
        stripped = []
        for t in tokens:
            if len(t) >= 2 and ((t[0] == '"' and t[-1] == '"') or (t[0] == "'" and t[-1] == "'")):
                t = t[1:-1]
            stripped.append(t)
        return stripped
    return tokens


def check_repo_llm_cmd(
    candidate: List[str], key: str = "judge.llm_cmd"
) -> Optional[str]:
    """Return a refusal reason for a repo-tracked llm_cmd, or None if OK.

    The governing rule: repository-tracked config may select among backends the
    operator has already enabled; it may never introduce a new binary, a new
    endpoint, or a credential. Env (ADR_KIT_LLM_CMD) and CLI (--llm-cmd) stay
    unrestricted because those are operator-controlled, not checked in by
    whoever last opened a pull request.

    SEC-HIGH (TASK-60), two reproduced bypasses this closes:

    1. `Path(candidate[0]).stem` discarded the directory before comparing, so a
       committed `bin/claude.exe` plus a committed `judge.llm_cmd` naming it
       passed the allowlist -- and shutil.which() resolves a path carrying a
       directory component directly, without a PATH search. A repository could
       ship the binary the judge executes. The stem also made every
       `claude.<ext>` (claude.sh, claude.bat, claude.py) pass.
    2. Only candidate[0] was inspected; every argument after it was unvalidated.

    So: no path separator anywhere in the binary token, exact match of the FULL
    token (no Path() call at all -- taking .name or .stem is the defect), and a
    safe-flag allowlist over the rest of the vector.

    `key` names the config key in the message, because the same vector can
    arrive from judge.llm_cmd or suggest.llm_cmd and an author fixing it needs
    to be told which one they wrote.
    """
    if not candidate:
        return f"{key} is empty"
    binary = candidate[0]
    if not binary:
        return f"{key}[0] is empty"
    # A literal "/" and "\\" are rejected on every platform, not just the
    # platform whose os.sep they are: a POSIX runner must still refuse
    # "bin\\claude", and a Windows runner must still refuse "bin/claude".
    separators = {os.sep, os.altsep, "/", "\\"}
    if any(sep and sep in binary for sep in separators):
        return (
            f"{key}[0]={binary!r} contains a path separator; "
            f"repo-tracked config may only name a bare binary resolved from PATH"
        )
    if ":" in binary:
        # "C:claude" is drive-relative and "name:stream" is an NTFS alternate
        # data stream; neither is a bare PATH lookup.
        return (
            f"{key}[0]={binary!r} contains a drive or stream separator; "
            f"repo-tracked config may only name a bare binary resolved from PATH"
        )
    if binary not in _LLM_CMD_ALLOWLIST:
        return (
            f"{key}[0]={binary!r} is not in the allowed list "
            f"{sorted(_LLM_CMD_ALLOWLIST)}"
        )
    i = 1
    while i < len(candidate):
        arg = candidate[i]
        head, sep, _value = arg.partition("=")
        if sep and head in _LLM_CMD_SAFE_VALUE_FLAGS:
            i += 1
            continue
        if arg in _LLM_CMD_SAFE_VALUE_FLAGS:
            if i + 1 >= len(candidate):
                return f"{key} flag {arg!r} is missing its value"
            i += 2
            continue
        if arg in _LLM_CMD_SAFE_FLAGS:
            i += 1
            continue
        return (
            f"{key} argument {arg!r} is not in the allowed flag set "
            f"{sorted(_LLM_CMD_SAFE_FLAGS | _LLM_CMD_SAFE_VALUE_FLAGS)}"
        )
    return None


def legacy_command_warnings(cfg_block: Dict, block: str) -> List[str]:
    """Say that a repo-tracked llm_cmd / llm_model is ignored, and why.

    Both entry points need this and both used to honour these keys, so it lives
    with the registry rather than in either script: the rule "repository-tracked
    configuration may never introduce a command" (ADR-017) either holds at every
    entry point or it holds at none of them.

    Keys are dead as configuration but still present in existing projects, so
    the message is precise about what replaced them rather than silent.
    """
    warnings: List[str] = []
    raw_cfg_cmd = cfg_block.get("llm_cmd")
    if raw_cfg_cmd:
        candidate = (
            [str(tok) for tok in raw_cfg_cmd]
            if isinstance(raw_cfg_cmd, list)
            else _split_cmd(str(raw_cfg_cmd))
        )
        detail = check_repo_llm_cmd(candidate, f"{block}.llm_cmd")
        warnings.append(
            f"{block}.llm_cmd is ignored: repository-tracked configuration may not "
            "supply a command or an argument vector (ADR-017). Select a backend "
            f"with judge.backend ({' | '.join(BACKEND_NAMES)}), or use "
            "ADR_KIT_LLM_CMD / --llm-cmd for an operator-controlled override."
            + (f" [{detail}]" if detail else "")
        )
    if cfg_block.get("llm_model"):
        warnings.append(
            f"{block}.llm_model is ignored: the host backend passes no model flag "
            "so each CLI resolves the model its own user configured (ADR-017). "
            "Use judge.openrouter_model or judge.ollama_model to pick a model "
            "for those backends."
        )
    return warnings


class LLMBackend:
    """One way of getting a verdict out of a model.

    Three failure taxonomies live behind this interface -- process spawn, HTTP
    status, and daemon availability -- and ADR-017 requires all three to map to
    the same outcome: degrade to declarative-only, never block. So `judge`
    returns None for every fault rather than raising, and `unavailable_reason`
    reports what can be known before spending anything.
    """

    kind = ""

    def describe(self) -> str:
        raise NotImplementedError

    def unavailable_reason(self) -> Optional[str]:
        """Why this backend cannot run, checked before the first call."""
        return None

    def judge(self, prompt: str, timeout_s: int, adr_id: str) -> Optional[str]:
        """Return the model's raw response text, or None to degrade.

        `adr_id` labels the call in warnings. adr-judge passes the ADR under
        review; adr-suggest has no ADR yet and passes its own label.
        """
        raise NotImplementedError


class SubprocessBackend(LLMBackend):
    """Spawn a client CLI, feed it the prompt on stdin, read stdout.

    Backs both the `host` backend and the operator overrides (--llm-cmd,
    ADR_KIT_LLM_CMD), because those differ in where the vector came from, not
    in how it is run.
    """

    kind = BACKEND_HOST

    def __init__(self, cmd: List[str], source: str, client: Optional[str] = None):
        self.cmd = list(cmd)
        self.source = source
        self.client = client

    def describe(self) -> str:
        label = self.client or "operator override"
        return f"{self.kind} ({label}): {' '.join(self.cmd)}"

    def unavailable_reason(self) -> Optional[str]:
        if not self.cmd:
            return "no host command was resolved"
        if shutil.which(self.cmd[0]) is None:
            return (
                f"{self.cmd[0]!r} is not on PATH; install the client CLI or "
                f"choose another judge.backend"
            )
        return None

    def judge(self, prompt: str, timeout_s: int, adr_id: str) -> Optional[str]:
        try:
            result = subprocess.run(
                self.cmd,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            _warn(
                f"LLM call timed out after {timeout_s}s on {adr_id}; skipping "
                f"LLM pass. Increase judge.llm_timeout_seconds in .adr-kit.json "
                f"if commits routinely exceed this."
            )
            return None
        except OSError as e:
            # A command that cannot be spawned at all (CreateProcess/execvp
            # failure) must degrade like every other tooling fault, not escape
            # as an uncaught exception and exit 1 -- that would read as
            # "violation".
            _warn(
                f"LLM command could not be started "
                f"({e.__class__.__name__}); skipping LLM pass."
            )
            return None
        if result.returncode != 0:
            # SEC-LOW: don't leak stderr (may contain tokens, paths, prompts)
            # by default. Operators opt in to the full payload via ADR_KIT_DEBUG.
            if os.environ.get("ADR_KIT_DEBUG"):
                _warn(
                    f"LLM command exited {result.returncode} on {adr_id}: "
                    f"{result.stderr.strip()[:200]!r}; skipping LLM pass."
                )
            else:
                _warn("LLM call failed. Rerun with ADR_KIT_DEBUG=1 for details.")
            return None
        return result.stdout


class HttpBackend(LLMBackend):
    """Shared urllib plumbing for the two network backends.

    ADR-016's zero-runtime-dependency constraint is binding, so this is
    urllib.request and nothing else. No vendor SDK enters the dependency set
    for a feature that posts one JSON document and reads one back.
    """

    endpoint = ""

    def _post(
        self, payload: Dict, headers: Dict[str, str], timeout_s: int, adr_id: str
    ) -> Optional[Dict]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            # Status is safe to print; the body may echo the prompt or a key
            # prefix, so it stays behind ADR_KIT_DEBUG like subprocess stderr.
            detail = ""
            if os.environ.get("ADR_KIT_DEBUG"):
                try:
                    detail = f": {e.read().decode('utf-8', errors='replace')[:200]!r}"
                except Exception:  # pragma: no cover - best effort only
                    detail = ""
            _warn(
                f"{self.kind} backend returned HTTP {e.code} on {adr_id}{detail}; "
                f"skipping LLM pass."
            )
            return None
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            _warn(
                f"{self.kind} backend unreachable on {adr_id} "
                f"({e.__class__.__name__}); skipping LLM pass."
            )
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            _warn(
                f"{self.kind} backend returned a non-JSON envelope on {adr_id}; "
                f"skipping LLM pass."
            )
            return None
        return data if isinstance(data, dict) else None


class OpenRouterBackend(HttpBackend):
    """OpenRouter chat completions, model chosen by the project.

    The key is read from the environment and only from the environment.
    docs/adr/.adr-kit.json is committed, so a key written there is a published
    key; see credential_refusal_message for the refusal that says so.
    """

    kind = BACKEND_OPENROUTER
    endpoint = OPENROUTER_ENDPOINT

    def __init__(self, model: Optional[str]):
        self.model = model

    def describe(self) -> str:
        return f"{self.kind}: {self.model or '<unset>'} via {self.endpoint}"

    def unavailable_reason(self) -> Optional[str]:
        if not self.model:
            return (
                "judge.openrouter_model is unset; set it to a provider/model "
                "slug (for example 'anthropic/claude-sonnet-4.5')"
            )
        if not os.environ.get(OPENROUTER_KEY_ENV):
            return (
                f"{OPENROUTER_KEY_ENV} is not set in the environment; export it "
                f"rather than writing a key into committed configuration"
            )
        return None

    def judge(self, prompt: str, timeout_s: int, adr_id: str) -> Optional[str]:
        data = self._post(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            },
            {"Authorization": f"Bearer {os.environ.get(OPENROUTER_KEY_ENV, '')}"},
            timeout_s,
            adr_id,
        )
        if data is None:
            return None
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            _warn(f"{self.kind} backend returned no choices on {adr_id}.")
            return None
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        return content if isinstance(content, str) else None


class OllamaBackend(HttpBackend):
    """A local daemon, so nothing leaves the machine.

    Measured at 3378 ms for one judge-shaped prompt against gemma4:12b on the
    reference machine. That is over ADR-015's two-second deterministic budget
    and legal under its explicit exemption for LLM passes, but a user choosing
    this backend is accepting slower commits and the settings surface says so.
    """

    kind = BACKEND_OLLAMA
    endpoint = OLLAMA_ENDPOINT

    def __init__(self, model: str):
        self.model = model

    def describe(self) -> str:
        return f"{self.kind}: {self.model} via {self.endpoint}"

    def unavailable_reason(self) -> Optional[str]:
        # Daemon reachability is deliberately NOT probed here: a probe costs a
        # round trip on every commit and answers a question the first real call
        # answers anyway, with the same degrade path.
        if not self.model:
            return "judge.ollama_model is unset"
        return None

    def judge(self, prompt: str, timeout_s: int, adr_id: str) -> Optional[str]:
        data = self._post(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            {},
            timeout_s,
            adr_id,
        )
        if data is None:
            return None
        response = data.get("response")
        return response if isinstance(response, str) else None


def _host_backend(
    judge_cfg: Dict, local_cfg: Dict, warnings: List[str]
) -> Optional[SubprocessBackend]:
    """Build the host backend from the installer-written client id.

    Returns None when no client was recorded. ADR-017: "If no host command was
    written (adr-kit used outside a client install), the judge degrades to
    declarative-only with one warning. It does not guess."
    """
    client = (local_cfg.get("judge") or {}).get("host_client")
    if not client:
        warnings.append(
            f"judge.backend is 'host' but no client was recorded in "
            f"{LOCAL_CONFIG_NAME}; the LLM pass will not run. Register one with "
            f"`adr-judge --set-backend host --host-client "
            f"<{'|'.join(HOST_COMMANDS)}>` or via /adr-kit:init."
        )
        return None
    if client not in HOST_COMMANDS:
        warnings.append(
            f"{LOCAL_CONFIG_NAME} names unknown host client {client!r}; "
            f"expected one of {sorted(HOST_COMMANDS)}. The LLM pass will not run."
        )
        return None
    return SubprocessBackend(HOST_COMMANDS[client], source="local", client=client)


def _openrouter_backend(
    judge_cfg: Dict, local_cfg: Dict, warnings: List[str]
) -> OpenRouterBackend:
    model = judge_cfg.get("openrouter_model")
    return OpenRouterBackend(str(model) if model else None)


def _ollama_backend(
    judge_cfg: Dict, local_cfg: Dict, warnings: List[str]
) -> OllamaBackend:
    return OllamaBackend(str(judge_cfg.get("ollama_model") or DEFAULT_OLLAMA_MODEL))


# THE registry ADR-017 names. A dict rather than an if-chain because the whole
# security argument rests on config selecting a KEY here and never supplying a
# value: judge.backend is looked up in this table or refused, so committed
# configuration has no path to a command, an argument vector, an endpoint or a
# credential. Every endpoint and every command lives on this side of the line.
BACKENDS = {
    BACKEND_HOST: _host_backend,
    BACKEND_OPENROUTER: _openrouter_backend,
    BACKEND_OLLAMA: _ollama_backend,
}


def resolve_llm_backend(
    judge_cfg: Dict,
    local_cfg: Dict,
    cli_cmd: Optional[str],
    env: Dict[str, str],
) -> Tuple[Optional[LLMBackend], List[str]]:
    """Pick the backend for this run and collect anything the user should know.

    Precedence, highest first: --llm-cmd, ADR_KIT_LLM_CMD, judge.backend. The
    first two are operator-controlled and therefore unrestricted; the third is
    a key looked up in the code-side BACKENDS table and can introduce nothing.

    Warnings are returned rather than printed so --show-config can render them
    without a judging run, and so the caller controls ordering.

    Both entry points resolve from `judge.*`: the backend is which model the
    project talks to, not which tool is asking, and a parallel `suggest.backend`
    would be a second place for the same answer to live.
    """
    # Repo-tracked command and model keys are dead as configuration (ADR-017)
    # but still present in old projects. Say so once, precisely.
    warnings = legacy_command_warnings(judge_cfg, "judge")

    if cli_cmd:
        return SubprocessBackend(_split_cmd(cli_cmd), source="flag"), warnings
    if env.get("ADR_KIT_LLM_CMD"):
        return (
            SubprocessBackend(_split_cmd(env["ADR_KIT_LLM_CMD"]), source="env"),
            warnings,
        )

    name = str(judge_cfg.get("backend", DEFAULT_BACKEND))
    factory = BACKENDS.get(name)
    if factory is None:
        warnings.append(
            f"judge.backend={name!r} is not one of {list(BACKEND_NAMES)}; "
            f"the LLM pass will not run."
        )
        return None, warnings
    return factory(judge_cfg, local_cfg, warnings), warnings


def find_credential_keys(config: object, path: str = "$") -> List[str]:
    """Return dotted paths of every credential-shaped key in a config document."""
    found: List[str] = []
    if isinstance(config, dict):
        for key, value in config.items():
            child = f"{path}.{key}"
            if isinstance(key, str) and _CREDENTIAL_KEY_RE.match(key.replace("-", "_")):
                found.append(child)
            found.extend(find_credential_keys(value, child))
    elif isinstance(config, list):
        for index, item in enumerate(config):
            found.extend(find_credential_keys(item, f"{path}[{index}]"))
    return found


def credential_refusal_message(path, offenders: List[str]) -> str:
    """The sentence a published credential earns, shared by both entry points.

    ADR-017 requires the refusal to name the environment variable, and the
    message has to be identical wherever it is raised: a user who fixes the
    file because adr-judge told them to must not meet a differently-worded
    version of the same problem from adr-suggest a second later.
    """
    return (
        f"{path}: refusing to read a credential from configuration "
        f"({', '.join(offenders)}). This file is committed, so a key "
        f"written here is a published key. Delete that key from the file "
        f"BY HAND and export {OPENROUTER_KEY_ENV} in your environment "
        f"instead; no adr-kit command can do it for you, because every "
        f"entry point (including --set-backend) refuses to load the file "
        f"while the key is in it. Then rotate the key: it is already in "
        f"your git history."
    )
