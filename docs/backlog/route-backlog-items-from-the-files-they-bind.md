# Route backlog items from the files they bind

> Recorded 2026-08-28, from the reviews of [ADR 020][]. Never filed as a GitHub issue.

## What

Give a `docs/backlog/` item the same backwards reach an ADR has: a session editing
`skills/nz-english/scan.py` should be told that two recorded items concern it, without
having to think to look.

## Why

ADR 020's whole argument is reach. Deferred work failed in the issue tracker because
nothing sent a reader there at the moment it mattered — the same gap [ADR 013][] closed
for decisions with `scope`, and [ADR 014][] closed for the sites they bind, with comments.

`docs/backlog/` as shipped does not close it. It buys provenance, versioning, and an item
that the branch fixing it deletes in the same commit — all real — but retrieval still
rests on a reader running `rg`, and `AGENTS.md` telling them to. That instruction is the
entire mechanism, and a session that skips it re-derives analysis already written down.

## The mechanism already exists

[`adr.py`][]'s `binding()` is what [`.githooks/pre-commit`][] uses to name every ADR whose
`scope` covers a staged path. A backlog item under `docs/backlog/` carrying its own scope
could ride the same reporting path, and the hook already runs on every commit. So the work
spans `skills/writing-adrs/`, `.githooks/` and the shape of every file in `docs/backlog/`.

## What makes it more than a copy of the ADR machinery

- Scope rot cuts the other way. `scope_problems()` errors on an entry naming nothing on
  disk, which is right for a decision that outlives a refactor. A backlog item whose file
  has since been deleted may simply be done, and failing the build over it turns finishing
  work into a chore.
- An item is deleted, not archived, so nothing should keep pointing at it.
- Items have no numbers, so the report has to name a path.

## Acceptance

- A staged change under a path an item scopes reports that item at commit time, by path.
- A backlog item naming a path that no longer exists does not fail the build.
- The ADR recording the mechanism supersedes ADR 020, whose Consequences state the gap
  as standing. Editing that statement in place would breach supersede-don't-edit.

[ADR 013]: ../adr/013-scope-adrs-by-the-paths-they-bind.md
[ADR 014]: ../adr/014-cite-adrs-from-code-comments.md
[ADR 020]: ../adr/020-track-deferred-work-in-the-repository.md
[`.githooks/pre-commit`]: ../../.githooks/pre-commit
[`adr.py`]: ../../skills/writing-adrs/adr.py
