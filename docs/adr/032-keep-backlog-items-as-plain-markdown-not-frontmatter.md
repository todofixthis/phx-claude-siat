---
status: Accepted
date: 2026-09-08
scope: [docs/backlog/, scripts/backlog.py]
summary: Keep docs/backlog/ items as plain Markdown with no frontmatter, rather than introducing metadata fields modelled on ADR frontmatter.
revisit-when: A second document type beyond ADRs adopts metadata frontmatter, making three data points — ADR's own included — toward a shared vocabulary.
---

# 032: Keep backlog items as plain Markdown, not frontmatter

## Context

[ADR 020][] put deferred work under `docs/backlog/`, one file per item.
`docs/backlog/README.md` fixes the file's shape: an H1 title, a blockquote saying when and
where the item was recorded, and freeform prose sections. There is no frontmatter and no
field a machine checks. [ADR 030][] later gave items a derived `scope`, read from their own
reference-style links rather than a frontmatter field. It did so to avoid a second
scoping syntax beside the one ADRs use.

Reviewing ADR 030 raised a wider question that it did not answer. Should a backlog item
carry frontmatter at all, for anything? That could be a `date` field, a `source` field, or
any metadata an ADR already states in a YAML block a parser can read. The case for it is
real. `frontmatter.py` already parses exactly this shape, and every ADR already has
`date`. Reusing both costs little, and every document under `docs/` would share one
metadata convention instead of two.

## Options

### Option 1: Do nothing (Accepted)

Keep a backlog item exactly as the Shape section of `docs/backlog/README.md` defines it:
an H1, a blockquote provenance line, and freeform sections. No frontmatter block, and no
parser to read one.

**Pros:** `docs/backlog/` keeps one document shape. The items on disk need no migration,
and the Shape section stays the whole spec. This matches ADR 030, which chose to derive
scope rather than add a frontmatter field to the same directory.
**Cons:** Provenance stays prose a person reads, not a field a machine checks. The date
and source in the blockquote can drift in format from item to item, and nothing catches
it.
**Risks:** A backlog item's shape stays as informal as the Shape section leaves it. The
failure ADR 013 found in `tags`, a convention nobody enforces, is a standing risk here
too. This decision does not close it.

### Option 2: Introduce frontmatter modelled on ADR's

Give a backlog item the same YAML frontmatter block an ADR has: `date` at least, and
perhaps a `source` field for what the blockquote states in prose today.

**Pros:** Reuses a parser and a convention that already exist instead of inventing
either. Every document under `docs/` gains one shared metadata vocabulary instead of one
that only ADRs use.
**Cons:** ADR frontmatter was designed for what an ADR is: a permanent record with a
`status` lifecycle, supersession between ADRs, and a `scope` that a build checks. A
backlog item has none of these. It is deleted as soon as its work lands (ADR 020), it has
no status of its own, and it already gets its `scope` from links, not a field (ADR 030).
Frontmatter that already exists for the first kind of document is not obviously right
for the second just because it exists.
**Risks:** Before any third case has asked for metadata, the only example to design a
shared vocabulary from is the ADR. A third case here means a second document type besides
ADRs. Designing from one example risks fitting the wrong shape to `docs/backlog/`, then
having to undo it when a real third case arrives with different needs.

## Decision

Option 1. The tooling argument for Option 2 is real, but it argues for reuse, not for
correctness. An ADR's frontmatter serves a document that is permanent, tracks a status,
and can be superseded by another ADR. A backlog item is the opposite on every count: it
is deleted as soon as its work lands, and it has no status of its own (ADR 020). Adopting
ADR frontmatter now would mean designing a shared convention from one data point, the
ADR, with only a second case in view. The "don't refactor until you've seen the same
thing three times" principle asks for a third. Revisit once a real third case exists to
design from, instead of fitting the ADR's shape onto a document it was not built for.

## Consequences

- The Shape section of `docs/backlog/README.md` is unchanged: an H1, the blockquote
  provenance line, and freeform sections. The items on disk need no migration.
- `backlog.py` takes on no frontmatter parsing. Its `for` lookup stays scoped by derived
  links alone, as ADR 030 sets out.
- Provenance stays a prose convention that a reader checks, not a parser. ADR 020 already
  accepted the same limit for this directory.
- One more request for backlog-item metadata is only the second data point, after ADR
  frontmatter. On its own, it is not grounds to reopen this ADR. `revisit-when` asks for
  a third.

[ADR 020]: 020-track-deferred-work-in-the-repository.md
[ADR 030]: 030-route-backlog-items-from-the-paths-they-bind.md
