# ADR Grilling Backlog task map

Created: 2026-07-20

Milestone: `ADR Grilling`

## Epic

| ID | Title | Status |
|---|---|---|
| TASK-45 | EPIC: Grilling for ADRs across the complete ADR lifecycle | Done |

## Child tasks

| Wave | ID | Title | Dependencies |
|---:|---|---|---|
| 1 | TASK-45.1 | Record the ADR Grilling architecture and public contracts | — |
| 2 | TASK-45.2 | Build the deterministic ADR readiness domain model | TASK-45.1 |
| 2 | TASK-45.3 | Add semantic Open Questions support to ADR profiles | TASK-45.1 |
| 3 | TASK-45.4 | Add the read-only adr-readiness CLI | TASK-45.2, TASK-45.3 |
| 3 | TASK-45.5 | Detect deterministic implementation links to Proposed ADRs | TASK-45.2 |
| 4 | TASK-45.6 | Expose readiness through the key-free MCP server | TASK-45.4, TASK-45.5 |
| 4 | TASK-45.7 | Implement the canonical adr-kit grilling workflow | TASK-45.3, TASK-45.4 |
| 5 | TASK-45.8 | Integrate grilling into ADR authoring and acceptance | TASK-45.7 |
| 6 | TASK-45.9 | Add adaptive reconstruction grilling to adr-kit init | TASK-45.8 |
| 6 | TASK-45.10 | Integrate grilling into review and judge workflows | TASK-45.5, TASK-45.8 |
| 6 | TASK-45.11 | Manage Proposed ADRs as an active guardian work queue | TASK-45.4, TASK-45.8 |
| 6 | TASK-45.12 | Add grilling to supersede, retire and revalidation flows | TASK-45.8 |
| 7 | TASK-45.13 | Add advisory grilling signals to hooks and pre-commit | TASK-45.5, TASK-45.7 |
| 7 | TASK-45.14 | Add deterministic PR readiness reporting and merge gate | TASK-45.4, TASK-45.5, TASK-45.8 |
| 8 | TASK-45.15 | Certify, document and release ADR Grilling end to end | TASK-45.6, TASK-45.9, TASK-45.10, TASK-45.11, TASK-45.12, TASK-45.13, TASK-45.14 |

Every child task has `TASK-45` as its Backlog parent, high priority, and
milestone `ADR Grilling`. TASK-45.1 through TASK-45.15 are Done.

## Dependency graph

```text
TASK-45.1
├── TASK-45.2
│   ├── TASK-45.4
│   │   ├── TASK-45.6
│   │   ├── TASK-45.7
│   │   ├── TASK-45.11
│   │   └── TASK-45.14
│   └── TASK-45.5
│       ├── TASK-45.6
│       ├── TASK-45.10
│       ├── TASK-45.13
│       └── TASK-45.14
└── TASK-45.3
    ├── TASK-45.4
    └── TASK-45.7

TASK-45.7
└── TASK-45.8
    ├── TASK-45.9
    ├── TASK-45.10
    ├── TASK-45.11
    ├── TASK-45.12
    └── TASK-45.14

TASK-45.6
TASK-45.9
TASK-45.10
TASK-45.11
TASK-45.12
TASK-45.13
TASK-45.14
└── TASK-45.15
```

The graph is acyclic. TASK-45.15 completed the release and certification
convergence after every independently implementable integration branch was
finished.
