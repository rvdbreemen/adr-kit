"""Validation and rendering for deterministic native client artifacts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from client_generation_model import (
    CLIENT_IDS,
    COPY_ROOTS,
    HOOK_RUNTIME_FILES,
    PROVENANCE,
    RUNTIME_SUPPORT_FILES,
    WORKFLOW_IDS,
    GenerationError,
    encoded_json,
)


def validate_capabilities(value: object, exception_registry: object) -> dict:
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise GenerationError("capability registry schema_version must be 1")
    if value.get("program_scope", {}).get("first_class_clients") != list(CLIENT_IDS):
        raise GenerationError("capability registry must contain exactly the three native clients")
    clients = value.get("clients")
    if not isinstance(clients, list) or [item.get("id") for item in clients] != list(CLIENT_IDS):
        raise GenerationError("capability client order or membership is invalid")
    for client in clients:
        for exception in client.get("degradations", []):
            required = {"id", "reason", "user_effect", "backstop", "blocks_certification"}
            if not required.issubset(exception):
                raise GenerationError(f"undocumented exception for {client['id']}")
    registered = {
        item.get("id"): item
        for item in (
            exception_registry.get("exceptions", [])
            if isinstance(exception_registry, dict)
            else []
        )
    }
    used = {
        item["id"]
        for client in clients
        for item in client.get("degradations", [])
    }
    if used != set(registered):
        raise GenerationError("capability exceptions differ from fixture registry")
    for exception in registered.values():
        fixture = Path(str(exception.get("fixture", "")))
        if fixture.is_absolute() or ".." in fixture.parts:
            raise GenerationError("exception fixture must be repository-relative")
    return value


def validate_workflows(value: object) -> dict:
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise GenerationError("workflow registry schema_version must be 1")
    if tuple(value.get("clients", {})) != CLIENT_IDS:
        raise GenerationError("workflow registry must contain exactly the three native clients")
    workflows = value.get("workflows")
    if not isinstance(workflows, list) or not workflows:
        raise GenerationError("workflow registry is empty")
    ids = [item.get("id") for item in workflows]
    if tuple(ids) != WORKFLOW_IDS:
        raise GenerationError(
            "workflow ids must match the complete canonical workflow set "
            f"({len(WORKFLOW_IDS)} entries)"
        )
    for item in workflows:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", str(item.get("id", ""))):
            raise GenerationError(f"invalid workflow id: {item.get('id')!r}")
        if not item.get("description") or not item.get("procedure"):
            raise GenerationError(f"incomplete workflow metadata: {item['id']}")
    return value


def _manifest_version(value: object, path: str) -> str:
    if not isinstance(value, dict) or value.get("name") != "adr-kit":
        raise GenerationError(f"invalid native manifest name: {path}")
    version = value.get("version")
    repository = str(value.get("repository", ""))
    if not isinstance(version, str) or value.get("license") != "MIT":
        raise GenerationError(f"invalid native manifest version/license: {path}")
    if "github.com/rvdbreemen/adr-kit" not in repository:
        raise GenerationError(f"native manifest lacks repository provenance: {path}")
    return version


def _marketplace_version(value: object, path: str) -> str | None:
    if not isinstance(value, dict) or value.get("name") is None:
        raise GenerationError(f"invalid marketplace manifest: {path}")
    plugins = value.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1 or plugins[0].get("name") != "adr-kit":
        raise GenerationError(f"marketplace must declare only adr-kit: {path}")
    version = plugins[0].get("version")
    return version if isinstance(version, str) else None


def validate_manifests(inputs: dict[str, object], version: str) -> None:
    # Collect every stale manifest before failing: aborting on the first one turns
    # a bump into a fix-one-rerun loop. packaging/version-sites.json is the shared
    # registry; scripts/bump-version.py writes them all in one command.
    stale: list[str] = []
    for path in (".claude-plugin/plugin.json", "codex/.codex-plugin/plugin.json", "copilot/plugin.json"):
        if _manifest_version(inputs[path], path) != version:
            stale.append(path)
    for path in (".claude-plugin/marketplace.json", ".github/plugin/marketplace.json"):
        if _marketplace_version(inputs[path], path) != version:
            stale.append(path)
    if stale:
        raise GenerationError(
            "stale version reference: "
            + ", ".join(stale)
            + f" (fix them all: python scripts/bump-version.py {version})"
        )
    if _marketplace_version(inputs[".agents/plugins/marketplace.json"], ".agents/plugins/marketplace.json") is not None:
        raise GenerationError("Codex local marketplace must inherit plugin version")
    claude = inputs[".claude-plugin/plugin.json"]
    codex = inputs["codex/.codex-plugin/plugin.json"]
    copilot = inputs["copilot/plugin.json"]
    if "hooks" in claude:
        raise GenerationError("Claude must use plugin-root hooks/hooks.json")
    if codex.get("hooks") != "./hooks/hooks.json":
        raise GenerationError("Codex manifest must reference ./hooks/hooks.json")
    if copilot.get("hooks") != "hooks.json":
        raise GenerationError("Copilot manifest must reference hooks.json")
    if codex.get("skills") != "./skills/" or copilot.get("skills") != "skills/":
        raise GenerationError("native manifest skill root is invalid")
    for path in (".mcp.json", "codex/.mcp.json", "copilot/.mcp.json"):
        value = inputs[path]
        if not isinstance(value, dict) or "adr-kit" not in value.get("mcpServers", {}):
            raise GenerationError(f"missing required MCP artifact: {path}")


def _runner_timeout(event: dict) -> int:
    value = event.get("runner_timeout_sec", 1)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 30:
        raise GenerationError(
            f"hook {event.get('id', '<unknown>')} runner_timeout_sec must be an integer from 1 to 30"
        )
    return value


def _codex_windows_command(event: dict) -> str:
    """Run Codex hooks fail-open when its plugin-root env is unavailable."""
    return (
        "cmd.exe /d /c if defined PLUGIN_ROOT if exist "
        '"%PLUGIN_ROOT%\\hooks\\run-hook.cmd" '
        'call "%PLUGIN_ROOT%\\hooks\\run-hook.cmd" '
        f'{event["command"]} codex-cli & exit /b 0'
    )


def _nested_hook_config(manifest: dict, client_id: str) -> dict:
    hooks: dict[str, list[dict]] = {}
    for event in manifest.get("events", []):
        native = event.get("clients", {}).get(client_id)
        if not native:
            continue
        runner_timeout = _runner_timeout(event)
        if client_id == "claude-code-cli":
            handler = {
                "type": "command",
                "command": (
                    '"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" '
                    f'{event["command"]} claude-code-cli'
                ),
                "timeout": runner_timeout,
            }
        else:
            codex_timeout = max(runner_timeout, 5)
            handler = {
                "type": "command",
                "command": (
                    '"$PLUGIN_ROOT/hooks/run-hook.cmd" '
                    f'{event["command"]} codex-cli'
                ),
                "commandWindows": _codex_windows_command(event),
                "timeout": codex_timeout,
            }
        entry: dict[str, object] = {"hooks": [handler]}
        if event.get("matcher"):
            entry["matcher"] = event["matcher"]
        hooks.setdefault(native, []).append(entry)
    return {
        "description": "ADR Kit deterministic fail-open lifecycle hooks.",
        "hooks": hooks,
    }


def _copilot_hook_config(manifest: dict) -> dict:
    hooks: dict[str, list[dict]] = {}
    for event in manifest.get("events", []):
        native = event.get("clients", {}).get("github-copilot-cli")
        if not native:
            continue
        command = event["command"]
        runner_timeout = _runner_timeout(event)
        hooks.setdefault(native, []).append({
            "type": "command",
            "bash": (
                'python3 "${PLUGIN_ROOT}/hooks/adr-hook.py" '
                f"--client github-copilot-cli --event {command} || true"
            ),
            "powershell": (
                '$native = "${PLUGIN_ROOT}/hooks/bin/windows-x64/adr-hook.exe"; '
                f'if (Test-Path $native) {{ & $native --client github-copilot-cli --event {command} }} '
                "else { $python = Get-Command python -ErrorAction SilentlyContinue; "
                f'if ($python) {{ & $python.Source "${{PLUGIN_ROOT}}/hooks/adr-hook.py" '
                f"--client github-copilot-cli --event {command} }} }}; exit 0"
            ),
            "cwd": "${PLUGIN_ROOT}",
            "timeoutSec": runner_timeout,
        })
    return {"version": 1, "hooks": hooks}


def native_hook_config(manifest: dict, client_id: str) -> bytes:
    if client_id == "github-copilot-cli":
        return encoded_json(_copilot_hook_config(manifest))
    return encoded_json(_nested_hook_config(manifest, client_id))


def render_skill(workflow: dict, client_id: str) -> bytes:
    invocation = (
        f"Invoke explicitly with `$adr-kit:{workflow['id']}` when needed."
        if client_id == "codex-cli"
        else (
            f"Select `adr-kit:{workflow['id']}` from `/skills`, or ask Copilot "
            f"to use the `{workflow['id']}` ADR Kit skill."
        )
    )
    lines = [
        "---",
        f"name: {workflow['id']}",
        f"description: {workflow['description']}",
        "license: MIT",
        "---",
        "",
        f"<!-- {PROVENANCE}; schema v1; client {client_id}. -->",
        f"# {workflow['title']}",
        "",
        invocation,
        "Resolve `<plugin-root>` from this installed skill. Use only bundled,",
        "local ADR Kit tools and follow this canonical workflow:",
        "",
    ]
    lines.extend(f"{index}. {step}" for index, step in enumerate(workflow["procedure"], 1))
    lines.extend([
        "",
        "Do not contact another model or mutate user-owned instructions.",
        "",
    ])
    return "\n".join(lines).encode("utf-8")


def render_prompt(workflow: dict, label: str, client_id: str) -> bytes:
    mutation = (
        "This workflow may write files; show material changes before applying them."
        if workflow["mutates"]
        else "This workflow is read-only."
    )
    return (
        f"<!-- {PROVENANCE}; schema v1; client {client_id}. -->\n"
        f"# {workflow['title']}\n\n"
        f"Use ADR Kit's `{workflow['id']}` skill in {label}. {mutation}\n"
        "Pass the remaining prompt as the workflow topic or target. Preserve the "
        "skill's confirmation and fail-open boundaries.\n"
    ).encode("utf-8")


def declared_source_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for name in COPY_ROOTS:
        source = root / name
        if not source.is_dir():
            raise GenerationError(f"missing declared input root: {name}")
        paths.extend(path for path in source.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    paths.extend(
        root / relative
        for relative in (*HOOK_RUNTIME_FILES, *RUNTIME_SUPPORT_FILES)
    )
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise GenerationError(
            "missing declared runtime input: "
            + ", ".join(str(path.relative_to(root)) for path in missing)
        )
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def inventory(root: Path, source_paths: Iterable[Path], source: dict) -> bytes:
    entries = []
    for path in source_paths:
        relative = path.relative_to(root).as_posix()
        if relative.startswith("bin/") and path.suffix == "" and path.name != "bump-version":
            entries.append({
                "path": relative,
                "ownership": "runtime",
                "purpose": f"ADR Kit {path.name} command",
                "invocation": "direct-or-python",
                "expected_mode": "100755",
                "provenance": "declared bin entrypoint",
            })
    direct_scripts = source.get("direct_scripts", [])
    if sum(bool(item.get("task_40_added")) for item in direct_scripts) > 4:
        raise GenerationError("TASK-40 direct-script budget exceeded")
    for item in sorted(direct_scripts, key=lambda value: value["path"]):
        relative = item["path"]
        if (root / relative).is_file():
            entries.append({
                "path": relative,
                "ownership": item["owner"],
                "purpose": item["purpose"],
                "invocation": "python",
                "expected_mode": "100644",
                "provenance": "packaging/executables-source.json",
            })
    return encoded_json({
        "schema_version": 1,
        "provenance": "Generated by scripts/build-client-adapters.py",
        "task_40_added_public_entrypoints": sorted(
            item["path"] for item in direct_scripts if item.get("task_40_added")
        ),
        "entries": sorted(entries, key=lambda item: item["path"]),
    })


def dependencies(source: dict) -> bytes:
    if source.get("runtime") != [] or source.get("policy", {}).get("runtime_dependency_budget") != 0:
        raise GenerationError("ADR Kit runtime dependency set must remain empty")
    if source.get("policy", {}).get("coverage_is_runtime") is not False:
        raise GenerationError("coverage/test tooling cannot be runtime metadata")
    for dependency in source.get("development", []):
        if dependency.get("exact_pin") is not None:
            required = {"compatibility_reason", "review_after", "update_mechanism", "removal_test", "adr"}
            if not required.issubset(dependency):
                raise GenerationError(f"exact dependency pin lacks exception evidence: {dependency.get('name')}")
    return encoded_json({
        "schema_version": 1,
        "provenance": "Generated by scripts/build-client-adapters.py from packaging/dependencies-source.json",
        "runtime": [],
        "development": source.get("development", []),
        "licenses": sorted({item["license"] for item in source.get("development", [])}),
    })
