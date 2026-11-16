---
status: Superseded
date: 2026-08-28
scope: [AGENTS.md, docs/backlog/]
summary: Record deferred work as files under docs/backlog/, leaving the GitHub issue tracker enabled for Renovate's dependency dashboard but not using it to track work.
revisit-when: A second person needs to see what is deferred without cloning, or bug reports start arriving in the tracker and need triaging beside deferred work.
superseded-by: 30
---

# 020: Track Deferred Work in the Repository

## Context

Work gets deferred here constantly. A review finds something real that is not this
release's problem, and the finding has to go somewhere. Three such notes accumulated during
the 5.0.0 cycle alone: two `nz-english` follow-ups from the [#37][] review, and an
assessment, deferred from [#27][], of whether [ADR 007][]'s revisit trigger had fired.

All three were filed as GitHub issues, and the agent that would act on each note never read
it again. Nothing under `AGENTS.md`, `.agents/`, `.githooks/`, or `.github/` sends an agent
to the tracker for deferred work. The one mention of the tracker in those four is a release
recovery step that closes issues. An agent exploring the repository has no reason to invent
the step. The note is out of sight at exactly the moment it matters: when a session edits
the file the note concerns.

[ADR 013][] closed that gap for decisions, by keying `scope` to the paths where a breach
would be authored. [ADR 014][] closed it for the sites those decisions bind, by citing the
decisions from comments. Both work by pointing from the bound file to the record. Deferred
work is the one category still outside the tree.

The repository has one maintainer and takes no outside contributions. It is, however, where
users land. [ADR 010][] pins the marketplace entry at this repository's `main`, so the
tracker is a real channel for someone who installed the plugin. Renovate's dependency
dashboard is also an issue, and is worth keeping.

## Options

Options 2, 3, and 4 all make deferred work invisible to anyone without a checkout. All three
also give up the assignment, labels, notifications, and cross-repository references that an
issue carries. None of that ranks them, because the audience for a deferred note is one
maintainer and their agents, and both read the working tree.

### Option 1: Do nothing — keep filing deferred work as GitHub issues

**Pros:** It needs no migration and no new convention to hold. The tracker already exists,
is searchable from any device, and gives each issue its own discussion thread.

**Cons:** The reader who needs a note cannot see it. A backlog that only the maintainer
polls keeps growing.

**Risks:** The gap widens and nothing reports it, because each issue filed reads as work
captured. Capturing a note that nobody retrieves is a failure that looks like success.

### Option 2: Record deferred work as files under `docs/backlog/` (Accepted)

Each item gets one Markdown file, in the same shape as `docs/adr/`.

**Pros:** The items are in the tree, so `rg` reaches them. They are versioned with the code
they describe, so a branch that fixes an item deletes it in the same commit.

**Cons:** An item has no status or age, and no thread once a discussion starts. Without an
issue number a fix cannot say `Closes #39`, so once the item is deleted, the deleting commit
is the only trace.

**Risks:** A directory of files with no lifecycle becomes a graveyard, the way a
`TODO.md` does.

#### Variant: a single `BACKLOG.md`

Rejected on the same grounds that make `docs/adr/` a directory. The two items carried across
already run to seventy lines each, every addition or deletion touches the same file, and
nobody can link to one item in a single file.

### Option 3: Record deferred work only where it binds, with no backlog at all

Every note becomes a `revisit-when` on the ADR it concerns, a `## Revisit watch` in that
ADR's body, or a comment at the site it would change.

**Pros:** This reaches the reader most directly. The note is in the file the reader has
open, not merely somewhere in the tree. It needs no new directory and no new convention.

**Cons:** Only work with a site can be recorded this way. A note that spans several files,
or names code that does not exist yet, has nowhere to go.

**Risks:** Authors feel pressure to attach a note to the nearest plausible file. That is how
a comment ends up asserting something the code beside it does not support.

### Option 4: Record deferred work in files and turn the issue tracker off

This is Option 2 plus the platform setting, so the convention enforces itself.

**Pros:** A note has no second place to land, and nobody has to hold the discipline. The
breach is impossible rather than discouraged.

**Cons:** Renovate's dependency dashboard is an issue, so it goes too. Users who installed
the plugin lose the one channel this repository offers them.

**Risks:** Renovate reports a broken config by opening an issue, and holds every update pull
request until someone fixes the config. With issues turned off, Renovate halts and cannot
say why, so the failure shows up as silence rather than as an error.

## Decision

Deferred work goes in `docs/backlog/`, one file per item. Option 3 is right for the notes it
fits, and it is how ADR 007's revisit assessment was absorbed rather than carried across.
But Option 3 cannot hold an item like the `scan.py` pre-commit work, which spans a tool, its
skill, and its exit-code contract. So the backlog is the default and Option 3 is the
exception. A note leaves `docs/backlog/` only when it is a condition that would reopen a
decision, a finding about whether such a condition has fired, or a constraint an editor must
meet. The reverse default, using the binding site wherever possible, fails on the commonest
deferral of all. One defect in one file fits no site, and Option 3's Risks would then put it
in a comment.

**The tracker stays enabled, so this is a convention and not a switch.** Option 4 was the
first plan and is the stronger mechanism. It is rejected because of what it takes with it,
and Renovate's silent halt is a cost nobody would notice paying. So filing an issue remains
the path of least resistance, one command against a file to write and link, with nothing but
`AGENTS.md` in its way. That is this decision's weak point, named here rather than
discovered later.

**Scope names no entry for the breach itself.** Someone files an issue through the GitHub
API, not by editing a path. `scope` names `AGENTS.md`, because deleting the convention there
repeals it. It also names `docs/backlog/`, where authors write compliance rather than a
breach. That entry is there so the pre-commit report reaches a session that already holds an
item. The entry widens the field's test, and naming either entry keeps this ADR out of ADR
013's count of decisions that scope `[]`. Both choices are deliberate: `[]` is the purer
answer, and it reaches nobody.

The convention's defence is `AGENTS.md`, which an agent meets at session start, before it
plans any deferral. That is earlier than a code comment, which an agent meets only once the
breaching file is open. The defence does not reach the maintainer typing `gh issue create`
by hand.

## Consequences

Nothing routes a reader to `docs/backlog/` the way `scope` routes them to an ADR. That is
this decision's own argument turned on its solution. The tracker failed because nothing sent a
reader to it. A directory of files is better only because `rg` reaches it, and `rg` reaches
an item only while the item names in its prose the paths it binds. That too is a convention
nothing checks. Closing the gap properly means giving an item a scope the pre-commit report
can read, and that work is recorded in `docs/backlog/` rather than built here.

`docs/backlog/` gets no rot check, whereas [`adr.py`][] verifies `scope` entries against the
filesystem. Nobody catches an item quietly fixed months ago, and a partly discharged item
reads as live. Deleting an item when its work lands is a habit, not an enforced step.

`docs/backlog/README.md` keeps the directory on disk. Git tracks files rather than
directories, so the intended steady state, with every item deleted as its work lands, would
otherwise remove `docs/backlog/`. `scope_problems()` fails the build on a scope entry that
names nothing, so success would break CI.

**A third home for a note now exists that `phx:writing-adrs` does not describe.** An
assessment of whether a revisit condition has fired goes in a `## Revisit watch` section in
the ADR's body, because `revisit-when` holds the condition and not the finding about it.
ADR 007 carries the first such section. The skill's Format section fixes the section list
and has no such heading, so this is a repo-local convention, recorded here and in
`AGENTS.md`.

The [`releasing`][] skill's recovery path still tells a human to close any `#NNN` that the
release notes reference. Those numbers are usually pull requests, and `gh issue` resolves a
pull-request number rather than rejecting it, so the instruction can act on the wrong
object. This is recorded in `docs/backlog/`. It is unrelated to where deferred work lives,
but was found while writing this ADR.

Issues #28, #38, and #39 must be closed once this ADR lands, each with a pointer to where
its content went, so the pointer resolves against `main`. Left open, they are live
duplicates of backlog items, and a session that finds one first works from a copy no branch
will ever delete. #2 is Renovate's dependency dashboard and stays open by design.

[#27]: https://github.com/todofixthis/phx-claude-siat/pull/27
[#37]: https://github.com/todofixthis/phx-claude-siat/pull/37
[ADR 007]: 007-keep-repo-scripts-stdlib-only.md
[ADR 010]: 010-pin-the-marketplace-entry-to-main.md
[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 014]: 014-cite-adrs-from-code-comments.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
