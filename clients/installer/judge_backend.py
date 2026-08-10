"""Record the machine-local judge host client at install time.

ADR-036 keeps ADR-017's resolution rule: ``judge.backend`` resolves to the host
client's CLI *recorded at install time*. The client is knowable here and only
here - a ``git commit`` is client-agnostic, it happens whether or not any agent
is running - so an install that skips this leaves the LLM half of the gate
silently off, which is what TASK-169 found on the reference machine.

What this module will not do is guess. ADR-017 refused to probe ``PATH``
because on a machine carrying all three CLIs the probe order would decide which
vendor receives the repository diff, and that is a privacy decision made by
accident. The same argument applies to a run installing several clients at
once: there is no non-arbitrary winner, so the operator is told how to choose
rather than having one chosen for them.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]

LOCAL_CONFIG_NAME = ".adr-kit.local.json"

# The installer speaks client names; the judge speaks client ids.
HOST_CLIENT_IDS = {
    "claude": "claude-code-cli",
    "codex": "codex-cli",
    "copilot": "github-copilot-cli",
}


def recorded_host_client(adr_dir: Path) -> str | None:
    """Read the recorded client, treating any unreadable file as unrecorded."""
    try:
        document = json.loads((adr_dir / LOCAL_CONFIG_NAME).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    judge = document.get("judge") if isinstance(document, dict) else None
    client = judge.get("host_client") if isinstance(judge, dict) else None
    return client if isinstance(client, str) and client else None


def _choose_command(adr_dir: Path, source: Path, client_id: str) -> str:
    return (
        f'python "{source / "bin" / "adr-judge"}" --adr-dir "{adr_dir}" '
        f"--record-host-client {client_id}"
    )


def record_host_client(
    source: Path,
    project_root: Path,
    installed: Sequence[str],
    *,
    runner: Runner,
    dry_run: bool = False,
) -> str | None:
    """Record the host client when this run leaves exactly one candidate.

    Returns the recorded client id, or None when nothing was written.
    """
    adr_dir = project_root / "docs" / "adr"
    if not adr_dir.is_dir() or not installed:
        return None

    existing = recorded_host_client(adr_dir)
    if existing:
        # An operator's recorded choice outranks anything an install infers.
        return None

    candidates = [name for name in installed if name in HOST_CLIENT_IDS]
    if len(candidates) != 1:
        print(
            "Judge host client: not recorded, because this run installed "
            + ", ".join(candidates)
            + " and picking one would decide which vendor sees your diffs. "
            "Record the client you commit from:"
        )
        for name in candidates:
            print(f"  {_choose_command(adr_dir, source, HOST_CLIENT_IDS[name])}")
        return None

    client_id = HOST_CLIENT_IDS[candidates[0]]
    if dry_run:
        print(f"Judge host client: would record {client_id} in {adr_dir / LOCAL_CONFIG_NAME}")
        return None

    result = runner(
        [
            sys.executable,
            str(source / "bin" / "adr-judge"),
            "--adr-dir",
            str(adr_dir),
            "--record-host-client",
            client_id,
        ]
    )
    if result.returncode:
        print(
            "  warning: the judge host client could not be recorded; the install "
            "remains valid but the LLM pass will stay off until you run:\n"
            f"  {_choose_command(adr_dir, source, client_id)}",
            file=sys.stderr,
        )
        return None
    print(f"Judge host client: recorded {client_id} for {adr_dir}")
    return client_id
