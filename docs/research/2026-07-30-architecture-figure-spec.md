 Specificatie: hoog-over architectuurplaat van adr-kit

Bedoeld om integraal aan een beeldgenererend model (ChatGPT) te geven. Gebaseerd op de
C4-documentatieset in `C4-Documentation/`, de ADR-set in `docs/adr/`, en directe verificatie
in de code. Alle getallen en labels hieronder zijn gemeten, niet geschat.

De spectekst is Nederlands; **alles tussen dubbele aanhalingstekens is een letterlijk te
tekenen label** en moet exact zo in de figuur staan (Engels, want de codebase en ADR's zijn
Engels).

---

## 1. Doel en publiek

Eén A3-liggende plaat die een technische lezer in circa dertig seconden laat zien wat
adr-kit is: een systeem dat architectuurbeslissingen vastlegt als bestanden, en die
beslissingen vervolgens op vier momenten terugduwt naar de mens en de AI-agent die code
schrijven — waarvan er precies één moment kan blokkeren.

De centrale boodschap die de plaat moet overbrengen: **drie lagen sturen (fail-open), één
vloer blokkeert (fail-closed).**

Niet bedoeld als deploymentdiagram. adr-kit is geen service; het is een toolkit die op de
machine van een ontwikkelaar en in CI draait.

## 2. Canvas en stijl

- Formaat: liggend, A3-verhouding (√2:1), of 1920×1200 px.
- Stijl: strak technisch diagram, platte vlakken, geen 3D, geen slagschaduw, geen
  wolkjes-iconografie. Denk aan een goed verzorgd C4-diagram of een figuur uit een
  engineering-paper.
- Typografie: één schreefloze familie. Zone-titels ~20 px, elementlabels ~14 px,
  pijllabels ~11 px cursief, annotaties ~11 px.
- Kleurgebruik functioneel, niet decoratief, en het moet in grijstinden leesbaar blijven:
  - **Blauw** — de engine (deterministische Python-code)
  - **Groen** — data-artefacten (bestanden op schijf)
  - **Amber/oker** — fail-open injectielagen (sturen, blokkeren nooit)
  - **Rood** — de fail-closed vloer (het enige dat blokkeert)
  - **Grijs** — externe systemen en actoren
  - **Paars, gestippelde rand** — optionele of nog niet afgeronde onderdelen
- Pijlen: doorlopend voor synchrone aanroepen, gestippeld voor optionele paden. Elke pijl
  krijgt een label met het *mechanisme*, nooit alleen "gebruikt".

## 3. Lay-out: vijf zones

Verdeel het canvas in vijf horizontale banden. Van boven naar beneden:

```
┌─────────────────────────────────────────────────────────────────────┐
│ ZONE A  (grijs)   Actors                                            │
├─────────────────────────────────────────────────────────────────────┤
│ ZONE B  (amber)   Three fail-open injection tiers                   │
│                                            ┌──────────────────────┐ │
│                                            │ ZONE C (rood)        │ │
│                                            │ Fail-closed floor    │ │
│                                            └──────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│ ZONE D  (blauw)   Deterministic engine                              │
├─────────────────────────────────────────────────────────────────────┤
│ ZONE E  (groen)   Decision store (source of truth)                  │
└─────────────────────────────────────────────────────────────────────┘
```

Zone C is smaller dan Zone B en staat rechts, op dezelfde hoogte als de onderkant van
Zone B, zodat visueel duidelijk is dat de vloer een aparte categorie is naast de drie
tiers — niet een vierde tier.

De belangrijkste visuele regel: **Zone E staat onderaan en alles leest ervan.** De
bestanden zijn het fundament, niet een database aan de zijkant.

---

## 4. Zone A — Actors (bovenste band, grijs)

Vier afgeronde rechthoeken, horizontaal naast elkaar:

1. **"Developer"** — subtitel: *"authors and accepts decisions"*
2. **"AI coding agent"** — subtitel: *"reads constraints, writes code"* — geef deze een
   iets zwaardere rand dan de andere drie; het is een eersteklas gebruiker van dit systeem,
   geen implementatiedetail.
3. **"Reviewer"** — subtitel: *"checks PRs against ADRs"*
4. **"CI"** — subtitel: *"GitHub Actions, 10 workflows"*

Rechts in deze band, visueel losgekoppeld, een kolom van drie kleine grijze blokjes onder
het kopje **"CLI clients"**:

- **"Claude Code"**
- **"Codex CLI"**
- **"GitHub Copilot CLI"**

Onder die kolom, in klein cursief: *"one engine, three generated distributions"*.

