"""Public release inputs are explicit and exclude repository-local state."""

from __future__ import annotations

import importlib.util
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "client_generation", ROOT / "scripts/client_generation.py"
)
assert SPEC and SPEC.loader
GEN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GEN
SPEC.loader.exec_module(GEN)
ALLOWLIST = json.loads((ROOT / "packaging/public-artifacts.json").read_text())


def test_public_artifact_allowlist_rejects_private_and_developer_state():
    forbidden = [
        "backlog/tasks/task-40.md",
        ".superpowers/brainstorm.md",
        ".git/config",
        ".github/workflows/release.yml",
        "tests/test_secret.py",
        "codex/__pycache__/x.pyc",
        ".adr-kit-cache/state.json",
        "secrets/token.txt",
        "docs/plans/internal.md",
        "docs/reviews/private.md",
        ".env",
        "private.pem",
        "hooks/bin/windows-x64/adr-hook.pdb",
    ]
    assert GEN.validate_release_paths(forbidden, ALLOWLIST) == sorted(forbidden)


def test_public_artifact_allowlist_accepts_only_declared_product_inputs():
    accepted = [
        ".claude-plugin/plugin.json",
        ".github/plugin/marketplace.json",
        "bin/adr",
        "clients/workflows.json",
        "codex/skills/adr/SKILL.md",
        "copilot/plugin.json",
        "hooks/manifest.json",
        "packaging/dependencies.json",
        "packaging/client-generation-benchmark.json",
        "prompts/claude-code-cli/adr.md",
        "scripts/build-client-adapters.py",
        "scripts/benchmark-client-generation.py",
        "skills/adr/SKILL.md",
    ]
    assert GEN.validate_release_paths(accepted, ALLOWLIST) == []


def test_runtime_dependency_and_entrypoint_budgets_are_machine_readable():
    dependencies = json.loads((ROOT / "packaging/dependencies.json").read_text())
    executables = json.loads((ROOT / "packaging/executables.json").read_text())
    assert dependencies["runtime"] == []
    assert len(executables["task_40_added_public_entrypoints"]) <= 4
    for item in executables["entries"]:
        assert item["ownership"] and item["purpose"] and item["provenance"]


def test_task_40_python_modules_stay_within_adr_010_line_budgets():
    entrypoints = (
        "scripts/benchmark-client-generation.py",
        "scripts/build-client-adapters.py",
        "scripts/settings.py",
        "scripts/setup-project.py",
    )
    support_modules = (
        "scripts/adr_settings.py",
        "scripts/client_certification.py",
        "scripts/client_evidence.py",
        "scripts/client_generation.py",
        "scripts/client_generation_artifacts.py",
        "scripts/client_generation_model.py",
        "scripts/client_generation_state.py",
        "scripts/project_setup.py",
        "clients/installer/payload.py",
    )
    for relative in entrypoints:
        lines = (ROOT / relative).read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 300, f"{relative} has {len(lines)} lines"
    for relative in support_modules:
        lines = (ROOT / relative).read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 400, f"{relative} has {len(lines)} lines"


def test_release_archive_is_built_only_from_the_allowlist(tmp_path):
    files = GEN.collect_release_files(ROOT, ALLOWLIST)
    assert files == sorted(set(files))
    assert GEN.validate_release_paths(files, ALLOWLIST) == []
    archive = tmp_path / "adr-kit-release.tar"
    with tarfile.open(archive, "w") as payload:
        for relative in files:
            payload.add(ROOT / relative, arcname=relative, recursive=False)
    with tarfile.open(archive) as payload:
        archived = sorted(member.name for member in payload if member.isfile())
    assert archived == files
    forbidden_tokens = (
        "backlog/",
        ".superpowers/",
        ".git/",
        ".github/workflows/",
        "tests/",
        "__pycache__/",
        ".adr-kit-cache/",
        ".pdb",
    )
    assert not any(
        token in path
        for path in archived
        for token in forbidden_tokens
    )
