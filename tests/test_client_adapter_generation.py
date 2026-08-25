"""Contracts for bounded, deterministic three-client adapter generation."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "client_generation.py"
SPEC = importlib.util.spec_from_file_location("client_generation", MODULE_PATH)
assert SPEC and SPEC.loader
GEN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GEN
SPEC.loader.exec_module(GEN)

# The canonical workflow set lives in the model module; assert against it
# rather than a literal, so adding a workflow is one edit and not three.
MODEL = sys.modules["client_generation_model"]


def _files(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


def _manifests() -> dict[str, object]:
    return {
        name: json.loads((ROOT / name).read_text(encoding="utf-8"))
        for name in (
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".agents/plugins/marketplace.json",
            "codex/.codex-plugin/plugin.json",
            ".github/plugin/marketplace.json",
            "copilot/plugin.json",
            ".mcp.json",
            "codex/.mcp.json",
            "copilot/.mcp.json",
        )
    }


def test_registry_and_workflows_are_exactly_three_clients():
    capabilities = json.loads((ROOT / "clients/capabilities.json").read_text())
    workflows = json.loads((ROOT / "clients/workflows.json").read_text())

    assert capabilities["program_scope"]["first_class_clients"] == list(GEN.CLIENT_IDS)
    assert list(workflows["clients"]) == list(GEN.CLIENT_IDS)
    assert len(workflows["workflows"]) == len(MODEL.WORKFLOW_IDS)
    assert [item["id"] for item in workflows["workflows"]] == sorted(
        item["id"] for item in workflows["workflows"]
    )
    raw = json.dumps((capabilities, workflows)).lower()
    for future in ("opencode", "kilocode", "kimicode", "cursor", "gemini", "qwen"):
        assert future not in raw


def test_clean_generation_is_byte_identical_and_warm_run_preserves_mtimes(tmp_path):
    output = tmp_path / "output with spaces and ünicode"
    first_stats, first_drift = GEN.generate(ROOT, output)
    first = _files(output)
    second_stats, second_drift = GEN.generate(ROOT, output)
    second = _files(output)

    assert first_drift
    assert first_stats.files_written == len(first)
    assert second_drift == []
    assert second_stats.files_written == 0
    assert first == second


def test_drift_check_detects_edit_missing_workflow_and_stale_output(tmp_path):
    output = tmp_path / "payload"
    GEN.generate(ROOT, output)
    skill = output / "codex/skills/adr/SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "hand edit\n", encoding="utf-8")
    stale = output / "copilot/skills/stale/SKILL.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale", encoding="utf-8")

    _, drift = GEN.generate(ROOT, output, check=True)

    assert "codex/skills/adr/SKILL.md" in drift
    assert "copilot/skills/stale/SKILL.md" in drift
    invalid = json.loads((ROOT / "clients/workflows.json").read_text())
    invalid["workflows"].pop()
    with pytest.raises(GEN.GenerationError, match="complete canonical"):
        GEN._validate_workflows(invalid)
    invalid["workflows"].append({"id": "adr", "description": "duplicate", "procedure": ["x"]})
    with pytest.raises(GEN.GenerationError, match="complete canonical"):
        GEN._validate_workflows(invalid)


def test_native_manifests_validate_version_provenance_and_registered_divergence():
    manifests = _manifests()
    release_version = manifests[".claude-plugin/plugin.json"]["version"]
    GEN._validate_manifests(manifests, release_version)
    stale = dict(manifests)
    stale["copilot/plugin.json"] = dict(stale["copilot/plugin.json"])
    stale["copilot/plugin.json"]["version"] = "0.0.0"
    with pytest.raises(GEN.GenerationError, match="stale version"):
        GEN._validate_manifests(stale, release_version)
    divergent = dict(manifests)
    divergent["codex/.codex-plugin/plugin.json"] = dict(
        divergent["codex/.codex-plugin/plugin.json"]
    )
    divergent["codex/.codex-plugin/plugin.json"]["hooks"] = {}
    with pytest.raises(GEN.GenerationError, match="must reference"):
        GEN._validate_manifests(divergent, release_version)


def test_native_hook_shapes_are_generated_from_the_canonical_hook_manifest():
    hooks = json.loads((ROOT / "hooks/manifest.json").read_text())
    claude = json.loads(GEN._native_hook_config(hooks, "claude-code-cli"))
    codex = json.loads(GEN._native_hook_config(hooks, "codex-cli"))
    copilot = json.loads(
        GEN._native_hook_config(hooks, "github-copilot-cli")
    )

    assert "SessionStart" in claude["hooks"]
    assert claude["hooks"]["SessionStart"][0]["hooks"][0]["command"].startswith(
        '"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd"'
    )
    assert claude["hooks"]["SessionStart"][0]["hooks"][0]["timeout"] == 5
    assert codex["hooks"]["SessionStart"][0]["hooks"][0]["timeout"] == 5
    assert copilot["hooks"]["sessionStart"][0]["timeoutSec"] == 5
    codex_handlers = [
        handler
        for entries in codex["hooks"].values()
        for entry in entries
        for handler in entry["hooks"]
    ]
    assert all("commandWindows" in handler for handler in codex_handlers)
    assert all("command_windows" not in handler for handler in codex_handlers)
    codex_pre_tool = codex["hooks"]["PreToolUse"][0]["hooks"][0]
    assert codex_pre_tool["commandWindows"].startswith(
        "cmd.exe /d /c if defined PLUGIN_ROOT if exist "
    )
    assert codex_pre_tool["commandWindows"].endswith("& exit /b 0")
    assert codex_pre_tool["timeout"] == 5
    assert claude["hooks"]["UserPromptSubmit"][0]["hooks"][0]["timeout"] == 5
    assert codex["hooks"]["UserPromptSubmit"][0]["hooks"][0]["timeout"] == 5
    assert copilot["hooks"]["userPromptSubmitted"][0]["timeoutSec"] == 5
    assert claude["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"] == 1
    assert set(copilot["hooks"]) == {
        "sessionStart",
        "userPromptSubmitted",
        "postToolUse",
    }
    assert all(
        {"bash", "powershell"} <= set(handler)
        for handlers in copilot["hooks"].values()
        for handler in handlers
    )
    invalid = json.loads(json.dumps(hooks))
    invalid["events"][0]["runner_timeout_sec"] = 0
    with pytest.raises(GEN.GenerationError, match="integer from 1 to 30"):
        GEN._native_hook_config(invalid, "codex-cli")
    invalid["events"][0]["runner_timeout_sec"] = True
    with pytest.raises(GEN.GenerationError, match="integer from 1 to 30"):
        GEN._native_hook_config(invalid, "github-copilot-cli")


def test_exceptions_have_rationale_effect_and_real_fixtures():
    registry = json.loads((ROOT / "clients/exceptions.json").read_text())
    capabilities = json.loads((ROOT / "clients/capabilities.json").read_text())
    GEN._validate_capabilities(capabilities, registry)
    for exception in registry["exceptions"]:
        assert exception["rationale"]
        assert exception["user_effect"]
        fixture = ROOT / exception["fixture"]
        assert fixture.is_file()
        assert json.loads(fixture.read_text())["exception_id"] == exception["id"]


def test_generated_skills_prompts_guides_and_hooks_have_stable_provenance():
    workflows = json.loads((ROOT / "clients/workflows.json").read_text())
    ids = {item["id"] for item in workflows["workflows"]}
    for client, skill_root in (
        ("codex-cli", ROOT / "codex/skills"),
        ("github-copilot-cli", ROOT / "copilot/skills"),
    ):
        assert {path.parent.name for path in skill_root.glob("*/SKILL.md")} == ids
        for path in skill_root.glob("*/SKILL.md"):
            text = path.read_text(encoding="utf-8")
            assert GEN.PROVENANCE in text
            assert client in text
            assert "C:\\" not in text and "/Users/" not in text
    for client in GEN.CLIENT_IDS:
        prompts = ROOT / "prompts" / client
        assert {path.stem for path in prompts.glob("*.md")} == ids
    assert GEN.PROVENANCE in (ROOT / "codex/instructions/ADR-guide.md").read_text()
    for path in (
        ROOT / "hooks/hooks.json",
        ROOT / "codex/hooks/hooks.json",
        ROOT / "copilot/hooks.json",
    ):
        value = json.loads(path.read_text())
        assert value.get("hooks")
    assert not (ROOT / ".claude-plugin/hooks").exists()
    # This used to assert the three committed adr-hook.exe copies hashed alike.
    # ADR-029 retired the artefact, so the invariant inverts: no hook tree may
    # carry a compiled host at all. Asserted on the trees rather than on the
    # copy manifest, because a binary reintroduced one client over is exactly
    # the divergence the manifest would not show.
    for tree in (ROOT / "hooks", ROOT / "codex/hooks", ROOT / "copilot/hooks"):
        assert not (tree / "bin").exists(), f"{tree}/bin came back"
        strays = sorted(
            path.relative_to(ROOT).as_posix()
            for path in tree.rglob("*")
            if path.suffix.lower() in {".exe", ".dll", ".so", ".dylib", ".pdb", ".rs"}
        )
        assert not strays, f"a compiled or Rust host shipped again: {strays}"


def test_fixture_text_and_mode_metadata_are_cross_platform_stable(tmp_path):
    workflow = {
        "id": "unicode",
        "description": "Works on Windows and POSIX paths with Unicode.",
        "title": "Café",
        "mutates": False,
        "procedure": ["Read `C:\\Program Files\\ADR Kit` and `/tmp/adr kit/é`."],
    }
    rendered = GEN._render_skill(workflow, "codex-cli")
    assert "Café".encode() in rendered
    assert b"\r\n" not in rendered
    inventory = json.loads((ROOT / "packaging/executables.json").read_text())
    assert inventory["entries"] == sorted(inventory["entries"], key=lambda item: item["path"])
    assert {item["expected_mode"] for item in inventory["entries"]} <= {"100644", "100755"}


def test_generator_has_no_network_or_runtime_dependency():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in ("requests", "urllib", "http.client", "socket", "subprocess"):
        assert f"import {forbidden}" not in source
    dependencies = json.loads((ROOT / "packaging/dependencies.json").read_text())
    assert dependencies["runtime"] == []
    assert "coverage" not in json.dumps(dependencies["runtime"]).lower()


def test_crlf_materialised_tree_is_not_drift_but_content_change_still_is(tmp_path):
    """A Windows checkout must not read as adapter drift (TASK-57).

    The generator emits LF. With core.autocrlf=true git materialises CRLF for
    any generated path .gitattributes does not pin, so a byte-exact comparison
    reported drift on 13 files while `git diff` was empty -- which made the
    release runbook's drift gate unusable on the Windows certification machine,
    and whose suggested fix rewrote those files as LF, producing phantom
    modifications that could mask real drift.

    Only the EOL dimension may be relaxed: a real content change must still be
    detected, including when it arrives alongside CRLF.
    """
    output = tmp_path / "payload"
    GEN.generate(ROOT, output)

    text_outputs = [
        p for p in output.rglob("*")
        if p.is_file() and b"\x00" not in p.read_bytes() and b"\n" in p.read_bytes()
    ]
    assert text_outputs, "expected at least one generated text file"

    # 1. Whole tree materialised as CRLF, content otherwise identical.
    for path in text_outputs:
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    _, drift = GEN.generate(ROOT, output, check=True)
    assert drift == [], f"CRLF materialisation reported as drift: {drift}"

    # 2. A real content change is still drift, even with CRLF line endings.
    victim = output / "codex/skills/adr/SKILL.md"
    victim.write_bytes(victim.read_bytes() + b"hand edit\r\n")
    _, drift = GEN.generate(ROOT, output, check=True)
    assert "codex/skills/adr/SKILL.md" in drift, "real drift masked by EOL normalisation"


def test_binary_outputs_are_never_eol_normalised():
    """A CRLF byte pair inside a binary is data, not a line ending.

    Normalising it would make two genuinely different binaries compare equal,
    so _same_content must refuse to normalise when either side contains NUL --
    the same binary heuristic git uses.
    """
    # Same bytes: equal regardless.
    assert GEN._same_content(b"\x00a\r\nb", b"\x00a\r\nb")
    # Differ only by a CRLF pair, but binary: must NOT be treated as equal.
    assert not GEN._same_content(b"\x00a\r\nb", b"\x00a\nb")
    # Text differing only by EOL: equal.
    assert GEN._same_content(b"a\r\nb", b"a\nb")
    # Text differing in content: not equal.
    assert not GEN._same_content(b"a\r\nX", b"a\nb")
    # A missing file is never a match.
    assert not GEN._same_content(None, b"a\n")


def test_runtime_support_files_are_mirrored_and_the_generator_is_not():
    """The mirrors carry what bin/ imports, and nothing that breaks the marker.

    RUNTIME_SUPPORT_FILES exists because bin/adr-doctor resolves modules by
    appending ROOT and ROOT/"scripts" to sys.path, so the mirror has to
    reproduce the layout. What must stay OUT matters just as much:
    adr_doctor_models.generated_tree_owner() identifies a generated tree by the
    ABSENCE of clients/workflows.json. Mirror that file and the doctor silently
    stops degrading and starts hard-failing again (ADR-032).
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "client_generation_model", ROOT / "scripts" / "client_generation_model.py"
    )
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)

    missing = [
        f"{client}/{relative}"
        for client in ("codex", "copilot")
        for relative in model.RUNTIME_SUPPORT_FILES
        if not (ROOT / client / relative).is_file()
    ]
    assert not missing, f"declared runtime support files absent from a mirror: {missing}"

    must_stay_absent = (
        "clients/workflows.json",
        "clients/capabilities.json",
        "scripts/client_generation.py",
        "scripts/client_generation_model.py",
        "scripts/build-client-adapters.py",
    )
    leaked = [
        f"{client}/{relative}"
        for client in ("codex", "copilot")
        for relative in must_stay_absent
        if (ROOT / client / relative).exists()
    ]
    assert not leaked, (
        f"generator inputs leaked into a mirror: {leaked}. clients/workflows.json in "
        "particular is the marker generated_tree_owner() reads -- mirroring it turns "
        "the doctor's honest degradation back into six false failures."
    )


