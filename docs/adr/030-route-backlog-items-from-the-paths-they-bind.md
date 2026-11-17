---
status: Accepted
date: 2026-09-05
scope: [.githooks/pre-commit, docs/backlog/, scripts/backlog.py, skills/writing-adrs/adr.py]
summary: Derive each docs/backlog/ item's scope from its own reference-style links, resolved the way an ADR's own links resolve, and report it from a sibling backlog.py `for` lookup .githooks/pre-commit runs alongside adr.py's; a dangling scope entry is never reported and never fails the build.
revisit-when: This lookup runs only in the opt-in pre-commit hook, with no pr.yml mirror the way ADR 021 gives ADR scope one.
---

# 030: Route backlog items from the paths they bind

## Context

[ADR 020][] gave deferred work a home in the repository, one file per item under
`docs/backlog/`. Its Consequences named the gap it left open: "Nothing routes a reader to
`docs/backlog/` the way `scope` routes them to an ADR... a directory of files is better
[than the issue tracker] only because `rg` reaches it — which works only while every item
names the paths it binds in its prose, itself a convention nothing checks. Closing this
properly means giving an item a scope the pre-commit report can read." [ADR 013][] closed
the same gap for decisions, and [ADR 014][] closed it for the code sites they bind.
Deferred work is the one category ADR 020 left open.

`docs/backlog/README.md` already asks authors for what a fix would need: "name the paths
an item binds in its prose." The twelve items on disk almost all follow that instruction
in the same way. Every item but one ends with a block of Markdown reference-style link
definitions that name the files it discusses. [`writing-adrs`][] requires the same block
of an ADR in its **Linking references** section. The one exception,
[`validate-the-plugin-hook-configuration-in-ci.md`][], names three paths in code spans and
has no link definitions. It would derive an empty scope and stay as unreachable as it is
today. Fixing that item's prose is outside this decision.

## Options

### Option 1: Do nothing

**Pros:** No migration, and no code to maintain. The instruction in
`docs/backlog/README.md` stays as it is.
**Cons:** Leaving the gap open repeats the failure ADR 013 measured in `tags`: a
convention that is documented and never checked.
**Risks:** The gap widens unnoticed. Nothing about a growing `docs/backlog/` shows that
nobody can find its items any more easily.

### Option 2: Derive scope from each item's own reference links (Accepted)

Add no frontmatter and no `scope:` field. A sibling module, `backlog.py`, parses each
item's reference-style link definitions and resolves each target relative to the item's
own file, as the **Linking references** section of `writing-adrs` already resolves an
ADR's. A target becomes scope unless it is an external URL or resolves into `docs/adr/`
or `docs/backlog/`. Those targets name a decision or a sibling item for context, not a
site the item's work would change. `.githooks/pre-commit` runs `backlog.py for` over
every staged path alongside `adr.py for`. It reports each item whose derived scope covers
a staged path, by file path, because a backlog item has no number.

**Pros:** No second scoping syntax beside the `scope:` frontmatter of an ADR. ADR 013 and
[ADR 019][] both already pushed back on that kind of accidental complexity, and the
Context measurement earns this option rather than assumes it.
**Cons:** Scope is only as complete as an item's links. An item that names a path in
prose without linking it, or that has no link block, derives an incomplete or empty
scope and stays as unreachable as it is today. This option makes sure something finds
the paths an item names. It does not check that an item names the right paths. That
stays an instruction to the author in `docs/backlog/README.md`.
**Risks:** Excluding `docs/adr/` and `docs/backlog/` is a judgement call. An item that
cites an ADR for context derives no scope from that citation, so editing the cited ADR
does not report the item. Most links into `docs/adr/` in the corpus today are citations
of this kind. The risk is accepted for two reasons. `adr.py for` already reports the
decisions that bind that ADR. And the branch that would edit the cited ADR normally
deletes the item too, which leaves little time for the omission to matter.

### Option 3: An explicit `## Scope` list, kept beside the links

Each item states its scope as its own bullet list, separate from what it links.

**Pros:** Scope is stated, not inferred. An item can name a path it does not link, and no
exclusion rule needs judgement.
**Cons:** A second scoping syntax next to the `scope:` frontmatter of an ADR, for a
directory that ADR 020 keeps as plain Markdown with no frontmatter on purpose. Each item
would carry two lists, the links and the scope bullets, to keep in step. That is how
`tags` decayed in a corpus nobody checked (ADR 013).
**Risks:** An author adds a link when they first discuss a file, but nothing requires
them to update a scope list. The list would drift from what the item concerns faster
than the links would. It buys explicitness with a field that is only as good as its
upkeep.

## Decision

Option 2. Deferred work stays where ADR 020 put it: one plain Markdown file per item under
`docs/backlog/`, with the issue tracker still unused for it. Each item gains a derived
scope, and `backlog.py` gains a reverse lookup, `for`, that `.githooks/pre-commit` runs
beside `adr.py`'s own. The corpus count settles it over Option 3. Eleven of twelve items
already write the reference-link block that `backlog.py` reads, so the mechanism asks for
no new authoring habit. An explicit scope list would add a second habit next to one
authors already follow.

`backlog.py` departs from `adr.py`'s `binding()` in two ways. Both follow from what a
backlog item is, and neither is a shortcut:

- **A dangling scope entry is never reported, and never fails a build.** ADR 013's
  `scope_problems()` is right to fail `check` when a decision's `scope` names nothing. The
  decision still binds, and its target moved or was deleted under it. A finished backlog
  item that names a deleted path is the ordinary case, not decay. The work is most likely
  done, and the branch that did it should already have deleted the item. Failing a build
  over that would make finishing work a chore. So `backlog.py` has no `scope_problems()`
  equivalent and no `check` command, and `pr.yml` has nothing to gate on.
- **Items are read fresh from `docs/backlog/*.md` on every lookup, and reported by
  path.** An item is deleted, not archived. Nothing should keep pointing at a deleted
  item the way `INDEX.md` keeps every ADR number forever. So `backlog.py` keeps no
  identity across commits that a deleted item could leave behind. It names each match by
  file path, because an item has no number.

## Consequences

- `.githooks/pre-commit` prints a second advisory block, `Backlog items concerning these
  paths:`, below the existing `Decisions binding these paths:` block, over the same list
  of staged paths. Like that block, it prints nothing when nothing matches.
- Supersedes ADR 020, whose Consequences describe the routing gap above as open. Editing
  that sentence in place would break the "supersede, don't edit" rule in `writing-adrs`.
  ADR 020's convention stays unchanged. Only the gap it named closes.
- `validate-the-plugin-hook-configuration-in-ci.md` derives no scope today, because it
  has no link-definition block. It shows the Cons of Option 2 in practice, and this
  decision leaves it as it is.
- No CI job runs `backlog.py`. This matches `adr.py for`, which is also advisory only.
  Both run only in a clone that has set `core.hooksPath`, as ADR 013's own
  Consequences describe.

[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 014]: 014-cite-adrs-from-code-comments.md
[ADR 019]: 019-do-not-generate-path-scoped-rules-from-adr-frontmatter.md
[ADR 020]: 020-track-deferred-work-in-the-repository.md
[`validate-the-plugin-hook-configuration-in-ci.md`]: ../backlog/validate-the-plugin-hook-configuration-in-ci.md
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
