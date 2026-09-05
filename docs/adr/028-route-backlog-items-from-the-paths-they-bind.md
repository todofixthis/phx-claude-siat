---
status: Accepted
date: 2026-09-05
scope: [.githooks/pre-commit, docs/backlog/, skills/writing-adrs/]
summary: Derive each docs/backlog/ item's scope from its own reference-style links, resolved the way an ADR's own links resolve, and report it from a sibling backlog.py `for` lookup .githooks/pre-commit runs alongside adr.py's; a dangling scope entry is never reported and never fails the build.
revisit-when: This lookup runs only in the opt-in pre-commit hook, with no pr.yml mirror the way ADR 021 gives ADR scope one.
---

# 028: Route backlog items from the paths they bind

## Context

[ADR 020][] gave deferred work a file home, one item per file under `docs/backlog/`, and
named its own gap in Consequences: "Nothing routes a reader to `docs/backlog/` the way
`scope` routes them to an ADR... a directory of files is better [than the issue tracker]
only because `rg` reaches it — which works only while every item names the paths it
binds in its prose, itself a convention nothing checks. Closing this properly means
giving an item a scope the pre-commit report can read." That is the gap [ADR 013][]
closed for decisions and [ADR 014][] closed for the sites they bind; deferred work is the
one category ADR 020 left it standing in.

`docs/backlog/README.md` already asks for the fix's raw material: "name the paths an
item binds in its prose." Read against the twelve items on disk, that instruction is
already followed almost everywhere, in one specific shape — every item but one ends with
a block of Markdown reference-style link definitions naming the files it discusses, the
same convention [`writing-adrs`][]'s own **Linking references** section requires of an
ADR. The one exception,
[`validate-the-plugin-hook-configuration-in-ci.md`][], names three paths in code spans
with no link definitions at all, so it would derive an empty scope and stay as
unreachable as it is today; fixing that item's own prose is outside this decision.

## Options

### Option 1: Do nothing

**Pros:** No migration, and no code to maintain. `docs/backlog/README.md`'s instruction
stands as it is.
**Cons:** Leaving the gap open repeats the "documented and unchecked" failure ADR 013
measured in `tags`.
**Risks:** The gap widens silently, since nothing about a growing `docs/backlog/`
signals that retrieval never improved.

### Option 2: Derive scope from each item's own reference links (Accepted)

Add no frontmatter and no `scope:` field. A sibling module, `backlog.py`, parses each
item's reference-style link definitions, resolves each target from the item's own file —
the way `writing-adrs`'s **Linking references** already resolves an ADR's — and keeps a
target as scope unless it is an external URL or resolves into `docs/adr/` or
`docs/backlog/` itself: those name a decision or a sibling item for context, not a site
the item's own work would touch. `.githooks/pre-commit` runs `backlog.py for` over every
staged path alongside `adr.py for`, reporting any item whose derived scope covers one, by
path rather than by number since a backlog item has none.

**Pros:** No second scoping syntax beside ADR's `scope:` frontmatter — the exact
accidental complexity ADR 013 and [ADR 019][] already pushed back on, and one the
Context measurement earns rather than assumes.
**Cons:** Scope is only as complete as an item's own links; an item that names a path in
prose without linking it, or omits the block entirely, derives an incomplete or empty
scope and stays exactly as unreachable as it is today — this closes "does something find
the paths an item names", not "does an item name the right paths", which is
`docs/backlog/README.md`'s instruction to the author and stays one.
**Risks:** The `docs/adr/`/`docs/backlog/` exclusion is a judgement call: an item that
cites an ADR for context (most links into `docs/adr/` in the corpus today) derives no
scope from that citation, so editing the cited ADR will not surface the item. Accepted
because `adr.py for` already reports that ADR's own bound decisions, and because a
backlog item citing an ADR is normally deleted by the same branch that would go on to
edit it, leaving little window for the omission to matter.

### Option 3: An explicit `## Scope` list, kept beside the links

Each item states its scope as its own bullet list, independent of what it links.

**Pros:** Explicit rather than inferred, so an unlinked path can still be named, and nothing
about the derivation's exclusions is a judgement call.
**Cons:** A second scoping syntax next to ADR's `scope:` frontmatter, for a directory
ADR 020 deliberately keeps as plain Markdown with no frontmatter. Two lists per item —
the links and the scope bullets — is two places to keep in sync, which is exactly how
`tags` decayed against a corpus nobody was checking (ADR 013).
**Risks:** A scope list nobody is required to update the way a link is naturally added
when a file is first discussed drifts from what the item actually concerns faster than
the links would, buying explicitness at the cost of a field only as good as its own
maintenance.

## Decision

Option 2. Deferred work stays exactly where ADR 020 put it — one plain Markdown file
per item under `docs/backlog/`, the issue tracker still unused for it — and gains a
derived scope and a reverse lookup, `backlog.py`'s `for`, that `.githooks/pre-commit` runs
as a sibling of `adr.py`'s own. The corpus measurement is what settles it over Option 3:
eleven of twelve items already write the reference-link block this reads, so the
mechanism costs no new authoring habit, where an explicit scope list would be a second
habit next to one already followed.

Two departures from `adr.py`'s own `binding()` follow from what a backlog item is, not
from a shortcut:

- **A dangling scope entry is never reported, and never fails a build.** ADR 013's
  `scope_problems()` is right to fail `check` on a decision's `scope` naming nothing —
  a decision is still binding and its target moved or was deleted under it. A finished
  backlog item naming a path that is now gone is the ordinary case, not rot: the work is
  most likely done, and the item should already have been deleted with it. Failing a
  build over that would turn finishing work into a chore, so `backlog.py` carries no
  `scope_problems()` equivalent and no `check` command at all — there is nothing here
  for `pr.yml` to gate on.
- **Items are read fresh from `docs/backlog/*.md` on every lookup, and reported by
  path.** An item is deleted, not archived — nothing should keep pointing at one the way
  `INDEX.md` keeps every ADR number forever — so `backlog.py` keeps no identity across
  commits for a deleted item to leave behind, and names each match by its own file path,
  having no number to report instead.

## Consequences

- `.githooks/pre-commit` prints a second advisory block, `Backlog items concerning these
  paths:`, beneath the existing `Decisions binding these paths:` one, over the same
  staged-path list — silent, as that one is, when nothing matches.
- Supersedes ADR 020, whose Consequences state the routing gap above as standing;
  editing that sentence in place would breach `writing-adrs`'s "supersede, don't edit".
  Its convention survives unchanged; only the named gap closes.
- `validate-the-plugin-hook-configuration-in-ci.md` derives no scope today, having no
  link-definitions block to derive one from — a live demonstration of the Option 2 Cons
  above, left as it is rather than fixed here.
- No CI job runs `backlog.py`, matching `adr.py for`'s own advisory-only reach: both run
  only in a clone that has set `core.hooksPath` per ADR 013's own Consequences.

[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 014]: 014-cite-adrs-from-code-comments.md
[ADR 019]: 019-do-not-generate-path-scoped-rules-from-adr-frontmatter.md
[ADR 020]: 020-track-deferred-work-in-the-repository.md
[`validate-the-plugin-hook-configuration-in-ci.md`]: ../backlog/validate-the-plugin-hook-configuration-in-ci.md
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
