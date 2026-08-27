---
id: TASK-191
title: Two agent-installer tests reach the live Copilot install instead of tmp_path
status: To Do
assignee: []
created_date: '2026-08-26 19:46'
updated_date: '2026-08-27 06:17'
labels: []
dependencies: []
references:
  - tests/test_agent_installer.py
  - clients/installer/native.py
priority: medium
type: bug
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`tests/test_agent_installer.py::test_rollback_proves_the_client_is_back_before_reporting_success` and `::test_failed_install_removes_a_marketplace_this_run_registered[copilot]` fail on a developer machine that has GitHub Copilot CLI installed with the adr-kit plugin, and pass in CI.

REPRODUCED 2026-08-26, and proven independent of any working-tree change: both fail identically on a clean `git worktree` of `origin/dev` (`66701a3`) with nothing applied.

The failure names a path on the machine itself, not a temporary directory:

```
RuntimeError: copilot's plugin directory cannot be replaced, so this install would fail
  partway through and leave copilot with less than it has now. Nothing was changed.

    directory: C:\Users\rvdbr\.copilot\installed-plugins\rvdbreemen-adr-kit-copilot
    reason:    [WinError 5] Access is denied
```

Both tests assert with `pytest.raises(RuntimeError, match=...)` on a message the fake runner is supposed to produce ("install failed: boom", "validation failed"). The real installer reaches the live plugin directory first, raises its own well-written diagnostic about a held directory, and the `match` fails. The test is red for a reason that has nothing to do with the code under test.

WHY THIS MATTERS MORE THAN A FLAKY TEST. CI passes because the runner has no Copilot install, so the suite is green on the one machine that cannot exercise this path and red on the machines that can. That is the inverse of the usual trap: not a test that is green under conditions masking a defect, but a test that is red under conditions that prove nothing. Either way the signal is worthless, and a developer learns to ignore two failures - which is how a real one gets ignored too.

The same class of defect bit the release on 2026-08-26 from the other side: `install-agent-envs.py --clients codex` failed with `os error 32` because a live `adr-mcp` process held the plugin cache as its working directory (TASK-188). Live client state and this test suite are entangled.

SUGGESTED DIRECTION, not a decision: the fake runner should be reached before any real filesystem probe, or the probe target should come from the injected source rather than the resolved user path. Whoever picks this up should first establish which of the two the installer's design intends, because that determines whether this is a test bug or a seam the installer is missing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Both tests pass on a machine with GitHub Copilot CLI installed and the adr-kit plugin present
- [ ] #2 Neither test reads or writes any path under the developer's home directory; the probe target is injected
- [ ] #3 The failure is reproduced before the fix is designed, and the record states whether the defect was in the test or in a missing seam in the installer
- [ ] #4 python -m pytest -q tests/test_agent_installer.py passes locally and in CI
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-27 06:17
---
BEWIJS DAT DE DIAGNOSE KLOPT, uit een run die niemand daarvoor opzette.

Op 2026-08-27 draaide de volledige suite vier keer. De eerste drie keer faalden deze twee tests. De vierde keer, na afloop van de v0.56.0-release, slaagden ze:

```
run 1   2 failed, 1824 passed   Codex en Copilot draaiden
run 2   9 failed, 1837 passed   idem, plus gelijktijdigheidsartefacten
run 3   2 failed, 1844 passed   idem
run 4   0 failed, 1848 passed   Codex en Copilot afgesloten, adr-mcp-processen gestopt
```

De enige variabele tussen run 3 en run 4 is dat de maintainer Codex en Copilot had afgesloten en dat vijf `adr-mcp`-processen - kinderen van de draaiende `codex.exe` - waren gestopt. Er is geen regel code gewijzigd die deze tests raakt.

Dat maakt het een gecontroleerd experiment in plaats van een vermoeden: deze twee tests meten of er een client draait, niet of de code werkt. Ze zijn groen op CI omdat de runner geen Copilot-installatie heeft, en rood op elke ontwikkelmachine die er wel een heeft.

EEN TWEEDE BEVINDING VOOR DEZELFDE SCOPE. Tijdens de v0.56.0-install meldde de codex-poging `rollback error: codex validation failed: adr-kit MCP server not listed`. Dat leest als schade van de rollback, maar `codex plugin list` toonde adr-kit onveranderd als `installed, enabled`. De rollback-validatie faalde omdat de MCP-server niet kon antwoorden terwijl zijn eigen map op slot zat. De installatie was intact; alleen de boodschap suggereerde het tegendeel. Een foutpad dat een niet-bestaande schade meldt kost een maintainer net zoveel tijd als een echte.
---
<!-- COMMENTS:END -->
