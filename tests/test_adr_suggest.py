"""End-to-end tests for bin/adr-suggest — the advisory ADR-needed detector.

Strategy mirrors tests/test_adr_judge_llm.py: instead of calling Anthropic for
real, inject a fake `claude` binary via --llm-cmd. The fake script reads the
prompt from stdin and emits a canned JSON detector verdict to stdout. This
exercises prompt construction, subprocess plumbing, the response parser, and
the advisory output without any network or auth dependency.

Core invariant under test: adr-suggest is ADVISORY. Every path here asserts
exit code 0 — a suggestion engine must never block a commit.
"""
import json
import pytest
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_SUGGEST = REPO_ROOT / "bin" / "adr-suggest"


def _make_project(tmp_path: Path, adrs: dict, enabled: bool = True) -> Path:
    """Create a minimal project with ADRs and an .adr-kit.json config.

    By default suggest.enabled is True so existing tests exercise the real
    suggestion path. Pass enabled=False to test the opt-in skip behaviour.
    """
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    for name, body in adrs.items():
        (tmp_path / "docs" / "adr" / name).write_text(
            textwrap.dedent(body), encoding="utf-8"
        )
    import json as _json
    (tmp_path / "docs" / "adr" / ".adr-kit.json").write_text(
        _json.dumps({"suggest": {"enabled": enabled}}), encoding="utf-8"
    )
    return tmp_path


def _make_fake_claude(tmp_path: Path, response: str, record_prompt: bool = False) -> Path:
    """Write a Python script that swallows stdin and emits `response`.

    When record_prompt is True the script also writes the received stdin
    (the full prompt) to <tmp>/captured-prompt.txt so a test can assert on
    what the model actually saw (e.g. that existing ADR titles were included).

    Using Python instead of bash means the fake works on Windows where shell
    scripts are not directly executable.
    """
    fake = tmp_path / "fake-claude.py"
    response_file = tmp_path / "fake-response.txt"
    response_file.write_text(response, encoding="utf-8")
    prompt_capture = tmp_path / "captured-prompt.txt"
    lines = [
        "import sys",
        "data = sys.stdin.buffer.read()",
    ]
    if record_prompt:
        lines.append(f"open({str(prompt_capture)!r}, 'wb').write(data)")
    lines.append(
        f"sys.stdout.buffer.write(open({str(response_file)!r}, 'rb').read())"
    )
    fake.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return fake


def _fake_cmd(fake: Path) -> str:
    """Return a properly-quoted --llm-cmd string for the given fake-claude script."""
    if sys.platform == "win32":
        import subprocess as _sp
        return _sp.list2cmdline([sys.executable, str(fake)])
    import shlex as _shlex
    return f"{_shlex.quote(sys.executable)} {_shlex.quote(str(fake))}"


def _run_suggest(tmp_path: Path, diff_text: str, *extra_args):
    """Run adr-suggest, capture (returncode, stdout, stderr)."""
    result = subprocess.run(
        [
            sys.executable, str(ADR_SUGGEST),
            "--diff", "-",
            "--adr-dir", str(tmp_path / "docs" / "adr"),
            "--repo-root", str(tmp_path),
            *extra_args,
        ],
        input=diff_text, capture_output=True, text=True, encoding="utf-8",
    )
    return result.returncode, result.stdout, result.stderr


# An existing ADR so the detector has a "do not duplicate" list to reason about.
EXISTING_ADR = """\
# ADR-001: Use eventual consistency for the audit log

## Status

Accepted, 2026-04-25.

## Context

Audit log writes lag the primary transaction by up to 5 seconds.

## Decision

The audit log is eventually consistent. Reads MUST tolerate a 5-second lag.

## Consequences

**Positive:** Lower write latency.
**Negative:** Reads need lag tolerance.
"""

# A diff that touches a real source file (a new dependency).
CODE_DIFF = """\
diff --git a/src/cache.py b/src/cache.py
--- a/src/cache.py
+++ b/src/cache.py
@@ -1 +1,4 @@
+import redis
+
+def get_client():
+    return redis.Redis(host="localhost")
"""

