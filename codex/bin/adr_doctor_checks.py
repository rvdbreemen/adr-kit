"""Fast client checks, bounded deep probes, and enumerated safe repairs."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

from adr_doctor_models import check, client_root, generated_tree_owner
from adr_settings import (
    SettingsError,
    resolve_settings,
)
from clients.installer.contracts import CLIENT_IDS
from clients.installer.detection import detect_clients
# client_generation is deliberately NOT imported here. It is the generator's own
# source and is not mirrored into a client tree, so a module-scope import would
# kill bin/adr-doctor at import time in codex/ and copilot/ -- the same shape as
# the v0.44.1 outage. _generated_check imports it lazily, behind a check that a
# mirror never passes.
from project_setup import (
    SetupError,
    apply_changes,
    collect_changes,
    validate_markers,
)

HOOK_EVENTS = {
    "claude": {
        "SessionStart",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "SubagentStart",
        "PreCompact",
    },
    "codex": {
        "SessionStart",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "SubagentStart",
        "PreCompact",
    },
    "copilot": {"sessionStart", "userPromptSubmitted", "postToolUse"},
}


def resolve_launcher_target(
    plugin_root: Path, command: str, args: list[str]
) -> tuple[str | None, list[str]]:
    expanded = [
        value.replace("${PLUGIN_ROOT}", str(plugin_root))
        .replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root))
        for value in args
    ]
    command_path = Path(command).expanduser()
    resolved_command = (
        str(command_path.resolve())
        if command_path.is_absolute()
        else shutil.which(command)
    )
    targets = []
    for value in expanded:
        candidate = Path(value)
        if not candidate.is_absolute() and value.startswith("."):
            candidate = plugin_root / candidate
        if candidate.suffix in {"", ".py", ".cmd", ".sh"} and (
            "/" in value or "\\" in value
        ):
            targets.append(str(candidate.resolve()))
    return resolved_command, targets


def check_mcp_launcher(
    plugin_root: Path, client: str, *, required: bool
) -> dict[str, Any]:
    root = client_root(plugin_root, client)
    if root is None:
        return check(
            "mcp-launcher", client=client, status="unsupported", required=False,
            summary=f"{client} is not installed in this generated client tree",
        )
    config_path = root / ".mcp.json"
    if not config_path.is_file():
        return check(
            "mcp-launcher", client=client, status="failed", required=required,
            summary=f"missing owned MCP manifest {config_path}",
            actions=[{"detail": f"Reinstall ADR Kit for {client}."}],
        )
    try:
        server = json.loads(config_path.read_text(encoding="utf-8"))[
            "mcpServers"
        ]["adr-kit"]
        command, args = server["command"], server["args"]
        if not isinstance(command, str) or not isinstance(args, list):
            raise TypeError("command/args")
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        return check(
            "mcp-launcher", client=client, status="failed", required=required,
            summary=f"invalid owned MCP manifest {config_path}: {exc}",
            actions=[{"detail": f"Reinstall ADR Kit for {client}."}],
        )
    resolved, targets = resolve_launcher_target(root, command, args)
    missing = [target for target in targets if not Path(target).is_file()]
    if resolved is None or missing:
        return check(
            "mcp-launcher", client=client, status="stale", required=required,
            summary="MCP launcher resolves to a missing command or removed payload",
            evidence=[
                {
                    "path": str(config_path),
                    "command": command,
                    "resolved_command": resolved,
                    "missing_targets": missing,
                }
            ],
            actions=[
                {
                    "command": (
                        f"{sys.executable} scripts/install-agent-envs.py "
                        f"--clients {client}"
                    )
                }
            ],
        )
    return check(
        "mcp-launcher", client=client, status="healthy", required=required,
        summary="MCP command and payload target resolve",
        evidence=[
            {
                "path": str(config_path),
                "resolved_command": resolved,
                "targets": targets,
            }
        ],
    )


def check_hook_package(plugin_root: Path, client: str) -> dict[str, Any]:
    root = client_root(plugin_root, client)
    if root is None:
        return check(
            "hook-package", client=client, status="unsupported", required=False,
            summary=f"{client} is not installed in this generated client tree",
        )
    config_path = (
        root / "hooks" / "hooks.json"
        if client != "copilot"
        else root / "hooks.json"
    )
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        hooks = payload["hooks"]
        if not isinstance(hooks, dict) or set(hooks) != HOOK_EVENTS[client]:
            raise ValueError("event set differs from the certified contract")
        handlers = [
            handler
            for groups in hooks.values()
            for group in groups
            for handler in (
                group.get("hooks", []) if client != "copilot" else [group]
            )
        ]
        if not handlers:
            raise ValueError("no command handlers")
        if client == "copilot":
            if any(
                not isinstance(handler.get("bash"), str)
                or not isinstance(handler.get("powershell"), str)
                for handler in handlers
            ):
                raise ValueError("missing bash or PowerShell command")
        elif any(handler.get("type") != "command" for handler in handlers):
            raise ValueError("non-command handler")
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        return check(
            "hook-package",
            client=client,
            status="failed",
            required=False,
            summary=f"broken native hook package: {config_path}: {exc}",
            actions=[{"detail": f"Reinstall ADR Kit for {client}."}],
        )
    runtime = root / "hooks" / "adr-hook.py"
    wrapper = root / "hooks" / "run-hook.cmd"
    # The Rust host used to be required here too. ADR-029 retired it, so
    # demanding the artefact would now fail every healthy install: Python is
    # the runtime on every platform.
    required_files = [runtime]
    if client != "copilot":
        required_files.append(wrapper)
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        return check(
            "hook-package",
            client=client,
            status="failed",
            required=False,
            summary="native hook config points at a missing runtime",
            evidence=[{"missing": missing}],
            actions=[{"detail": f"Reinstall ADR Kit for {client}."}],
        )
    return check(
        "hook-package",
        client=client,
        status="healthy",
        required=False,
        summary="native hook shape and Windows/POSIX launchers resolve",
        evidence=[{"path": str(config_path), "events": sorted(hooks)}],
    )


def _generated_check(plugin_root: Path, check_only: bool) -> tuple[dict, list[dict]]:
    # A generated tree holds no canonical inputs to diff against, so there is
    # nothing here to be stale. Returning before the import matters twice: the
    # generator's source is not mirrored, and in repair mode generate() would
    # otherwise write into the very tree it is inspecting.
    if generated_tree_owner(plugin_root) is not None:
        return check(
            "generated-adapters", status="unsupported", required=False,
            summary="generated client tree carries no canonical inputs to diff",
            actions=[{
                "detail": (
                    "Run adr-doctor from the ADR Kit payload root to check "
                    "adapter drift."
                )
            }],
        ), []
    from client_generation import GenerationError, generate  # not mirrored
    try:
        _stats, drift = generate(plugin_root, check=True)
    except (GenerationError, OSError) as exc:
        return check(
            "generated-adapters", status="failed",
            summary=f"generated artifact check failed: {exc}",
        ), []
    if not drift:
        return check(
            "generated-adapters", status="healthy",
            summary="generated client artifacts match canonical inputs",
        ), []
    if check_only:
        return check(
            "generated-adapters", status="stale",
            summary="generated client artifacts drifted",
            actions=[{
                "command": (
                    f"{sys.executable} "
                    f"{plugin_root / 'scripts' / 'build-client-adapters.py'}"
                )
            }],
        ), []
    try:
        generate(plugin_root, check=False)
    except (GenerationError, OSError) as exc:
        return check(
            "generated-adapters", status="failed",
            summary=f"safe regeneration failed: {exc}",
        ), []
    evidence = {"kind": "generated-adapters", "path": str(plugin_root)}
    return check(
        "generated-adapters", status="repaired",
        summary="regenerated owned client artifacts",
        repairs=[evidence],
    ), [evidence]


def _guidance_check(root: Path) -> dict:
    guide = root / ".adr-kit" / "ADR-guide.md"
    problems = []
    for relative in ("AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md"):
        path = root / relative
        if not path.is_file():
            continue
        try:
            validate_markers(path.read_text(encoding="utf-8-sig"), path)
        except (OSError, UnicodeError, SetupError) as exc:
            problems.append(str(exc))
    if problems:
        return check(
            "project-guidance", status="failed",
            summary="managed instruction markers are malformed",
            evidence=[{"problems": problems}],
            actions=[{"command": "python scripts/setup-project.py --dry-run"}],
        )
    if not guide.is_file():
        return check(
            "project-guidance", status="degraded", required=False,
            summary="project has no generated ADR guide",
            actions=[{"command": "python scripts/setup-project.py"}],
        )
    return check(
        "project-guidance", status="healthy",
        summary="guide and managed instruction markers are structurally valid",
        evidence=[{"path": str(guide)}],
    )


def run_client_checks(
    root: Path,
    plugin_root: Path,
    *,
    global_settings: Path | None,
    check_only: bool,
    allow_fix: bool,
) -> tuple[list[dict], list[dict]]:
    checks, repairs = [], []
    generated, generated_repairs = _generated_check(plugin_root, check_only)
    checks.append(generated)
    repairs.extend(generated_repairs)
    try:
        settings = resolve_settings(root, global_path=global_settings)["values"]
        checks.append(check(
            "settings", status="healthy",
            summary="global/project settings parsed with known keys",
        ))
    except SettingsError as exc:
        settings = None
        checks.append(check(
            "settings", status="failed", summary=str(exc),
            actions=[{"detail": "Correct the named ADR Kit settings file."}],
        ))
    guidance = _guidance_check(root)
    checks.append(guidance)
    integration_required = (root / ".adr-kit" / "ADR-guide.md").is_file()
    detected = detect_clients()
    for name in CLIENT_IDS:
        enabled = settings["clients"][name]["enabled"] if settings else None
        if enabled is False:
            checks.append(check(
                "native-client", client=name, status="disabled", required=False,
                summary="client disabled by effective settings",
            ))
            continue
        client = detected.get(name)
        checks.append(check(
            "native-client", client=name,
            status="healthy" if client else "unsupported",
            required=False,
            summary=(
                f"detected {client.version} at {client.executable}"
                if client else "native CLI not installed"
            ),
            evidence=[{"version": client.version, "path": client.executable}] if client else [],
        ))
        checks.append(
            check_mcp_launcher(
                plugin_root, name, required=integration_required
            )
        )
        checks.append(check_hook_package(plugin_root, name))
    if allow_fix and guidance["status"] in {
        "degraded",
        "failed",
    }:
        selected = [
            name for name in CLIENT_IDS
            if name in detected
            and settings
            and settings["clients"][name]["enabled"] is not False
        ]
        try:
            changes, configure = collect_changes(
                root,
                plugin_root,
                selected,
                pre_commit_enabled=bool(
                    settings and settings["pre_commit"]["enabled"]
                ),
            )
            apply_changes(root, changes, configure_hooks_path=configure)
            for change in changes:
                repair = {
                    "kind": change.action,
                    "path": str(change.path),
                }
                repairs.append(repair)
            if changes:
                checks.append(check(
                    "project-guidance-fix",
                    status="repaired",
                    summary="backed up and converged ADR Kit-owned project guidance",
                    repairs=repairs[-len(changes):],
                    actions=[
                        {
                            "detail": (
                                f"Restore backups under "
                                f"{root / '.adr-kit' / 'backups'} if needed."
                            )
                        }
                    ],
                ))
        except SetupError as exc:
            checks.append(check(
                "project-guidance-fix",
                status="failed",
                summary=f"managed repair stopped safely: {exc}",
            ))
    return checks, repairs
