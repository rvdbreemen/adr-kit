"""Registry and immutable state contracts for the ADR Kit installer."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


ClientId = Literal["claude", "codex", "copilot"]
CLIENT_IDS: tuple[ClientId, ...] = ("claude", "codex", "copilot")


@dataclass(frozen=True)
class ClientSpec:
    id: ClientId
    capability_id: str
    version_marker: str
    marketplace: str
    manifest: str
    native_manager: str
    update_trigger: str


SPECS = {
    spec.id: spec
    for spec in (
        ClientSpec(
            "claude",
            "claude-code-cli",
            "Claude Code",
            "rvdbreemen-adr-kit",
            ".claude-plugin/plugin.json",
            "claude plugin",
            "native-manager-deferred",
        ),
        ClientSpec(
            "codex",
            "codex-cli",
            "codex-cli",
            "rvdbreemen-adr-kit-codex",
            "codex/.codex-plugin/plugin.json",
            "codex plugin",
            "native-manager-deferred",
        ),
        ClientSpec(
            "copilot",
            "github-copilot-cli",
            "GitHub Copilot CLI",
            "rvdbreemen-adr-kit-copilot",
            "copilot/plugin.json",
            "copilot plugin",
            "native-manager-deferred",
        ),
    )
}


@dataclass(frozen=True)
class DetectedClient:
    id: ClientId
    executable: str
    version: str
    config_override: str | None
    native_manager_available: bool
    installed_version: str | None
    source: str | None
    source_sha256: str | None
    legacy_footprints: tuple[str, ...]
    disabled: bool
    trusted: bool | None
    duplicate_roots: tuple[str, ...]

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ClientPlan:
    id: ClientId
    selected: bool
    current_state: str
    desired_state: str
    reason: str
    migrations: tuple[str, ...]
    backups: tuple[str, ...]
    activation: tuple[str, ...]
    validation: tuple[str, ...]
    rollback: tuple[str, ...]
    removals: tuple[str, ...]
    update_trigger: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class InstallPlan:
    schema_version: int
    adr_kit: dict[str, Any]
    settings: dict[str, Any]
    clients: tuple[ClientPlan, ...]
    requires_confirmation: bool

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ClientResult:
    id: ClientId
    status: Literal["noop", "installed", "updated", "removed", "failed", "rolled-back"]
    changed: bool
    evidence_path: str | None = None
    detail: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def require_client_id(value: str) -> ClientId:
    if value not in SPECS:
        raise ValueError(f"unsupported client: {value}")
    return value  # type: ignore[return-value]