# A docs-only diff — must be skipped without an LLM round-trip.
DOCS_DIFF = """\
diff --git a/docs/guide.md b/docs/guide.md
--- a/docs/guide.md
+++ b/docs/guide.md
@@ -1 +1,2 @@
+# Guide
+Some prose.
"""

# A version-bump-only diff (lockfile) — also skipped.
LOCKFILE_DIFF = """\
diff --git a/package-lock.json b/package-lock.json
--- a/package-lock.json
+++ b/package-lock.json
@@ -1 +1,2 @@
+  "version": "1.2.4",
+  "lockfileVersion": 3
"""


def test_needs_adr_high_confidence_prints_advisory(tmp_path):
    """needs_adr=true, high confidence -> advisory text on stderr, exit 0."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    fake = _make_fake_claude(tmp_path, json.dumps({
        "needs_adr": True,
        "confidence": "high",
        "reason": "introduces redis as a new caching dependency",
        "suggested_title": "Adopt Redis for caching",
        "category": "dependency",
    }))
    code, out, err = _run_suggest(proj, CODE_DIFF, "--llm-cmd", _fake_cmd(fake))
    assert code == 0
    assert "[adr-suggest] This change looks like a new dependency decision" in err
    assert "introduces redis as a new caching dependency" in err
    assert "Adopt Redis for caching" in err
    assert "NOT blocked" in err
    assert out.strip() == "", "advisory goes to stderr, stdout stays clean"


def test_needs_adr_false_prints_nothing(tmp_path):
    """needs_adr=false -> no advisory, exit 0."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    fake = _make_fake_claude(tmp_path, json.dumps({
        "needs_adr": False,
        "confidence": "high",
        "reason": "routine refactor",
        "suggested_title": "",
        "category": "none",
    }))
    code, out, err = _run_suggest(proj, CODE_DIFF, "--llm-cmd", _fake_cmd(fake))
    assert code == 0
    assert "This change looks like a new" not in err


def test_low_confidence_stays_silent(tmp_path):
    """needs_adr=true but low confidence -> no advisory (avoid noise), exit 0."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    fake = _make_fake_claude(tmp_path, json.dumps({
        "needs_adr": True,
        "confidence": "low",
        "reason": "maybe a small pattern",
        "suggested_title": "Something",
        "category": "architecture",
    }))
    code, out, err = _run_suggest(proj, CODE_DIFF, "--llm-cmd", _fake_cmd(fake))
    assert code == 0
    assert "This change looks like a new" not in err


def test_docs_only_diff_skips_llm(tmp_path):
    """A docs-only diff is skipped WITHOUT invoking the LLM, exit 0."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    # Fake that crashes if invoked — proves the LLM is never called.
    crashing = tmp_path / "crashing-fake.py"
    crashing.write_text("import sys; sys.exit(99)\n", encoding="utf-8")
    code, out, err = _run_suggest(proj, DOCS_DIFF, "--llm-cmd", _fake_cmd(crashing))
    assert code == 0
    assert "skipped: no code changes" in err


def test_version_bump_lockfile_skips_llm(tmp_path):
    """A lockfile-only diff is treated as non-decision and skipped, exit 0."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    crashing = tmp_path / "crashing-fake.py"
    crashing.write_text("import sys; sys.exit(99)\n", encoding="utf-8")
    code, out, err = _run_suggest(proj, LOCKFILE_DIFF, "--llm-cmd", _fake_cmd(crashing))
    assert code == 0
    assert "skipped: no code changes" in err


def test_empty_diff_skips_llm(tmp_path):
    """An empty diff is skipped, exit 0."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    crashing = tmp_path / "crashing-fake.py"
    crashing.write_text("import sys; sys.exit(99)\n", encoding="utf-8")
    code, out, err = _run_suggest(proj, "", "--llm-cmd", _fake_cmd(crashing))
    assert code == 0


