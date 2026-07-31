"""Git path decoding and snapshot behavior for require_pattern.

The snapshot mode decides where `require_pattern` reads a file's post-image
from, and each of the three modes is exercised here, including the choice the
MCP `adr_judge` tool makes on its caller's behalf.
"""

from __future__ import annotations

import importlib.util
import json
import runpy
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
JUDGE = ROOT / "bin" / "adr-judge"
MCP = ROOT / "bin" / "adr-mcp"
JUDGE_NS = runpy.run_path(str(JUDGE))


def test_parse_diff_decodes_git_c_quoted_paths():
    diff = (
        'diff --git "a/src/\\303\\251\\tquote\\".py" '
        '"b/src/\\303\\251\\tquote\\".py"\n'
        '--- "a/src/\\303\\251\\tquote\\".py"\n'
        '+++ "b/src/\\303\\251\\tquote\\".py"\n'
        "@@ -0,0 +1 @@\n"
        "+Foo()\n"
    )

    files = JUDGE_NS["parse_diff"](diff)

    assert list(files) == ['src/é\tquote".py']
    assert files['src/é\tquote".py'].added == [(1, "Foo()")]


def test_parse_diff_preserves_unquoted_spaces_and_delete_path():
    changed = (
        "diff --git a/src/my file.py b/src/my file.py\n"
        "--- a/src/my file.py\n"
        "+++ b/src/my file.py\n"
        "@@ -1 +1 @@\n"
        "+value = 2\n"
    )
    deleted = (
        "diff --git a/src/old file.py b/src/old file.py\n"
        "--- a/src/old file.py\n"
        "+++ /dev/null\n"
        "@@ -1 +0,0 @@\n"
        "-value = 1\n"
    )

    changed_files = JUDGE_NS["parse_diff"](changed)
    deleted_files = JUDGE_NS["parse_diff"](deleted)

    assert list(changed_files) == ["src/my file.py"]
    assert list(deleted_files) == ["src/old file.py"]
    assert deleted_files["src/old file.py"].deleted is True


