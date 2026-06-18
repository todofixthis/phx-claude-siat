---
name: domain-breakdown
description: Use when a project has no existing domain breakdown document, or when the existing document needs updating — a domain has been added, split, merged, or significantly repurposed, or the `last-reviewed` date is more than three months behind the latest commit that touched domain boundaries
---

# Domain Breakdown

## Overview

A domain breakdown gives any contributor (human or agent) a single starting point to understand how a project's concerns are divided and how they relate. It has two parts: a **Mermaid relationship diagram** and a **hierarchical text description** grouped by logical clusters.

## Process

### 1. Explore first

Read enough of the codebase to answer:

- What are the distinct areas of responsibility?
- Which ones are foundational services used by many others?
- Which ones are leaf domains used by nothing else?
- Which ones naturally cluster together?

Don't read every file. Focus on top-level directories, entry points, and any existing documentation.

### 2. Identify groups and domains

Organise domains into logical groups that reflect *what they are*, not the directory structure:

- **Infrastructure / Shared services** — databases, caches, messaging, config — used by everything, no business logic of their own
- **Core entities** — the central nouns of the system (users, orders, products, accounts)
- **Feature domains** — discrete areas of functionality
- **Analytics / Reporting** — read-only aggregations and exports
- **Integration / Migration** — one-off or external-facing connectors

When a domain doesn't fit any group, let it stand alone at the same heading level as the groups.

### 3. Build the Mermaid diagram

Use `graph LR` (left-to-right). Use `subgraph` for clusters; standalone domains are bare nodes.

```
graph LR
    subgraph infra["Infrastructure"]
        DB["Database\nMigrations · connection pool"]
        Queue["Message Queue\nAsync jobs · retries"]
    end

    Users["Users\nAccounts · authentication"]

    Users -->|persisted in| DB
    Users -->|publishes events to| Queue
```

Arrow labels describe the **conceptual relationship**, not code calls:

| ✅ Good labels | ❌ Bad labels |
|---|---|
| `held at brokers` | `calls getBrokerById()` |
| `posts journal entries` | `writes to journal_entry table` |
| `converts to USD` | `calls toUsd()` |
| `seeds on first run` (dashed `-.->`) | `imports CSV rows` |

Never label with method names, table names, or field names.

### 4. Write the hierarchical text

Structure:
- `###` heading for each group (or standalone domain at top level)
- 1–2 sentence group intro explaining what members share
- `####` heading for each domain within the group

Each domain entry:

```markdown
**Purpose:** One sentence.
**Key concepts:** Plain-English description of the domain's main entities. No code type names.
**Inputs:** What triggers activity in this domain.
**Outputs:** What this domain produces.
```

Plain-English key concepts only — no code symbols, table names, or field lists:

| ❌ Code-reference | ✅ Conceptual |
|---|---|
| `UserRecord (id UUID, email string)` | Each user has an identity and a set of roles that control access. |
| `JournalEntry (account_id, amount_usd INTEGER)` | Each financial event is recorded as a balanced set of debit/credit lines. |

If a domain's description exceeds five lines, cut it — this is an orientation map, not a reference manual.

### 5. Choose the file location

- If a `docs/` directory exists: write to `docs/architecture.md`
- Otherwise: create `ARCHITECTURE.md` at the project root

Never overwrite an existing file — check first.

Add a `last-reviewed` date at the top of the file, immediately after any heading:

```markdown
_Last reviewed: YYYY-MM-DD_
```

Update this date whenever the document is revised.

### 6. Wire into agent instructions

Find the project's agent instruction file (`AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, etc.). Add a pointer in the project structure section:

> The Domain Breakdown section of `docs/architecture.md` is a starting point for orientation — treat it as a map that may lag the territory. Before relying on it, check the `last-reviewed` date against recent commits. Update it (using the `domain-breakdown` skill) if it is more than three months behind, or if a domain has been added, split, merged, or significantly repurposed since that date.

If no agent instruction file exists, create `AGENTS.md` at the project root with a minimal section containing the pointer.

### 7. Updating an existing document

Read the current document, identify which domains changed, update only those entries and any affected diagram edges, and bump the `last-reviewed` date. Do not regenerate from scratch — that discards accumulated editorial decisions.

## Common mistakes from RED testing

| What agents do without this skill | What to do instead |
|---|---|
| ASCII diagram or no diagram at all | Always use `graph LR` Mermaid |
| `graph TD` — renders subgraphs side-by-side, wide layout | Use `graph LR` — stacks subgraphs vertically |
| "Domain X owns tables Y, Z and exposes API endpoint /foo" | Purpose + key concepts only; no tables, endpoints, or fields |
| Flat alphabetical list of domains | Group first, then order by importance within the group |
| Forget to update AGENTS.md / CLAUDE.md | Step 6 is mandatory — the breakdown is only useful if agents are directed to it |
| Name the file DOMAINS.md, OVERVIEW.md, etc. | Use `docs/architecture.md` or `ARCHITECTURE.md` for consistency |
