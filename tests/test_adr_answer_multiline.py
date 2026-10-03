"""`bin/adr answer` and the Open Questions parsers treat a question as an item.

An Open Question that wraps onto a second line, or carries nested bullets, is
one question. Every parser used to read one line at a time (TASK-194):

* `answer` marked only the first line, so the answer landed mid-question and
  the rest of the question trailed below it;
* `--question <text>` searched the first line only;
* each nested bullet counted as a question of its own;
* a continuation line ending in `?` counted as an unresolved question that
  `answer` could not target, so `accept` stayed blocked after every question
  had been answered.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN = REPO_ROOT / "bin"
ADR = BIN / "adr"

if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))

import adr_format  # noqa: E402


QUESTIONS = (
    "- [ ] Does the trust relationship survive the publish job being\n"
    "  invoked through `workflow_call`? npm matches against\n"
    "  the initiating workflow filename.\n"
    "- [ ] Which registry mirrors do we keep,\n"
    "  and does it need review?\n"
    "- [ ] Which fallback applies?\n"
    "  - nested option A\n"
    "  - nested option B\n"
)


def _project(tmp_path: Path, questions: str = QUESTIONS) -> Path:
    root = tmp_path / "project"
    (root / "docs" / "adr").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    (root / "docs" / "adr" / ".adr-kit.local.json").write_text(
        json.dumps({"lifecycle": {"signer": "User: Test Runner"}}), encoding="utf-8"
    )
    subprocess.run(
        [sys.executable, str(ADR), "new", "Publish through a reusable workflow",
         "--adr-dir", str(root / "docs" / "adr")],
        cwd=root, check=True, capture_output=True,
    )
    path = _path(root)
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"(## Open Questions\n\n).*?(\n## )",
        lambda m: m.group(1) + questions + m.group(2),
        text, count=1, flags=re.S,
    )
    path.write_text(text, encoding="utf-8")
    return root


def _path(root: Path) -> Path:
    return next((root / "docs" / "adr").glob("ADR-001*.md"))


def _answer(root: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(ADR), "answer", "ADR-001", *args,
         "--adr-dir", str(root / "docs" / "adr")],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def _open_questions(text: str) -> str:
    return re.search(r"## Open Questions\n\n(.*?)\n## ", text, re.S).group(1)


def test_each_wrapped_or_nested_question_counts_once(tmp_path):
    text = _path(_project(tmp_path)).read_text(encoding="utf-8")

    unresolved = adr_format.unresolved_open_questions(text)

    assert len(unresolved) == 3, unresolved
    assert any("initiating workflow filename" in q for q in unresolved)
    assert not any(q.startswith("and does it need review") for q in unresolved)
    assert not any(q.startswith("nested option") for q in unresolved)


def test_the_answer_lands_after_the_whole_question(tmp_path):
    root = _project(tmp_path)

    result = _answer(root, "--question", "1", "--answer", "ANS-ONE.")

    assert result.returncode == 0, result.stderr
    section = _open_questions(_path(root).read_text(encoding="utf-8"))
    assert section.startswith(
        "- [x] Does the trust relationship survive the publish job being\n"
        "  invoked through `workflow_call`? npm matches against\n"
        "  the initiating workflow filename.\n"
        "  — **Answered "
    ), section
    assert "ANS-ONE." in section


def test_a_single_line_question_keeps_the_one_line_form(tmp_path):
    root = _project(tmp_path, "- [ ] Who owns the dead-letter policy?\n")

    assert _answer(root, "--answer", "Platform team.").returncode == 0

    section = _open_questions(_path(root).read_text(encoding="utf-8"))
    assert section.startswith("- [x] Who owns the dead-letter policy? — **Answered ")


def test_text_on_a_continuation_line_selects_the_question(tmp_path):
    root = _project(tmp_path)

    result = _answer(root, "--question", "workflow_call", "--answer", "Yes.")

    assert result.returncode == 0, result.stderr
    assert "- [x] Does the trust relationship" in _path(root).read_text(encoding="utf-8")


def test_answering_every_question_unblocks_acceptance(tmp_path):
    root = _project(tmp_path)

    for _ in range(3):
        assert _answer(root, "--question", "1", "--answer", "Done.").returncode == 0

    text = _path(root).read_text(encoding="utf-8")
    assert adr_format.unresolved_open_questions(text) == []
    assert _answer(root, "--answer", "again").returncode == 2
    # The nested options stay where they were, under their own question.
    assert "  - nested option A\n  - nested option B\n" in text


def test_the_confirmation_is_not_cut_mid_word(tmp_path):
    root = _project(tmp_path)

    result = _answer(root, "--question", "1", "--answer", "Yes.")

    echoed = result.stdout.splitlines()[0]
    assert echoed.startswith("answered in ")
    shown = echoed.split(": ", 1)[1]
    full = (
        "Does the trust relationship survive the publish job being invoked "
        "through `workflow_call`? npm matches against the initiating workflow "
        "filename."
    )
    if shown != full:
        assert shown.endswith(" ..."), shown
        kept = shown[: -len(" ...")]
        assert full.startswith(kept) and full[len(kept)] == " ", shown


def test_answered_and_unanswered_forms_share_one_identity(tmp_path):
    """ADR-022's append-only guard must see an answered question, not a deletion."""
    root = _project(tmp_path)
    before = adr_format.all_open_questions(_path(root).read_text(encoding="utf-8"))

    assert _answer(root, "--question", "1", "--answer", "Yes.").returncode == 0

    after = adr_format.all_open_questions(_path(root).read_text(encoding="utf-8"))
    assert set(before) == set(after)
    assert sum(after.values()) == 1
