"""Git path decoding and explicit-diff snapshot behavior."""

from __future__ import annotations

import json
import runpy
import subprocess
import sys
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
JUDGE = ROOT / "bin" / "adr-judge"
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


def _run_explicit(tmp_path: Path, diff: str) -> subprocess.CompletedProcess:
    adr_dir = tmp_path / "docs" / "adr"
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
            "diff",
            "--json",
        ],
        input=diff,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
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


def test_explicit_modified_diff_fails_closed_when_post_image_is_incomplete(
    tmp_path,
):
    target = tmp_path / "src" / "existing.txt"
    target.parent.mkdir()
    target.write_text("REQUIRED\nunstaged working tree data\n", encoding="utf-8")
    diff = (
        "diff --git a/src/existing.txt b/src/existing.txt\n"
        "--- a/src/existing.txt\n"
        "+++ b/src/existing.txt\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )

    result = _run_explicit(tmp_path, diff)

    assert result.returncode == 1
    finding = json.loads(result.stdout)["findings"][0]
    assert "does not contain a complete post-image" in finding["message"]
    assert "failed closed" in finding["message"]
