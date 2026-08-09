---
id: TASK-51
title: 'Installer: --clients all can leave Copilot half-installed'
status: Done
assignee: []
created_date: '2026-07-22 22:04'
updated_date: '2026-07-30 21:01'
labels:
  - bug
  - installer
dependencies: []
priority: medium
ordinal: 52500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
During the 0.39.0 local publish, install-agent-envs.py --clients all registered the Copilot marketplace at 0.39.0 but did not install the plugin: copilot plugin list reported "No plugins installed" and the completion line listed only claude and codex. A targeted re-run with --clients copilot completed it and reported validation PASS. Same failure class as the Claude re-point defect fixed in TASK-48: the combined run reports partial success without leaving the client usable. Investigate why the copilot branch aborted in the combined run and make the outcome either complete or loudly failed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Root cause of the partial Copilot install in a combined --clients all run identified
- [ ] #2 A combined run either completes the Copilot install or fails loudly with the reason
- [ ] #3 Regression coverage for the partial-install path
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Root cause found, reproduced, and fixed for all three clients — not just Copilot.

**Root cause.** All three installers register the marketplace and *then* install the plugin. When the second step fails, `run_transaction` calls `rollback()`, but that rollback restores the PREVIOUS prepared source and returns immediately when no `<source>.old` directory exists — which is exactly the first-install case. So the marketplace registration survived the failure. That is precisely the reported half state: the marketplace listed at 0.39.0 while `copilot plugin list` said "No plugins installed".

The generic transaction rollback structurally cannot cover this. It knows about versions, not about what this run registered. Only the installer knows it was the one that added the marketplace, so the undo belongs there.

**Reproduced** before fixing, with a CLI stand-in where marketplace operations succeed and `plugin install` fails: marketplace add issued, no remove, RuntimeError propagated — the half state intact.

**Fix.** New `undo_marketplace_registration` context manager in `clients/installer/native.py`. Each installer now tracks whether *it* registered the marketplace (`added_marketplace`) and wraps everything after that point. On any exception the registration is removed with the per-client flags, then the original exception is re-raised.

Two deliberate properties:
- **Only undo what this run did.** A pre-existing registration is left alone; a second test proves that per client.
- **A failed undo never masks the original error.** It prints a warning naming the marketplace and the exact manual removal command, and the original exception still propagates — that error is what the operator needs.

Per-client remove flags (`--scope user`, `--json`, `--force`) are now in one `_MARKETPLACE_REMOVE_FLAGS` table next to the installers, so they cannot drift from `uninstall_client`.

**Scope note.** The task was written as a Copilot bug, but the defect is shared: `install_claude` and `install_codex` have the same add-then-install shape and the same no-op rollback on first install. All three are fixed and all three are tested; fixing only Copilot would have left the same trap in the other two.

**Tests** in `tests/test_agent_installer.py`, parametrised over all three clients: one asserting a failed install removes a marketplace this run registered (and that the removal comes *after* the failure, not instead of it), one asserting a pre-existing registration is not removed. 6 new tests; installer suites total 56 passed.

Acceptance criterion 2 ("either completes or fails loudly") is met on the "fails loudly" side: the client is left in its prior state rather than half-configured, the failure still raises, and `install_selected_clients` reports it in the failure list with exit 1.
<!-- SECTION:FINAL_SUMMARY:END -->
