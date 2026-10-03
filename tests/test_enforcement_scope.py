"""An Enforcement rule whose scope resolves to nothing can never fire (TASK-204).

The question TASK-204 asks -- is a decision implemented everywhere it says it
applies? -- is semantic in general. The deterministic part of it is narrow but
real: a rule whose `path_glob` matches no tracked file is checked against
nothing, so every gate that asks "was it violated?" answers green forever.
`adr-judge --check-scope` names those rules; `adr-audit --whole-codebase`
carries the finding as advisory. Neither changes an exit code (spec R15: a
record must stay satisfiable by editing it, never refused on arrival).

The two instances the task records are pinned below as what this check does
NOT see, so that nobody reads its silence as "implemented".
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_JUDGE = REPO_ROOT / "bin" / "adr-judge"
ADR_AUDIT = REPO_ROOT / "bin" / "adr-audit"


def _adr(num: int, status: str, enforcement: dict, decision: str = "Do the thing.") -> str:
    return (
        f"# ADR-{num:03d} Scoped Decision\n\n"
        f"## Status\n\n{status}, 2026-07-20.\n\n"
        f"## Context\n\nWhy.\n\n"
        f"## Decision\n\n{decision}\n\n"
        f"## Enforcement\n\n```json\n{json.dumps(enforcement, indent=2)}\n```\n"
    )


def _project(tmp_path: Path, adrs: dict, files: dict) -> Path:
    root = tmp_path / "proj"
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    for name, text in adrs.items():
        (adr_dir / name).write_text(text, encoding="utf-8")
    for rel, text in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
    return root


def _check_scope(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ADR_JUDGE), "--check-scope", "--json",
         "--adr-dir", str(root / "docs" / "adr"), "--repo-root", str(root)],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
        stdin=subprocess.DEVNULL,
    )


REQUIRE_CLASSIC = {
    "require_pattern": [
        {"pattern": "platformMuteUart0Console", "path_glob": "src/esp32classic/**/*.cpp",
         "message": "The PIC path must mute the console."}
    ]
}


def test_a_glob_that_matches_no_tracked_file_is_named(tmp_path):
    root = _project(
        tmp_path,
        {"ADR-001-mute.md": _adr(1, "Accepted", REQUIRE_CLASSIC)},
        {"src/common/console.cpp": "void platformMuteUart0Console() {}\n"},
    )

    result = _check_scope(root)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["rules_checked"] == 1
    [finding] = report["findings"]
    assert finding["adr"] == "ADR-001"
    assert finding["rule"] == "require_pattern"
    assert finding["path_glob"] == "src/esp32classic/**/*.cpp"
    assert "matches no tracked file" in finding["message"]


def test_a_glob_that_resolves_is_not_reported(tmp_path):
    root = _project(
        tmp_path,
        {"ADR-001-mute.md": _adr(1, "Accepted", REQUIRE_CLASSIC)},
        {"src/esp32classic/board.cpp": "platformMuteUart0Console();\n"},
    )

    report = json.loads(_check_scope(root).stdout)

    assert report["findings"] == []
    assert report["rules_checked"] == 1


def test_only_accepted_records_are_checked(tmp_path):
    root = _project(
        tmp_path,
        {"ADR-001-mute.md": _adr(1, "Proposed", REQUIRE_CLASSIC)},
        {"src/common/console.cpp": "x\n"},
    )

    report = json.loads(_check_scope(root).stdout)

    assert report["findings"] == []
    assert report["rules_checked"] == 0


def test_the_whole_codebase_audit_carries_the_finding_as_advisory(tmp_path):
    root = _project(
        tmp_path,
        {"ADR-001-mute.md": _adr(1, "Accepted", REQUIRE_CLASSIC)},
        {"src/common/console.cpp": "void platformMuteUart0Console() {}\n"},
    )

    result = subprocess.run(
        [sys.executable, str(ADR_AUDIT), "--whole-codebase", "--format", "json",
         "--adr-dir", str(root / "docs" / "adr"), "--repo-root", str(root)],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
        stdin=subprocess.DEVNULL,
    )

    report = json.loads(result.stdout)
    scope = report["scope"]
    assert [f["adr"] for f in scope["findings"]] == ["ADR-001"]
    # Advisory: the scope finding alone does not move the exit code.
    assert result.returncode in (0, 3), result.stderr


# ---------------------------------------------------------------------------
# The two recorded instances, pinned as what the deterministic check cannot see
# ---------------------------------------------------------------------------

def test_a_call_behind_a_guard_that_excludes_the_target_is_out_of_reach(tmp_path):
    """OTGW-firmware ADR-168: the mitigation was compiled out on esp32-classic.

    Both call sites sat inside `#if HAS_RUNTIME_HW_DETECT`, which is 1 only on
    the combo board. The symbol exists, the file is in scope, the pattern
    matches: everything a text check can ask is true, and the decision still
    does not run on the target it names. Seeing that needs the preprocessor
    per target, which is a build question, so it goes to the review checklist.
    """
    rule = {
        "require_pattern": [
            {"pattern": "platformMuteUart0Console", "path_glob": "src/**/*.cpp"}
        ]
    }
    root = _project(
        tmp_path,
        {"ADR-168-mute.md": _adr(168, "Accepted", rule)},
        {"src/common/console.cpp": (
            "#if HAS_RUNTIME_HW_DETECT\n"
            "  platformMuteUart0Console();\n"
            "#endif\n"
        )},
    )

    report = json.loads(_check_scope(root).stdout)

    assert report["findings"] == []
    assert "not proof" in report["limits"]


def test_an_enumeration_implemented_in_part_is_out_of_reach(tmp_path):
    """adr-kit ADR-041: five eligibility conditions in prose, one in code.

    The decision listed five reasons a record is queue-eligible; the code
    tested one. No Enforcement rule names the other four, so there is no
    scope to resolve and nothing deterministic to compare the prose with.
    """
    root = _project(
        tmp_path,
        {"ADR-041-queue.md": _adr(
            41, "Accepted", {"llm_judge": False},
            decision=(
                "Eligible: unresolved human input, ready-for-confirmation, an "
                "active implementation link, shipped evidence while Proposed, "
                "or a quality score below 0.70."
            ),
        )},
        {"bin/queue.py": "eligible = bool(item.get('open_questions'))\n"},
    )

    report = json.loads(_check_scope(root).stdout)

    assert report["findings"] == []
    assert report["rules_checked"] == 0
