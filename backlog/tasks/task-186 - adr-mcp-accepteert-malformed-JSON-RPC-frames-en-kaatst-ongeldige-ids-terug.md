---
id: TASK-186
title: adr-mcp accepteert malformed JSON-RPC frames en kaatst ongeldige ids terug
status: Done
assignee:
  - '@claude'
created_date: '2026-08-23 21:40'
updated_date: '2026-08-26 05:23'
labels:
  - mcp
  - conformance
  - adr-016
dependencies: []
references:
  - >-
    docs/adr/ADR-016-serve-both-mcp-protocol-eras-from-one-hand-rolled-stdio-server.md
  - >-
    https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/index.mdx
  - >-
    https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2026-07-28/schema.ts
modified_files:
  - bin/adr-mcp
  - codex/bin/adr-mcp
  - copilot/bin/adr-mcp
  - tests/test_adr_mcp.py
priority: low
type: bug
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
De stdio-server `bin/adr-mcp` is op vier punten toegeeflijker dan JSON-RPC 2.0 en de MCP-basisprotocolregels toestaan. Op één punt schendt hij de spec in zijn *eigen* uitgaande frame: een `id` die de client meestuurt wordt verbatim teruggekaatst zonder typecontrole, waardoor het antwoord zelf niet meer tegen `JSONRPCResultResponse` valideert.

Geen van de vier breekt een bestaande client — ze maken de server alleen te vergevingsgezind, en een niet-conforme client krijgt stilzwijgend een geldig ogend antwoord in plaats van een bruikbare fout. De waarde van deze taak is dat een spec-afwijking in uitgaande frames de enige categorie is die de tegenpartij niet kan corrigeren.

ALLE VIER GEREPRODUCEERD op v0.54.0 (2026-08-23) door losse frames op stdin te pipen naar `python bin/adr-mcp --root .`:

1. `"id": null` op een verder geldig modern `tools/list` wordt beantwoord met `"id": null` en een volledig resultaat. `basic/index.mdx:47` zegt "the ID MUST NOT be null". Het eigen antwoord faalt daarmee `JSONRPCResultResponse`. Oorzaak: er wordt alleen op aanwezigheid van de sleutel gecontroleerd (`bin/adr-mcp:1023-1024`).
2. `"id": 1.5` en `"id": {"a":1}` worden verbatim teruggekaatst. `schema.ts:261` definieert `RequestId = string | number`; het officiële `schema.json` wijst een object af.
3. Het `jsonrpc`-lid wordt nooit gecontroleerd: een frame zonder `jsonrpc`, of met `"jsonrpc": "1.0"`, wordt normaal bediend en krijgt `"jsonrpc": "2.0"` terug (`bin/adr-mcp:1021-1030`).
4. `io.modelcontextprotocol/clientCapabilities` wordt alleen op aanwezigheid getoetst; de waarde `"nonsense"` (een string) wordt geaccepteerd en `server/discover` slaagt (`bin/adr-mcp:904-908`). `RequestMetaObject` typeert het veld als `ClientCapabilities`; een schema-ongeldige params hoort `-32602` te krijgen.

BUITEN SCOPE — bewust niet oplossen:

* Parse-error- en batch-antwoorden dragen `"id": null` (`bin/adr-mcp:1136,1139`). Dit is een spec-tegen-spec-conflict: `schema.json` laat null niet toe op `JSONRPCErrorResponse.id`, maar JSON-RPC 2.0 §5 verplicht Null wanneer de id onleesbaar is, en `basic/index.mdx:103` staat die uitzondering toe. Geen enkele fix voldoet aan beide. Het huidige gedrag is gepind op `tests/test_adr_mcp.py:207-210` en `:1381-1384`. Laten staan.
* Een `notifications/*`-frame dat een `id` draagt wordt stil genegeerd. Dat is ADR-016's eigen regel ("drops every `notifications/*` frame without replying ... and that behaviour is preserved. It is conformant"), toegepast op een rand die de ADR niet benoemt. Geen onbehandelde afwijking.

ADR-CONTEXT: ADR-016 is bindend (gate `adr-mcp-dual-era-v1`) en eist onder Must Not dat de server geen ongedefinieerde codes in het gereserveerde bereik `-32020..-32099` uitgeeft en geen nieuwe codes in `-32000..-32019` alloceert. `-32600` (Invalid Request) en `-32602` (Invalid params) zijn beide standaard JSON-RPC-codes en vallen buiten die verboden bereiken. ADR-016 eist verder dat `bin/adr-mcp`, `codex/bin/adr-mcp` en `copilot/bin/adr-mcp` byte-identiek blijven: bewerk het canonieke bestand en regenereer met `python scripts/build-client-adapters.py`, bevestig met `--check`.

