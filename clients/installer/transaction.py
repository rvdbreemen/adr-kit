"""Per-client lock, evidence, and rollback primitives."""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

from .contracts import ClientResult


STALE_LOCK_SECONDS = 15 * 60


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


@contextmanager
def client_lock(
    state_root: Path,
    client: str,
    *,
    stale_seconds: float = STALE_LOCK_SECONDS,
) -> Iterator[Path]:
    lock = state_root / "locks" / f"{client}.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        age = time.time() - lock.stat().st_mtime
        if age <= stale_seconds:
            raise RuntimeError(f"{client} installer is already locked: {lock}")
        lock.unlink()
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"{client} installer is already locked: {lock}") from exc
    try:
        os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
        os.close(descriptor)
        yield lock
    finally:
        lock.unlink(missing_ok=True)


def run_transaction(
    client: str,
    *,
    state_root: Path,
    apply: Callable[[], None],
    validate: Callable[[], None],
    rollback: Callable[[], None],
) -> ClientResult:
    evidence = state_root / "evidence" / f"{client}-last-transaction.json"
    started = time.time()
    with client_lock(state_root, client):
        try:
            apply()
            validate()
        except BaseException as exc:
            rollback_error = None
            try:
                rollback()
            except BaseException as rollback_exc:
                rollback_error = str(rollback_exc)
            payload = {
                "schema_version": 1,
                "client": client,
                "status": "rolled-back" if rollback_error is None else "failed",
                "error": str(exc),
                "rollback_error": rollback_error,
                "started_at_epoch": started,
                "finished_at_epoch": time.time(),
            }
            _atomic_json(evidence, payload)
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(
                f"{client} activation failed; rollback "
                f"{'completed' if rollback_error is None else 'failed'}: {exc}"
            ) from exc
        _atomic_json(
            evidence,
            {
                "schema_version": 1,
                "client": client,
                "status": "healthy",
                "started_at_epoch": started,
                "finished_at_epoch": time.time(),
            },
        )
    return ClientResult(client, "updated", True, str(evidence))