## 5. Zone B — Three fail-open injection tiers (amber)

Drie gelijkwaardige blokken naast elkaar. Boven de drie, één doorlopende amberkleurige
balk met de tekst: **"Fail-open: always exit 0 — these steer, they never block"**.

**Tier 1 — "Session tier"**
- hook: `"SessionStart"`
- inhoud: *"guardian staleness nudge + ADR-INDEX.md map"*
- tools: `"adr-guardian"`, `"adr-index"`

**Tier 2 — "Prompt & task tier"**
- hooks: `"UserPromptSubmit"` en pull-toegang
- inhoud: *"ranked governing ADRs for this prompt"*
- tools: `"adr-context"`, `"adr-related"`, `"adr-mcp"` (5 read-only MCP tools)

**Tier 3 — "Edit tier"**
- hooks: `"PreToolUse"` en `"PostToolUse"`, beide met matcher `"Edit|MultiEdit|Write"`
- inhoud: *"injects the governing Decision text before the edit; nudge after"*
- tools: `"adr-watch"`
- klein label bij dit blok: *"token-budgeted, cooldown via .adr-kit-state.json"*

## 6. Zone C — Fail-closed floor (rood, rechts, apart)

Eén rood blok, duidelijk zwaarder omkaderd dan de amberblokken:

- titel: **"Enforcement floor"**
- subtitel: *"the only mechanism that blocks"*
- trigger: `"git pre-commit"` en `"CI action"`
- tool: `"adr-judge"` — met daaronder klein: *"1987 lines, largest single script"*
- twee regels eronder, want dit is de nuance die de plaat eerlijk maakt:
  - *"declarative regex pass — always on, free, fails closed"*
  - *"LLM judge pass — opt-in only (ADR-001)"* — dit tweede regeltje in **paars,
    gestippeld**, want het is niet standaard aan.

## 7. Zone D — Deterministic engine (blauw)

Eén groot blauw kader met de titel **"Deterministic engine — `bin/`"** en daaronder
klein: *"Python 3.10+, stdlib-only by design, 40 executables + 17 shared modules,
~18 400 lines"*.

