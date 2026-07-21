# ADR Grilling benchmark report

## Certification environment

- Date: 2026-07-20
- Platform: Windows 11 `10.0.26200`
- Python: CPython 3.12.9
- Samples: 30 warm samples per path
- Fixture: 50 Proposed ADRs; linkage adds 500 changed paths
- Clock: injected as `2026-07-20`
- Command: `python scripts/benchmark-adr-grilling.py --samples 30`

## Readiness, linkage and MCP

| Path | p50 | p95 | maximum | Budget | Result |
|---|---:|---:|---:|---:|---|
| Readiness core, 50 ADRs | 51.880 ms | 66.246 ms | 71.654 ms | p95 <= 100 ms | PASS |
| Linkage, 500 unique paths / 50 ADRs | 136.527 ms | 150.444 ms | 160.457 ms | p95 <= 250 ms, max <= 1 s | PASS |
| Single-ADR CLI | 283.670 ms | 305.961 ms | 307.396 ms | p95 <= 500 ms | PASS |
| All-Proposed CLI | 269.565 ms | 314.849 ms | 357.927 ms | p95 <= 1 s, max <= 2 s | PASS |
| Persistent MCP, all Proposed | 281.059 ms | 336.830 ms | 358.672 ms | <= 100 ms adapter overhead | PASS |
| PR readiness action, 500 unique paths / 50 ADRs | 911.954 ms | 1,150.890 ms | 1,619.274 ms | p95 <= 5 s | PASS |

Measured MCP adapter overhead was 21.981 ms against the separately sampled CLI
p95. The persistent server benchmark excludes server startup, as the MCP
contract serves multiple calls per process.

## Existing-command comparison

| Existing command | p50 | p95 | maximum |
|---|---:|---:|---:|
| `adr-status` | 230.560 ms | 280.112 ms | 300.620 ms |
| `adr-context` | 285.727 ms | 315.880 ms | 347.875 ms |

The readiness CLI is in the same process-startup envelope as the existing
commands. The core and 500-path linkage operations remain below their tighter
in-process budgets. The script exits non-zero when a budget fails, so CI can
reuse the same deterministic certification.

The PR-action fixture uses two real commits and 500 distinct changed source
files. Each file explicitly cites one of the 50 Proposed ADRs, exercising the
same detached-SHA comparison and blocking-report path used by GitHub Actions.

Compared with the first accepted 30-sample feature baseline, p95 changed by
-2.5 percent for core, +0.8 percent for linkage, +3.1 percent for single-ADR
CLI, -9.8 percent for all-Proposed CLI, +8.6 percent for persistent MCP,
+11.2 percent for `adr-status`, and +1.1 percent for `adr-context`. Every
existing measured path therefore remains inside the 20 percent regression
limit. The CI action is new and is assessed against its absolute budget.

## SessionStart cache path

The Windows native host was rebuilt from `hooks/native/adr-hook.rs` and measured
with the derived readiness cache present:

| Path | Samples | p50 | p95 | maximum | Budget | Result |
|---|---:|---:|---:|---:|---:|---|
| SessionStart native host | 30 | 31.216 ms | 36.169 ms | 43.067 ms | p50 <= 50 ms, p95 <= 150 ms, hard <= 500 ms | PASS |

Command:

```powershell
python bin/adr-guardian refresh-readiness --project-root . --today 2026-07-20
# hooks.hook_benchmark.measure(..., samples=30)
```

The measurement includes process startup and a warm filesystem. Other hook
events received no new readiness calculation or subprocess; their p95 and hard
budgets remained green in the same run. Some 25/30 ms p50 targets showed the
already-recorded Windows process-floor variance, while the changed SessionStart
path passed every target with substantial headroom.

After the index-only edit advisory was added, a second 30-sample run recorded:

| Event | p50 | p95 | maximum | Effective result |
|---|---:|---:|---:|---|
| SessionStart | 31.412 ms | 37.563 ms | 37.956 ms | PASS |
| UserPromptSubmit | 29.874 ms | 35.224 ms | 35.269 ms | PASS |
| SubagentStart | 28.948 ms | 34.059 ms | 42.055 ms | PASS |
| PreToolUse | 29.135 ms | 35.690 ms | 35.763 ms | PASS with documented 20% CI variance |
| PostToolUse | 29.336 ms | 35.993 ms | 39.393 ms | PASS with documented 20% CI variance |
| PreCompact | 32.021 ms | 42.142 ms | 43.432 ms | PASS with documented 20% CI variance |
| Stop | 22.561 ms | 26.624 ms | 42.921 ms | PASS |

All p95 and hard limits passed directly. The three p50 observations above the
nominal target remained within the method's pre-existing 20% CI variance
allowance and the recorded Windows process-creation floor. No timeout occurred.
The single pre-commit signal subprocess measured p50 444.398 ms, p95 616.388
ms, and maximum 721.188 ms, well below the existing 5-second warning threshold.

## Three-client artifact generation

The canonical model now contains 15 workflows and generates the Claude, Codex,
and Copilot payloads. The same Windows host ran 30 clean and 30 persistent
warm-no-op samples:

| State | Files | Bytes | p50 | p95 | maximum | Budget | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| Clean full generation | 218 written | 1,961,611 written | 845.074 ms | 896.896 ms | 925.082 ms | p95 <= 2 s; max <= 5 s | PASS |
| Warm unchanged | 0 read / 0 written | 0 read / 0 written | 112.585 ms | 128.694 ms | 141.799 ms | p95 <= 500 ms; max <= 1 s; zero writes | PASS |

The approved pre-feature p95 regression thresholds are 1,000 ms clean and
150 ms warm, with 20 percent variance allowed. Clean p95 is 10.31 percent below
that reference and warm p95 is 14.20 percent below it, so neither path regressed
by more than 20 percent. Standalone Python startup in the same run measured
p50 161.551 ms and p95 192.647 ms. Peak traced generator memory was 617,105
bytes.

Command:

```powershell
python scripts/benchmark-client-generation.py --samples 30
```
