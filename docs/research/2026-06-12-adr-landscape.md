# ADR-tooling landscape research (2026-06-12)

Deep-research naar vergelijkbare ADR-tools en agent-guardrail-patronen, als input voor de
doorontwikkeling van adr-kit richting team-gebruik (meerdere developers + AI coding agents
per repository). Uitgevoerd met een multi-agent research-harness: 5 zoekhoeken, 22 bronnen
gefetcht, 109 claims geëxtraheerd, top-25 adversarieel geverifieerd (3 onafhankelijke
verificatie-agents per claim).

> **Leeswijzer betrouwbaarheid.** Claims gemarkeerd **[geverifieerd 3-0]** zijn door drie
> onafhankelijke agents tegen de primaire bron bevestigd. Claims gemarkeerd
> **[single-source]** komen uit een gefetchte primaire bron (meestal de README) maar de
> adversariële verificatie is niet voltooid door een sessielimiet — ze zijn *niet weerlegd*,
> alleen niet dubbel gecheckt. Eén claim is daadwerkelijk weggestemd en is hier weggelaten.

## 1. Klassiek ADR-tooling-landschap

**[geverifieerd 3-0]** De canonieke catalogus [adr.github.io/adr-tooling](https://adr.github.io/adr-tooling/)
(laatst bijgewerkt 2026-05-11) bevat **geen enkele AI-agent-georiënteerde tool** — geen
Claude Code plugins, editor rules, MCP servers, or LLM features. De catalogus is volledig
georganiseerd rond templates:

- **MADR-tools:** adr-log, ADR Manager, Backstage ADR plugin, Log4brains, pyadr
- **Nygard-tools:** adr-tools (plus ports in C#, Go, Java, Node.js, PHP, PowerShell, Python, Rust), adr-viewer, Loqbooq, Talo
- **Multi-template:** ADG (Nygard/MADR/QOC), ReflectRally

Kanttekening: afwezigheid in deze catalogus bewijst geen afwezigheid in de wereld — de
claim is beperkt tot de catalogus zelf.

**[geverifieerd 3-0]** **Log4brains** (thomvaill, ~1,5k stars) is de meest feature-rijke
klassieke tool: docs-as-code knowledge base die ADRs publiceert als statische website
(GitHub/GitLab Pages, S3), met interactieve CLI, hot-reload preview, zoeken en tijdlijn.
Lifecycle-management is echter beperkt tot **vier handmatig bewerkte statusstrings**
(Proposed/accepted/deprecated/superseded). Geen staleness/drift-detectie, geen enforcement
op codewijzigingen, geen AI op de roadmap. Laatste release v1.1.0 (dec 2024) — feitelijk
slow-moving/dormant.

**[geverifieerd 3-0]** **adr-tools** (npryce, 5,5k stars, 631 forks) is de canonieke
Nygard-traditie shell-CLI. Dormant: laatste release 3.0.0 dateert van **juli 2018**.
Editor-centrische, mens-georiënteerde workflow; geen enforcement, linting of agent-features.

**Conclusie klassiek landschap [geverifieerd, synthese]:** geen enkele bevestigde klassieke
tool biedt diff-enforcement, staleness/drift-detectie, archiverings-automatisering of
AI-agent-integratie — exact de featureset van adr-kit (adr-judge, Guardian, adr-context).

## 2. AI-agent-native ADR-tooling

Alle onderstaande beschrijvingen zijn **[single-source]** tenzij anders vermeld.

### mcp-adr-analysis-server (tosin2013) — meest serieuze adjacente speler

**[handmatig nageverifieerd 2026-06-12 tegen de GitHub-pagina]:**

- TypeScript / Node.js 20+, stdio MCP-transport, **73 MCP-tools**, npm-installeerbaar
- Tree-sitter AST-analyse voor 50+ talen, ripgrep-zoeken, knowledge graph code↔ADR
- "Smart Code Linking": AI-gestuurde koppeling van codebestanden aan ADRs
- Doelclients: lokale MCP-compatibele codeeragents
- Adoptie: **29 stars**, 13 forks, v2.6.8 (mei 2026), actief onderhouden, >80% testdekking
- De README vermeldt **niet**: drift-detectie, staleness-metrics, supersede/archive-lifecycle

Overlap met adr-kit: adr-context (code-linking) en deels adr-suggest. Géén tegenhanger van
adr-judge (diff-enforcement) of Guardian (staleness). Lage adoptie ondanks grote
feature-oppervlakte; de complexiteit (73 tools) is eerder een waarschuwing dan een voorbeeld.

### Claude Code plugins/skills (alle alleen creatie/templating)

| Tool | Features | Lifecycle/enforcement |
|---|---|---|
| dariuszparys/claude-code-toolkit (`adr`-plugin) | `/adr:create` (MADR), lint-hooks (markdownlint), index-regeneratie via adr-log | Geen — leunt op externe Node-tools |
| andronics/claude-plugin-adr | `/adr-create`, `/adr-list`, `/adr-status`, `/adr-link` + decision-recorder skill (auto-invoke bij architectuurdiscussies) | Geen enforcement, geen drift-detectie |
| everything-claude-code ADR-skill (affaan-m) | Nygard-format, sequentiële nummering (0001…), docs/adr-layout met index | Vier-status-veld; geen staleness/archivering |
| ai-software-architect (codenamev) | Markdown AI-architectuurframework, ADR-templates, multi-perspective reviews; Claude-plugin én npm-MCP | Geen lifecycle-management, geen diff-enforcement |

### Niet onderzocht (gefetcht, claims ongeverifieerd — handmatig checken vóór positioneringsclaims)

- joshrotenberg/adrs (Rust-CLI?)
- archcore-ai/cli
- archgate.dev

## 3. Onbeantwoorde onderzoeksvragen

De verificatiefase liep tegen een sessielimiet; deze vragen blijven open:

1. Hoe wiren teams in de praktijk ADRs in agent-guardrails — CLAUDE.md/rules-injectie vs
   MCP-context-servers vs architectural fitness functions (ArchUnit, dependency-cruiser,
   eslint-boundaries) vs spec-driven workflows (spec-kit)? Welke patronen reduceren
   aantoonbaar architectuurdrift?
2. Wat zegt de literatuur over geautomatiseerde decision-drift-detectie en
   staleness/archiverings-beleid? (Bronnen gefetcht maar ongeverifieerd:
   platformtoolsmith.com over ADRs + fitness functions, archgate.dev, spec-kit.)
3. Reële adoptie/kwaliteit van mcp-adr-analysis-server voorbij de README.

## 4. Positionering adr-kit

De combinatie **enforcement (adr-judge) + lifecycle (Guardian/adr-retire) +
context-injectie (adr-context)** is in het geverifieerde klassieke landschap uniek en in
het AI-native landschap minstens zeldzaam. De concurrentie zit óf op creatie/templating
(Claude-plugins), óf op brede analyse zonder lifecycle (mcp-adr-analysis-server). De
grootste bedreiging is niet een bestaande tool maar het tempo van het ecosysteem.

Geïdentificeerde kansen (uitgewerkt in ROADMAP.md):

1. **In-flight guidance** — PostToolUse-hook die tijdens het editen relevante ADRs nudge't
   (dicht het gat tussen SessionStart-context en pre-commit-enforcement).
2. **Dunne MCP-server** (Python, stdio, 4-6 tools) — zelfde guardrails toolneutraal naar
   lokale stdio MCP-clients; bewust contrast met de 73-tools-aanpak.
3. **Team-veilige nummering** — CI-duplicaatcheck + renumber-tool tegen merge-conflicten
   bij parallelle branches/agents.
4. **Guardian team-modus** — CI-cron sweep i.p.v. alleen per-machine SessionStart-state.
5. **Catalogus-aanmelding** — PR naar adr.github.io/adr-tooling; adr-kit zou de eerste
   AI-agent-tool in de canonieke catalogus zijn.

## Bronnen

Primair (hergefetcht/geverifieerd): adr.github.io/adr-tooling · github.com/thomvaill/log4brains ·
github.com/npryce/adr-tools · github.com/tosin2013/mcp-adr-analysis-server

Primair (single-source): github.com/dariuszparys/claude-code-toolkit ·
github.com/andronics/claude-plugin-adr · github.com/affaan-m/everything-claude-code ·
github.com/codenamev/ai-software-architect · github.com/joshrotenberg/adrs ·
github.com/archcore-ai/cli · github.com/github/spec-kit · archgate.dev ·
architecture.lullabot.com

Secundair: techtarget.com (ADR best practices) · icepanel.medium.com ·
platformtoolsmith.com (ADRs + fitness functions) · hidekazu-konishi.com ·
developersvoice.com · angulararchitects.io · aipatternbook.com · verdent.ai (skills vs MCP)