Binnen dat kader vijf subblokken naast elkaar (dit is het component-niveau; teken géén
losse CLI's):

1. **"Decision Record Engine"** — *"parse, validate, index, migrate; 3 body profiles: canonical / MADR / Nygard"*
2. **"Enforcement & Verification"** — *"4 gates + diff-vs-ADR judging + sandboxed regex"*
3. **"Selective Context Retrieval"** — *"rank ADRs by Enforcement path_glob, then keywords"*
4. **"Health, Guardian & Lifecycle"** — *"staleness, readiness, retirement, doctor"*
5. **"Agent & Client Integration"** — *"MCP server, hooks, installer, skills"*

Onder het blauwe kader, klein cursief en visueel als een voetnoot: *"no third-party runtime
dependencies; `jsonschema` optional and lazily imported"*.

## 8. Zone E — Decision store (onderste band, groen)

Vier groene blokken, elk als een documentsymbool (rechthoek met omgeslagen hoek), zodat
zichtbaar is dat het bestanden zijn:

1. **"docs/adr/ADR-NNN-*.md"** — label: *"source of truth — 16 ADRs, immutable once Accepted"*
2. **"ADR-INDEX.md"** — label: *"compact human/session map"*
3. **"ADR-INDEX.json"** — label: *"node-and-edge graph for agents (ADR-007, ADR-014)"*
4. **".adr-kit-state.json"** — label: *"per-machine cooldown state, gitignored"* — geef dit
   blok een lichtere vulling; het is vluchtige staat, geen kennis.

Binnen elk ADR-blok, of ernaast, drie kleine chips die de secties tonen die de rest van het
systeem machinaal leest: **"## Status"**, **"## Decision"**, **"## Enforcement (JSON)"**.
Dit is belangrijk: het maakt zichtbaar dat een ADR geen vrij proza is maar een contract.

---

## 9. Pijlen — richting en labels

Teken precies deze verbindingen. Elk label letterlijk overnemen.

**Van actors naar het systeem**

| Van | Naar | Label |
|---|---|---|
| "Developer" | "Decision Record Engine" | *"authors ADR via skill / subagent"* |
| "Developer" | Zone C "Enforcement floor" | *"git commit"* |
| "AI coding agent" | Zone B, Tier 2 | *"pulls context (MCP tool call)"* |
| "CI" | Zone C | *"runs judge + readiness on PR"* |
| "Reviewer" | Zone E, ADR-blok | *"reads decisions"* |

**Van de tiers naar de agent — dit is de kern van de plaat**

| Van | Naar | Label |
|---|---|---|
| Tier 1 | "AI coding agent" | *"injects at session start"* |
| Tier 2 | "AI coding agent" | *"injects per prompt"* |
| Tier 3 | "AI coding agent" | *"injects Decision before the edit"* |

Deze drie pijlen wijzen **omhoog**, van Zone B naar Zone A. Dat is de essentie: het systeem
duwt kennis naar de agent toe. Maak ze visueel het opvallendst van alle pijlen — dit is wat
adr-kit doet.

**Zone C blokkeert**

Eén rode pijl van "Enforcement floor" terug naar "Developer", label: *"blocks the commit on
violation"*. Geef deze pijl een dikkere lijn en eventueel een klein stop-symbool. Dit is de
enige pijl in de hele plaat die iets tegenhoudt.

**Naar de engine en de store**

| Van | Naar | Label |
|---|---|---|
| Alle drie tiers (bundel tot één pijl) | Zone D | *"subprocess call"* |
| Zone C | Zone D | *"subprocess call"* |
| Zone D | Zone E | *"reads Markdown + generated index"* |
| "Decision Record Engine" | "ADR-INDEX.md" en "ADR-INDEX.json" | *"generates (bin/adr-index)"* |

**Distributie, rechtsonder als aparte kleine cluster**

| Van | Naar | Label |
|---|---|---|
| Zone D | "CLI clients" kolom | *"projected per client by the installer"* |

Bij die pijl een annotatie in klein cursief: *"36 of 40 engine files byte-identical across
distributions; skills, instructions and schemas are transformed per client"*. Dit is een
gemeten feit en het voorkomt de verkeerde conclusie dat er drie implementaties zijn.

**Externe systemen, rechterrand, grijs**

Drie kleine grijze blokjes met gestippelde pijlen naar binnen:
- **"git"** — *"diff, hooks, worktrees"*
- **"GitHub"** — *"Actions, PR annotations"*
- **"claude CLI"** — gestippeld en **paars**, label: *"optional LLM passes only"*

## 10. Annotaties over de huidige staat

De opdracht was expliciet: erkenning voor wat het systeem *momenteel* is. Plaats daarom
rechtsonder een apart kadertje met de titel **"Current state — known limitations"** en
daarin deze vier regels, letterlijk:

1. *"MCP server still speaks the pre-2026 `initialize` handshake; dual-era support decided in ADR-016 (Accepted) but not yet implemented (TASK-58)"*
2. *"LLM judge and guardian LLM tier are opt-in; a normal commit calls no paid model"*
3. *"Native Rust hook implementations under hooks/native/ are experimental; Python is the shipped path"*
4. *"Four hook events are implemented (session-start, user-prompt-submit, pre-tool-use, post-tool-use) while ADR-004 describes three tiers"*

Dit kader moet visueel rustig zijn — dunne grijze rand, geen alarmkleur. Het is
volwassenheidsinformatie, geen waarschuwing.

## 11. Legenda

Linksonder, compact:

- Blauw = deterministic Python engine
- Groen = file on disk
- Amber = fail-open, steers
- Rood = fail-closed, blocks
- Paars gestippeld = optional or in progress
- Grijs = external system or actor
- Doorlopende pijl = synchronous call · gestippelde pijl = optional path

## 12. Wat expliciet NIET tekenen

- Geen 39 losse CLI-namen. Blijf op componentniveau; de plaat wordt onleesbaar.
- Geen Docker-, Kubernetes- of serversymbolen. Dit systeem wordt niet gedeployed.
- Geen databasecilinder. De opslag is platte Markdown in git; dat is een architecturale
  keuze en moet als bestanden zichtbaar blijven.
- Geen wolk voor "AI". Het model is een actor bovenaan, geen infrastructuur.
- Geen tijdlijn of sequentienummers op de pijlen. Dit is een structuurplaat, geen
  sequencediagram.
- Geen testsuite als apart blok in de hoofdstroom. Vermeld die alleen als voetnoot bij Zone
  D: *"~18 900 lines of tests, larger than the engine itself"*.

## 13. Beoordelingscriterium

De plaat is gelukt als een lezer zonder uitleg de volgende drie vragen kan beantwoorden:

0. Waar leeft de kennis? → de groene bestanden onderaan, in git.
1. Hoe komt die kennis bij degene die code schrijft? → via de drie amberkleurige lagen die
   omhoog duwen.
2. Wat gebeurt er als iemand een beslissing schendt? → de rode vloer houdt de commit tegen,
   en dat is het enige dat tegenhoudt.
#
