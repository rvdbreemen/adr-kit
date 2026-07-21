from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
HOOKS = ROOT / "hooks"
sys.path.insert(0, str(BIN))
sys.path.insert(0, str(HOOKS))

from adr_grill_signal import analyze_index  # noqa: E402
from adr_hook_core import evaluate, parse_payload  # noqa: E402


def _index(status: str = "Proposed") -> dict:
    return {
        "schema_version": 1,
        "adrs": [
            {
                "id": "ADR-007",
                "title": "Storage boundary",
                "path": "ADR-007-storage.md",
                "status": status,
                "decision_summary": "Use the storage service boundary.",
                "scope": {"path_globs": ["src/storage/**"]},
                "metadata": {"verified_in": ["src/storage/service.py"]},
            }
        ],
    }


def test_index_signal_distinguishes_linked_proposed_suspected_and_no_signal():
    linked = analyze_index(
        _index(), ["src/storage/service.py"], "implements ADR-007"
    )
    assert linked["linked_proposed"][0]["adr_id"] == "ADR-007"
    assert linked["linked_proposed"][0]["command"] == "/adr-kit:grill ADR-007"
    assert linked["suspected_decisions"] == []

    suspected = analyze_index(_index(), ["infra/main.tf"], "")
    assert suspected["linked_proposed"] == []
    assert suspected["suspected_decisions"][0]["command"] == (
        "/adr-kit:grill --source infra/main.tf"
    )

    assert analyze_index(_index(), ["src/ui/button.py"], "")["signal_count"] == 0
    accepted = analyze_index(
        _index("Accepted"), ["src/storage/service.py"], "ADR-007"
    )
    assert accepted["linked_proposed"] == []


def test_signal_output_is_bounded_deduplicated_and_cross_shell_safe():
    hostile = "infra/it's config.yml\n::error::"
    posix = analyze_index(_index(), [hostile, hostile], "", shell="posix")
    powershell = analyze_index(_index(), [hostile], "", shell="powershell")
    assert posix["signal_count"] <= 3
    serialized = json.dumps(posix)
    assert "::error::" not in serialized
    assert "\n" not in posix["suspected_decisions"][0]["command"]
    assert "''" in powershell["suspected_decisions"][0]["command"]


def test_edit_hook_emits_client_native_link_without_starting_interaction(tmp_path):
    project = tmp_path / "repo"
    adr_dir = project / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-INDEX.json").write_text(json.dumps(_index()), encoding="utf-8")
    envelope = parse_payload(
        json.dumps(
            {
                "cwd": str(project),
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": "src/storage/service.py"},
            }
        ).encode(),
        "codex-cli",
    )
    assert envelope is not None
    context, kind = evaluate(envelope)
    assert kind == "post-edit"
    assert "$adr-kit:grill ADR-007" in context
    assert "invoke a model" not in context


def test_cli_errors_are_controlled_and_precommit_is_fail_open(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(BIN / "adr-grill-signal"),
            "--repo-root",
            str(tmp_path),
            "--staged",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 2
    wrapper = (ROOT / "templates" / "githooks" / "pre-commit").read_text(
        encoding="utf-8"
    )
    assert "adr-grill-signal" in wrapper
    assert "|| true" in wrapper
    assert "adr-judge above remains the only local blocking path" in wrapper
    assert "--staged" in wrapper
