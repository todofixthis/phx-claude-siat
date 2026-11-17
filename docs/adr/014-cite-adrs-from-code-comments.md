---
status: Accepted
date: 2026-08-10
scope: [.agents/, .githooks/, AGENTS.md, docs/, scripts/, skills/]
summary: Cite ADRs from comments and docstrings as a documented convention — the number and what the decision forbids at that line, never the reasoning — fixing the citation format now, and deferring a check that citations survive until an archival defence first depends on one.
revisit-when: An ADR is archived on a defence that rests on a comment in code.
---

# 014: Cite ADRs from code comments

## Context

Code in this repository already cites ADRs, far more widely than the practice's
undocumented status suggests. There are 54 references across eleven files outside
`docs/adr/`, including [`validate_manifests.py`][], [`adr.py`][], [`versions.py`][],
[`frontmatter.py`][], [`release_notes.py`][], and four test modules. Nothing records the
practice as a convention, so whoever wrote each citation settled two things alone. The
citation *format* split: `ADR 007` appears 33 times and `docs/adr/007` 21 times. What a
citation carries split too, ranging from a bare number to a sentence of reasoning.

Where a citation *sits* matters more than either. [`writing-adrs`][] lets an ADR be
`Archived`, kept in force but dropped from the index an agent loads, when a defence exists
that a breacher meets **while the work is still being planned**. It names a comment as one
of only two qualifying defences. By that timing test, many existing citations would not
qualify. Ten of the 20 in `validate_manifests.py` sit inside error strings, which a
breacher meets when a check fails, after the wrong work is already built. A comment in the
code someone is reading qualifies. The same words in a failure message do not.

So a decision needs recording before more code is written against it, and a second
question sits under it. A comment goes stale when its ADR is superseded, and vanishes when
a refactor removes the code that carries it. The second case is the dangerous one. An
`Archived` ADR is invisible by design, so nothing reports that its defence has gone. No
ADR is `Archived` today, so nothing depends on a comment defence yet.

## Options

Options 2 and 3 both leave the 54 existing citations standing and both settle the format
split, so neither wins on that. They differ on where the convention's authority lies: in
prose that an author follows, or in a schema that a check enforces.

### Option 1: Do nothing

Citations continue as an undocumented habit.

**Pros:** Nothing to write, and the habit has produced usable comments in eleven files
without guidance.
**Cons:** Both splits widen, leaving two formats and no agreed content. The timing point
above stays unstated just as decisions become archivable on it.
**Risks:** A comment that restates an ADR's reasoning drifts from the ADR, and a reader who
finds the drift cannot tell which of the two is current.

### Option 2: A documented convention, enforced by review (Accepted)

`writing-adrs` states what a citation carries and where it must sit to count as a defence.
[`AGENTS.md`][] fixes this repository's citation format and points code authors at both.
Nothing checks either.

**Pros:** Reaches the author while they write, the only point where the convention
applies. Prose can also express the part no check could: a citation's *location* is what
makes it a defence.
**Cons:** Rests on authors and reviewers, so nothing reports a citation that a refactor
deletes.
**Risks:** Documented and unchecked is how `tags` decayed ([ADR 013][]).

### Option 3: A checked citation schema

Make the citation a machine-readable annotation, a fixed marker that CI parses. On every
pull request, CI checks the annotation's shape, that its number resolves, and that its
target is not superseded.

**Pros:** The format cannot split again, a mistyped number fails the build, and the corpus
stays inspectable as data instead of prose.
**Cons:** Covers the cheap half. What matters for an archival defence is whether a
citation sits where the work is planned, and no parser can judge that. A schema that
validates shape while the decision goes undefended reports the wrong thing with
confidence.
**Risks:** An annotation syntax is a second grammar in the tree, and nothing outside this
repository reads it. [`skills/`][] ships to users whose checkout has no `docs/adr/` at
all.

## Decision

Document the convention and fix the format. Do not mechanise the convention.

Option 3 loses on what it cannot see. The rule worth enforcing is that a citation
defending an archived decision sits where a breach is *authored*, not where it fails. That
distinction lives in the reader's path through the code, not in the citation's syntax. A
check that passed all 54 existing references while most of them sit in error strings
would be worse than no check. It would report a defended corpus, and people would believe
it.

**On deferring the liveness check.** A narrower relative of Option 3 would assert that an
`Archived` ADR whose defence names a comment still has one. This ADR postpones that check
and does not reject it. The reason is not that the check is untestable. This repository
tests by fixture, and an `Archived` ADR with a citation present and absent is a fixture
like any other. The check waits because nobody can write its predicate down yet. "A
citation exists" needs a pattern to match, and until this ADR the tree held two patterns.
The first real archival defence will settle whether the check should count comments,
weigh their location, or refuse to guess. Fixing the format now makes the check writable
later. What the deferral gains is a specification, not saved effort.

`--for` (ADR 013) already covers part of the gap, and that coverage makes the deferral
affordable, not merely cheap. A refactor that deletes a citation must stage the file that
held it, and the pre-commit hook reports every decision whose `scope` names a staged path,
`Archived` ones included. The coverage is partial, because hooks are opt-in per clone. But
the failure mode is watched, not unwatched.

## Consequences

- One format. Comments and docstrings use `ADR 007`, because there the citation is prose a
  reader meets in passing. Error messages keep the `docs/adr/007` path form, because there
  the reader is stopped and needs somewhere to go.
- The "never restate the reasoning" rule binds comments and docstrings, not error
  messages. Someone already blocked reads an error, and a clause of *why* is what makes the
  error actionable. The drift risk is worth carrying there.
- A citation in `skills/` ships to users with no `docs/adr/` to open, so it must be useful
  on its own when its pointer leads nowhere. In anything published, prefer naming the
  constraint over the number.
- Archiving on a comment defence now costs more than a status change. The comments go in
  the same change, `archived-because` names where they are, and the archiver decides
  whether the liveness check is due. The skill says so at the point of archiving, because a
  `revisit-when` nobody reads is a note, not a trigger.
- Until an ADR is archived on a comment defence, a deleted citation costs discoverability,
  not a defence. If nobody ever uses `Archived`, that state is permanent and harmless.

[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`AGENTS.md`]: ../../AGENTS.md
[`frontmatter.py`]: ../../scripts/frontmatter.py
[`release_notes.py`]: ../../scripts/ci/release_notes.py
[`skills/`]: ../../skills/
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
[`versions.py`]: ../../scripts/ci/versions.py
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