def test_missing_llm_binary_graceful_skip(tmp_path):
    """A missing CLI -> advisory stderr note, exit 0 (never blocks)."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    code, out, err = _run_suggest(
        proj, CODE_DIFF, "--llm-cmd", "/nonexistent/path/to/claude-bin"
    )
    assert code == 0, "missing CLI must not block commits"
    assert "LLM unavailable; skipped" in err
    assert "This change looks like a new" not in err


def test_malformed_llm_json_graceful_skip(tmp_path):
    """Garbage from the LLM -> graceful skip, exit 0."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    fake = _make_fake_claude(tmp_path, "I cannot help with that. No JSON here.")
    code, out, err = _run_suggest(proj, CODE_DIFF, "--llm-cmd", _fake_cmd(fake))
    assert code == 0, "unparseable LLM output must NOT block commits"
    assert "LLM unavailable; skipped" in err
    assert "This change looks like a new" not in err


def test_json_emits_parseable_object(tmp_path):
    """--json emits the parsed result object to stdout, exit 0."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    fake = _make_fake_claude(tmp_path, json.dumps({
        "needs_adr": True,
        "confidence": "high",
        "reason": "new dependency",
        "suggested_title": "Adopt Redis",
        "category": "dependency",
    }))
    code, out, err = _run_suggest(proj, CODE_DIFF, "--json", "--llm-cmd", _fake_cmd(fake))
    assert code == 0
    parsed = json.loads(out)
    assert parsed["needs_adr"] is True
    assert parsed["confidence"] == "high"
    assert parsed["category"] == "dependency"
    assert parsed["suggested_title"] == "Adopt Redis"


def test_json_skip_for_docs_only(tmp_path):
    """--json on a docs-only diff emits a skipped object, exit 0, no LLM."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    crashing = tmp_path / "crashing-fake.py"
    crashing.write_text("import sys; sys.exit(99)\n", encoding="utf-8")
    code, out, err = _run_suggest(
        proj, DOCS_DIFF, "--json", "--llm-cmd", _fake_cmd(crashing)
    )
    assert code == 0
    parsed = json.loads(out)
    assert parsed["skipped"] is True
    assert parsed["needs_adr"] is False


def test_fenced_json_response_parsed(tmp_path):
    """Parser tolerates ```json ... ``` wrapped detector responses."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    raw = "Here is my analysis:\n\n```json\n" + json.dumps({
        "needs_adr": True,
        "confidence": "medium",
        "reason": "new wire format",
        "suggested_title": "Define binary wire format",
        "category": "api-contract",
    }) + "\n```\n"
    fake = _make_fake_claude(tmp_path, raw)
    code, out, err = _run_suggest(proj, CODE_DIFF, "--llm-cmd", _fake_cmd(fake))
    assert code == 0
    assert "new api-contract decision" in err
    assert "Define binary wire format" in err


def test_existing_adr_titles_included_in_prompt(tmp_path):
    """The existing ADR id + title must reach the model in the prompt."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    fake = _make_fake_claude(
        tmp_path,
        json.dumps({
            "needs_adr": False, "confidence": "high", "reason": "x",
            "suggested_title": "", "category": "none",
        }),
        record_prompt=True,
    )
    code, out, err = _run_suggest(proj, CODE_DIFF, "--llm-cmd", _fake_cmd(fake))
    assert code == 0
    captured = (tmp_path / "captured-prompt.txt").read_text(encoding="utf-8")
    assert "ADR-001" in captured
    assert "Use eventual consistency for the audit log" in captured
    assert "ALREADY EXIST" in captured
    # The diff content should also be present.
    assert "import redis" in captured


def test_no_existing_adrs_prompt_has_sentinel(tmp_path):
    """With no ADRs on disk the prompt still lists a clear '(none recorded yet)'."""
    proj = tmp_path
    (proj / "docs" / "adr").mkdir(parents=True)
    # Enable suggest so the pass actually runs (opt-in default as of v0.17.0).
    import json as _json
    (proj / "docs" / "adr" / ".adr-kit.json").write_text(
        _json.dumps({"suggest": {"enabled": True}}), encoding="utf-8"
    )
    fake = _make_fake_claude(
        tmp_path,
        json.dumps({
            "needs_adr": True, "confidence": "high", "reason": "first decision",
            "suggested_title": "Pick a web framework", "category": "architecture",
        }),
        record_prompt=True,
    )
    code, out, err = _run_suggest(proj, CODE_DIFF, "--llm-cmd", _fake_cmd(fake))
    assert code == 0
    captured = (tmp_path / "captured-prompt.txt").read_text(encoding="utf-8")
    assert "(none recorded yet)" in captured
    assert "new architecture decision" in err


