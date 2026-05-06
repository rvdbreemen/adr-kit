"""End-to-end tests for the LLM judge pass added in v0.13.0.

Strategy: instead of calling Anthropic for real, inject a fake `claude`
binary via --llm-cmd. The fake script reads the prompt from stdin and
emits a canned JSON verdict to stdout. This exercises the prompt construction,
the subprocess plumbing, the response parser, and the verdict-to-finding
conversion without any network or auth dependency.
"""
import json
import os
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_JUDGE = REPO_ROOT / "bin" / "adr-judge"


def _make_project(tmp_path: Path, adrs: dict) -> Path:
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    for name, body in adrs.items():
        (tmp_path / "docs" / "adr" / name).write_text(textwrap.dedent(body), encoding="utf-8")
    return tmp_path


def _make_fake_claude(tmp_path: Path, response: str) -> Path:
    """Write a shell script that swallows its argv + stdin and emits `response`.

    Returns the path. Caller passes it via --llm-cmd. The canned response is
    written to a side-file so newlines, fences, and backslashes survive
    intact (printf '%s' doesn't interpret escapes; printf '%b' interprets
    too many; cat preserves bytes exactly).
    """
    fake = tmp_path / "fake-claude"
    response_file = tmp_path / "fake-response.txt"
    response_file.write_text(response, encoding="utf-8")
    body = (
        "#!/usr/bin/env bash\n"
        "cat >/dev/null\n"
        f"cat {response_file}\n"
    )
    fake.write_text(body, encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return fake


def _run_judge(tmp_path: Path, diff_text: str, *extra_args):
    """Run adr-judge with --json, capture parsed output + exit code."""
    result = subprocess.run(
        [
            sys.executable, str(ADR_JUDGE),
            "--diff", "-",
            "--adr-dir", str(tmp_path / "docs" / "adr"),
            "--repo-root", str(tmp_path),
            "--json",
            *extra_args,
        ],
        input=diff_text, capture_output=True, text=True, encoding="utf-8",
    )
    if not result.stdout.strip():
        return result.returncode, {"_stderr": result.stderr}
    return result.returncode, json.loads(result.stdout)


# A free-form ADR with llm_judge:true and no declarative rules.
LLM_JUDGE_ADR = """\
# ADR-001: Use eventual consistency for the audit log

## Status

Accepted, 2026-04-25.

## Context

Audit log writes lag the primary transaction by up to 5 seconds.

## Decision

The audit log is eventually consistent. Reads of the audit log MUST tolerate
a 5-second lag. Code paths that need synchronous audit semantics MUST NOT
read from the audit-log replica; they read from the primary.

## Alternatives Considered

- Synchronous: rejected, doubles write latency.
- No audit: rejected, compliance.

## Consequences

**Positive:**
- Lower primary write latency.

**Negative:**
- Reads need lag tolerance.

## Related Decisions

- None.

## References

- None.

## Enforcement

```json
{"llm_judge": true}
```
"""

SAMPLE_DIFF = """\
diff --git a/src/audit.py b/src/audit.py
--- a/src/audit.py
+++ b/src/audit.py
@@ -1 +1,3 @@
+def show_audit():
+    return audit_replica.read_synchronously()
"""


def test_llm_pass_disabled_by_default(tmp_path):
    """Without --llm the LLM pass does NOT fire; legacy advisory is emitted."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": LLM_JUDGE_ADR})
    code, out = _run_judge(proj, SAMPLE_DIFF)
    assert code == 0
    assert out["summary"]["violations"] == 0
    assert out["summary"]["advisories"] == 1, "v0.12.x advisory preserved when --llm is off"


def test_llm_pass_violation_blocks_commit(tmp_path):
    """With --llm and a fake claude returning VIOLATION, exit code is 1."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": LLM_JUDGE_ADR})
    fake = _make_fake_claude(tmp_path, json.dumps({
        "ADR-001": {"verdict": "VIOLATION", "reason": "introduces synchronous read of audit_replica in src/audit.py"}
    }))
    code, out = _run_judge(proj, SAMPLE_DIFF, "--llm", "--llm-cmd", str(fake))
    assert code == 1
    assert out["summary"]["violations"] == 1
    assert out["summary"]["advisories"] == 0, "advisory replaced by real verdict"
    f = out["findings"][0]
    assert f["adr"] == "ADR-001"
    assert f["rule"] == "llm_judge"
    assert "audit_replica" in f["message"]


def test_llm_pass_ok_lets_commit_through(tmp_path):
    """When the LLM verdict is OK, no finding is emitted and exit is 0."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": LLM_JUDGE_ADR})
    fake = _make_fake_claude(tmp_path, json.dumps({"ADR-001": {"verdict": "OK"}}))
    code, out = _run_judge(proj, SAMPLE_DIFF, "--llm", "--llm-cmd", str(fake))
    assert code == 0
    assert out["summary"]["violations"] == 0


def test_llm_response_with_fenced_json(tmp_path):
    """Parser tolerates ```json ... ``` wrapped responses."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": LLM_JUDGE_ADR})
    raw = "Here is the verdict:\n\n```json\n" + json.dumps({
        "ADR-001": {"verdict": "VIOLATION", "reason": "x"}
    }) + "\n```\n"
    fake = _make_fake_claude(tmp_path, raw)
    code, out = _run_judge(proj, SAMPLE_DIFF, "--llm", "--llm-cmd", str(fake))
    assert code == 1
    assert out["summary"]["violations"] == 1


