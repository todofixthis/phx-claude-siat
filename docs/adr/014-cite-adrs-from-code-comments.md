---
status: Accepted
date: 2026-08-10
scope: [.agents/, .githooks/, AGENTS.md, docs/, scripts/, skills/]
summary: Cite ADRs from comments and docstrings as a documented convention — the number and what the decision forbids at that line, never the reasoning — fixing the citation format now, and deferring a check that citations survive until an archival defence first depends on one.
revisit-when: An ADR is archived on a defence that rests on a comment in code.
---

# 014: Cite ADRs from code comments

## Context

Code here already cites ADRs, and far more widely than the practice's undocumented status
suggests: 54 references across eleven files outside `docs/adr/`, including
[`validate_manifests.py`][], [`generate_index.py`][], [`versions.py`][],
[`frontmatter.py`][], [`release_notes.py`][] and four test modules. Nothing records this as
a convention, so two things were settled by whoever wrote each one. The citation *format*
split — `ADR 007` appears 33 times and `docs/adr/007` 21 — and so did what a citation
carries, which ranges from a bare number to a sentence of reasoning.

Where a citation *sits* turns out to matter more than either. [`writing-adrs`][] lets an
ADR be `Archived` — kept in force but dropped from the index an agent loads — when a
defence exists that a breacher meets **while the work is still being planned**, and names
a comment as one of only two qualifying defences. Judged by that timing test, many of the
existing citations would not qualify: 10 of the 20 in `validate_manifests.py` sit inside
error strings, which a breacher meets when a check fails, after the wrong work is already
built. A comment in the code someone is reading qualifies; the same words in a failure
message do not.

That leaves a decision to record before more code is written against it, and a second
question underneath it. A comment goes stale when its ADR is superseded, and vanishes when
the code carrying it is refactored away. The second is the one that bites: an `Archived`
ADR is invisible by design, so nothing reports that its defence has gone. No ADR is
`Archived` today, so nothing yet depends on one.

## Options

Options 2 and 3 both leave the 54 existing citations standing and both settle the format
split; neither is distinguished by that. What separates them is whether the convention's
authority is prose that an author follows or a schema that a check enforces.

### Option 1: Do nothing

Citations continue as an undocumented habit.

**Pros:** Nothing to write, and the habit has produced usable comments for eleven files
without guidance.
**Cons:** Both splits widen — two formats and no agreed content — and the timing point
above stays unstated at exactly the moment decisions become archivable on it.
**Risks:** A comment that restates an ADR's reasoning drifts from it, and the reader who
finds the drift cannot tell which of the two is current.

### Option 2: A documented convention, enforced by review (Accepted)

`writing-adrs` states what a citation carries and where it must sit to count as a defence;
[`AGENTS.md`][] fixes this repo's citation format and points code authors at both. Nothing
checks either.

**Pros:** Reaches the author at the moment of writing, which is the only point the
convention applies, and can express the part no check could — that a citation's *location*
is what makes it a defence.
**Cons:** Rests on authors and reviewers, so a citation deleted in a refactor goes
unreported.
**Risks:** Documented and unchecked is how `tags` decayed ([ADR 013][]).

### Option 3: A checked citation schema

Make the citation a machine-readable annotation — a fixed marker CI parses — and enforce
shape, resolvable number, and non-superseded target on every pull request.

**Pros:** The format cannot split again, a typo'd number fails the build, and the corpus
stays inspectable as data rather than prose.
**Cons:** Buys the cheap half. What matters for an archival defence is whether a citation
sits where the work is planned, and no parser can judge that; a schema that validates
shape while the decision goes undefended is a check that reports the wrong thing
confidently.
**Risks:** An annotation syntax is a second grammar in the tree, and one nothing outside
this repo reads — [`skills/`][] ships to users whose checkout has no `docs/adr/` at all.

## Decision

Document the convention and fix the format; do not mechanise it.

Option 3 loses on what it cannot see. The rule worth enforcing is that a citation defending
an archived decision sits where a breach is *authored* rather than where it fails, and that
distinction lives in the reader's path through the code, not in the citation's syntax. A
check that passed on all 54 existing references while most of them sit in error strings
would be worse than no check — it would report a defended corpus and be believed.

**On deferring the liveness check.** Option 3's narrower cousin — assert that an `Archived`
ADR whose defence names a comment still has one — is not rejected, only postponed, and not
because it is untestable: this repo tests by fixture, and an `Archived` ADR with a citation
present and absent is a fixture like any other. It is postponed because its predicate
cannot yet be written down. "A citation exists" needs a pattern to match, and until this
ADR the tree held two; the first real archival defence is what settles whether the check
should count comments, weigh their location, or refuse to guess. Fixing the format now is
what makes that check writable later — the deferral buys specification, not effort.

`--for` (ADR 013) already covers part of the gap and is why the deferral is affordable
rather than merely cheap: a refactor deleting a citation must stage the file holding it, and
the pre-commit hook reports every decision whose `scope` names a staged path, `Archived`
ones included. It is partial — hooks are opt-in per clone — but it means the failure mode
is watched, not unwatched.

## Consequences

- One format: `ADR 007` in comments and docstrings, where the citation is prose a reader
  meets in passing. The `docs/adr/007` path form stays in error messages, where the reader
  is stopped and needs somewhere to go.
- The "never restate the reasoning" rule binds comments and docstrings, not error
  messages. An error is read by someone already blocked, and a clause of *why* is what
  makes it actionable — the drift risk is worth carrying there.
- A citation in `skills/` ships to users with no `docs/adr/` to open, so it must carry
  enough on its own to be useful as a dead pointer. Prefer naming the constraint over the
  number in anything published.
- Archiving on a comment defence now costs more than a status flip: the comments go in the
  same change, `archived-because` names where, and the archiver decides whether the
  liveness check is due. The skill says so at the point of archiving, because a
  `revisit-when` nobody reads is a note, not a trigger.
- Until an ADR is archived on a comment defence, a deleted citation costs discoverability
  rather than a defence. If `Archived` is never used, that state is permanent and harmless.

[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[`AGENTS.md`]: ../../AGENTS.md
[`frontmatter.py`]: ../../scripts/frontmatter.py
[`generate_index.py`]: ../../scripts/adr/generate_index.py
[`release_notes.py`]: ../../scripts/ci/release_notes.py
[`skills/`]: ../../skills/
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
[`versions.py`]: ../../scripts/ci/versions.py
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