def test_the_pass_runs_by_default(tmp_path):
    """ADR-035: on by default, on the same terms ADR-017 set for the judge.

    This asserted the opposite until 2026-08-06. The opt-in came from ADR-001,
    which ADR-017 superseded without carrying its reasoning to this second entry
    point, so the default outlived the decision behind it and R2's second half
    -- "is there a decision nobody recorded?" -- effectively never ran.

    The test it replaces could not have caught the flip either way: it asserted
    `"skipped" in err` against a fake that exits 99, and an LLM failure prints
    "skipped" exactly like an opt-in skip does. It passed under both defaults.
    This one asserts the advisory itself.
    """
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "docs" / "adr" / "ADR-001-eventual.md").write_text(
        textwrap.dedent(EXISTING_ADR), encoding="utf-8"
    )
    fake = _make_fake_claude(tmp_path, json.dumps({
        "needs_adr": True,
        "confidence": "high",
        "reason": "new redis dependency",
        "suggested_title": "Adopt Redis",
        "category": "dependency",
    }))

    code, out, err = _run_suggest(tmp_path, CODE_DIFF, "--llm-cmd", _fake_cmd(fake))

    assert code == 0, "a suggestion may never block"
    assert "This change looks like a new" in err


def test_the_disable_switch_works_in_this_script_not_only_in_the_hook(tmp_path):
    """ADR-035: the variable this script advertises has to work when it runs.

    `bin/adr-suggest` prints "Disable: ADR_KIT_SUGGEST_DISABLE=1" in its own
    advisory, but only `templates/githooks/pre-commit` read it. The pull-request
    guard spawns this script directly, so at that moment the documented switch
    did nothing -- the documented-but-unread no-op ADR-001 was written to fix,
    in this same file. Off by default hid it; on by default makes it the first
    thing a user reaches for.

    Asserted against an *explicitly enabled* pass, so it discriminates. Run
    against a default-off build with no config, nothing happens either way and
    the test proves nothing -- the trap the replaced default test fell into.
    """
    import os as _os

    project = _make_project(
        tmp_path, {"ADR-001-eventual.md": EXISTING_ADR}, enabled=True
    )
    fake = _make_fake_claude(tmp_path, json.dumps({
        "needs_adr": True,
        "confidence": "high",
        "reason": "new redis dependency",
        "suggested_title": "Adopt Redis",
        "category": "dependency",
    }))

    def _run(env_extra):
        return subprocess.run(
            [
                sys.executable, str(ADR_SUGGEST),
                "--diff", "-",
                "--adr-dir", str(project / "docs" / "adr"),
                "--repo-root", str(project),
                "--llm-cmd", _fake_cmd(fake),
            ],
            input=CODE_DIFF,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**_os.environ, **env_extra},
        )

    # Control: enabled, and the advisory appears. Without this the assertion
    # below could pass because the pass never ran for an unrelated reason.
    enabled = _run({"ADR_KIT_SUGGEST": "1"})
    assert "This change looks like a new" in enabled.stderr, (
        "the control run produced no advisory, so the disable assertion below "
        f"would prove nothing.\nstderr={enabled.stderr!r}"
    )

    disabled = _run({"ADR_KIT_SUGGEST": "1", "ADR_KIT_SUGGEST_DISABLE": "1"})

    assert disabled.returncode == 0
    assert "This change looks like a new" not in disabled.stderr, (
        "ADR_KIT_SUGGEST_DISABLE=1 did not suppress the pass in adr-suggest "
        "itself; only templates/githooks/pre-commit honoured it, so the "
        "pull-request path ignored the switch this script advertises"
    )


def test_a_project_can_still_switch_the_pass_off(tmp_path):
    """`suggest.enabled: false` remains the per-project off switch (ADR-035)."""
    project = _make_project(
        tmp_path, {"ADR-001-eventual.md": EXISTING_ADR}, enabled=False
    )
    fake = _make_fake_claude(tmp_path, json.dumps({
        "needs_adr": True,
        "confidence": "high",
        "reason": "new redis dependency",
        "suggested_title": "Adopt Redis",
        "category": "dependency",
    }))

    code, out, err = _run_suggest(project, CODE_DIFF, "--llm-cmd", _fake_cmd(fake))

    assert code == 0
    assert "This change looks like a new" not in err