def test_llm_response_with_prose_around_json(tmp_path):
    """Parser tolerates leading/trailing prose around the JSON object."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": LLM_JUDGE_ADR})
    raw = (
        "Sure! After reviewing the diff against the ADR I think the change is fine.\n"
        + json.dumps({"ADR-001": {"verdict": "OK"}})
        + "\nLet me know if you need anything else."
    )
    fake = _make_fake_claude(tmp_path, raw)
    code, out = _run_judge(proj, SAMPLE_DIFF, "--llm", "--llm-cmd", str(fake))
    assert code == 0


def test_llm_unparseable_response_falls_back(tmp_path):
    """Garbage from the LLM produces a WARN and exit 0 — never blocks commit."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": LLM_JUDGE_ADR})
    fake = _make_fake_claude(tmp_path, "I cannot help with that.")
    code, out = _run_judge(proj, SAMPLE_DIFF, "--llm", "--llm-cmd", str(fake))
    assert code == 0, "unparseable LLM output must NOT block commits"


def test_llm_missing_binary_falls_back(tmp_path):
    """When the configured CLI does not exist, judge emits WARN and exits 0."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": LLM_JUDGE_ADR})
    # Use a binary path that definitely doesn't exist.
    code, out = _run_judge(
        proj, SAMPLE_DIFF, "--llm", "--llm-cmd", "/nonexistent/path/to/claude-bin"
    )
    assert code == 0, "missing CLI must not block commits — graceful fallback"
    # No LLM violation emitted; only the legacy advisory.
    assert out["summary"]["violations"] == 0


def test_llm_no_targets_skips_call(tmp_path):
    """ADRs without llm_judge:true don't trigger the LLM pass at all."""
    declarative_only = textwrap.dedent("""\
        # ADR-002: No String

        ## Status

        Accepted, 2026-04-25.

        ## Decision

        No String class.

        ## Alternatives Considered

        - String: rejected.
        - char[]: accepted.

        ## Consequences

        **Positive:**
        - Lower fragmentation.

        **Negative:**
        - More boilerplate.

        ## Related Decisions

        - None.

        ## References

        - None.

        ## Enforcement

        ```json
        {"forbid_pattern": [{"pattern": "\\\\bString\\\\b"}]}
        ```
    """)
    proj = _make_project(tmp_path, {"ADR-002-nostring.md": declarative_only})
    # Fake binary that would crash if invoked — to prove it isn't.
    crashing = _make_fake_claude(tmp_path, "")
    crashing.write_text("#!/usr/bin/env bash\nexit 99\n", encoding="utf-8")
    code, out = _run_judge(proj, SAMPLE_DIFF, "--llm", "--llm-cmd", str(crashing))
    # No llm_judge:true ADRs → LLM batch not invoked → exit 0 with no violations.
    assert code == 0


def test_llm_pass_via_env_no_llm_disables(tmp_path):
    """ADR_KIT_NO_LLM=1 forces declarative-only even when --llm is passed."""
    proj = _make_project(tmp_path, {"ADR-001-eventual.md": LLM_JUDGE_ADR})
    fake = _make_fake_claude(tmp_path, json.dumps({
        "ADR-001": {"verdict": "VIOLATION", "reason": "would-be-violation"}
    }))
    env = {**os.environ, "ADR_KIT_NO_LLM": "1"}
    result = subprocess.run(
        [
            sys.executable, str(ADR_JUDGE),
            "--diff", "-",
            "--adr-dir", str(proj / "docs" / "adr"),
            "--repo-root", str(proj),
            "--llm",
            "--llm-cmd", str(fake),
            "--json",
        ],
        input=SAMPLE_DIFF, capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    # ADR_KIT_NO_LLM forces v0.12.x advisory mode → 0 violations, 1 advisory.
    assert out["summary"]["violations"] == 0
    assert out["summary"]["advisories"] == 1


def test_llm_batches_multiple_adrs_in_one_call(tmp_path):
    """Two llm_judge ADRs result in ONE claude invocation, not two."""
    counter_path = tmp_path / "counter"
    counter_path.write_text("0", encoding="utf-8")
    second_adr = LLM_JUDGE_ADR.replace("ADR-001", "ADR-002").replace(
        "Use eventual consistency for the audit log",
        "Some other free-form decision",
    )
    proj = _make_project(tmp_path, {
        "ADR-001-eventual.md": LLM_JUDGE_ADR,
        "ADR-002-other.md": second_adr,
    })
    # Fake claude that increments a counter file each invocation.
    fake = tmp_path / "counting-fake"
    response_file = tmp_path / "counting-response.txt"
    response_file.write_text(json.dumps({
        "ADR-001": {"verdict": "OK"},
        "ADR-002": {"verdict": "OK"},
    }), encoding="utf-8")
    fake.write_text(textwrap.dedent(f"""\
        #!/usr/bin/env bash
        cat >/dev/null
        n=$(cat {counter_path})
        echo $((n+1)) > {counter_path}
        cat {response_file}
    """), encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    code, out = _run_judge(proj, SAMPLE_DIFF, "--llm", "--llm-cmd", str(fake))
    assert code == 0
    invocations = int(counter_path.read_text().strip())
    assert invocations == 1, f"LLM should be called exactly once, was called {invocations} times"