def test_generated_client_tree_is_distinguishable_from_the_payload_root():
    """The identity test is positive, not 'my import failed'."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "adr_doctor_models", ROOT / "bin" / "adr_doctor_models.py"
    )
    models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models)

    assert models.generated_tree_owner(ROOT) is None
    assert models.generated_tree_owner(ROOT / "codex") == "codex"
    assert models.generated_tree_owner(ROOT / "copilot") == "copilot"

    # And the re-rooting that follows from it.
    assert models.client_root(ROOT, "codex") == ROOT / "codex"
    assert models.client_root(ROOT / "codex", "codex") == ROOT / "codex"
    assert models.client_root(ROOT / "codex", "copilot") is None


def test_copilot_powershell_wrapper_dispatches_python_and_nothing_else():
    """ADR-029: the generated Copilot wrapper must reach for no second engine.

    TASK-160 made this wrapper gate the native exe behind ADR_KIT_NATIVE_HOOK=1,
    matching run-hook.cmd. ADR-029 then retired the binary outright, so the gate
    has nothing left to gate — and Copilot was the one client whose generated
    artifact ever preferred the exe unconditionally, which is why this asserts
    on the generated file rather than on the generator that writes it.
    """
    import json as _json
    from pathlib import Path as _Path
    hooks_file = _Path(__file__).resolve().parent.parent / "copilot" / "hooks.json"
    if not hooks_file.exists():
        import pytest as _pytest
        _pytest.skip("generated copilot/hooks.json not present")
    doc = _json.loads(hooks_file.read_text(encoding="utf-8"))
    blob = _json.dumps(doc)
    for token in ("adr-hook.exe", "ADR_KIT_NATIVE_HOOK", "hooks/bin/"):
        assert token not in blob, (
            f"the generated Copilot wrapper still reaches for a native host: {token!r}"
        )
    # Positive half: every powershell handler must still dispatch the one host.
    # Walked from doc["hooks"], not doc: the predecessor iterated doc.values()
    # and so ranged over the version number and the hooks map rather than the
    # event lists, which left its per-handler assertion dead. Only its
    # whole-blob check was ever doing work.
    handlers = [
        entry["powershell"]
        for event in doc["hooks"].values()
        for entry in (event if isinstance(event, list) else [event])
        if isinstance(entry, dict) and "powershell" in entry
    ]
    assert len(handlers) == len(doc["hooks"]), (
        f"expected one powershell handler per event, got {len(handlers)} "
        f"for {sorted(doc['hooks'])}"
    )
    for ps in handlers:
        assert "adr-hook.py" in ps, ps
