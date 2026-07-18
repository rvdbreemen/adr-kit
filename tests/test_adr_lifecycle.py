"""Tests for bin/adr lifecycle commands."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ADR = REPO_ROOT / "bin" / "adr"
ADR_INDEX = REPO_ROOT / "bin" / "adr-index"
ADR_SCHEMA = REPO_ROOT / "bin" / "adr_schema.py"


def _load_schema_module():
    spec = importlib.util.spec_from_file_location("adr_schema", ADR_SCHEMA)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SCHEMA = _load_schema_module()


def _load_lifecycle_module():
    import importlib.machinery

    loader = importlib.machinery.SourceFileLoader("adr_lifecycle", str(ADR))
    spec = importlib.util.spec_from_loader("adr_lifecycle", loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["adr_lifecycle"] = mod
    loader.exec_module(mod)
    return mod


def _body(num: int, title: str, status: str = "Proposed") -> str:
    return textwrap.dedent(
        f"""\
        # ADR-{num:03d} {title}

        ## Status

        {status}, 2026-07-01.

        ## Context

        Lifecycle commands should keep ADR state coherent.

        ## Decision

        Mutate lifecycle metadata with local deterministic commands.

        ## Alternatives Considered

        - Manual edits: rejected because they drift.
        - Hosted workflow: rejected because adr-kit must remain local.

        ## Consequences

        **Positive:**
        - Agents can perform safe lifecycle edits.

        **Negative:**
        - The command must preserve append-only history.

        ## Related Decisions

        - None.

        ## References

        - tests/test_adr_lifecycle.py
        """
    )


def _write_adr(adr_dir: Path, num: int, title: str, status: str = "Proposed") -> Path:
    data = {
        "id": f"ADR-{num:03d}",
        "title": title,
        "status": status,
        "date": "2026-07-01",
        "binding": False,
        "gate": None,
        "documents_shipped": False,
        "verified_in": [],
        "supersedes": [],
        "superseded_by": None,
    }
    path = adr_dir / f"ADR-{num:03d}-{title.lower().replace(' ', '-')}.md"
    path.write_text(SCHEMA.render_frontmatter(data) + _body(num, title, status), encoding="utf-8")
    return path


def _frontmatter(path: Path):
    raw, body = SCHEMA.split_frontmatter(path.read_text(encoding="utf-8"))
    return SCHEMA.parse_frontmatter(raw), body


def _run_adr(*args: str):
    return subprocess.run(
        [sys.executable, str(ADR), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _index_check(adr_dir: Path):
    return subprocess.run(
        [sys.executable, str(ADR_INDEX), "--check", str(adr_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("command", "expected"),
    [("propose", "Proposed"), ("accept", "Accepted"), ("reject", "Rejected")],
)
def test_status_commands_update_frontmatter_history_and_index(tmp_path, command, expected):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(adr_dir, 1, "Lifecycle Command")

    result = _run_adr(
        command,
        "1",
        "--adr-dir",
        str(adr_dir),
        "--date",
        "2026-07-06",
        "--changed-by",
        "Codex",
        "--reason",
        f"{expected} in test",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    data, body = _frontmatter(path)
    assert data["status"] == expected
    assert data["date"] == "2026-07-06"
    assert f"{expected}, 2026-07-06." in body
    assert f"status: {expected}" in body
    assert "changed_by: Codex" in body
    assert _index_check(adr_dir).returncode == 0


def test_supersede_updates_both_files_reciprocally_and_refreshes_index(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    old_path = _write_adr(adr_dir, 160, "Old Decision", status="Accepted")
    new_path = _write_adr(adr_dir, 164, "New Decision", status="Accepted")

    result = _run_adr(
        "supersede",
        "160",
        "--by",
        "164",
        "--adr-dir",
        str(adr_dir),
        "--date",
        "2026-07-06",
        "--changed-by",
        "Codex",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    old_data, old_body = _frontmatter(old_path)
    new_data, new_body = _frontmatter(new_path)
    assert old_data["status"] == "Superseded"
    assert old_data["superseded_by"] == "ADR-164"
    assert "Superseded by ADR-164, 2026-07-06." in old_body
    assert "status: Superseded" in old_body
    assert "ADR-160" in new_data["supersedes"]
    assert "Supersedes ADR-160" in new_body
    check = _index_check(adr_dir)
    assert check.returncode == 0, check.stderr + check.stdout
    readme = (adr_dir / "README.md").read_text(encoding="utf-8")
    assert "Superseded by ADR-164" in readme
    assert "Supersedes ADR-160" in readme


@pytest.mark.parametrize("command", ["propose", "reject"])
def test_accepted_adr_rejects_illegal_transitions_without_mutation(tmp_path, command):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(adr_dir, 1, "Binding Decision", status="Accepted")
    before = path.read_bytes()

    result = _run_adr(command, "1", "--adr-dir", str(adr_dir))

    assert result.returncode == 2
    assert "illegal lifecycle transition" in result.stderr
    assert path.read_bytes() == before


def test_acceptance_gates_block_incomplete_record_without_mutation(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(adr_dir, 1, "Incomplete Candidate")
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "## Alternatives Considered\n\n"
            "- Manual edits: rejected because they drift.\n"
            "- Hosted workflow: rejected because adr-kit must remain local.\n\n",
            "",
        ),
        encoding="utf-8",
    )
    before = path.read_bytes()

    result = _run_adr("accept", "1", "--adr-dir", str(adr_dir))

    assert result.returncode == 2
    assert "acceptance blocked" in result.stderr
    assert path.read_bytes() == before


def test_two_file_write_failure_rolls_back_first_replacement(tmp_path, monkeypatch):
    lifecycle = _load_lifecycle_module()
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("first-original", encoding="utf-8")
    second.write_text("second-original", encoding="utf-8")
    real_atomic_write = lifecycle._atomic_write_text
    calls = 0

    def fail_second_write(path, text):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected second-write failure")
        real_atomic_write(path, text)

    monkeypatch.setattr(lifecycle, "_atomic_write_text", fail_second_write)

    with pytest.raises(lifecycle.AdrLifecycleError, match="rolled back"):
        lifecycle._write_transaction(
            [(first, "first-new"), (second, "second-new")]
        )

    assert first.read_text(encoding="utf-8") == "first-original"
    assert second.read_text(encoding="utf-8") == "second-original"
    assert not list(tmp_path.glob(".*.tmp"))


def test_index_failure_rolls_back_both_supersession_records_and_indexes(
    tmp_path,
    monkeypatch,
):
    lifecycle = _load_lifecycle_module()
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    old_path = _write_adr(adr_dir, 1, "Old Binding", status="Accepted")
    new_path = _write_adr(adr_dir, 2, "New Binding", status="Accepted")
    readme = adr_dir / "README.md"
    readme.write_text("original readme", encoding="utf-8")
    before = {
        old_path: old_path.read_bytes(),
        new_path: new_path.read_bytes(),
        readme: readme.read_bytes(),
    }

    def fail_after_partial_index(target):
        (target / "README.md").write_text("partial index", encoding="utf-8")
        (target / "ADR-INDEX.md").write_text("partial index", encoding="utf-8")
        raise lifecycle.AdrLifecycleError("injected index failure")

    monkeypatch.setattr(lifecycle, "run_index", fail_after_partial_index)
    args = SimpleNamespace(
        adr_dir=str(adr_dir),
        old="1",
        by="2",
        date="2026-07-18",
        changed_by="test",
        reason=None,
    )

    with pytest.raises(lifecycle.AdrLifecycleError, match="rolled back"):
        lifecycle.command_supersede(args)

    assert {path: path.read_bytes() for path in before} == before
    assert not (adr_dir / "ADR-INDEX.md").exists()
    assert not (adr_dir / "ADR-INDEX.json").exists()

