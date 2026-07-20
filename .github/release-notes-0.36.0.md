# ADR Kit v0.36.0

ADR Kit v0.36.0 delivers one certified native governance experience for Claude
Code CLI, OpenAI Codex CLI, and GitHub Copilot CLI.

## Highlights

- One canonical set of 14 ADR workflows generates optimized native skills and
  prompts for all three supported clients.
- Client-native manifests, fail-open hooks, and key-free MCP declarations
  preserve each CLI's real discovery and lifecycle contracts.
- The idempotent installer detects installed clients, presents its plan,
  prepares a verified local payload, supports stable updates and rollback, and
  preserves unrelated user configuration.
- Fast and deep doctor modes diagnose generated drift, settings, client
  registration, MCP, hooks, latency, and optional local-model judgment.
- Windows-native hook and generator performance are release gates. The
  deterministic generator's warm no-op path performs zero content rewrites.
- Native evidence for all three clients is bound to the exact candidate commit
  and prepared payload. Release automation consumes separately retained
  evidence to avoid a self-referential candidate hash.

## Scope and compatibility

The current first-class scope is exactly Claude Code CLI, Codex CLI, and GitHub
Copilot CLI. Windows is the certified native baseline. macOS and Linux are
best-effort, and wider coding-agent support remains deferred to TASK-43.

ADR Kit retains its zero-runtime-dependency policy and supports Python 3.10 and
newer. Paid or cloud model judgment remains explicit opt-in.

## Verification

- Full repository suite: 746 passed, 6 expected skips.
- Strict ADR lint and generated ADR indexes: pass.
- Generated client adapter drift: clean.
- Windows generator benchmark: clean p95 735.485 ms; warm no-op p95 60.974 ms;
  zero warm writes.
- The stable release is published only after the all-three native Windows
  certification workflow passes for the exact candidate.
