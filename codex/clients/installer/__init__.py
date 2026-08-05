"""Desired-state installer support for ADR Kit's three native CLI clients."""

from .contracts import (
    CLIENT_IDS,
    SPECS,
    ClientPlan,
    ClientResult,
    ClientSpec,
    DetectedClient,
    InstallPlan,
)

__all__ = (
    "CLIENT_IDS",
    "SPECS",
    "ClientPlan",
    "ClientResult",
    "ClientSpec",
    "DetectedClient",
    "InstallPlan",
)
