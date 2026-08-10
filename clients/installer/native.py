"""Native plugin-manager mutations for the three certified clients."""

from __future__ import annotations

import contextlib
import json
import os
import platform
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .contracts import CLIENT_IDS, SPECS
from .detection import Client
from .payload import PREPARED_MARKER

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
MARKETPLACES = {name: SPECS[name].marketplace for name in CLIENT_IDS}

# Per-client flags for `plugin marketplace remove`. Kept beside the installers
# so undo_marketplace_registration and uninstall_client cannot drift apart.
_MARKETPLACE_REMOVE_FLAGS = {
    "claude": ("--scope", "user"),
    "codex": ("--json",),
    "copilot": ("--force",),
}


@contextlib.contextmanager
def undo_marketplace_registration(
    client: Client, *, added: bool, dry_run: bool, runner: Runner
):
    """Remove a marketplace this run registered, if the install then fails.

    TASK-51: all three installers register the marketplace and *then* install
    the plugin. When the second step failed on a first install, the
    registration survived -- the reported half state where the marketplace was
    listed at the new version but `plugin list` said "No plugins installed".

    The generic transaction rollback cannot cover this: it restores the
    PREVIOUS prepared source, so it returns immediately when no `<source>.old`
    exists, which is exactly the first-install case. Only the installer knows
    it was the one that registered the marketplace, so the undo belongs here.

    A failure to undo never masks the original error -- it is reported and the
    original exception propagates, because that error is what the operator
    needs to act on.
    """
    try:
        yield
    except BaseException:
        if added and not dry_run:
            marketplace = MARKETPLACES[client.name]
            flags = _MARKETPLACE_REMOVE_FLAGS[client.name]
            command = [
                client.executable, "plugin", "marketplace", "remove",
                marketplace, *flags,
            ]
            print(f"  undo: removing marketplace registered by this run")
            print(f"  $ {display_command(command)}")
            try:
                result = runner(command)
                if result.returncode:
                    detail = (result.stderr or result.stdout).strip()
                    print(
                        f"  WARNING: could not remove {marketplace}; it is still "
                        f"registered without a working plugin. Remove it manually: "
                        f"{display_command(command)}"
                        + (f" ({detail})" if detail else ""),
                        file=sys.stderr,
                    )
            except OSError as undo_exc:
                print(
                    f"  WARNING: could not remove {marketplace} ({undo_exc}); it is "
                    f"still registered without a working plugin.",
                    file=sys.stderr,
                )
        raise


def display_command(command: Sequence[str], system: str | None = None) -> str:
    return subprocess.list2cmdline(list(command)) if (system or platform.system()) == "Windows" else shlex.join(list(command))


def json_output(result: subprocess.CompletedProcess[str]) -> object:
    try:
        return json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError):
        return None


def require_success(result: subprocess.CompletedProcess[str], description: str) -> None:
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{description} failed ({result.returncode})" + (f": {detail}" if detail else ""))


def _string_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for entry in value for item in _string_values(entry)]
    if isinstance(value, dict):
        return [item for entry in value.values() for item in _string_values(entry)]
    return []


def _normalized_path_text(value: str) -> str:
    return value.replace("\\\\?\\", "").replace("\\", "/").rstrip("/").casefold()


def marketplace_source_matches(value: object, source: Path) -> bool:
    expected = _normalized_path_text(str(source.resolve()))
    return any(
        _normalized_path_text(candidate) == expected or expected in _normalized_path_text(candidate)
        for candidate in _string_values(value)
    )


def claude_marketplace_source_matches(value: object, source: Path) -> bool:
    if marketplace_source_matches(value, source):
        return True
    # Fallback for an older Claude CLI that reports a prepared directory source
    # WITHOUT an explicit path: trust the prepared marker so we do not churn.
    # If the registration DOES carry a path, the mismatch above is authoritative
    # so a version bump (e.g. .../marketplaces/0.36.0 -> .../0.37.0) re-points
    # instead of silently keeping the stale directory and never advancing.
    if isinstance(value, dict) and value.get("source") in {"directory", "local"}:
        has_path = any(
            isinstance(v, str) and ("/" in v or "\\" in v)
            for key, v in value.items()
            if key in {"path", "installLocation", "root", "source"}
        )
        if not has_path and (source / PREPARED_MARKER).is_file():
            return True
    return False


def invoke(
    command: Sequence[str], *, dry_run: bool, runner: Runner
) -> subprocess.CompletedProcess[str]:
    printable = display_command(command)
    print(f"  $ {printable}")
    if dry_run:
        return subprocess.CompletedProcess(command, 0, "", "")
    result = runner(command)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"command failed ({result.returncode}): {printable}\n{detail}")
    return result


