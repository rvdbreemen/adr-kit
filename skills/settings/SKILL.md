---
name: settings
description: "Show and change adr-kit settings: LLM backend, judge-by-default, hooks, the status-history signer, guardian cadence. Use to inspect where a value comes from or to change one."
argument-hint: "[key] [value]"
disable-model-invocation: true
allowed-tools: [Read, Bash]
---

# adr-kit settings

`$ARGUMENTS` may name a key to show, or a `key=value` to set. Empty shows
everything with its provenance.

One place for every knob. Before this existed a user changed settings in three
disjoint places and one text editor, and two things were simply unreachable:
`judge.llm_enabled` could be switched on by a shipped writer but never off, and
the status-history signer had nowhere to live that anyone would find.

## Show

```bash
python3 "$ADR_KIT/bin/adr-settings" --adr-dir docs/adr
```

Every row carries its **provenance** — project, machine-local, default, or an
environment override. That is the column that answers the question a settings
screen exists for: not "what is this set to" but "why is it set to that".

Add `--all` for every key the schema knows, `--format json` for a machine
reading, `--list` for just the key names.

## Change

```bash
python3 "$ADR_KIT/bin/adr-settings" --adr-dir docs/adr --set judge.llm_enabled=false
python3 "$ADR_KIT/bin/adr-settings" --adr-dir docs/adr --unset guardian.enabled
```

Values are typed against the schema before they land: `--set guardian.enabled=maybe`
is refused rather than stored as a truthy string, and a refused write leaves no
file behind.

## Which file a setting lands in, and why it matters

| Scope | File | Contains |
|---|---|---|
| project | `docs/adr/.adr-kit.json` (tracked) | team decisions: judge behaviour, guardian cadence, retrieval limits |
| machine-local | `docs/adr/.adr-kit.local.json` (gitignored) | personal or machine facts: `lifecycle.signer`, `judge.host_client` |

The command routes each write itself and says where it landed. The split is not
bookkeeping: a signer written to the tracked file would put one person's name on
every teammate's acceptance, which is a false attribution rather than a missing
one. And a host client is a fact about one machine, not a decision about the
project.

## Settings that live elsewhere on purpose

- **The signer** can also be set through `bin/adr signer --set "User: <name>"`,
  which additionally offers `git config user.name` as a proposal and can audit
  existing history for entries with no human actor.
- **Hook installation** is `/adr-kit:install-hooks`, because installing a hook
  writes files outside the config and needs its own consent.
- **The LLM backend** can also be set through `adr-judge --set-backend`, which
  validates the choice against the live registry.

This command shows all of them; where another surface does more than write a
value, it says so rather than duplicating the work.

## What is never shown

A credential is reported as a boolean about the environment — whether a key is
present, never the key. A settings screen needs to know that the environment is
configured; it does not need the secret to say so.
