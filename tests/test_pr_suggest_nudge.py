"""The pull-request moment asks both halves of R2, not one (TASK-97, ADR-024).

R2 asks two questions when a branch becomes a pull request: does this change
violate an accepted decision, and does it contain a decision nobody recorded.
Only the first was answered. The second happened if someone typed
`/adr-kit:review` or had individually opted into `ADR_KIT_SUGGEST`, which in
practice means it did not happen.

The nudge joins the guard rather than getting a moment of its own, because this
one is already intercepted and the user is already waiting. What it must never
do is deny: a suggestion is a question about a decision nobody recorded, and
blocking on one teaches people to write an empty ADR to get past it -- the
failure mode that produced six rule-less Enforcement blocks in this repository.

Gate anchor for ADR-024: adr-pr-suggest-v1
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _guard():
    if str(ROOT / "hooks") not in sys.path:
        sys.path.insert(0, str(ROOT / "hooks"))
    spec = importlib.util.spec_from_file_location(
        "adr_pr_guard_under_test", ROOT / "hooks" / "adr_pr_guard.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GUARD = _guard()


class _Result:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


SUGGESTION = (
    "[adr-suggest] This change looks like it introduces a durable decision.\n"
    "[adr-suggest]   swapping the HTTP client is a dependency choice\n"
)


def test_the_nudge_is_extracted_from_what_adr_suggest_actually_prints(monkeypatch, tmp_path):
    """Only the suggestion lines, not the skipped/unavailable notes.

    adr-suggest prints "(skipped: ...)" and "LLM unavailable" on commits that
    introduce no decision. Surfacing those at the pull-request moment would make
    the guard noisy on exactly the branches it has nothing to say about.
    """
    noisy = SUGGESTION + "[adr-suggest] (skipped: no LLM backend configured)\n"
    monkeypatch.setattr(GUARD, "_run", lambda *a, **k: _Result(stderr=noisy))
    suggest = tmp_path / "adr-suggest"
    suggest.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    text = GUARD._nudge(tmp_path, tmp_path, suggest, "diff", 5)

    assert "durable decision" in text
    assert "swapping the HTTP client" in text
    assert "skipped" not in text


def test_a_branch_with_no_candidate_decision_says_nothing(monkeypatch, tmp_path):
    """AC#5. A clean branch must see nothing at all."""
    monkeypatch.setattr(
        GUARD, "_run", lambda *a, **k: _Result(stderr="[adr-suggest] (skipped: no decision)\n")
    )
    suggest = tmp_path / "adr-suggest"
    suggest.write_text("", encoding="utf-8")

    assert GUARD._nudge(tmp_path, tmp_path, suggest, "diff", 5) == ""


def test_a_failing_suggest_is_silent_rather_than_loud(monkeypatch, tmp_path):
    """The advisory half must never turn an outage into a message.

    The judge's failures are worth reporting because an unchecked branch looks
    exactly like a clean one. A missing suggestion carries no such ambiguity.
    """
    def boom(*args, **kwargs):
        raise OSError("no interpreter")

    monkeypatch.setattr(GUARD, "_run", boom)
    suggest = tmp_path / "adr-suggest"
    suggest.write_text("", encoding="utf-8")

    assert GUARD._nudge(tmp_path, tmp_path, suggest, "diff", 5) == ""


def test_the_nudge_is_bounded_by_what_is_left_of_the_guards_budget(monkeypatch, tmp_path):
    """AC#4. One budget for the whole moment, not one per subprocess.

    The guard's Deadline exists because every call site used to carry its own
    constant and the worst case was 114 s inside a 5 s budget. The nudge must
    spend from the same deadline, and pass it down so killing the child also
    bounds the model call it makes.
    """
    seen = {}

    def capture(argv, cwd, timeout, stdin_text=None):
        seen["argv"] = argv
        seen["timeout"] = timeout
        return _Result(stderr=SUGGESTION)

    monkeypatch.setattr(GUARD, "_run", capture)
    suggest = tmp_path / "adr-suggest"
    suggest.write_text("", encoding="utf-8")

    GUARD._nudge(tmp_path, tmp_path, suggest, "diff", 3)

    assert seen["timeout"] == 3
    assert "--llm-timeout" in seen["argv"]
    assert seen["argv"][seen["argv"].index("--llm-timeout") + 1] == "3"


