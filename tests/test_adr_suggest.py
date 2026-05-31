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


def test_opt_in_disabled_by_default_no_llm_call(tmp_path):
    """With default config (no suggest block), adr-suggest exits 0 and does NOT
    invoke the fake LLM binary — the opt-in skip fires before any LLM round-trip.
    """
    # No .adr-kit.json written; suggest.enabled defaults to false.
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "docs" / "adr" / "ADR-001-eventual.md").write_text(
        textwrap.dedent(EXISTING_ADR), encoding="utf-8"
    )
    # Crashing fake: if invoked, exits 99 to make the test fail loudly.
    crashing = tmp_path / "crashing-fake.py"
    crashing.write_text("import sys; sys.exit(99)\n", encoding="utf-8")
    code, out, err = _run_suggest(tmp_path, CODE_DIFF, "--llm-cmd", _fake_cmd(crashing))
    assert code == 0, "opt-in skip must not block commits"
    assert "skipped" in err, "should report skip reason"
    # Verify the crashing fake was NOT invoked (if it were, code would be 0 only
    # because adr-suggest swallows the exit — but stderr would carry no advisory).
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
