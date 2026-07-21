"""Bounded, deterministic client-adapter generation for ADR Kit."""

from __future__ import annotations

import stat
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPT_DIR = str(Path(__file__).resolve().parent)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from client_generation_artifacts import (
    declared_source_files,
    dependencies,
    inventory,
    native_hook_config,
    render_prompt,
    render_skill,
    validate_capabilities,
    validate_manifests,
    validate_workflows,
)
from client_generation_model import (
    CLIENT_IDS,
    COPY_EXCLUSIONS,
    COPY_ROOTS,
    GENERATED_CLIENTS,
    HOOK_RUNTIME_FILES,
    PROVENANCE,
    SOURCE_FILES,
    GenerationError,
    Stats,
    expected_version,
    read,
    read_json,
    write,
)
from client_generation_state import (
    collect_release_files,
    load_early_state,
    load_fast_state,
    save_fast_state,
    validate_release_paths,
)

# Preserve the focused validation surface used by contract tests and downstream
# maintainers while implementation lives in bounded support modules.
_validate_capabilities = validate_capabilities
_validate_workflows = validate_workflows
_validate_manifests = validate_manifests
_native_hook_config = native_hook_config
_render_skill = render_skill
_render_prompt = render_prompt


def generate(
    source_root: Path,
    output_root: Path | None = None,
    check: bool = False,
) -> tuple[Stats, list[str]]:
    source_root = source_root.resolve()
    output_root = (output_root or source_root).resolve()
    stats = Stats()
    source_paths = declared_source_files(source_root)
    if not check and load_early_state(source_root, output_root, source_paths, stats):
        return stats, []

    inputs = {name: read_json(source_root / name, stats) for name in SOURCE_FILES}
    version = expected_version(source_root, stats)
    validate_capabilities(
        inputs["clients/capabilities.json"],
        inputs["clients/exceptions.json"],
    )
    workflows = validate_workflows(inputs["clients/workflows.json"])
    validate_manifests(inputs, version)
    hook_manifest = inputs["hooks/manifest.json"]
    if hook_manifest.get("schema_version") != 1:
        raise GenerationError("hook manifest schema_version must be 1")

    expected: dict[str, tuple[bytes, int | None]] = {}
    for source in source_paths:
        relative = source.relative_to(source_root).as_posix()
        if relative in COPY_EXCLUSIONS:
            continue
        content = read(source, stats).replace(b"\r\n", b"\n")
        if relative == "instructions/ADR-guide.md":
            content = f"<!-- {PROVENANCE}; schema v1. -->\n".encode() + content
        mode = stat.S_IMODE(source.stat().st_mode)
        for client_dir in GENERATED_CLIENTS.values():
            expected[f"{client_dir}/{relative}"] = (content, mode)

    for workflow in workflows["workflows"]:
        for client_id, client in workflows["clients"].items():
            expected[f"{client['prompt_root']}/{workflow['id']}.md"] = (
                render_prompt(workflow, client["label"], client_id),
                None,
            )
            if client_id in GENERATED_CLIENTS:
                expected[f"{client['skill_root']}/{workflow['id']}/SKILL.md"] = (
                    render_skill(workflow, client_id),
                    None,
                )
            elif not (
                source_root / client["skill_root"] / workflow["id"] / "SKILL.md"
            ).is_file():
                raise GenerationError(
                    f"missing canonical rich skill: {workflow['id']}"
                )

    for relative in HOOK_RUNTIME_FILES:
        source = source_root / relative
        content = read(source, stats)
        if source.suffix.casefold() not in {".exe", ".dll"}:
            content = content.replace(b"\r\n", b"\n")
        suffix = relative.removeprefix("hooks/")
        mode = stat.S_IMODE(source.stat().st_mode)
        for client_dir in GENERATED_CLIENTS.values():
            expected[f"{client_dir}/hooks/{suffix}"] = (content, mode)

    native_hook_targets = {
        "claude-code-cli": "hooks/hooks.json",
        "codex-cli": "codex/hooks/hooks.json",
        "github-copilot-cli": "copilot/hooks.json",
    }
    for client_id, target in native_hook_targets.items():
        expected[target] = (native_hook_config(hook_manifest, client_id), None)
    expected["packaging/dependencies.json"] = (
        dependencies(inputs["packaging/dependencies-source.json"]),
        None,
    )
    expected["packaging/executables.json"] = (
        inventory(
            source_root,
            source_paths,
            inputs["packaging/executables-source.json"],
        ),
        None,
    )

    generated_roots = [
        *(
            f"{directory}/{root}"
            for directory in GENERATED_CLIENTS.values()
            for root in COPY_ROOTS
        ),
        *(f"{directory}/skills" for directory in GENERATED_CLIENTS.values()),
        *(client["prompt_root"] for client in workflows["clients"].values()),
        "codex/hooks",
        "copilot/hooks",
    ]
    if not check and load_fast_state(output_root, expected, generated_roots):
        stats.unchanged = len(expected)
        return stats, []

    ordered_outputs = sorted(expected.items())

    def read_output(item: tuple[str, tuple[bytes, int | None]]) -> bytes | None:
        try:
            return (output_root / item[0]).read_bytes()
        except FileNotFoundError:
            return None

    if output_root.exists():
        # Windows file-open latency dominates existing-output validation. Reads
        # are independent, bounded, and joined in deterministic path order.
        with ThreadPoolExecutor(
            max_workers=min(16, max(1, len(ordered_outputs)))
        ) as pool:
            actual_outputs = list(pool.map(read_output, ordered_outputs))
    else:
        # A clean destination cannot contain an output. Avoid creating and
        # joining a thread pool only to raise FileNotFoundError for every path.
        actual_outputs = [None] * len(ordered_outputs)

    drift: list[str] = []
    pending_writes: list[tuple[Path, bytes, int | None]] = []
    for (relative, (content, mode)), actual in zip(
        ordered_outputs,
        actual_outputs,
    ):
        destination = output_root / relative
        if actual is not None:
            stats.files_read += 1
            stats.bytes_read += len(actual)
        mode_matches = (
            mode is None
            or (
                destination.is_file()
                and stat.S_IMODE(destination.stat().st_mode) == mode
            )
        )
        if actual == content and mode_matches:
            stats.unchanged += 1
            continue
        drift.append(relative)
        if not check:
            pending_writes.append((destination, content, mode))

    if pending_writes:
        def write_output(item: tuple[Path, bytes, int | None]) -> None:
            write(item[0], item[1], item[2], stats)

        with ThreadPoolExecutor(max_workers=min(16, len(pending_writes))) as pool:
            list(pool.map(write_output, pending_writes))

    expected_set = set(expected)
    for root_name in generated_roots:
        root_path = output_root / root_name
        if not root_path.is_dir():
            continue
        for path in root_path.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(output_root).as_posix()
            if "/hooks/bin/" in f"/{relative}" or relative in expected_set:
                continue
            drift.append(relative)
            if not check:
                path.unlink()

    forbidden = validate_release_paths(
        expected,
        inputs["packaging/public-artifacts.json"],
    )
    if forbidden:
        raise GenerationError(
            "generated output outside public allowlist: " + ", ".join(forbidden)
        )
    if not check:
        save_fast_state(
            source_root,
            output_root,
            source_paths,
            expected,
            generated_roots,
        )
    return stats, sorted(set(drift))