Meegenomen opruiming: de docstring op `bin/adr-mcp:941` spreekt nog van "the five tools" terwijl er sinds ADR-040 zeven zijn.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Een request met id null wordt afgewezen met JSON-RPC -32600 in plaats van beantwoord met een resultaat dat id null draagt
- [x] #2 Een request met een id die geen string of getal is (float met fractie, object, array, boolean) wordt afgewezen met -32600 en de id wordt niet teruggekaatst
- [x] #3 Een frame zonder jsonrpc-lid of met een andere waarde dan "2.0" wordt afgewezen met -32600
- [x] #4 Een modern gerouteerd request waarvan io.modelcontextprotocol/clientCapabilities geen object is, wordt beantwoord met -32602 dat de ongeldige sleutel benoemt
- [x] #5 Parse-error- en batch-antwoorden blijven id null dragen; de bestaande assertions op tests/test_adr_mcp.py:207-210 en :1381-1384 blijven ongewijzigd slagen
- [x] #6 Een notifications/*-frame met een id blijft stil genegeerd, conform de regel die ADR-016 vastlegt
- [x] #7 Elk nieuw afwijzingspad is gepind in tests/test_adr_mcp.py onder gate adr-mcp-dual-era-v1, inclusief een geval per ongeldig id-type
- [x] #8 De zeven bestaande tools blijven bereikbaar in beide era's en de legacy-handshake blijft ongewijzigd tegenover de vier handshake-revisies
- [x] #9 De docstring op bin/adr-mcp:941 noemt het juiste aantal tools
- [x] #10 python scripts/build-client-adapters.py --check meldt changed=0 en de drie adr-mcp-kopieen zijn byte-identiek
- [x] #11 python -m pytest -q slaagt volledig
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Zelfde branch als TASK-187 (`fix/retire-native-hook-and-jsonrpc-hygiene`): de bestandsverzamelingen zijn disjunct, maar beide taken lopen uit op één regeneratie en één volledige pytest van ~11 minuten. Twee losse commits, zodat de maintainer ze alsnog kan splitsen.

## Onderzoek

`bin/adr-mcp` is identiek op `origin/dev` en op de release-tip, dus de basis maakt hier niet uit.

Alle validatie hoort op één plek: `dispatch()` (`bin/adr-mcp:1021`). Die functie leest nu `req_id = message.get("id")` en `is_notification = "id" not in message` en gaat daarna direct door op `method`. Het `jsonrpc`-lid wordt nergens gelezen. `serve()` (`:1126`) vangt al parse-fouten en niet-objecten af met `id` null; dat blijft ongemoeid.

De envelope-controle zit in `modern_envelope_error()` (`:891`), die vandaag alleen aanwezigheid van de twee `_meta`-sleutels toetst en daarna het type van `protocolVersion`. De `clientCapabilities`-typecontrole hoort daar direct naast, in dezelfde stijl.

## Ontwerpbeslissing die vastlegging verdient: welke ids zijn geldig

De AC eist afwijzing van "float met fractie". Ik wijs **elke** float af, ook een integrale `1.0`. Reden: `schema.json` typeert `RequestId` als `string | integer`, en Python kan een integrale float niet terugkaatsen zonder hem als `1.0` te serialiseren — een niet-integer in ons **eigen** uitgaande frame, precies de fout die deze taak opheft. Normaliseren naar `1` zou de waarde behouden maar de representatie stilzwijgend veranderen, wat JSON-RPC's "MUST be the same as the value of the id member in the Request Object" op de proef stelt. Afwijzen is de enige optie die ons uitgaande frame gegarandeerd geldig houdt. Geen bekende client stuurt een float-id, en JSON-RPC 2.0 zegt zelf "Numbers SHOULD NOT contain fractional parts".

Let op `bool`: `isinstance(True, int)` is `True` in Python, dus booleans moeten expliciet worden uitgesloten.

Geldig blijft dus: `str` of `int`, met uitzondering van `bool`.

## Welke id draagt het foutantwoord

Bij een ongeldige id kan de server de id niet terugkaatsen — dat zou de schending herhalen. Het foutantwoord krijgt daarom `id: null`, exact de conventie die `serve()` al voert voor parse-fouten. Dat is JSON-RPC 2.0 §5 ("If there was an error in detecting the id ... it MUST be Null") en het houdt D6 ongemoeid.

## Stappen

1. In `dispatch()`, vóór alle andere afhandeling: `jsonrpc` moet aanwezig zijn en `"2.0"` luiden, anders `-32600`. Daarna de id-vorm: aanwezig-maar-ongeldig geeft `-32600` met `id: null`.
2. Volgorde is bewust: het `jsonrpc`-lid eerst, want een frame dat niet eens JSON-RPC 2.0 beweert te zijn, verdient geen inhoudelijke beoordeling. Een notification (`id` afwezig) die op één van beide struikelt, krijgt nog steeds geen antwoord — de notificatieregel gaat voor.
3. In `modern_envelope_error()`: `clientCapabilities` moet een object zijn, anders `-32602` met de sleutelnaam erin, in dezelfde stijl als de bestaande `protocolVersion`-controle.
4. Docstring op `:941` en de verouderde "five tool handlers"-comment in `dispatch()` op het juiste aantal brengen.
5. Tests in `tests/test_adr_mcp.py` onder gate `adr-mcp-dual-era-v1`: per ongeldig id-type een geval (null, float met fractie, integrale float, object, array, bool), ontbrekend en verkeerd `jsonrpc`, en `clientCapabilities` als string. Plus een regressie dat een geldige `str`-id en een geldige `int`-id ongemoeid blijven.
6. Regenereren met `python scripts/build-client-adapters.py`, bevestigen met `--check`.

