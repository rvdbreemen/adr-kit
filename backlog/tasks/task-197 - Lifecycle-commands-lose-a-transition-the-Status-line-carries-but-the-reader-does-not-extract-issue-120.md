---
id: TASK-197
title: >-
  Lifecycle commands lose a transition the Status line carries but the reader
  does not extract (issue #120)
status: Done
assignee: []
created_date: '2026-08-27 05:53'
updated_date: '2026-08-27 06:16'
labels: []
dependencies: []
references:
  - 'https://github.com/rvdbreemen/adr-kit/issues/120'
  - bin/adr
  - templates/adr-kit-guide.md
priority: high
type: bug
ordinal: 41000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub issue #120. Reproduced 2026-08-27, but only after a first fixture gave a false negative - worth recording, because the shape of the Status line is the whole defect.

WHAT HAPPENS. `ensure_status_history` (bin/adr:372) runs before `set_status_line` precisely so an ADR that predates the status_history convention does not lose its earlier transition when the line is overwritten. It returns early in two cases: a history block already exists (:388), or the recovered transition equals the pending one (:391, commented "Same status on the same day: there is no earlier transition to keep").

`read_status_line` extracts only the LEADING word and the FIRST date. On a real record whose Status line reads

    Superseded by ADR-088, 2026-08-07. Originally Accepted, 2026-05-08.

it returns ("Superseded", "2026-08-07"). That equals the pending transition of a `supersede` repair, so the early return fires, nothing is seeded, and `set_status_line` then replaces the whole line - STATUS_RE captures group 2 as `[^\n]*`.

REPRODUCTION, exit 0, reports `superseded:`:

    'Originally Accepted'  0 occurrences
    '2026-05-08'           0 occurrences
    status_history         1 entry: 2026-08-07 / Superseded

The May acceptance and its attribution are gone, and the history now asserts the ADR's first-ever transition was Superseded.

THE FALSE NEGATIVE, AND WHY IT MATTERS. A first fixture using `Accepted, 2026-05-08. Decision Maker: ...` recovered correctly: two entries, with `changed_by: unknown` and an honest note that the actor was never recorded. The recovery mechanism works. The defect fires only when the leading transition happens to equal the pending one, which is exactly the case a maintainer hits when repairing a record that already claims the transition it is being given.

THE DOCUMENTED CONTRACT DOES NOT COVER THIS. `templates/adr-kit-guide.md` promises: "If the Status line does not yield both a status and a date, the command refuses instead of writing a history that silently omits the earlier transition." Here the line yields both - just not both TRANSITIONS. The promise is written for an unparseable line, not for a line carrying more than the reader reads. The comment at :392 is an inference that holds for one transition and fails for two.

DECIDED WITH THE MAINTAINER, 2026-08-27: option C plus B as a backstop. Always preserve the literal Status line text in the seeded entry's reason, so nothing is lost even when the prose is not parsed into structure; and refuse when the line carries a second date the recovered transition does not account for, because that is the case where the tool demonstrably does not know what it is discarding. Rejected: parsing every transition out of prose, because each shape missed is silent loss again.

The reason field is safe to carry arbitrary prose: history_entry runs it through _yaml_scalar, which quotes anything containing ": " - the guard TASK-70 added after three ADRs in this repository broke their own history block that way.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A seeded recovery entry carries the literal Status line text, so an unparsed transition survives in the record even when it is not structured
- [x] #2 A Status line carrying a second date the recovered transition does not account for makes the command refuse, naming the file and the line rather than rewriting it
- [x] #3 The refusal message tells the maintainer what to do instead, since the case it fires on is a legitimate repair
- [x] #4 The case that already worked keeps working: a line whose leading transition differs from the pending one still seeds a recovered entry
- [x] #5 The reason field survives a Status line containing a colon-space without breaking the status_history block
- [x] #6 Regression tests cover the equal-transition-with-extra-history case, the ordinary recovery case and the quoting case, and fail against the current code
- [x] #7 python -m pytest -q passes
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-27 06:16
---
GEMERGED, EN DE SUITE IS VOOR HET EERST DEZE SESSIE VOLLEDIG SCHOON.

```
1848 passed, 12 skipped in 805.40s
```

Nul failures. Dat is opmerkelijk, want de twee `test_agent_installer`-tests uit TASK-191 faalden vandaag bij elke eerdere volledige run. Ze slaagden nu omdat de maintainer Codex en Copilot had afgesloten en de vijf overgebleven `adr-mcp`-processen waren gestopt - dus stond de live Copilot-installatie niet meer op slot.

Dat is het sluitende bewijs voor de diagnose in TASK-191: die tests falen niet door de code maar door de aanwezigheid van een draaiende client. Bewijs toegevoegd aan dat record.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Issue #120 is gesloten met de combinatie die de maintainer koos: de letterlijke Status-regel bewaren, en weigeren wanneer die regel een tweede transitie draagt. Gemerged in `dev` via PR #139 (`58a27de`).

WAT ER FOUT WAS. `ensure_status_history` zaait de transitie die een ADR alleen op zijn Status-regel draagt, voordat `set_status_line` die regel overschrijft. Maar `read_status_line` neemt het leidende woord en de eerste datum, dus `Superseded by ADR-088, 2026-08-07. Originally Accepted, 2026-05-08.` levert `("Superseded", "2026-08-07")` - gelijk aan de aanstaande transitie van een supersede-reparatie. De gelijkheidscheck keerde vroeg terug, er werd niets gezaaid, en de hele regel werd vervangen. Exit 0, en de acceptatie van mei was weg.

DE FIX, TWEE DELEN. De gezaaide entry draagt de Status-regel nu letterlijk in zijn `reason`, dus wat de parser niet tot structuur kan maken overleeft alsnog - in de fixture redt dat een `Decision Maker`-attributie die in geen enkel veld past. En een tweede datum die de teruggewonnen transitie niet verklaart laat het commando weigeren, met de regel, wat het houdt, wat het zou verliezen en wat de maintainer in plaats daarvan moet doen.

Verworpen: elke transitie uit proza parsen. Elke vorm die zo'n parser mist is opnieuw stil verlies.

`templates/adr-kit-guide.md` documenteerde één weigergrond en documenteert er nu twee. De belofte daar - nooit een historie schrijven die stilzwijgend een eerdere transitie weglaat - was geschreven voor een onleesbare regel, niet voor een regel die meer draagt dan de lezer eruit haalt.

REPRODUCTIE KOSTTE TWEE FIXTURES, en dat hoort in het record. De eerste, met een afwijkende leidende transitie, herstelde correct in twee entries. Dat was een vals negatief: de trigger is niet "twee transities" maar "de leidende transitie is gelijk aan de aanstaande". Pas de letterlijke vorm uit het rapport legde de fout bloot.

VERIFICATIE. Beide regressietests falen aantoonbaar op de oude code met de juiste symptomen: exit 0 en `superseded:` waar een weigering hoort, en een `reason` zonder de regeltekst. De twee #119-tests bleven daarbij groen, wat de juiste discriminatie is. Volledige suite: 1848 passed, 12 skipped, nul failures.
<!-- SECTION:FINAL_SUMMARY:END -->
