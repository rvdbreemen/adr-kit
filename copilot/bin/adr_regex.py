"""Killable, bounded regex evaluation for repository-authored policy."""

from __future__ import annotations

import atexit
import json
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional


DEFAULT_REGEX_TIMEOUT_SECONDS = 1.0
DEFAULT_REGEX_INPUT_BYTES = 2 * 1024 * 1024
DEFAULT_REGEX_PATTERN_CHARS = 4096


class RegexEvaluationError(RuntimeError):
    """Base error for a regex that could not be evaluated safely."""


class RegexTimeoutError(RegexEvaluationError):
    """Raised when an isolated regex exceeds its wall-clock budget."""


class RegexBudgetError(RegexEvaluationError):
    """Raised when regex pattern or input exceeds its deterministic budget."""


class RegexEvaluator:
    """One persistent worker process, restarted after timeout or failure."""

    def __init__(
        self,
        *,
        timeout_seconds: float = DEFAULT_REGEX_TIMEOUT_SECONDS,
        max_input_bytes: int = DEFAULT_REGEX_INPUT_BYTES,
        max_pattern_chars: int = DEFAULT_REGEX_PATTERN_CHARS,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_input_bytes = max_input_bytes
        self.max_pattern_chars = max_pattern_chars
        self._process: Optional[subprocess.Popen[str]] = None
        self._responses: "queue.Queue[Optional[str]]" = queue.Queue()

    def _start(self) -> None:
        worker = Path(__file__).resolve().with_name("adr_regex_worker.py")
        self._responses = queue.Queue()
        self._process = subprocess.Popen(
            [sys.executable, str(worker)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert self._process.stdout is not None
        # Capture stdout and the response queue as locals so that if the
        # evaluator is restarted (e.g. after a timeout), the old reader thread
        # puts its sentinel None into the *old* queue rather than the new one.
        _stdout = self._process.stdout
        _responses: "queue.Queue[Optional[str]]" = self._responses

        def _read() -> None:
            for response in _stdout:
                _responses.put(response)
            _responses.put(None)

        threading.Thread(target=_read, daemon=True).start()

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        try:
            process.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def _terminate(self) -> None:
        process = self._process
        self._process = None
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()

    def search(self, pattern: str, text: str, flags: int = 0) -> bool:
        if len(pattern) > self.max_pattern_chars:
            raise RegexBudgetError(
                f"pattern length {len(pattern)} exceeds {self.max_pattern_chars} characters"
            )
        input_bytes = len(text.encode("utf-8", errors="replace"))
        if input_bytes > self.max_input_bytes:
            raise RegexBudgetError(
                f"input size {input_bytes} exceeds {self.max_input_bytes} bytes"
            )
        if self._process is None or self._process.poll() is not None:
            self._start()
        assert self._process is not None
        assert self._process.stdin is not None
        request = json.dumps(
            {"pattern": pattern, "text": text, "flags": flags},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        try:
            self._process.stdin.write(request + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            self._terminate()
            raise RegexEvaluationError(f"isolated regex worker failed: {exc}") from exc
        try:
            response_line = self._responses.get(timeout=self.timeout_seconds)
        except queue.Empty as exc:
            self._terminate()
            raise RegexTimeoutError(
                f"regex exceeded {self.timeout_seconds:.3f}s wall-clock budget"
            ) from exc
        if response_line is None:
            self._terminate()
            raise RegexEvaluationError("isolated regex worker exited unexpectedly")
        try:
            response = json.loads(response_line)
        except json.JSONDecodeError as exc:
            self._terminate()
            raise RegexEvaluationError(
                "isolated regex worker returned invalid JSON"
            ) from exc
        if not response.get("ok"):
            raise RegexEvaluationError(
                f"isolated regex worker rejected pattern: {response.get('error', 'unknown error')}"
            )
        return bool(response.get("matched"))


_DEFAULT_EVALUATOR: Optional[RegexEvaluator] = None


def bounded_regex_search(pattern: str, text: str, flags: int = 0) -> bool:
    """Search in an isolated process with fixed input and wall-clock budgets."""
    global _DEFAULT_EVALUATOR
    if _DEFAULT_EVALUATOR is None:
        _DEFAULT_EVALUATOR = RegexEvaluator()
    return _DEFAULT_EVALUATOR.search(pattern, text, flags)


def _close_default() -> None:
    global _DEFAULT_EVALUATOR
    if _DEFAULT_EVALUATOR is not None:
        _DEFAULT_EVALUATOR.close()
        _DEFAULT_EVALUATOR = None


atexit.register(_close_default)