## Risico

De dual-era-poort telt 46 tests over 1401 regels; de legacy-handshake tegenover vier revisies mag niet verschuiven. De nieuwe controles zitten vóór de era-routering, dus ze gelden voor beide era's — dat is bedoeld, want `jsonrpc` en `id` zijn basisprotocol, niet era-specifiek. De bestaande assertions op `:207-210` en `:1381-1384` (parse-error en batch met `id: null`) moeten ongewijzigd blijven slagen; die frames bereiken `dispatch()` niet.
<!-- SECTION:PLAN:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Claude
created: 2026-08-25 23:00
---
VERIFICATIE 2026-08-26 — NIET AFGESLOTEN. De code is geschreven en gemerged, maar zit **niet in `main`**.

Bewijs:
- PR #124 "Retire the native hook binary (ADR-029) and tighten adr-mcp JSON-RPC conformance" is gemerged in **`dev`** op 2026-08-25T22:26:43Z, met base `dev`, niet `main`.
- `git merge-base --is-ancestor 2f41914 origin/main` → **NO**. Dezelfde check tegen `origin/dev` → YES.
- `origin/main` staat op `1f4cc11` = v0.54.0. Dit werk zit in de v0.55.0-lijn.
- Tag `v0.55.0` wijst naar `77278c1` (de `origin/dev`-tip) en is **geen** ancestor van `origin/main`. Er bestaat geen GitHub Release voor v0.55.0; de laatste is v0.54.0.
- De `release-publish.yml`-run op tag v0.55.0 (2026-08-25) rapporteert `failure`.

De taak blijft In Progress tot v0.55.0 in `main` landt. Dat is release-werk, geen implementatiewerk: de ACs #1..#11 zijn inhoudelijk afgehandeld in PR #124, alleen het pad naar `main` ontbreekt nog.
---

author: Claude
created: 2026-08-25 23:05
---
AANVULLING: AC#10 en AC#11 zijn wél bewezen, door CI op PR #124. Het Implementation Plan deelde de branch met TASK-187, wiens notities eindigen met 'Resultaat volgt in deze taak' voor de geïsoleerde pytest-run — dat resultaat is nooit in enig record beland. De PR-checks vullen dat gat:

```
pytest                                pass  2m2s   ← volledige suite (AC#11)
validate                              pass  28s    ← bevat build-client-adapters.py --check (AC#10)
Python 3.10 ubuntu / macos / windows  pass
Python 3.12 ubuntu / macos / windows  pass       ← pytest -q --strict-markers, 6 combinaties
ADR Enforcement (declarative)         pass
generated ADR indexes are up to date  pass
adr-readiness                         pass
adr-lint smoke test on examples/      pass
```

Alle twaalf groen. `dev` heeft `validate` als required context met `enforce_admins: true`, dus de merge kan die niet omzeild hebben.

Voor deze taak is `main` daarmee de enige resterende blokkade — anders dan bij TASK-187, waar AC#5 daarnaast nog een openstaande maintainer-keuze is.
---

author: Claude
created: 2026-08-26 05:23
---
AFGESLOTEN 2026-08-26. De enige resterende blokkade uit comment #1 — de route naar `main` — is weg. Het werk is gepubliceerd als **v0.55.1** (niet v0.55.0; zie TASK-188 voor waarom dat nummer is overgeslagen).

Bewijs uit `origin/main` (= `3b5ca00`), niet uit de branch:

```
$ git show origin/main:bin/adr-mcp | grep -n '32600\|clientCapabilities\|RequestId'
106: CLIENT_CAPABILITIES_META_KEY = "io.modelcontextprotocol/clientCapabilities"
789: INVALID_REQUEST = -32600
845: `RequestId` is `string | number` in schema.ts and `string | integer` in the
```

AC#10 (byte-identiek over de drie trees, ADR-016's eis) is direct getoetst op blob-niveau in plaats van via een checksumvergelijking:

```
8c3f5e443f4e29352e5f33f23c26a7062040dd29  bin/adr-mcp
8c3f5e443f4e29352e5f33f23c26a7062040dd29  codex/bin/adr-mcp
8c3f5e443f4e29352e5f33f23c26a7062040dd29  copilot/bin/adr-mcp
```

Één blob-SHA voor alle drie — dat is byte-identiek per definitie, niet bij benadering.

AC#11 (volledige suite) is tweemaal onafhankelijk bewezen op de release-commit: lokaal `1824 passed, 12 skipped in 683.85s`, en de twaalf checks op PR [#127](https://github.com/rvdbreemen/adr-kit/pull/127) inclusief `pytest` en zes Python 3.10/3.12-combinaties over ubuntu, macos en windows. AC#2 (`build-client-adapters.py --check`, `changed=0`) idem, lokaal en via `validate`.

Release: https://github.com/rvdbreemen/adr-kit/releases/tag/v0.55.1
---
<!-- COMMENTS:END -->