def install_claude(
    client: Client, source: Path, dry_run: bool, runner: Runner, desired_version: str | None = None
) -> None:
    listed = runner([client.executable, "plugin", "marketplace", "list", "--json"])
    require_success(listed, "Claude marketplace listing")
    entries = {
        item.get("name"): item
        for item in (json_output(listed) or [])
        if isinstance(item, dict)
    }
    marketplace = entries.get(MARKETPLACES["claude"])
    if marketplace is not None and not claude_marketplace_source_matches(marketplace, source):
        invoke(
            [client.executable, "plugin", "marketplace", "remove", MARKETPLACES["claude"], "--scope", "user"],
            dry_run=dry_run, runner=runner,
        )
        marketplace = None
    added_marketplace = marketplace is None
    if added_marketplace:
        invoke(
            [client.executable, "plugin", "marketplace", "add", str(source), "--scope", "user"],
            dry_run=dry_run, runner=runner,
        )
    with undo_marketplace_registration(
        client, added=added_marketplace, dry_run=dry_run, runner=runner
    ):
        installed = runner([client.executable, "plugin", "list", "--json"])
        require_success(installed, "Claude plugin listing")
        plugin_id = f"adr-kit@{MARKETPLACES['claude']}"
        user_entry = next(
            (
                item for item in (json_output(installed) or [])
                if isinstance(item, dict)
                and item.get("id") == plugin_id
                and item.get("scope", "user") == "user"
            ),
            None,
        )
        user_install = user_entry is not None
        if desired_version and user_entry and user_entry.get("version") == desired_version:
            print(f"  no-op: {plugin_id} {desired_version} is already healthy")
            return
        invoke(
            [client.executable, "plugin", "update" if user_install else "install", plugin_id, "--scope", "user"],
            dry_run=dry_run, runner=runner,
        )


