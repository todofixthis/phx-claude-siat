---
status: Accepted
date: 2026-08-30
scope: [.agents/rules/, docs/adr/, scripts/adr/, skills/writing-adrs/]
summary: Do not generate path-scoped rule files from ADR frontmatter at any granularity; a hand-written rule stating a constraint stays welcome, and INDEX.md with the `--for` lookup remains how a path reaches the decisions binding it.
revisit-when: A harness loads a path-scoped rule on the creation of a matching file or on a shell read, so what a rule reaches stops depending on how a session happens to read; or the mandated index read is measured and found not to be happening.
---

# 019: Do not generate path-scoped rules from ADR frontmatter

## Context

[ADR 018][] admitted a path-scoped rule as an archival defence and rejected generating one
per decision as such a defence. A different proposal followed: have [`generate_index.py`][]
also write rule files keyed to `scope`, so the decisions binding a file arrive when an agent
reads it. That is delivery of the index rather than a defence, and it answers a failure
[`AGENTS.md`][] already documents — `scope` entries are exact paths and prefixes, and a
reader treating them as literal paths misses most of what binds a file, with nothing to say
so.

The mechanism was measured before the proposal was judged, 018 having recorded one of its
behaviours wrong. A rule nested a directory deep loads. Several matching rules load
together, in one block. A rule loads **once per session, at the first read matching its
globs**, and not again — not on a later read of the same file, nor of another file
matching the same globs — while a rule matched only by a later read arrives then. Each
subagent is its own session, inheriting no load from whoever dispatched it. So 018's
Option 4 risk, that "every matching read pulls in prose nobody wrote", overstates the
cost: it is once per rule, per session. What does not load is unchanged from 018 — the
`Write` creating a matching file, and any read from a shell.

Everything the proposal needs therefore works.

## Options

### Option 1: Do nothing (Accepted)

[`INDEX.md`][] read as `AGENTS.md` requires, the `--for` lookup from a path, and a
hand-written rule where an area earns one, as [`testing.md`][] does today for [ADR 016][].

A programme of such rules covering every scoped area is the same approach at another scale:
prose per area with nothing forcing it to keep up, and partial coverage indistinguishable
from finished coverage.

**Pros:** One representation of a decision's row, and an instruction to read it that reaches
every contributor by every tool.
**Cons:** The prefix-matching error `AGENTS.md` warns about stays the reader's to avoid
unaided. `--for` runs over staged paths, so the one route that fires unasked arrives after
the work is authored — the timing the skill rejects when the same shape is offered as an
archival defence — and its silence is ambiguous, meaning equally that nothing binds, that
the hook was never installed, or that the generator failed into `|| exit 0`.
**Risks:** The route rests on an instruction being followed, and nothing reports the reader
who does not.

### Option 2: Generate rules from ADR frontmatter

The generator writes rule files whose `paths` come from `scope`. Two things vary — how
finely they are keyed, and what they carry:

- **Per distinct `scope` entry, carrying the decisions that name it** — exact. Matching
  rules load together, so a read of `scripts/adr/generate_index.py` receives the `scripts/`
  rule and the `scripts/adr/` rule both, leaving nothing to match by hand. Twenty-two files
  here, and an unmatched rule loads nothing, so their number is hygiene rather than a
  reader's cost.
- **Per top-level directory** — bounded by the tree rather than the corpus, seven to nine
  files here, but unable to tell `scripts/adr/` from `scripts/ci/`. Complete, it carries
  the ten decisions naming anything beneath `scripts/`; incomplete, it is silently partial.
- **One file covering every bound path** — `INDEX.md` with a trigger attached.
- **Any of those carrying no rows** — globs from `scope`, and a body saying only to run the
  lookup and read the index.

**Pros:** Keyed exactly, it does the prefix matching `AGENTS.md` warns about mechanically,
which is the failure that prompted the proposal, and hands it over while the author is
reading rather than once they stage.
**Cons:** Every row-carrying form answers "which decisions bind this file", and an agent
holding that answer has reason to treat the index read as discharged — where `AGENTS.md`
asks for it to answer a different question.
**Risks:** `.agents/rules/` becomes half authored and half generated, and a hand edit to a
generated file is regenerated away without a word.

## Decision

Do nothing.

The measurements clear Option 2 of the objections easiest to make, and the exact form works.
Matching rules compose, so it hands an author every decision naming the path in front of
them with no matching left to do — mechanically retiring a failure `AGENTS.md` documents and
`--for` can only report once paths are staged. On delivering what binds a file it beats the
accepted option, and nothing below pretends otherwise.

What it does not deliver is what the mandated read is for. `AGENTS.md` requires reading
`INDEX.md` before proposing architectural or tooling changes, so that a settled decision is
not relitigated; that is a question about the corpus, and a rule keyed to the file in hand
answers the narrower one of what binds it. An agent holding the narrow answer has every
reason to treat the broad instruction as discharged, and nothing in the session tells the
two apart. That is the displacement — not that the generated route says less about this
file, since exactly keyed it says more, but that it looks like the answer to a question it
was never asked.

The mandated read is not reliable, and this ADR says so three times over. It is, though, the
only route that reaches every reader by every tool, which no rule does. Declining that trade
turns on the failure modes not overlapping: a reader who skips the index knows they skipped
it, where a reader served a rule cannot tell they were served anything less than everything.

The row-free variant escapes all of that — a rule saying only "run the lookup, read the
index" cannot be mistaken for an answer — and it is declined on a smaller ground. What it
carries already sits in `AGENTS.md`, which is in context from the start, so it buys salience
at the price of another generated artefact to keep matched to `scope`. If salience turns out
to be what was missing, that is the variant to reach for, and the one this decision would
give up first.

## Consequences

- `.agents/rules/` stays authored, and a rule added there is still welcome; what this
  forbids is the generated kind, not the directory.
- Scoping `skills/writing-adrs/` and `.agents/rules/` means an edit to the skill's rule
  section, or to a rules file, reports this decision alongside those already binding them;
  `scripts/adr/` is scoped for the generator that would write them.
- 018 keeps its status and gains a Consequences bullet pointing here, its Option 4 con —
  that a `summary` says what was decided rather than what to do — standing untouched, the
  bar there being a defence rather than delivery.
- That is a kind of edit to a settled ADR [`writing-adrs`][] does not name: correcting a
  premise a later measurement falsified, leaving the reasoning and the status alone. Like
  the workflows it does name, it strikes the premise in 018's body, that being where a
  reader of 018 meets it.
- A repository without the `.claude/rules` symlink 018 found load-bearing has no version of
  this proposal to weigh at all, nothing there loading a rule.

[ADR 016]: 016-anchor-every-default-path-to-the-module.md
[ADR 018]: 018-admit-a-path-scoped-rule-as-an-archival-defence.md
[`AGENTS.md`]: ../../AGENTS.md
[`generate_index.py`]: ../../scripts/adr/generate_index.py
[`INDEX.md`]: INDEX.md
[`testing.md`]: ../../.agents/rules/testing.md
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
