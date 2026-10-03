"""The judge's LLM pass has a wall-clock ceiling that a host CLI cannot defeat.

TASK-210. Three things let one judge run last far longer than its timeouts
promise:

* `subprocess.run(..., capture_output=True, timeout=N)` kills only the direct
  child, then waits for EOF on the pipes. A grandchild that inherited stdout
  (a host CLI starting its own helpers) keeps the pipe open, so the call
  returned only when the grandchild did: measured 60 s for a 2 s timeout.
* The pass is one call per `llm_judge` ADR with a per-call timeout and no
  ceiling for the whole pass.
* `adr-judge-precommit` waited on adr-judge without any timeout.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN = REPO_ROOT / "bin"
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))

import adr_llm  # noqa: E402

from test_adr_judge_llm import _load_judge_module  # noqa: E402


def _fake_cli(tmp_path: Path, *, parent_lingers: bool) -> list:
    """A host CLI that starts a 30 s grandchild holding the inherited stdout."""
    script = tmp_path / "fake_cli.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import subprocess, sys, time
            sys.stdin.read()
            child = subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(30)"]
            )
            open({str(tmp_path / 'grandchild.pid')!r}, "w").write(str(child.pid))
            if {parent_lingers!r}:
                time.sleep(30)
            print("{{}}")
            """
        ),
        encoding="utf-8",
    )
    return [sys.executable, str(script)]


def _alive(pid: int) -> bool:
    # Never os.kill(pid, 0) on Windows: CPython turns it into TerminateProcess.
    if os.name == "nt":
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
        ).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def test_a_lingering_grandchild_cannot_hold_a_timed_out_call(tmp_path):
    backend = adr_llm.SubprocessBackend(_fake_cli(tmp_path, parent_lingers=True), "test")

    started = time.monotonic()
    result = backend.judge("prompt", 2, "ADR-001")
    elapsed = time.monotonic() - started

    assert result is None
    assert elapsed < 12, f"timed-out call took {elapsed:.1f}s"
    pid = int((tmp_path / "grandchild.pid").read_text())
    deadline = time.monotonic() + 5
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.2)
    assert not _alive(pid), "the timeout must take the grandchild down with it"


def test_an_exited_cli_returns_even_while_its_grandchild_runs(tmp_path):
    backend = adr_llm.SubprocessBackend(_fake_cli(tmp_path, parent_lingers=False), "test")

    started = time.monotonic()
    result = backend.judge("prompt", 20, "ADR-001")
    elapsed = time.monotonic() - started

    assert result is not None and result.strip() == "{}"
    assert elapsed < 12, f"call waited {elapsed:.1f}s on the grandchild's pipe"


def test_run_cli_returns_output_and_exit_code(tmp_path):
    # Bytes in, bytes out: a real host CLI speaks UTF-8 whatever the console
    # code page, and the test child must not decode through cp1252.
    echo = [
        sys.executable,
        "-c",
        "import sys; d=sys.stdin.buffer.read().decode('utf-8');"
        "sys.stdout.buffer.write(d.upper().encode('utf-8')); sys.exit(3)",
    ]

    result = adr_llm.run_cli(echo, "héllo", 20)

    assert result.returncode == 3
    assert result.stdout.strip() == "HÉLLO"


class _SlowBackend(adr_llm.LLMBackend):
    """Spends exactly the timeout it is given, and records it."""

    def __init__(self):
        self.timeouts = []

    def judge(self, prompt, timeout_s, adr_id):
        self.timeouts.append(timeout_s)
        time.sleep(timeout_s)
        return None


def test_the_whole_pass_stops_at_its_deadline():
    aj = _load_judge_module()
    backend = _SlowBackend()
    targets = [
        {"adr_id": f"ADR-00{n}", "title": "t", "decision": "d"} for n in range(1, 5)
    ]
    attestation = {"evaluated": [], "degraded": False, "degraded_reason": None}

    started = time.monotonic()
    result = aj.run_llm_batch(
        targets, "diff", backend, 1, attestation=attestation, pass_timeout_s=1.5
    )
    elapsed = time.monotonic() - started

    assert result is None
    assert elapsed < 3, f"pass ran {elapsed:.1f}s past a 1.5 s ceiling"
    assert len(backend.timeouts) == 2
    assert backend.timeouts[0] == 1
    assert 0 < backend.timeouts[1] <= 0.6
    assert attestation["degraded"] is True
    assert "ADR-003" in attestation["degraded_reason"]
    assert "ADR-004" in attestation["degraded_reason"]
    assert "pass deadline" in attestation["degraded_reason"]


def test_the_precommit_wrapper_gives_up_on_a_hung_judge(tmp_path):
    """The wrapper's own ceiling is a backstop for a judge that never returns."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "adr-judge-precommit").write_text(
        (BIN / "adr-judge-precommit").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (bindir / "adr-judge").write_text(
        "import sys, time\nsys.stdin.read()\ntime.sleep(60)\n", encoding="utf-8"
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)

    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(bindir / "adr-judge-precommit")],
        cwd=repo,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "ADR_KIT_JUDGE_TIMEOUT_S": "2"},
        timeout=60,
    )
    elapsed = time.monotonic() - started

    assert elapsed < 20, f"wrapper waited {elapsed:.1f}s"
    assert proc.returncode == 2
    assert "timed out" in proc.stderr
