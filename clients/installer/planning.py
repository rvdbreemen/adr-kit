"""Deterministic desired-state planning and rendering."""

from __future__ import annotations

import json
from pathlib import Path

from .contracts import CLIENT_IDS, SPECS, ClientPlan, DetectedClient, InstallPlan


def build_plan(
    detected: dict[str, DetectedClient],
    *,
    source: Path,
    version: str,
    source_sha256: str,
    effective_settings: dict,
    requested: tuple[str, ...] | None = None,
    remove: bool = False,
) -> InstallPlan:
    requested_set = set(requested) if requested is not None else None
    clients: list[ClientPlan] = []
    requires_confirmation = False
    for name in CLIENT_IDS:
        state = detected.get(name)
        setting = effective_settings["clients"][name]["enabled"]
        selected = state is not None and setting is not False
        if requested_set is not None:
            selected = name in requested_set
        current = "absent" if state is None else (
            f"installed:{state.installed_version}" if state.installed_version else "detected"
        )
        desired = "removed" if remove else (f"installed:{version}" if selected else current)
        migrations: tuple[str, ...] = ()
        if state and state.installed_version and state.installed_version.split(".", 1)[0] != version.split(".", 1)[0]:
            migrations = (f"major-version:{state.installed_version}->{version}",)
            requires_confirmation = True
        clients.append(
            ClientPlan(
                id=SPECS[name].id,
                selected=selected,
                current_state=current,
                desired_state=desired,
                reason=(
                    "explicit selection"
                    if requested_set is not None
                    else "detected and enabled"
                    if selected
                    else "not detected or opted out"
                ),
                migrations=migrations,
                backups=("client registration", "prepared payload") if selected else (),
                activation=("native plugin manager",) if selected and not remove else (),
                validation=("manifest", "digest", "MCP initialize/tools-list", "plugin list") if selected and not remove else (),
                rollback=("restore previous healthy registration",) if selected else (),
                removals=("ADR Kit-owned registration and generated payload",) if remove and selected else (),
                update_trigger=SPECS[name].update_trigger,
            )
        )
    return InstallPlan(
        schema_version=1,
        adr_kit={
            "version": version,
            "source": str(source.resolve()),
            "source_sha256": source_sha256,
        },
        settings=effective_settings,
        clients=tuple(clients),
        requires_confirmation=requires_confirmation,
    )


def render_plan(plan: InstallPlan, *, format: str = "human") -> str:
    payload = plan.as_dict()
    if format == "json":
        return json.dumps(payload, indent=2, sort_keys=True)
    lines = [
        f"ADR Kit {plan.adr_kit['version']} desired-state plan",
        f"Source: {plan.adr_kit['source']}",
    ]
    for client in plan.clients:
        marker = "SELECTED" if client.selected else "SKIP"
        lines.append(
            f"{client.id}: {marker}; {client.current_state} -> "
            f"{client.desired_state}; {client.reason}"
        )
        for label, values in (
            ("migrations", client.migrations),
            ("backups", client.backups),
            ("activation", client.activation),
            ("validation", client.validation),
            ("rollback", client.rollback),
            ("removals", client.removals),
        ):
            lines.append(f"  {label}: {', '.join(values) if values else '(none)'}")
    if plan.requires_confirmation:
        lines.append("Confirmation required: breaking-version migration.")
    return "\n".join(lines)