def test_the_entrypoint_never_denies_on_a_suggestion_alone():
    """AC#3, read off the source of the one function that can deny.

    A suggestion reaching the deny branch is the failure ADR-024 names, and it
    would be invisible in a passing suite until the day someone's clean branch
    was blocked for containing a decision.
    """
    source = (ROOT / "hooks" / "adr-hook.py").read_text(encoding="utf-8")
    body = source[source.index("def _pr_guard") : source.index("def _emit")]

    deny_lines = [line for line in body.splitlines() if '"pr-guard-deny"' in line]
    assert deny_lines, "the deny branch disappeared"
    for line in deny_lines:
        assert "nudge" not in line, (
            "the deny verdict is being produced from the nudge; a suggestion may "
            "never block the tool call (ADR-024)"
        )

    assert '"pr-guard-suggest"' in body, "the nudge never reaches the user"
    # And the branch that returns it must be reached only when the judge allowed.
    suggest_at = body.index('"pr-guard-suggest"')
    deny_at = body.index('"pr-guard-deny"')
    assert deny_at < suggest_at, "the advisory branch precedes the denial branch"


def test_the_guard_passes_a_suggest_path_at_all():
    """Without this the whole feature is inert and nothing else here would fail."""
    source = (ROOT / "hooks" / "adr-hook.py").read_text(encoding="utf-8")
    assert "suggest=" in source and "adr-suggest" in source


@pytest.mark.parametrize("client", ["codex", "copilot"])
def test_both_mirrors_carry_the_nudge(client):
    """The v0.44.1 outage was a guard that existed in one tree and not the others."""
    mirrored = (ROOT / client / "hooks" / "adr_pr_guard.py").read_text(encoding="utf-8")
    assert "def _nudge(" in mirrored
    entry = (ROOT / client / "hooks" / "adr-hook.py").read_text(encoding="utf-8")
    assert "pr-guard-suggest" in entry


def test_the_nudge_reads_the_stream_adr_suggest_actually_writes_to(tmp_path):
    """End to end against the real script, because the fakes agreed with the bug.

    `_nudge` filtered `result.stdout`. `emit_advisory` writes every advisory
    line to **stderr** -- deliberately, so stdout stays pipe-clean for `--json`
    -- so the filter matched nothing and ADR-024's nudge could never reach a
    user. Every unit test above passed throughout: each one fabricated a
    `_Result` carrying the text on stdout, so the suite asserted the guard
    against the guard's own mistaken belief rather than against the program it
    calls.

    This drives the real `bin/adr-suggest` with a stub backend, so the two
    sides have to agree on the stream or this fails.
    """
    import json
    import subprocess

    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / ".adr-kit.json").write_text(
        json.dumps({"suggest": {"enabled": True}}), encoding="utf-8"
    )

    reply = json.dumps(
        {
            "needs_adr": True,
            "confidence": "high",
            "reason": "swapping the HTTP client is a dependency choice",
            "suggested_title": "Choose an HTTP client",
            "category": "dependency",
        }
    )
    stub = tmp_path / "stub.py"
    stub.write_text(
        "import sys\nsys.stdout.write(%r)\n" % reply, encoding="utf-8"
    )

    diff = (
        "diff --git a/app.py b/app.py\n"
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1 +1 @@\n"
        "-import requests\n"
        "+import httpx\n"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin" / "adr-suggest"),
            "--diff", "-",
            "--adr-dir", str(adr_dir),
            "--llm-cmd", f'"{sys.executable}" "{stub}"',
        ],
        input=diff,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    on_stderr = [
        line for line in (result.stderr or "").splitlines()
        if line.startswith("[adr-suggest] This change")
    ]
    on_stdout = [
        line for line in (result.stdout or "").splitlines()
        if line.startswith("[adr-suggest] This change")
    ]
    assert on_stderr, (
        "bin/adr-suggest emitted no advisory on stderr, so this test can no "
        f"longer prove which stream _nudge must read.\nstdout={result.stdout!r}"
        f"\nstderr={result.stderr!r}"
    )
    assert not on_stdout, "the advisory reached stdout; _nudge now reads the wrong stream"

    # Given that real process output, the guard surfaces it.
    class _Real:
        stdout, stderr, returncode = result.stdout, result.stderr, 0

    original = GUARD._run
    GUARD._run = lambda *a, **k: _Real()
    try:
        suggest = tmp_path / "adr-suggest"
        suggest.write_text("", encoding="utf-8")
        text = GUARD._nudge(tmp_path, adr_dir, suggest, diff, 5)
    finally:
        GUARD._run = original

    assert "This change looks like" in text
    assert "dependency choice" in text