def test_opt_in_env_enables_suggest(tmp_path):
    """ADR_KIT_SUGGEST=1 enables the pass even without suggest.enabled in config."""
    import os as _os
    # No .adr-kit.json — opt-in via env only.
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "docs" / "adr" / "ADR-001-eventual.md").write_text(
        textwrap.dedent(EXISTING_ADR), encoding="utf-8"
    )
    fake = _make_fake_claude(tmp_path, json.dumps({
        "needs_adr": True,
        "confidence": "high",
        "reason": "new redis dependency",
        "suggested_title": "Adopt Redis",
        "category": "dependency",
    }))
    env = {**_os.environ, "ADR_KIT_SUGGEST": "1"}
    result = subprocess.run(
        [
            sys.executable, str(ADR_SUGGEST),
            "--diff", "-",
            "--adr-dir", str(tmp_path / "docs" / "adr"),
            "--repo-root", str(tmp_path),
            "--llm-cmd", _fake_cmd(fake),
        ],
        input=CODE_DIFF, capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert result.returncode == 0
    assert "This change looks like a new dependency decision" in result.stderr


# ---------------------------------------------------------------------------
# --intent-file (v0.21+, /adr-kit:review support)
# ---------------------------------------------------------------------------

NO_DECISION_RESPONSE = json.dumps({
    "needs_adr": False,
    "confidence": "high",
    "reason": "routine refactor",
    "suggested_title": "",
    "category": "none",
})


def test_intent_file_content_reaches_prompt_delimited(tmp_path):
    """--intent-file text lands in the prompt inside its own sentinel data
    fence (task-12 hardening), after the security preamble and before the
    diff section."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    intent = tmp_path / "intent.txt"
    intent.write_text(
        "feat: switch session storage to Redis\n\nPR: we now keep sessions in Redis.",
        encoding="utf-8",
    )
    fake = _make_fake_claude(tmp_path, NO_DECISION_RESPONSE, record_prompt=True)
    code, out, err = _run_suggest(
        proj, CODE_DIFF, "--llm-cmd", _fake_cmd(fake),
        "--intent-file", str(intent),
    )
    assert code == 0
    captured = (tmp_path / "captured-prompt.txt").read_text(encoding="utf-8")
    assert "Stated intent" in captured
    assert "switch session storage to Redis" in captured
    # The intent block is fenced like every other untrusted block: ADR list,
    # intent, and diff each carry their own BEGIN/END sentinel pair (6), plus
    # the two marker literals quoted in the SECURITY instruction.
    assert captured.count("<<<ADR-KIT-DATA-") == 8
    # Order: intent block sits between its label and the diff section.
    label_at = captured.index("Stated intent")
    diff_at = captured.index("Diff (untrusted data):")
    assert label_at < captured.index("switch session storage to Redis") < diff_at


def test_no_intent_file_prompt_has_no_intent_section(tmp_path):
    """Without --intent-file the prompt carries no intent section (back-compat:
    byte-identical to the no-intent prompt shape)."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    fake = _make_fake_claude(tmp_path, NO_DECISION_RESPONSE, record_prompt=True)
    code, out, err = _run_suggest(proj, CODE_DIFF, "--llm-cmd", _fake_cmd(fake))
    assert code == 0
    captured = (tmp_path / "captured-prompt.txt").read_text(encoding="utf-8")
    assert "Stated intent" not in captured
    # Only the ADR list and the diff are fenced when no intent is supplied
    # (2 pairs), plus the two marker literals in the SECURITY instruction.
    assert captured.count("<<<ADR-KIT-DATA-") == 6


def test_missing_intent_file_is_usage_error(tmp_path):
    """A bad --intent-file path is a genuine usage error: exit 2, no LLM call."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    fake = _make_fake_claude(tmp_path, NO_DECISION_RESPONSE)
    code, out, err = _run_suggest(
        proj, CODE_DIFF, "--llm-cmd", _fake_cmd(fake),
        "--intent-file", str(tmp_path / "does-not-exist.txt"),
    )
    assert code == 2
    assert "--intent-file" in err


def test_intent_file_truncated_at_cap(tmp_path):
    """Intent longer than INTENT_MAX_CHARS is truncated with a marker; the
    tail never reaches the prompt."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    intent = tmp_path / "intent.txt"
    intent.write_text(
        ("decision noise " * 700) + "TAIL-SENTINEL-NEVER-IN-PROMPT",
        encoding="utf-8",
    )
    fake = _make_fake_claude(tmp_path, NO_DECISION_RESPONSE, record_prompt=True)
    code, out, err = _run_suggest(
        proj, CODE_DIFF, "--llm-cmd", _fake_cmd(fake),
        "--intent-file", str(intent),
    )
    assert code == 0
    captured = (tmp_path / "captured-prompt.txt").read_text(encoding="utf-8")
    assert "[intent truncated]" in captured
    assert "TAIL-SENTINEL-NEVER-IN-PROMPT" not in captured


# ---------------------------------------------------------------------------
# ADR-017 / TASK-72: adr-suggest resolves its model through the shared backend
# registry, carries no pinned model, and never executes a repo-tracked command.
#
# This file survived ADR-017 by a day: the ADR named adr-suggest in its
# `components` but scoped its Enforcement globs to adr-judge, so nothing checked
# this script. The tests below assert the properties the ADR states, on objects
# rather than by grepping the source -- a grep passes just as happily against a
# comment as against code.
# ---------------------------------------------------------------------------

def _load_suggest_module():
    """Import bin/adr-suggest as a module (it is an extension-less script)."""
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader("adr_suggest_mod", str(ADR_SUGGEST))
    spec = importlib.util.spec_from_loader("adr_suggest_mod", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["adr_suggest_mod"] = module
    loader.exec_module(module)
    return module


class _Args:
    """The one argparse field resolve_backend reads."""

    def __init__(self, llm_cmd=None):
        self.llm_cmd = llm_cmd


def test_host_backend_resolves_with_no_model_flag():
    """Criterion #1: the registry supplies the command, and it carries no pin.

    The pinned default this replaced sent every user's diff to one vendor on a
    model tag they never chose, however they had configured their own agent.
    """
    asg = _load_suggest_module()
    backend, warnings = asg.resolve_backend(
        _Args(), {}, {"judge": {"host_client": "codex-cli"}}
    )
    assert backend.cmd == ["codex", "exec"]
    assert not any("model" in token for token in backend.cmd), backend.cmd
    assert warnings == []


def test_only_the_host_backend_is_reachable_from_suggest():
    """The whole enum resolves here, and the enum is host-only (ADR-036)."""
    asg = _load_suggest_module()
    retired, warnings = asg.resolve_backend(
        _Args(), {"judge": {"backend": "ollama", "ollama_model": "gemma4:12b"}}, {}
    )
    assert retired is None
    assert any("retired by ADR-036" in w for w in warnings), warnings

@pytest.mark.parametrize("block", ["suggest", "judge"])
def test_repo_tracked_llm_cmd_never_becomes_the_command(block):
    """Criterion #2, on the object: the config vector is not what gets run.

    The vector below is the TASK-60 bypass shape -- a basename on the allowlist
    with a directory component in front of it. The resolver adr-suggest used to
    carry compared only `Path(candidate[0]).name` / `.stem`, so it accepted this
    and handed it to subprocess, letting a committed file choose the binary.
    Now the same config yields the registry's own backend and a warning.
    """
    asg = _load_suggest_module()
    poisoned = ["bin/claude.exe", "-p", "--dangerously-skip-permissions"]
    cfg = {"judge": {"backend": "host"}}
    cfg.setdefault(block, {})["llm_cmd"] = poisoned
    backend, warnings = asg.resolve_backend(
        _Args(), cfg, {"judge": {"host_client": "claude-code-cli"}}
    )
    assert backend.cmd == ["claude", "-p"], "the registry supplied the command"
    assert "bin/claude.exe" not in backend.cmd
    assert "--dangerously-skip-permissions" not in backend.cmd
    ignored = [w for w in warnings if w.startswith(block + ".llm_cmd is ignored")]
    assert ignored, warnings
    # The diagnostic still says WHY that particular vector was dangerous, and
    # names the key the author actually wrote.
    assert "path separator" in ignored[0]
    assert block + ".llm_cmd[0]" in ignored[0]


@pytest.mark.parametrize("block", ["suggest", "judge"])
def test_repo_tracked_llm_model_no_longer_pins_a_model(block):
    """A model tag in committed config is reported as ignored, not obeyed.

    It used to be reassembled into a `--model <tag>` invocation of one vendor's
    CLI, which is the pin ADR-017 removed wearing a different hat.
    """
    asg = _load_suggest_module()
    cfg = {"judge": {"backend": "host"}}
    cfg.setdefault(block, {})["llm_model"] = "some-vendor-tag"
    backend, warnings = asg.resolve_backend(
        _Args(), cfg, {"judge": {"host_client": "claude-code-cli"}}
    )
    assert backend.cmd == ["claude", "-p"]
    assert "some-vendor-tag" not in " ".join(backend.cmd)
    assert any(w.startswith(block + ".llm_model is ignored") for w in warnings), warnings


def test_operator_overrides_are_still_honoured():
    """--llm-cmd and ADR_KIT_LLM_CMD stay unrestricted.

    They come from the person running the command, not from whoever last opened
    a pull request, so ADR-017 leaves them alone. The rest of this file runs
    almost entirely through --llm-cmd; this asserts that on purpose rather than
    relying on it as a side effect.
    """
    asg = _load_suggest_module()
    backend, _ = asg.resolve_backend(_Args("some-binary --flag"), {}, {})
    assert backend.cmd == ["some-binary", "--flag"]
    assert backend.source == "flag"


def test_repo_tracked_command_is_never_executed(tmp_path):
    """Criterion #2 end to end: no marker file, no advisory, no block.

    The command in the committed config writes a marker and prints a verdict
    that would produce a suggestion. Neither appears, because it is never run.
    """
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    marker = tmp_path / "poisoned-command-ran.txt"
    verdict = json.dumps({
        "needs_adr": True, "confidence": "high", "reason": "poison",
        "suggested_title": "Poison", "category": "dependency",
    })
    poison = tmp_path / "claude.py"
    poison.write_text(
        "open({!r}, 'w').write('ran')\nprint({!r})\n".format(str(marker), verdict),
        encoding="utf-8",
    )
    (proj / "docs" / "adr" / ".adr-kit.json").write_text(
        json.dumps({"suggest": {"enabled": True, "llm_cmd": [str(poison), "-p"]}}),
        encoding="utf-8",
    )
    code, out, err = _run_suggest(proj, CODE_DIFF)
    assert code == 0, err[:600]
    assert not marker.exists(), "a repo-tracked command was executed"
    assert "suggest.llm_cmd is ignored" in err
    assert "This change looks like" not in err, "the poisoned verdict was used"


def test_unavailable_backend_is_a_silent_no_op(tmp_path):
    """Criterion #3: no backend, no commit blocked, no suggestion invented.

    ADR-001's guarantee that tooling drift never costs a user their commit is
    retained verbatim by ADR-017, and it has to hold for the suggestion pass
    exactly as it does for the judge.
    """
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    code, out, err = _run_suggest(proj, CODE_DIFF)
    assert code == 0, err[:600]
    assert "This change looks like" not in err
    assert "no client was recorded" in err, err[:600]


def test_credential_in_committed_config_is_refused_by_name(tmp_path):
    """The one thing that is NOT a silent no-op, and deliberately so.

    An unavailable backend is tooling drift and degrades quietly. A key written
    into a committed file is a published key -- a user error that must be seen,
    and staying quiet about it would leave the key in the repository. Same
    sentence adr-judge raises, from the same function.
    """
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": EXISTING_ADR})
    (proj / "docs" / "adr" / ".adr-kit.json").write_text(
        json.dumps({"suggest": {"enabled": True, "api_key": "sk-not-a-real-key"}}),
        encoding="utf-8",
    )
    code, out, err = _run_suggest(proj, CODE_DIFF)
    assert code == 2
    assert "refusing to read a credential" in err
    assert "sk-not-a-real-key" not in err, "the refusal must not echo the key"
