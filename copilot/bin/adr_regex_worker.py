#!/usr/bin/env python3
"""Isolated regex worker for adr-kit policy evaluation.

The parent process owns all timeouts and can terminate this process if CPython's
backtracking regex engine becomes unresponsive.
"""

from __future__ import annotations

import json
import re
import sys


def main() -> int:
    for line in sys.stdin:
        try:
            request = json.loads(line)
            pattern = re.compile(request["pattern"], int(request.get("flags", 0)))
            match = pattern.search(request["text"])
            response = {"ok": True, "matched": match is not None}
        except (KeyError, TypeError, ValueError, re.error) as exc:
            response = {"ok": False, "error": str(exc)}
        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
