---
status: Superseded
date: 2026-08-28
scope: [AGENTS.md, docs/backlog/]
summary: Record deferred work as files under docs/backlog/, leaving the GitHub issue tracker enabled for Renovate's dependency dashboard but not using it to track work.
revisit-when: A second person needs to see what is deferred without cloning, or bug reports start arriving in the tracker and need triaging beside deferred work.
superseded-by: 28
---

# 020: Track Deferred Work in the Repository

## Context

Work gets deferred constantly here: a review finds something real that is not this
release's problem, and it has to go somewhere. Three such notes accumulated during the
5.0.0 cycle alone — two `nz-english` follow-ups from the [#37][] review, and an assessment
of whether [ADR 007][]'s revisit trigger had fired, deferred from [#27][].

All three were filed as GitHub issues, and none was read again by the thing that would act
on it. Nothing under `AGENTS.md`, `.agents/`, `.githooks/` or `.github/` sends an agent to
the tracker for deferred work — the one mention in those four is a release recovery step
that closes issues — and an agent exploring the repository has no reason to invent the
step. The note is out of sight at exactly the moment it matters: the session editing the
file it concerns.

That is the gap [ADR 013][] closed for decisions, by keying `scope` to the paths where a
breach would be authored, and [ADR 014][] closed for the sites those decisions bind, by
citing them from comments. Both work by pointing from the bound file to the record.
Deferred work is the one category still outside the tree.

The repository is single-maintainer and takes no outside contributions. It is, however,
where users land: [ADR 010][] pins the marketplace entry at this repository's `main`, so
the tracker is a real channel for someone who installed the plugin — and Renovate's
dependency dashboard is an issue too, and worth keeping.

## Options

Options 2, 3 and 4 all make deferred work invisible to anyone without a checkout, and give
up the assignment, labels, notifications and cross-repository references an issue carries.
None of that ranks them: the audience for a deferred note is one maintainer and their
agents, both of whom read the working tree.

### Option 1: Do nothing — keep filing deferred work as GitHub issues

**Pros:** No migration, and no new convention to hold. The tracker is already there,
searchable from any device, and each issue keeps its own discussion thread.

**Cons:** Invisible to the reader who needs it. A backlog only the maintainer polls is a
backlog that grows.

**Risks:** The gap widens silently, because each issue filed reads as work captured, and
capture without retrieval is the failure that looks like success.

### Option 2: Record deferred work as files under `docs/backlog/` (Accepted)

One Markdown file per item, mirroring `docs/adr/`'s shape.

**Pros:** In the tree, so `rg` reaches it, and versioned with the code the item describes
— a branch that fixes an item deletes it in the same commit.

**Cons:** No status or age, and no thread once a discussion starts. Without an issue
number a fix cannot say `Closes #39`, so once the item is deleted the only trace is the
deleting commit.

**Risks:** A directory of files with no lifecycle becomes a graveyard, the way a `TODO.md`
does.

#### Variant: a single `BACKLOG.md`

Rejected on the same grounds `docs/adr/` is a directory: the two items carried across
already run to seventy lines each, every addition or deletion touches the same file, and
one file cannot be linked to per item.

### Option 3: Record deferred work only where it binds, with no backlog at all

Every note becomes a `revisit-when` on the ADR it concerns, a `## Revisit watch` in that
ADR's body, or a comment at the site it would change.

**Pros:** The strongest form of reach — the note is not merely in the tree, it is in the
file the reader has open. Needs no new directory and no new convention.

**Cons:** Only work with a site can be recorded this way. A note spanning several files,
or naming code that does not exist yet, has nowhere to sit.

**Risks:** Pressure to attach a note to the nearest plausible file, which is how a comment
ends up asserting something the code beside it does not support.

### Option 4: Record deferred work in files and turn the issue tracker off

Option 2 plus the platform setting, so the convention enforces itself.

**Pros:** No second place for a note to land, and no discipline to hold — the breach is
impossible rather than discouraged.

**Cons:** Renovate's dependency dashboard is an issue, so it goes too, and users who
installed the plugin lose the one channel this repository offers them.

**Risks:** Renovate reports a broken config by opening an issue and holding every update
pull request until someone fixes it. Silenced, it halts and cannot say why, which surfaces
as silence rather than as an error.

## Decision

Deferred work goes in `docs/backlog/`, one file per item. Option 3 is right for the notes
it fits, and is how ADR 007's revisit assessment was absorbed rather than carried across —
but it cannot hold an item like the `scan.py` pre-commit work, which spans a tool, its
skill and its exit-code contract. So the backlog is the default and Option 3 the
exception: a note leaves `docs/backlog/` only when it is a condition reopening a decision,
a finding about whether one has fired, or a constraint an editor must meet. Put the other
way round — use the binding site where you can — the commonest deferral of all, one defect
in one file, fits no site, and Option 3's Risks then put it in a comment.

**The tracker stays enabled, so this is a convention and not a switch.** Option 4 was the
first plan and is the stronger mechanism; it is rejected on what it takes with it, and
Renovate's silent halt is the cost that would be paid without anyone noticing. So filing
an issue remains the path of least resistance — one command against a file to write and
link — with nothing but `AGENTS.md` in its way. That is this decision's weak point, named
here rather than discovered later.

**Scope names no entry for the breach itself.** Filing an issue is authored against the
GitHub API, not a path. `scope` names `AGENTS.md`, where deleting the convention repeals
it, and `docs/backlog/`, where compliance rather than a breach is authored — that one is
there so the pre-commit report reaches a session already holding an item. It widens the
field's test, and naming either entry keeps this ADR out of ADR 013's count of decisions
scoping `[]`. Both are deliberate: `[]` is the purer answer and reaches nobody.

The convention's defence is `AGENTS.md`, met at session start before any deferral is
planned — earlier than a code comment, which is met only once the breaching file is open.
It does not reach the maintainer typing `gh issue create` by hand.

## Consequences

Nothing routes a reader to `docs/backlog/` the way `scope` routes them to an ADR. That is
this decision's own argument turned on its solution: the tracker failed because no reader
was sent to it, and a directory of files is better only because `rg` reaches it — which
works only while every item names the paths it binds in its prose, itself a convention
nothing checks. Closing this properly means giving an item a scope the pre-commit report
can read, which is recorded in `docs/backlog/` rather than built here.

`docs/backlog/` gets no rot check, where `scope` entries are verified against the
filesystem by [`adr.py`][]. An item quietly fixed months ago is caught by
nobody, and a partly discharged one reads as live; deleting an item when its work lands is
a habit, not an enforced step.

`docs/backlog/README.md` is what keeps the directory on disk. Git tracks files rather than
directories, so the intended steady state — every item deleted as its work lands — would
otherwise remove `docs/backlog/`, and `scope_problems()` fails the build on a scope entry
naming nothing. Success would break CI.

**A third home for a note now exists that `phx:writing-adrs` does not describe.** An
assessment of whether a revisit condition has fired goes in a `## Revisit watch` section
in the ADR's body, because `revisit-when` holds the condition and not the finding about
it. ADR 007 carries the first. The skill's Format section fixes the section list and has
no such heading, so this is a repo-local convention, recorded here and in `AGENTS.md`.

The [`releasing`][] skill's recovery path still tells a human to close any `#NNN` the
release notes reference. Those numbers are usually pull requests, and `gh issue` resolves
a pull-request number rather than rejecting it, so the instruction can act on the wrong
object. Recorded in `docs/backlog/`; unrelated to where deferred work lives, but found
while writing this.

Issues #28, #38 and #39 must be closed with a pointer to where their content went, once
this lands, so the pointer resolves against `main`. Left open they are live duplicates of
backlog items, and a session finding one first works from a copy no branch will ever
delete. #2 is Renovate's dependency dashboard and stays open by design.

[#27]: https://github.com/todofixthis/phx-claude-siat/pull/27
[#37]: https://github.com/todofixthis/phx-claude-siat/pull/37
[ADR 007]: 007-keep-repo-scripts-stdlib-only.md
[ADR 010]: 010-pin-the-marketplace-entry-to-main.md
[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 014]: 014-cite-adrs-from-code-comments.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