def install_codex(
    client: Client, source: Path, dry_run: bool, runner: Runner, desired_version: str | None = None
) -> None:
    listed = runner([client.executable, "plugin", "marketplace", "list", "--json"])
    require_success(listed, "Codex marketplace listing")
    payload = json_output(listed)
    marketplaces = {
        item.get("name"): item
        for item in (payload or {}).get("marketplaces", [])
        if isinstance(item, dict)
    } if isinstance(payload, dict) else {}
    marketplace = marketplaces.get(MARKETPLACES["codex"])
    installed = runner([client.executable, "plugin", "list", "--json"])
    require_success(installed, "Codex plugin listing")
    payload = json_output(installed)
    plugin_id = f"adr-kit@{MARKETPLACES['codex']}"
    entries = {
        item.get("pluginId"): item
        for item in (payload or {}).get("installed", [])
        if isinstance(item, dict)
    } if isinstance(payload, dict) else {}
    if marketplace is not None and not marketplace_source_matches(marketplace, source):
        if plugin_id in entries:
            invoke([client.executable, "plugin", "remove", plugin_id], dry_run=dry_run, runner=runner)
            entries = {}
        invoke(
            [client.executable, "plugin", "marketplace", "remove", MARKETPLACES["codex"], "--json"],
            dry_run=dry_run, runner=runner,
        )
        marketplace = None
    added_marketplace = marketplace is None
    if added_marketplace:
        invoke(
            [client.executable, "plugin", "marketplace", "add", str(source), "--json"],
            dry_run=dry_run, runner=runner,
        )
    with undo_marketplace_registration(
        client, added=added_marketplace, dry_run=dry_run, runner=runner
    ):
        desired = desired_version or json.loads(
            (source / "codex" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        ).get("version")
        if entries.get(plugin_id, {}).get("version") != desired:
            if plugin_id in entries:
                invoke([client.executable, "plugin", "remove", plugin_id], dry_run=dry_run, runner=runner)
            invoke([client.executable, "plugin", "add", plugin_id, "--json"], dry_run=dry_run, runner=runner)


def copilot_plugin_directory(env: Mapping[str, str] | None = None) -> Path:
    values = os.environ if env is None else env
    home = values.get("COPILOT_HOME")
    root = Path(home) if home else Path.home() / ".copilot"
    return root / "installed-plugins" / MARKETPLACES["copilot"]


def directory_replacement_blocked_by(path: Path) -> str | None:
    """Return why `path` cannot be replaced, or None when it can.

    Copilot upgrades a plugin by replacing its directory, so a directory that
    cannot be renamed cannot be upgraded. Two syscalls before anything is
    touched buy a great deal: without this probe the install fails halfway and
    the rollback takes the client's working registration down with it.
    """
    if not path.is_dir():
        return None
    probe = path.with_name(path.name + ".adr-kit-probe")
    try:
        path.rename(probe)
    except OSError as exc:
        return str(exc)
    try:
        probe.rename(path)
    except OSError as exc:  # pragma: no cover - the lock would have to appear mid-probe
        raise RuntimeError(
            f"probe could not restore {path}; it is now at {probe} and must be renamed back by hand"
        ) from exc
    return None


_LOCKED_PLUGIN_DIRECTORY = """copilot's plugin directory cannot be replaced, so this install would fail
  partway through and leave copilot with less than it has now. Nothing was changed.

    directory: {path}
    reason:    {reason}

  An editor holding the ADR Kit plugin keeps this directory open. VS Code is the
  usual cause: it runs the plugin as an MCP server and keeps handles on the
  plugin directory, which blocks the rename copilot needs. Closing the editor
  window for this project releases them; killing the server process alone does
  not, because the editor restarts it within seconds.

  Close the editor, then run this command again."""


def install_copilot(
    client: Client, source: Path, dry_run: bool, runner: Runner, desired_version: str | None = None
) -> None:
    if not dry_run:
        blocked = directory_replacement_blocked_by(copilot_plugin_directory())
        if blocked:
            raise RuntimeError(
                _LOCKED_PLUGIN_DIRECTORY.format(path=copilot_plugin_directory(), reason=blocked)
            )
    marketplaces = runner([client.executable, "plugin", "marketplace", "list"])
    require_success(marketplaces, "Copilot marketplace listing")
    listing = marketplaces.stdout + marketplaces.stderr
    registered = MARKETPLACES["copilot"] in listing
    if registered and not marketplace_source_matches(listing, source):
        invoke(
            [client.executable, "plugin", "marketplace", "remove", MARKETPLACES["copilot"], "--force"],
            dry_run=dry_run, runner=runner,
        )
        registered = False
    added_marketplace = not registered
    if added_marketplace:
        invoke([client.executable, "plugin", "marketplace", "add", str(source)], dry_run=dry_run, runner=runner)
    with undo_marketplace_registration(
        client, added=added_marketplace, dry_run=dry_run, runner=runner
    ):
        listed = runner([client.executable, "plugin", "list"])
        require_success(listed, "Copilot plugin listing")
        installed = registered and "adr-kit" in (listed.stdout + listed.stderr).lower()
        if installed and desired_version and desired_version in (listed.stdout + listed.stderr):
            print(f"  no-op: adr-kit {desired_version} is already healthy")
            return
        command = (
            [client.executable, "plugin", "update", "adr-kit"]
            if installed
            else [client.executable, "plugin", "install", f"adr-kit@{MARKETPLACES['copilot']}"]
        )
        invoke(command, dry_run=dry_run, runner=runner)


INSTALLERS = {"claude": install_claude, "codex": install_codex, "copilot": install_copilot}


def restore_previous_install(
    name: str, client: Client, source: Path, runner: Runner,
    *, had_plugin: bool, marker_name: str,
) -> None:
    """Put the client back, then prove it is back (TASK-164).

    Reinstalling and reporting success without checking is how copilot was left
    with nothing twice. `had_plugin` comes from the client's own registration
    (TASK-166): a client with nothing to lose is not failed for still having
    nothing.
    """
    previous = source.with_name(source.name + ".old")
    if previous.is_dir():
        marker = json.loads((previous / marker_name).read_text(encoding="utf-8"))
        INSTALLERS[name](client, previous, False, runner, desired_version=marker.get("version"))
    if had_plugin:
        validate_install(name, client, runner)


def validate_install(name: str, client: Client, runner: Runner) -> None:
    result = runner(
        [client.executable, "plugin", "list", "--json"]
        if name in {"claude", "codex"}
        else [client.executable, "plugin", "list"]
    )
    expected = f"adr-kit@{MARKETPLACES[name]}"
    if result.returncode or expected not in (result.stdout + result.stderr):
        raise RuntimeError(f"{name} validation failed: ADR Kit plugin not listed")
    if name in {"codex", "copilot"}:
        mcp = runner([client.executable, "mcp", "list"])
        if mcp.returncode or "adr-kit" not in (mcp.stdout + mcp.stderr):
            raise RuntimeError(f"{name} validation failed: adr-kit MCP server not listed")
    print(f"  validation: PASS ({name})")


def uninstall_client(client: Client, *, dry_run: bool, runner: Runner) -> None:
    name, marketplace = client.name, MARKETPLACES[client.name]
    plugin_id = f"adr-kit@{marketplace}"
    if name == "claude":
        commands = [
            [client.executable, "plugin", "uninstall", plugin_id, "--scope", "user"],
            [client.executable, "plugin", "marketplace", "remove", marketplace, "--scope", "user"],
        ]
    elif name == "codex":
        commands = [
            [client.executable, "plugin", "remove", plugin_id],
            [client.executable, "plugin", "marketplace", "remove", marketplace, "--json"],
        ]
    else:
        commands = [
            [client.executable, "plugin", "uninstall", "adr-kit"],
            [client.executable, "plugin", "marketplace", "remove", marketplace, "--force"],
        ]
    for command in commands:
        result = invoke(command, dry_run=dry_run, runner=runner)
        if not dry_run and result.returncode:
            raise RuntimeError(f"{name} uninstall failed")
