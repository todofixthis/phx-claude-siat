# Backlog

This directory holds deferred work, one file per item. Deferred work is never a GitHub
issue in this repository (ADR 020), so an item that is not in this directory is recorded
nowhere.

Read this directory before you start on an area. Nothing routes you to it, and
`rg <area> docs/backlog/` is the whole mechanism. **So name the paths an item binds in its
prose.** An item that never mentions the file it concerns can't be found by the only means
of finding it, and nothing reports the miss.

`.githooks/pre-commit` also reports an item whose reference-link definitions (see Shape of
an item, below) name a staged path. It resolves those links the way an ADR's own links
resolve (ADR 030). A link to an external URL, or into `docs/adr/` or `docs/backlog/`
itself, derives no scope. An item without the link block, or one that names a path only in
prose, derives none either, and stays as unreachable as it was before.

The branch that finishes an item's work deletes the item. The "Deferred work" section of
`AGENTS.md` decides what belongs here rather than on an ADR or in a comment.

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

Between What and Acceptance, add whatever the item needs and nothing more: a
reproduction, the complications that shape the design, or the bound on a fix. Provenance
is the field most easily lost. An item that doesn't say where it came from can't be judged
stale.
