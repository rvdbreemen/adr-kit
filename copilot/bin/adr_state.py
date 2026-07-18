"""Cross-platform transactional JSON state updates for adr-kit hooks."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple, TypeVar


T = TypeVar("T")
StateMutation = Callable[[Dict], Tuple[bool, T]]


class StateLockTimeout(OSError):
    """Raised when a state transaction cannot acquire its cross-process lock."""


@contextlib.contextmanager
def state_lock(state_path: Path, timeout_seconds: float = 2.0):
    """Hold an exclusive cross-process lock for a complete state transaction."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.parent / f"{state_path.name}.lock"
    handle = open(lock_path, "a+b")
    deadline = time.monotonic() + timeout_seconds
    mechanism = None
    try:
        while mechanism is None:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                mechanism = "fcntl"
            except ImportError:
                try:
                    import msvcrt

                    handle.seek(0, os.SEEK_END)
                    if handle.tell() == 0:
                        handle.write(b"\0")
                        handle.flush()
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    mechanism = "msvcrt"
                except OSError:
                    pass
            except OSError:
                pass

            if mechanism is None:
                if time.monotonic() >= deadline:
                    raise StateLockTimeout(
                        f"timed out locking state file {state_path}"
                    )
                time.sleep(0.01)
        yield
    finally:
        if mechanism == "fcntl":
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        elif mechanism == "msvcrt":
            try:
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        handle.close()


def load_state(
    state_path: Path,
    default_factory: Callable[[], Dict],
    warning: Optional[Callable[[str], None]] = None,
) -> Dict:
    """Load one JSON object, returning a fresh default on missing/corrupt data."""
    if not state_path.exists():
        return default_factory()
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("state root is not a JSON object")
        return data
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        if warning is not None:
            warning(
                f"state file {state_path} unreadable or corrupt "
                f"({exc.__class__.__name__}); treating as empty state"
            )
        return default_factory()


def atomic_save_state(state_path: Path, state: Dict) -> None:
    """Atomically replace state using a unique same-directory temporary file."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=state_path.parent,
            prefix=f".{state_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(state, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        os.replace(temp_path, state_path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def update_state(
    state_path: Path,
    default_factory: Callable[[], Dict],
    mutation: StateMutation[T],
    warning: Optional[Callable[[str], None]] = None,
    timeout_seconds: float = 2.0,
) -> Optional[T]:
    """Lock, load, mutate, and optionally save state as one transaction."""
    try:
        with state_lock(state_path, timeout_seconds=timeout_seconds):
            state = load_state(state_path, default_factory, warning)
            dirty, result = mutation(state)
            if dirty:
                atomic_save_state(state_path, state)
            return result
    except (OSError, StateLockTimeout) as exc:
        if warning is not None:
            warning(f"state update skipped: {exc}")
        return None