def _run_explicit(
    tmp_path: Path, diff: str, snapshot: str = "diff"
) -> subprocess.CompletedProcess:
    adr_dir = tmp_path / "docs" / "adr"
    if not adr_dir.is_dir():
        adr_dir.mkdir(parents=True)
        (adr_dir / "ADR-001-required.md").write_text(
            textwrap.dedent(
                """\
                # ADR-001 Required Marker

                ## Status

                Accepted, 2026-07-18.

                ## Decision

                Require a marker.

                ## Enforcement

                ```json
                {
                  "require_pattern": [
                    {"pattern": "^REQUIRED$", "path_glob": "src/**/*.txt"}
                  ]
                }
                ```
                """
            ),
            encoding="utf-8",
        )
    return subprocess.run(
        [
            sys.executable,
            str(JUDGE),
            "--diff",
            "-",
            "--adr-dir",
            str(adr_dir),
            "--repo-root",
            str(tmp_path),
            "--snapshot",
            snapshot,
            "--json",
        ],
        input=diff,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


MODIFIED_DIFF = (
    "diff --git a/src/existing.txt b/src/existing.txt\n"
    "--- a/src/existing.txt\n"
    "+++ b/src/existing.txt\n"
    "@@ -1 +1 @@\n"
    "-old\n"
    "+new\n"
)


def test_explicit_diff_reconstructs_complete_new_file(tmp_path):
    diff = (
        "diff --git a/src/new.txt b/src/new.txt\n"
        "--- /dev/null\n"
        "+++ b/src/new.txt\n"
        "@@ -0,0 +1 @@\n"
        "+REQUIRED\n"
    )

    result = _run_explicit(tmp_path, diff)

    assert result.returncode == 0
    assert json.loads(result.stdout)["summary"]["violations"] == 0


def test_explicit_modified_diff_is_advisory_never_a_blocking_violation(tmp_path):
    """TASK-65 / ADR-009: an unactionable finding must not block.

    `diff` mode has no post-image for a MODIFIED file, so the rule cannot be
    evaluated. That is a fact about the invocation, not about the author's
    code -- no edit to the diff can clear it -- so it is reported as an
    advisory that names the remedy, and the exit code stays 0.
    """
    target = tmp_path / "src" / "existing.txt"
    target.parent.mkdir()
    target.write_text("REQUIRED\nunstaged working tree data\n", encoding="utf-8")

    result = _run_explicit(tmp_path, MODIFIED_DIFF)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["summary"] == {
        "adrs_checked": 1,
        "violations": 0,
        "advisories": 1,
    }
    finding = payload["findings"][0]
    assert finding["severity"] == "advisory"
    assert finding["path"] == "src/existing.txt"
    # The message must point at the one thing the reader can actually do.
    assert "--snapshot staged or --snapshot worktree" in finding["message"]


def test_worktree_snapshot_evaluates_the_real_post_image(tmp_path):
    """`worktree` reads the checked-out file, so the verdict is about content."""
    target = tmp_path / "src" / "existing.txt"
    target.parent.mkdir()
    target.write_text("REQUIRED\nworking tree data\n", encoding="utf-8")

    result = _run_explicit(tmp_path, MODIFIED_DIFF, snapshot="worktree")

    assert result.returncode == 0
    assert json.loads(result.stdout)["summary"]["violations"] == 0


def test_worktree_snapshot_still_blocks_when_the_marker_is_absent(tmp_path):
    """The same mode blocks on a real breach: the downgrade is not a bypass."""
    target = tmp_path / "src" / "existing.txt"
    target.parent.mkdir()
    target.write_text("nothing required here\n", encoding="utf-8")

    result = _run_explicit(tmp_path, MODIFIED_DIFF, snapshot="worktree")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["summary"]["violations"] == 1
    assert payload["findings"][0]["severity"] == "violation"


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not on PATH")
def test_staged_snapshot_reads_the_index_and_is_unchanged_by_the_downgrade(tmp_path):
    """The pre-commit path (`--snapshot staged`) behaves exactly as before.

    core.autocrlf is pinned off so the `^REQUIRED$` anchor sees LF endings on
    Windows too; a CRLF blob would defeat the MULTILINE `$` and make this test
    lie about the mode rather than about the content.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "core.autocrlf", "false"], check=True
    )
    target = tmp_path / "src" / "existing.txt"
    target.parent.mkdir()

    target.write_text("REQUIRED\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "src/existing.txt"], check=True)
    # The worktree is then dirtied: only the INDEX content may decide.
    target.write_text("marker deleted after staging\n", encoding="utf-8", newline="\n")

    passing = _run_explicit(tmp_path, MODIFIED_DIFF, snapshot="staged")
    assert passing.returncode == 0
    assert json.loads(passing.stdout)["summary"] == {
        "adrs_checked": 1,
        "violations": 0,
        "advisories": 0,
    }

    subprocess.run(["git", "-C", str(tmp_path), "add", "src/existing.txt"], check=True)
    failing = _run_explicit(tmp_path, MODIFIED_DIFF, snapshot="staged")
    assert failing.returncode == 1
    assert json.loads(failing.stdout)["findings"][0]["severity"] == "violation"


def test_deleted_file_still_fails_closed_as_a_violation(tmp_path):
    """`missing` is actionable -- the author deleted the file -- so it blocks."""
    diff = (
        "diff --git a/src/existing.txt b/src/existing.txt\n"
        "--- a/src/existing.txt\n"
        "+++ /dev/null\n"
        "@@ -1 +0,0 @@\n"
        "-REQUIRED\n"
    )

    result = _run_explicit(tmp_path, diff)

    assert result.returncode == 1
    finding = json.loads(result.stdout)["findings"][0]
    assert finding["severity"] == "violation"
    assert "absent in the selected snapshot" in finding["message"]


def test_unsafe_path_still_fails_closed_as_unknown():
    """A path-traversal refusal keeps the fail-closed `unknown` state.

    Only the "this mode cannot see a modified post-image" case was downgraded;
    a rejected path is a security decision and stays a blocking violation.
    """
    DiffFile = JUDGE_NS["DiffFile"]
    read_snapshot_content = JUDGE_NS["read_snapshot_content"]

    escaping = DiffFile(path="../outside.txt", old_path=None, added=[], is_new=False)
    assert read_snapshot_content(escaping, ROOT, "diff", None) == ("unknown", None)

    modified = DiffFile(path="src/existing.txt", old_path=None, added=[], is_new=False)
    assert read_snapshot_content(modified, ROOT, "diff", None) == (
        "indeterminate",
        None,
    )


def _load_mcp_module():
    """Import bin/adr-mcp as a module (no .py extension, no side effects)."""
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader("adr_mcp_snapshot_probe", str(MCP))
    spec = importlib.util.spec_from_loader("adr_mcp_snapshot_probe", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_mcp_judge_tool_asks_for_the_worktree_post_image(tmp_path, monkeypatch):
    """TASK-65: the MCP caller has a worktree, so the tool must use it.

    An advisory is better than a fabricated violation, but the agent still
    learns nothing about its own code. `worktree` is what makes the answer
    real; `diff` was chosen for a caller that has no checkout, which is not
    the shape of an MCP client.
    """
    mcp = _load_mcp_module()
    captured: dict = {}

    def fake_run_cli(script, args, root, stdin_text=None, env_extra=None):
        captured["script"] = script
        captured["args"] = args
        captured["env_extra"] = env_extra
        return 0, "{}", ""

    monkeypatch.setattr(mcp, "run_cli", fake_run_cli)
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)

    mcp.tool_adr_judge({"diff": "diff --git a/x b/x\n"}, tmp_path, adr_dir)

    assert captured["script"] == "adr-judge"
    args = captured["args"]
    assert args[args.index("--snapshot") + 1] == "worktree"
    # Unchanged guarantees: no LLM pass, ever.
    assert "--llm" not in args
    assert captured["env_extra"] == {"ADR_KIT_NO_LLM": "1"}


def test_snapshot_cache_short_circuits_repeated_reads():
    """The per-run snapshot cache dedups by (snapshot_mode, path).

    A file targeted by several require_pattern rules, or by several ADRs, is
    fetched once per pre-commit pass instead of re-reading its snapshot per
    rule. Uses the git-free ``diff`` reconstruction path so the assertions are
    deterministic, and proves a cache hit is returned verbatim (the read is
    skipped) via a poisoned entry. Guards the hot-path optimization against
    silent regression.
    """
    DiffFile = JUDGE_NS["DiffFile"]
    read_snapshot_content = JUDGE_NS["read_snapshot_content"]

    diff_file = DiffFile(
        path="src/new.txt", old_path=None, added=[(1, "REQUIRED")], is_new=True
    )
    key = ("diff", "src/new.txt")
    cache: dict = {}

    first = read_snapshot_content(diff_file, ROOT, "diff", cache)
    assert first == ("present", "REQUIRED\n")
    # A miss populates the cache under the (snapshot_mode, path) key.
    assert cache[key] == ("present", "REQUIRED\n")

    # A hit returns the stored value verbatim, so the read is genuinely skipped.
    cache[key] = ("present", "SENTINEL-not-recomputed")
    assert read_snapshot_content(diff_file, ROOT, "diff", cache) == (
        "present",
        "SENTINEL-not-recomputed",
    )

    # No cache means no hidden global sharing: the read always runs.
    assert read_snapshot_content(diff_file, ROOT, "diff", None) == (
        "present",
        "REQUIRED\n",
    )
