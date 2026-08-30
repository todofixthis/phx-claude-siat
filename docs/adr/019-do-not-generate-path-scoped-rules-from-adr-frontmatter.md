---
status: Accepted
date: 2026-08-30
scope: [.agents/rules/, docs/adr/, scripts/adr/, skills/writing-adrs/]
summary: Do not generate path-scoped rule files from ADR frontmatter at any granularity; a hand-written rule stating a constraint stays welcome, and INDEX.md with the `--for` lookup remains how a path reaches the decisions binding it.
revisit-when: A harness loads a path-scoped rule on the creation of a matching file or on a shell read, so what a rule reaches stops depending on how a session happens to read; or the mandated index read is found not to be happening, leaving no complete route for a generated one to displace.
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

The mechanism was measured before the proposal was judged, 018 having recorded one of these
wrong. A rule nested a directory deep loads. Several matching rules load together, in one
block. A rule loads **once per session, at the first read matching its globs**, and not
again — not on a later read of the same file, nor of another file matching the same globs —
while a rule matched only by a later read arrives then. Each subagent is its own session,
inheriting no load from whoever dispatched it. So 018's Option 4 risk, that "every matching
read pulls in prose nobody wrote", overstates the cost: it is once per rule, per session.
What does not load is unchanged from 018 — the `Write` creating a matching file, and any
read from a shell.

Everything the proposal needs therefore works.

## Options

### Option 1: Do nothing (Accepted)

[`INDEX.md`][] read as `AGENTS.md` requires, the `--for` lookup from a path, and a
hand-written rule where an area earns one, as [`testing.md`][] does today for [ADR 016][].

Extending those hand-written rules to every scoped area, as a programme rather than one
area at a time, is the same approach at a different scale: prose per area with nothing
forcing it to keep up, and partial coverage indistinguishable from finished coverage. It is
not a separate option, and one area at a time is what this one already is.

**Pros:** One representation of a decision's row, and an instruction to read it that holds
whatever the tooling does.
**Cons:** The prefix-matching error `AGENTS.md` warns about stays the reader's to avoid
unaided. `--for` runs over staged paths, so the one reverse route that fires unasked arrives
after the work is authored — the timing the skill rejects when the same shape is offered as
an archival defence — and its silence is ambiguous, meaning equally that nothing binds, that
the hook was never installed, or that the generator failed into `|| exit 0`.
**Risks:** The whole route rests on an instruction being followed, and nothing reports the
reader who does not.

### Option 2: Generate rules from ADR frontmatter

The generator writes rule files whose `paths` cover scoped paths and whose bodies list the
decisions binding them. Granularity trades precision against the shape of the tree, and
neither end escapes both:

- **Per distinct `scope` entry** — exact, and the most files: the eighteen decisions in
  force here name twenty-two entries between them. File count is hygiene rather than a
  reader's cost, since an unmatched rule loads nothing, so this end is the precise one.
- **Per top-level directory** — bounded by the repository rather than by the corpus, about
  eight files here, but it cannot tell `scripts/adr/` from `scripts/ci/`. Complete, it
  carries every decision naming anything beneath the directory — ten of the eighteen, for
  `scripts/`. Incomplete, it is silently partial.
- **One file covering every bound path** — one file, every row on a touch of anything, which
  is `INDEX.md` with a trigger attached.

**Pros:** The decisions binding a file arrive while it is being read, before the work is
authored, which `--for` cannot reach anyone in time to do. Prefixes become globs
mechanically, retiring a translation 018 books as a cost on the author.
**Cons:** An automatic partial route displaces a mandated complete one.
**Risks:** `.agents/rules/` becomes half authored and half generated, and a hand edit to a
generated file is regenerated away without a word.

## Decision

Do nothing.

The measurements clear Option 2 of the objections easiest to make. The layout works, and an
unmatched rule loads nothing, so file count is a question of repository hygiene rather than
of a reader's context. On delivery Option 2 beats the accepted option outright: it reaches
an author while they are reading, where `--for` reaches them only once they stage.

What decides it is displacement, and the thing displaced is an instruction rather than a
habit. `AGENTS.md` requires reading `INDEX.md` and working out from its Scope column which
decisions cover the files being changed. An agent handed the decisions naming the path in
front of it has been given every reason to treat that instruction as already discharged, and
no way to tell from inside the session whether what it holds is everything, part, or — in a
session that read from a shell — nothing at all. [ADR 014][] turned down a check on that
shape: one reporting a defended corpus is worse than none, being believed.

The obvious repair is a line in each generated file saying it may be incomplete and the
lookup should still be run. That is the strongest form of the option, and it splits on the
granularity above rather than surviving it. Made exact, the file is complete for the paths
it names and the disclaimer carries the rest, so what is delivered is the index read it was
meant to save. Made bounded, the file cannot be both complete and precise: ten decisions of
eighteen on a touch of anything under `scripts/`, or fewer and quietly so. Either way the
mandated read is still owed, and the thing that made the mechanism attractive was that it
would not be.

That `--for` arrives late is the honest price of the accepted option, and it is not the same
failure, because `--for` is not what Option 1 rests on. The unconditional route is the
instruction to read the index, which depends on no hook firing and no glob matching. The
hook is an aid on top of it; the generated rule would be an aid that erodes it.

## Consequences

- `.agents/rules/` stays authored, and a rule added there is still welcome; what this
  forbids is the generated kind, not the directory.
- Scoping `skills/writing-adrs/` and `.agents/rules/` means an edit to the skill's rule
  section, or to a rules file, reports this decision alongside those already binding them.
  Both are where the guidance to generate these would be written.
- 018 keeps its status and gains a Consequences bullet pointing here, its Option 4 con —
  that a `summary` says what was decided rather than what to do — standing untouched, the
  bar there being a defence rather than delivery.
- That is a kind of edit to a settled ADR [`writing-adrs`][] does not name: correcting a
  premise a later measurement falsified, leaving the reasoning and the status alone. Like
  the workflows it does name, it marks the body where the premise is set out and not only
  the frontmatter, the body being what a reader of that ADR meets.
- Every delivery claim above rests on the `.claude/rules` symlink 018 found load-bearing.
  Without it nothing loads, so a repository laid out differently has no version of this
  proposal to weigh.

[ADR 014]: 014-cite-adrs-from-code-comments.md
[ADR 016]: 016-anchor-every-default-path-to-the-module.md
[ADR 018]: 018-admit-a-path-scoped-rule-as-an-archival-defence.md
[`AGENTS.md`]: ../../AGENTS.md
[`generate_index.py`]: ../../scripts/adr/generate_index.py
[`INDEX.md`]: INDEX.md
[`testing.md`]: ../../.agents/rules/testing.md
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
