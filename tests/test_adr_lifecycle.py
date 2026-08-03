"""Tests for bin/adr lifecycle commands."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent

# `ADR-*.md` also matches ADR-INDEX.md, which every lifecycle command writes in
# the same transaction as the record. `glob` yields filesystem order, not sorted
# order, so `next(glob("ADR-*.md"))` returned the record on Windows and the
# generated index on Linux -- a test that passed locally and failed in CI while
# the code it guards was fine. Anchor on the digits and there is only one match.
ADR_RECORD_GLOB = "ADR-[0-9]*.md"

ADR = REPO_ROOT / "bin" / "adr"
ADR_INDEX = REPO_ROOT / "bin" / "adr-index"
ADR_SCHEMA = REPO_ROOT / "bin" / "adr_schema.py"


def _created_adr(adr_dir: Path) -> Path:
    """The one numbered ADR a `bin/adr new` fixture just created."""
    records = sorted(adr_dir.glob(ADR_RECORD_GLOB))
    assert len(records) == 1, f"expected exactly one ADR, found {[p.name for p in records]}"
    return records[0]


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
    # The blocker itself, not only the count of blockers.
    assert "completeness:" in result.stderr
    assert path.read_bytes() == before


def _history_entries(body: str):
    """Return the status_history entries of an ADR body, in file order."""
    entries = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("- date:"):
            entries.append({"date": stripped.split(":", 1)[1].strip()})
        elif entries and ":" in stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition(":")
            if key in {"status", "changed_by", "reason", "changed_via"}:
                entries[-1][key] = value.strip()
    return entries


def _set_status(path: Path, frontmatter_date: str, status_line: str) -> None:
    """Rewrite a fixture into the pre-status_history shape TASK-68 describes."""
    text = path.read_text(encoding="utf-8")
    text = text.replace('date: "2026-07-01"', f'date: "{frontmatter_date}"')
    text = re.sub(
        r"(## Status\n\n)[^\n]*", rf"\g<1>{status_line}", text, count=1
    )
    path.write_text(text, encoding="utf-8")


def test_supersede_preserves_the_acceptance_date_of_a_pre_history_adr(tmp_path):
    """TASK-68: the only record of the acceptance must survive the supersession."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    old_path = _write_adr(adr_dir, 1, "Old Decision", status="Accepted")
    _write_adr(adr_dir, 2, "New Decision", status="Accepted")
    _set_status(old_path, "2026-05-31", "Accepted, 2026-05-31.")
    assert "status_history" not in old_path.read_text(encoding="utf-8")

    result = _run_adr(
        "supersede", "1", "--by", "2", "--adr-dir", str(adr_dir),
        "--date", "2026-07-06", "--changed-by", "Codex",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    _data, body = _frontmatter(old_path)
    assert "2026-05-31" in body
    entries = _history_entries(body)
    assert [(e["date"], e["status"]) for e in entries] == [
        ("2026-05-31", "Accepted"),
        ("2026-07-06", "Superseded"),
    ]
    # The actor was never recorded; recovering the date must not invent one.
    assert entries[0]["changed_by"] == "unknown"
    assert entries[0]["changed_via"] == "unrecorded"
    assert entries[1]["changed_by"] == "Codex"


def test_supersede_leaves_an_existing_status_history_block_alone(tmp_path):
    """ADRs that already carry a history block keep their previous behaviour."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    old_path = _write_adr(adr_dir, 1, "Old Decision", status="Accepted")
    _write_adr(adr_dir, 2, "New Decision", status="Accepted")
    existing = (
        "## Status History\n\n"
        "```yaml\n"
        "status_history:\n"
        "  - date: 2026-05-31\n"
        "    status: Accepted\n"
        "    changed_by: Ford Prefect\n"
        "    reason: Original acceptance\n"
        "    changed_via: adr-kit lifecycle\n"
        "```\n\n"
    )
    old_path.write_text(
        old_path.read_text(encoding="utf-8").replace(
            "## Context\n", existing + "## Context\n", 1
        ),
        encoding="utf-8",
    )

    result = _run_adr(
        "supersede", "1", "--by", "2", "--adr-dir", str(adr_dir),
        "--date", "2026-07-06", "--changed-by", "Codex",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    _data, body = _frontmatter(old_path)
    entries = _history_entries(body)
    assert [(e["date"], e["status"], e["changed_by"]) for e in entries] == [
        ("2026-05-31", "Accepted", "Ford Prefect"),
        ("2026-07-06", "Superseded", "Codex"),
    ]
    assert "changed_by: unknown" not in body


@pytest.mark.parametrize(
    ("command", "expected"),
    [("propose", "Proposed"), ("accept", "Accepted"), ("reject", "Rejected")],
)
def test_status_commands_seed_a_missing_history_with_the_prior_transition(
    tmp_path, command, expected
):
    """TASK-68 #6: mutate_status drives accept/reject/propose through the same pair."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(adr_dir, 1, "Lifecycle Command")
    _set_status(path, "2026-06-12", "Proposed, 2026-06-12.")

    result = _run_adr(
        command, "1", "--adr-dir", str(adr_dir), "--date", "2026-07-06",
        "--changed-by", "Codex",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    _data, body = _frontmatter(path)
    entries = _history_entries(body)
    assert [(e["date"], e["status"]) for e in entries] == [
        ("2026-06-12", "Proposed"),
        ("2026-07-06", expected),
    ]
    assert entries[0]["changed_by"] == "unknown"


def test_document_seeds_a_missing_history_before_appending(tmp_path):
    """The third append_status_history caller creates a block too."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(adr_dir, 1, "Shipped Decision", status="Accepted")
    _set_status(path, "2026-06-12", "Accepted, 2026-06-12.")
    pointer = adr_dir / "evidence.txt"
    pointer.write_text("shipped", encoding="utf-8")

    result = _run_adr(
        "document", "1", "--adr-dir", str(adr_dir), "--verified-in", str(pointer),
        "--date", "2026-07-06", "--changed-by", "Codex",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    _data, body = _frontmatter(path)
    entries = _history_entries(body)
    assert [(e["date"], e["changed_by"]) for e in entries] == [
        ("2026-06-12", "unknown"),
        ("2026-07-06", "Codex"),
    ]


def test_same_day_transition_is_not_duplicated_as_a_recovered_entry(tmp_path):
    """Nothing earlier exists to preserve when the transition is the same one."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    path = _write_adr(adr_dir, 1, "Lifecycle Command")

    result = _run_adr(
        "propose", "1", "--adr-dir", str(adr_dir), "--date", "2026-07-01",
        "--changed-by", "Codex",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    _data, body = _frontmatter(path)
    assert [(e["date"], e["status"]) for e in _history_entries(body)] == [
        ("2026-07-01", "Proposed")
    ]
    assert "changed_by: unknown" not in body


def test_supersede_refuses_when_the_prior_transition_cannot_be_recovered(tmp_path):
    """TASK-68 #3: refuse rather than write a history that omits the earlier entry."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    old_path = _write_adr(adr_dir, 1, "Old Decision", status="Accepted")
    _write_adr(adr_dir, 2, "New Decision", status="Accepted")
    old_path.write_text(
        old_path.read_text(encoding="utf-8")
        .replace('date: "2026-07-01"', "date: null")
        .replace("Accepted, 2026-07-01.", "Accepted (see the mailing list thread)."),
        encoding="utf-8",
    )
    before = old_path.read_bytes()

    result = _run_adr(
        "supersede", "1", "--by", "2", "--adr-dir", str(adr_dir),
        "--date", "2026-07-06",
    )

    assert result.returncode == 2
    assert "cannot be recovered" in result.stderr
    assert "no date" in result.stderr
    assert old_path.read_bytes() == before


def test_accept_resolves_a_supersedes_target_from_the_adr_directory(tmp_path):
    """TASK-67 #1: a successor already linked to its target must be acceptable."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    old_path = _write_adr(adr_dir, 1, "Old Decision", status="Accepted")
    new_path = _write_adr(adr_dir, 2, "New Decision")

    linked = _run_adr(
        "supersede", "1", "--by", "2", "--adr-dir", str(adr_dir),
        "--date", "2026-07-06", "--changed-by", "Codex",
    )
    assert linked.returncode == 0, linked.stderr + linked.stdout
    new_data, _body = _frontmatter(new_path)
    assert new_data["supersedes"] == ["ADR-001"]

    result = _run_adr(
        "accept", "2", "--adr-dir", str(adr_dir), "--date", "2026-07-07",
        "--changed-by", "Codex",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert _frontmatter(new_path)[0]["status"] == "Accepted"
    assert _frontmatter(old_path)[0]["superseded_by"] == "ADR-002"


def test_acceptance_is_not_blocked_by_an_unrelated_broken_adr(tmp_path):
    """TASK-67 #2: the wider lookup is context, not a wider verdict."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    _write_adr(adr_dir, 1, "Old Decision", status="Accepted")
    new_path = _write_adr(adr_dir, 2, "New Decision")
    broken = _write_adr(adr_dir, 3, "Broken Decision", status="Accepted")
    # Frontmatter says Accepted, the body says something else: a consistency
    # FAIL that belongs to ADR-003 alone.
    _set_status(broken, "2026-07-01", "Proposed, 2026-07-01.")

    linked = _run_adr(
        "supersede", "1", "--by", "2", "--adr-dir", str(adr_dir),
        "--date", "2026-07-06", "--changed-by", "Codex",
    )
    assert linked.returncode == 0, linked.stderr + linked.stdout

    result = _run_adr(
        "accept", "2", "--adr-dir", str(adr_dir), "--date", "2026-07-07",
        "--changed-by", "Codex",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert _frontmatter(new_path)[0]["status"] == "Accepted"


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



# ===========================================================================
# TASK-70: status_history blocks must be valid YAML, not just mini-parser food
# ===========================================================================
#
# history_entry() used to emit every field as a bare plain scalar. A value
# containing ": " ends the scalar and re-reads as a nested mapping, which takes
# the WHOLE block down -- not just that line. Three ADRs in docs/adr were
# written that way (007, 008, 009), each through a `reason` holding free text
# such as "Human approval: records the ...", and the documented
# `--changed-by "User: <name>"` produces the same shape.
#
# It survived because adr-kit reads these blocks with its own line-oriented
# mini-parser, which takes everything after the first colon as the value. The
# project's lint reported 17/17 PASS with three unparseable blocks on disk, so
# these tests deliberately use a REAL YAML parser -- asserting with the
# mini-parser would reproduce exactly the blind spot that hid the defect.

HOSTILE_HISTORY_VALUES = [
    # (status, changed_by, reason, changed_via)
    ("Accepted", "User: Robert van den Breemen", "Human approval: records it", "adr-kit lifecycle"),
    ("Superseded", "unknown", "Amended by ADR-014: advance the gate", "unrecorded"),
    ("Proposed", "- leading dash", "trailing colon:", "has # hash"),
    ("Rejected", '"quoted"', r'back\slash and "quotes"', "*anchor"),
    ("Accepted", "  padded  ", "", "@at-sign"),
]


def test_history_entry_round_trips_through_a_real_yaml_parser():
    """Every hostile scalar shape survives write -> parse unchanged."""
    yaml = pytest.importorskip(
        "yaml",
        reason="PyYAML absent; a silent pass here is what let TASK-70 survive",
    )
    adr = _load_lifecycle_module()

    block = "status_history:\n" + "".join(
        adr.history_entry(status, changed_by, reason, changed_via, "2026-07-31")
        for status, changed_by, reason, changed_via in HOSTILE_HISTORY_VALUES
    )
    parsed = yaml.safe_load(block)["status_history"]

    assert len(parsed) == len(HOSTILE_HISTORY_VALUES)
    for entry, (status, changed_by, reason, changed_via) in zip(
        parsed, HOSTILE_HISTORY_VALUES
    ):
        assert entry["status"] == status
        assert entry["changed_by"] == changed_by
        assert entry["reason"] == reason
        assert entry["changed_via"] == changed_via


def test_every_status_history_block_in_the_repo_parses():
    """Directory-wide guard: a future regression fails here, not downstream.

    The three ADRs this caught were only found by reaching for a real parser.
    Without this test the next one is found by whoever consumes the ADRs from
    outside adr-kit, which is far too late.
    """
    yaml = pytest.importorskip(
        "yaml",
        reason="PyYAML absent; a silent pass here is what let TASK-70 survive",
    )
    adr_dir = Path(__file__).resolve().parent.parent / "docs" / "adr"
    failures = []
    checked = 0
    for path in sorted(adr_dir.glob("ADR-*.md")):
        match = re.search(r"```yaml\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
        if not match:
            continue
        checked += 1
        try:
            yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            failures.append(f"{path.name}: {str(exc).splitlines()[0]}")

    assert checked > 0, "no status_history blocks found; the glob or fence changed"
    assert not failures, "unparseable status_history blocks:\n  " + "\n  ".join(failures)


def test_adr_new_quotes_an_actor_containing_a_colon(tmp_path):
    """`User: <name>` is the actor shape spec.md R8 prescribes, and a raw colon
    turns the status_history block into unparseable YAML.

    accept and supersede route their actor through _yaml_scalar; creation did
    not, and substituted the template placeholder verbatim. The block then
    parsed for adr-kit's own mini-parser and failed for real YAML - the same
    class of defect that corrupted three shipped ADRs before.
    """
    import subprocess
    import sys

    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    result = subprocess.run(
        [
            sys.executable, str(REPO_ROOT / "bin" / "adr"), "new", "A Decision With A Signer",
            "--adr-dir", str(adr_dir),
            "--changed-by", "User: Robert van den Breemen",
        ],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stderr

    text = _created_adr(adr_dir).read_text(encoding="utf-8")
    block = re.search(r"```yaml\n(status_history:.*?)\n```", text, re.DOTALL)
    assert block, "no status_history block was written"

    # Assert the quoted shape without a parser first, so this guards the
    # regression on every run. The sibling test above reaches for PyYAML and is
    # therefore skipped wherever PyYAML is absent -- which is every CI runner
    # here, because ADR-016 makes zero runtime dependencies load-bearing and the
    # workflow installs pytest and nothing else. A check that only runs on the
    # one machine that happens to have the library is not a check.
    assert 'changed_by: "User: Robert van den Breemen"' in block.group(1), (
        "the actor was substituted unquoted; a raw colon makes the block "
        "unparseable to every YAML reader outside adr-kit's own mini-parser"
    )

    # Then, where a real parser exists, prove it actually parses.
    yaml = pytest.importorskip(
        "yaml", reason="PyYAML absent; the structural assertion above still ran"
    )
    parsed = yaml.safe_load(block.group(1))
    assert parsed["status_history"][0]["changed_by"] == "User: Robert van den Breemen"


def test_lifecycle_refuses_to_sign_on_the_users_behalf(tmp_path):
    """No configured signer and no flag means refuse, not sign as 'adr-kit'."""
    import subprocess
    import sys

    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr"), "new", "An Unsigned Decision",
         "--adr-dir", str(adr_dir)],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )

    assert result.returncode != 0
    assert "no signer configured" in result.stderr
    assert not list(adr_dir.glob(ADR_RECORD_GLOB)), "nothing may be written on refusal"


def test_configured_signer_is_used_when_no_flag_is_given(tmp_path):
    """The machine-local config supplies the actor; the flag stays optional."""
    import json as _json
    import subprocess
    import sys

    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / ".adr-kit.local.json").write_text(
        _json.dumps({"lifecycle": {"signer": "User: Configured Human"}}), encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr"), "new", "A Signed Decision",
         "--adr-dir", str(adr_dir)],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )

    assert result.returncode == 0, result.stderr
    created = _created_adr(adr_dir)
    assert 'changed_by: "User: Configured Human"' in created.read_text(encoding="utf-8")


def test_an_illegal_transition_reports_illegality_not_a_missing_signer(tmp_path):
    """Validate the act before the actor: the error must name the real problem."""
    import subprocess
    import sys

    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr"), "new", "A Decision",
         "--adr-dir", str(adr_dir), "--changed-by", "User: Test Signer"],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr"), "accept", "ADR-001",
         "--adr-dir", str(adr_dir), "--changed-by", "User: Test Signer"],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    # Accepted -> Proposed is illegal, and this call also has no signer.
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "adr"), "propose", "ADR-001",
         "--adr-dir", str(adr_dir)],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )

    assert result.returncode == 2
    assert "illegal lifecycle transition" in result.stderr, (
        "the signer check must not preempt the legality check; an illegal "
        "transition has to report that it is illegal"
    )
