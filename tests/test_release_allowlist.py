"""Public release inputs are explicit and exclude repository-local state."""

from __future__ import annotations

import importlib.util
import json
import re
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
        "bin/adr-hook.pdb",
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
        # The release driver (ADR-042). Its phases live in the support modules
        # below, so this stays the thin orchestration layer it is meant to be.
        "scripts/release.py",
    )
    support_modules = (
        "scripts/adr_settings.py",
        "scripts/client_certification.py",
        "scripts/client_support_matrix.py",
        "scripts/client_evidence.py",
        "scripts/client_generation.py",
        "scripts/client_generation_artifacts.py",
        "scripts/client_generation_model.py",
        "scripts/client_generation_state.py",
        "scripts/project_setup.py",
        "clients/installer/payload.py",
        "clients/installer/smoke.py",
        "clients/installer/judge_backend.py",
        "clients/installer/registrations.py",
        "clients/installer/bounded.py",
        # Budgeted from v0.50.0: it was the largest unbudgeted installer module
        # and TASK-164 pushed it to 406 lines before anything noticed.
        "clients/installer/native.py",
        # Budgeted from v0.56.0: release_phases.py crossed 400 lines while it
        # still carried its own process helpers, which is what split them out
        # into release_shell.py, and later its npm handling, which is
        # release_npm.py. Budget all three so the seams hold.
        "scripts/release_phases.py",
        "scripts/release_shell.py",
        "scripts/release_npm.py",
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


# A release payload must never carry a maintainer's machine layout. Home
# directories are the leak that matters: they name a real person and expose
# the build host. Documentation may still *illustrate* such a path, so a user
# segment is only acceptable when it is an obvious stand-in.
REDACTED_USER_SEGMENTS = frozenset(
    {
        "...",
        "<user>",
        "<username>",
        "%username%",
        "$user",
        "public",
        "default",
        "test",
        "testuser",
        "runner",
    }
)

USER_HOME_PATH = re.compile(
    r"(?:[A-Za-z]:[\\/]{1,2}Users|/home|/Users)[\\/]{1,2}([^\\/\s\"']{1,64})",
    re.IGNORECASE,
)

# Compiled artifacts have no reason to mention a Windows drive at all; a hit
# there is build-host debug metadata (`C:\Users\...\.cargo\...`) rather than
# prose, so binaries are held to the stricter rule.
WINDOWS_DRIVE_PATH = re.compile(r"[A-Za-z]:[\\/]{1,2}[A-Za-z0-9._\\/ -]{3,80}")


def developer_home_leaks(text):
    """Return home-directory paths in ``text`` that name a concrete user."""
    return [
        match.group(0)
        for match in USER_HOME_PATH.finditer(text)
        if match.group(1).lower() not in REDACTED_USER_SEGMENTS
    ]


def _release_payload():
    for relative in GEN.collect_release_files(ROOT, ALLOWLIST):
        data = (ROOT / relative).read_bytes()
        yield relative, data, data.decode("utf-8", "replace")


def test_released_files_carry_no_maintainer_home_directories():
    leaks = {
        relative: found
        for relative, _, text in _release_payload()
        if (found := developer_home_leaks(text))
    }
    assert leaks == {}, f"maintainer paths reached the release payload: {leaks}"


def test_released_binaries_embed_no_windows_build_paths():
    leaks = {
        relative: found
        for relative, data, text in _release_payload()
        if b"\0" in data[:8192] and (found := WINDOWS_DRIVE_PATH.findall(text))
    }
    assert leaks == {}, f"binaries embed build-host paths: {leaks}"


def test_home_directory_scanner_flags_real_leaks_and_spares_placeholders():
    # Without this the scan could silently pass by matching nothing at all.
    leaking = (
        "D:/Users/robert/documenten/adr-kit/bin/adr-judge",
        r"C:\Users\Robert\AppData\Local\adr-kit",
        r"C:\\Users\\rvdbreemen\\.cargo\\registry",
        "/home/robert/src/adr-kit",
        "/Users/breemen/adr-kit",
    )
    for sample in leaking:
        assert developer_home_leaks(sample), f"missed a leak: {sample}"

    redacted = (
        r"On Windows this mangles paths like C:\\Users\\... -> C:Users...",
        "[adr-kit] Engine: D:/Users/.../adr-kit/bin/adr-judge",
        "C:/Users/test/AppData/Local/adr-kit/marketplaces",
        r"C:\Program Files\ADR Kit",
        "/rustc/2d8144b7880597b6e6d3dfd63a9a9efae3f533d3/library",
        "https://github.com/rvdbreemen/adr-kit",
    )
    for sample in redacted:
        assert not developer_home_leaks(sample), f"false positive: {sample}"
