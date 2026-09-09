---
status: Accepted
date: 2026-09-08
scope: [docs/backlog/, scripts/backlog.py]
summary: Keep docs/backlog/ items as plain Markdown with no frontmatter, rather than introducing metadata fields modelled on ADR frontmatter.
revisit-when: A second document type beyond ADRs adopts metadata frontmatter, making three data points — ADR's own included — toward a shared vocabulary.
---

# 032: Keep backlog items as plain Markdown, not frontmatter

## Context

[ADR 020][] put deferred work under `docs/backlog/`, one file per item; that file's
shape, fixed in `docs/backlog/README.md`, is an H1 title, a blockquote naming when and
where it was recorded, and freeform prose sections — no frontmatter, no machine-checked
fields. [ADR 030][] later gave items a derived `scope`, read from their own reference-style
links rather than a frontmatter field, specifically to avoid a second scoping syntax
beside ADR's own.

Reviewing that decision raised the wider question ADR 030 did not: not just scope, but
whether a backlog item should carry frontmatter at all, for anything — a `date` field, a
`source` field, any metadata an ADR already states as a YAML block a parser can read.
The case for it is real: `frontmatter.py` already parses exactly this shape, and every
ADR already carries `date`; reusing both costs little and would give every document
under `docs/` one metadata convention instead of two.

## Options

### Option 1: Do nothing (Accepted)

Keep a backlog item exactly as `docs/backlog/README.md`'s Shape defines it: an H1, a
blockquote provenance line, freeform sections. No frontmatter block, no parser reading
one.

**Pros:** One document shape for `docs/backlog/`, unchanged — no migration of the items
already on disk, and the Shape section stays the whole spec. Consistent with ADR 030,
which chose derivation over a second frontmatter field for the same directory.
**Cons:** Provenance stays prose a human reads rather than a field a machine checks —
the date and source in the blockquote can drift in format across items with nothing to
catch it.
**Risks:** A backlog item's shape stays exactly as informal as the Shape section leaves
it, so whatever ADR 013 caught in `tags` — a convention nobody enforces — is a standing
risk here too, just not one this decision closes.

### Option 2: Introduce frontmatter modelled on ADR's

Give a backlog item the same YAML frontmatter block an ADR carries — `date` at least,
perhaps a `source` field for what the blockquote states in prose today.

**Pros:** Reuses a parser and a convention that already exist, rather than inventing
either. Every document under `docs/` gains one shared metadata vocabulary instead of an
ADR-only one.
**Cons:** ADR frontmatter was designed for what an ADR is: a permanent record with a
`status` lifecycle, cross-ADR supersession, and a `scope` a build gates on. A backlog
item is none of that — it is deleted the moment its work lands (ADR 020), carries no
status of its own, and already gets its `scope` from links, not a field (ADR 030). Frontmatter
built for the first shape is not obviously right for the second merely because it
already exists.
**Risks:** Designing a shared vocabulary from one example — ADR's — before a third case
(a second document type beyond ADR's own) has ever asked for metadata risks fitting the
wrong shape to `docs/backlog/` and then having to unpick it once a real third case
arrives with different needs.

## Decision

Option 1. The tooling argument for Option 2 is real, but it argues for reuse, not for
correctness: an ADR's frontmatter answers what a permanent, status-tracked, superseded-by-
another-ADR document needs, and a backlog item's whole character — deleted the moment its
work lands, carrying no status of its own (ADR 020) — is the opposite of that on every
axis. Adopting it now would be designing a shared convention off a single
data point — ADR's own — with only a second case in view, not the third the "don't
refactor until you've seen the same thing three times" principle asks for. Revisit once a
real third case exists to design from, rather than retrofitting ADR's shape onto a
document it was never built for.

## Consequences

- `docs/backlog/README.md`'s Shape is unchanged: an H1, the blockquote provenance line,
  freeform sections. No migration of the items on disk.
- `backlog.py` gains no frontmatter-parsing responsibility. Its `for` lookup stays
  scoped by derived links alone, per ADR 030.
- Provenance stays a prose convention, checked by a reader rather than a parser — the
  same limitation ADR 020 already accepted for this directory.
- A single further request for backlog-item metadata is only the second data point —
  ADR's own frontmatter being the first — and not itself grounds to reopen this ADR;
  `revisit-when` asks for a third.

[ADR 020]: 020-track-deferred-work-in-the-repository.md
[ADR 030]: 030-route-backlog-items-from-the-paths-they-bind.md
