"""Opt-out migration for the LLM judge (TASK-74).

The interesting property under test is memory: a bare `llm_judge: false` is a
leftover from the old default and must be re-proposed, while a `false` with a
reason is a decision somebody made and must survive every later upgrade.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATE = REPO_ROOT / "bin" / "adr-migrate"


def _load_module():
    loader = importlib.machinery.SourceFileLoader(
        "adr_llm_judge_migration", str(REPO_ROOT / "bin" / "adr_llm_judge_migration.py")
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    # Register before exec: anything that resolves a class back through
    # sys.modules[cls.__module__] (dataclasses does) sees None otherwise.
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


mig = _load_module()


def _adr(enforcement: str, status: str = "Accepted, 2026-04-25.") -> str:
    return textwrap.dedent(
        f"""\
        # ADR-001: A decision

        ## Status

        {status}

        ## Decision

        Do the thing.

        ## Alternatives Considered

        - Other: rejected.
        - This: accepted.

        ## Consequences

        **Positive:**
        - Good.

        **Negative:**
        - Costly.

        ## Related Decisions

        - None.

        ## References

        - None.

        ## Enforcement

        ```json
        {enforcement}
        ```
        """
    )


def _write(tmp_path: Path, name: str, body: str) -> Path:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    path = adr_dir / name
    path.write_text(body, encoding="utf-8")
    return path


def _block(path: Path) -> dict:
    block, error = mig.read_enforcement(path.read_text(encoding="utf-8"))
    assert error is None, error
    return block


def test_bare_false_is_legacy_and_gets_proposed(tmp_path):
    path = _write(
        tmp_path,
        "ADR-001-a.md",
        _adr('{"forbid_pattern": [{"pattern": "x", "path_glob": "src/**"}], "llm_judge": false}'),
    )
    row = mig.classify(path)
    assert row["state"] == mig.STATE_LEGACY_OFF
    assert row["proposal"] == "enable"


def test_reasoned_false_is_remembered_and_left_alone(tmp_path):
    path = _write(
        tmp_path,
        "ADR-001-a.md",
        _adr(
            '{"forbid_pattern": [{"pattern": "x", "path_glob": "src/**"}], '
            '"llm_judge": false, "llm_judge_reason": "reviewed by hand"}'
        ),
    )
    row = mig.classify(path)
    assert row["state"] == mig.STATE_OPTED_OUT

    before = path.read_text(encoding="utf-8")
    result = mig.apply(tmp_path / "docs" / "adr")
    assert result["enabled"] == []
    assert path.read_text(encoding="utf-8") == before, "a reasoned opt-out is untouched"


def test_enable_removes_the_key_rather_than_writing_true(tmp_path):
    path = _write(
        tmp_path,
        "ADR-001-a.md",
        _adr('{"forbid_pattern": [{"pattern": "x", "path_glob": "src/**"}], "llm_judge": false}'),
    )
    mig.apply(tmp_path / "docs" / "adr")
    block = _block(path)
    assert "llm_judge" not in block, "absent means the default, which is now true"
    assert block["forbid_pattern"], "the rules survive the rewrite"


def test_rule_less_block_is_marked_no_code_surface_not_enabled(tmp_path):
    path = _write(tmp_path, "ADR-001-a.md", _adr('{"llm_judge": false}'))
    result = mig.apply(tmp_path / "docs" / "adr")

    assert result["enabled"] == []
    assert result["opted_out"][0]["adr"] == "ADR-001"
    block = _block(path)
    assert block["llm_judge"] is False
    assert "no code surface" in block["llm_judge_reason"]


def test_force_enable_overrides_the_no_code_surface_proposal(tmp_path):
    path = _write(tmp_path, "ADR-001-a.md", _adr('{"llm_judge": false}'))
    result = mig.apply(tmp_path / "docs" / "adr", force_enable_ids=["ADR-001"])

    assert [r["adr"] for r in result["enabled"]] == ["ADR-001"]
    assert result["enabled"][0]["unbounded_scope"] is True, (
        "the caller must be able to see that this costs a call on every commit"
    )
    assert "llm_judge" not in _block(path)


def test_opt_out_requires_a_reason(tmp_path):
    _write(
        tmp_path,
        "ADR-001-a.md",
        _adr('{"forbid_pattern": [{"pattern": "x", "path_glob": "src/**"}], "llm_judge": false}'),
    )
    with pytest.raises(ValueError, match="reason"):
        mig.apply(tmp_path / "docs" / "adr", opt_out_ids=["ADR-001"])


def test_dry_run_writes_nothing(tmp_path):
    path = _write(
        tmp_path,
        "ADR-001-a.md",
        _adr('{"forbid_pattern": [{"pattern": "x", "path_glob": "src/**"}], "llm_judge": false}'),
    )
    before = path.read_text(encoding="utf-8")
    result = mig.apply(tmp_path / "docs" / "adr", dry_run=True)

    assert [r["adr"] for r in result["enabled"]] == ["ADR-001"]
    assert path.read_text(encoding="utf-8") == before


def test_second_run_is_a_no_op(tmp_path):
    path = _write(
        tmp_path,
        "ADR-001-a.md",
        _adr('{"forbid_pattern": [{"pattern": "x", "path_glob": "src/**"}], "llm_judge": false}'),
    )
    mig.apply(tmp_path / "docs" / "adr")
    after_first = path.read_text(encoding="utf-8")
    second = mig.apply(tmp_path / "docs" / "adr")

    assert second["enabled"] == []
    assert path.read_text(encoding="utf-8") == after_first


def test_non_accepted_adrs_are_left_alone(tmp_path):
    path = _write(
        tmp_path,
        "ADR-001-a.md",
        _adr('{"llm_judge": false}', status="Superseded by ADR-002, 2026-05-01."),
    )
    before = path.read_text(encoding="utf-8")
    result = mig.apply(tmp_path / "docs" / "adr")

    assert result["enabled"] == []
    assert path.read_text(encoding="utf-8") == before


def test_rewrite_preserves_prose_outside_the_block(tmp_path):
    body = _adr('{"forbid_pattern": [{"pattern": "x", "path_glob": "src/**"}], "llm_judge": false}')
    path = _write(tmp_path, "ADR-001-a.md", body)
    mig.apply(tmp_path / "docs" / "adr")
    after = path.read_text(encoding="utf-8")

    for section in ("## Decision", "Do the thing.", "## Consequences", "## References"):
        assert section in after
    assert after.count("```json") == 1


def test_cli_dry_run_reports_without_writing(tmp_path):
    path = _write(
        tmp_path,
        "ADR-001-a.md",
        _adr('{"forbid_pattern": [{"pattern": "x", "path_glob": "src/**"}], "llm_judge": false}'),
    )
    before = path.read_text(encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable, str(MIGRATE), str(tmp_path / "docs" / "adr"),
            "--enable-llm-judge", "--dry-run", "--format", "json",
        ],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [r["adr"] for r in payload["enabled"]] == ["ADR-001"]
    assert payload["dry_run"] is True
    assert path.read_text(encoding="utf-8") == before


def test_cli_refuses_an_opt_out_without_a_reason(tmp_path):
    _write(
        tmp_path,
        "ADR-001-a.md",
        _adr('{"forbid_pattern": [{"pattern": "x", "path_glob": "src/**"}], "llm_judge": false}'),
    )
    result = subprocess.run(
        [
            sys.executable, str(MIGRATE), str(tmp_path / "docs" / "adr"),
            "--enable-llm-judge", "--except", "ADR-001",
        ],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 2
    assert "reason" in result.stderr


def test_migrated_block_still_validates_for_the_judge(tmp_path):
    """A reasoned opt-out must not make the Enforcement block structurally invalid."""
    loader = importlib.machinery.SourceFileLoader("adr_judge_mod", str(REPO_ROOT / "bin" / "adr-judge"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    judge = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = judge  # dataclasses resolves classes through this
    loader.exec_module(judge)

    path = _write(tmp_path, "ADR-001-a.md", _adr('{"llm_judge": false}'))
    mig.apply(tmp_path / "docs" / "adr")
    block = _block(path)

    assert judge.validate_enforcement(block) == []
    assert judge.validate_enforcement({"llm_judge_reason": "x"}) != [], (
        "a reason without an explicit false is meaningless and must be flagged"
    )
