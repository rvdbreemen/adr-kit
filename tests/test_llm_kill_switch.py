"""ADR_KIT_NO_LLM=1 stops every model call, not only the judge's (TASK-221).

The judge honoured it, but adr-suggest and adr-substance resolved their backend
without looking, so a user who exported it to keep diffs off any model still
had the suggestion pass call one on every commit. The switch now lives in the
shared resolver, which all three entry points use.

Each end-to-end test has a control that runs the same command without the
switch and sees the fake model called, so a skipped call proves the switch and
not a broken fixture.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN = REPO_ROOT / "bin"
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))

import adr_llm  # noqa: E402

from test_adr_substance import _adr_dir, _fake_cli  # noqa: E402

SUGGEST = BIN / "adr-suggest"
SUBSTANCE = BIN / "adr-substance"

CODE_DIFF = (
    "diff --git a/app/cache.py b/app/cache.py\n"
    "new file mode 100644\n"
    "--- /dev/null\n"
    "+++ b/app/cache.py\n"
    "@@ -0,0 +1,3 @@\n"
    "+import redis\n"
    "+CLIENT = redis.Redis(host='cache', port=6379)\n"
    "+def get(key): return CLIENT.get(key)\n"
)


def _env(fake_cmd: str, *, no_llm: bool) -> dict:
    env = dict(os.environ)
    env.pop("ADR_KIT_SUGGEST_DISABLE", None)
    env.pop("ADR_KIT_NO_LLM", None)
    env["ADR_KIT_LLM_CMD"] = fake_cmd
    if no_llm:
        env["ADR_KIT_NO_LLM"] = "1"
    return env


def test_the_resolver_returns_no_backend_under_the_switch():
    local = {"judge": {"host_client": "claude-code-cli"}}
    for cli_cmd, env in (
        (None, {"ADR_KIT_NO_LLM": "1"}),
        ("some-llm --flag", {"ADR_KIT_NO_LLM": "1"}),
        (None, {"ADR_KIT_NO_LLM": "1", "ADR_KIT_LLM_CMD": "some-llm"}),
    ):
        backend, warnings = adr_llm.resolve_llm_backend({}, local, cli_cmd, env)
        assert backend is None
        assert any("ADR_KIT_NO_LLM" in w for w in warnings)


def test_the_resolver_ignores_a_switch_that_is_not_one():
    backend, _ = adr_llm.resolve_llm_backend({}, {}, None, {"ADR_KIT_NO_LLM": "0", "ADR_KIT_LLM_CMD": "x"})
    assert backend is not None


def _substance(adr_dir: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SUBSTANCE), "--adr-dir", str(adr_dir)],
        capture_output=True, text=True, encoding="utf-8",
        stdin=subprocess.DEVNULL, env=env, timeout=60,
    )


def test_adr_substance_calls_no_model_under_the_switch(tmp_path):
    adr_dir = _adr_dir(tmp_path)
    fake = _fake_cli(tmp_path, {"findings": []})
    prompts = tmp_path / "prompts.txt"

    _substance(adr_dir, _env(fake, no_llm=False))
    assert prompts.exists(), "control: without the switch the fake model is called"
    prompts.unlink()

    result = _substance(adr_dir, _env(fake, no_llm=True))
    assert result.returncode == 0, result.stderr
    assert not prompts.exists()


def _suggest(adr_dir: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SUGGEST), "--diff", "-", "--adr-dir", str(adr_dir)],
        input=CODE_DIFF, capture_output=True, text=True, encoding="utf-8",
        env=env, timeout=60,
    )


def test_adr_suggest_calls_no_model_under_the_switch(tmp_path):
    adr_dir = _adr_dir(tmp_path)
    fake = _fake_cli(tmp_path, {"suggest": False})
    prompts = tmp_path / "prompts.txt"

    _suggest(adr_dir, _env(fake, no_llm=False))
    assert prompts.exists(), "control: without the switch the fake model is called"
    prompts.unlink()

    result = _suggest(adr_dir, _env(fake, no_llm=True))
    assert result.returncode == 0, result.stderr
    assert not prompts.exists()
