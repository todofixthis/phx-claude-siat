# Backlog

Deferred work, one file per item. Deferred work is never a GitHub issue here (ADR 020), so
an item that is not in this directory is not recorded anywhere.

Read this directory before starting on an area — nothing routes you to it, and
`rg <area> docs/backlog/` is the whole mechanism. **So name the paths an item binds in its
prose**: an item that never mentions the file it concerns cannot be found by the only means
of finding it, and nothing reports the miss.

`.githooks/pre-commit` also reports an item whose reference-link definitions (see Shape,
below) name a staged path — the same links, resolved the way an ADR's own links resolve
(ADR 028). A link to an external URL, or into `docs/adr/` or `docs/backlog/` itself,
derives no scope; an item without the link block, or one that names a path only in
prose, derives none either and stays as unreachable as it was before.

An item is deleted by the branch that finishes its work. `AGENTS.md`'s "Deferred work"
section decides what belongs here rather than on an ADR or in a comment.

## Shape of an item

```markdown
# <title, as a claim about the work — not a bug report headline>

> Recorded <ISO date>, <where it came from>. <Was it a GitHub issue, and which.>

## What

The work, naming the files it binds.

## Why it is still worth doing

Cut this only where the What already answers it.

## Acceptance

What would count as done, one bullet per testable claim.
```

Between What and Acceptance, add whatever the item needs and nothing it does not —
a reproduction, the complications that shape the design, the bound on a fix. Provenance is
the field most easily lost: an item that does not say where it came from cannot be judged
stale.
